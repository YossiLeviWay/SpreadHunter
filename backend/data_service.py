"""
Data service: fetches option chains from Massive.com API first,
falls back to Yahoo Finance (yfinance) if the primary API is unavailable.
"""

import asyncio
import logging
from datetime import datetime, timedelta, date

import httpx
import yfinance as yf

from config import MASSIVE_API_KEY, MASSIVE_BASE_URL, MIN_DTE, MAX_DTE, RISK_FREE_RATE
from calculator import build_spread
from tickers import TICKER_CATEGORIES

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _dte(exp_str: str) -> int:
    """Days to expiration from today."""
    exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
    return (exp_date - date.today()).days


def _mid(bid: float, ask: float) -> float:
    if bid is None or ask is None or ask <= 0:
        return 0.0
    return round((bid + ask) / 2, 4)


# ─────────────────────────────────────────────
# Massive.com API client
# ─────────────────────────────────────────────

async def _fetch_massive(ticker: str, client: httpx.AsyncClient) -> list[dict] | None:
    """
    Attempt to pull option chain data from the Massive.com REST API.
    Returns a list of spread dicts or None on failure.
    """
    headers = {
        "Authorization": f"Bearer {MASSIVE_API_KEY}",
        "X-API-Key": MASSIVE_API_KEY,
        "Accept": "application/json",
    }

    # Try a few common endpoint patterns
    endpoints = [
        f"{MASSIVE_BASE_URL}/v1/options/chain",
        f"{MASSIVE_BASE_URL}/options/chain",
        f"{MASSIVE_BASE_URL}/v1/options",
    ]

    for url in endpoints:
        try:
            resp = await client.get(
                url,
                params={"symbol": ticker, "option_type": "put"},
                headers=headers,
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"Massive.com success for {ticker} at {url}")
                return _parse_massive_response(ticker, data)
            elif resp.status_code in (401, 403):
                logger.warning(f"Massive.com auth failed ({resp.status_code}) for {ticker}")
                return None  # Don't try other endpoints if auth fails
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.debug(f"Massive.com request error for {ticker} at {url}: {e}")
            continue

    return None


def _parse_massive_response(ticker: str, data: dict) -> list[dict]:
    """
    Parse Massive.com API response into a list of spread candidates.
    Adapt this function once the exact response schema is confirmed.
    """
    spreads = []
    category = TICKER_CATEGORIES.get(ticker, "Stock")

    # Attempt to extract option chain from common response shapes
    options = (
        data.get("options")
        or data.get("chain")
        or data.get("data", {}).get("options")
        or []
    )

    # Group puts by expiration
    puts_by_exp: dict[str, list] = {}
    current_price: float = data.get("underlying_price") or data.get("price") or 0.0

    for opt in options:
        if opt.get("option_type", "").lower() != "put":
            continue
        exp = opt.get("expiration_date") or opt.get("expiry") or ""
        if not exp:
            continue
        try:
            dte = _dte(exp)
        except ValueError:
            continue
        if not (MIN_DTE <= dte <= MAX_DTE):
            continue
        puts_by_exp.setdefault(exp, []).append(opt)

    for exp, puts in puts_by_exp.items():
        dte = _dte(exp)
        puts.sort(key=lambda x: x.get("strike", 0), reverse=True)

        for i, short_opt in enumerate(puts):
            short_strike = float(short_opt.get("strike", 0))
            if not short_strike or short_strike >= current_price:
                continue

            distance_pct = (current_price - short_strike) / current_price * 100
            if not (2.0 <= distance_pct <= 20.0):
                continue

            short_mid = _mid(short_opt.get("bid", 0), short_opt.get("ask", 0))
            iv = float(short_opt.get("implied_volatility") or short_opt.get("iv") or 0)
            if short_mid < 0.05 or iv <= 0:
                continue

            for width in [2.5, 5.0, 10.0]:
                long_target = short_strike - width
                long_candidates = [p for p in puts if abs(float(p.get("strike", 0)) - long_target) <= 1.0]
                if not long_candidates:
                    continue
                long_opt = long_candidates[0]
                long_mid = _mid(long_opt.get("bid", 0), long_opt.get("ask", 0))
                if long_mid <= 0:
                    continue

                spread = build_spread(
                    ticker=ticker,
                    category=category,
                    current_price=current_price,
                    short_strike=short_strike,
                    long_strike=float(long_opt.get("strike", 0)),
                    short_mid=short_mid,
                    long_mid=long_mid,
                    iv=iv,
                    dte=dte,
                    expiration=exp,
                    r=RISK_FREE_RATE,
                )
                if spread and spread["return_on_risk"] >= 10:
                    spreads.append(spread)

    return spreads


# ─────────────────────────────────────────────
# Yahoo Finance fallback
# ─────────────────────────────────────────────

def _fetch_yfinance(ticker: str) -> list[dict]:
    """Fetch and process option chains using yfinance as a fallback."""
    spreads = []
    category = TICKER_CATEGORIES.get(ticker, "Stock")

    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.fast_info
        current_price = float(info.last_price or 0)
        if current_price <= 0:
            logger.warning(f"Could not get price for {ticker}")
            return spreads

        today = date.today()
        valid_exps = [
            exp for exp in (yf_ticker.options or [])
            if MIN_DTE <= (datetime.strptime(exp, "%Y-%m-%d").date() - today).days <= MAX_DTE
        ]

        for exp in valid_exps:
            dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days

            try:
                chain = yf_ticker.option_chain(exp)
                puts = chain.puts
            except Exception as e:
                logger.debug(f"yfinance option_chain failed for {ticker} {exp}: {e}")
                continue

            if puts is None or puts.empty:
                continue

            # Filter: OTM puts with valid bids
            otm = puts[
                (puts["strike"] < current_price) &
                (puts["bid"] > 0) &
                (puts["ask"] > 0)
            ].copy()
            otm = otm.sort_values("strike", ascending=False)

            for _, short_row in otm.iterrows():
                short_strike = float(short_row["strike"])
                distance_pct = (current_price - short_strike) / current_price * 100
                if not (2.0 <= distance_pct <= 20.0):
                    continue

                iv = float(short_row.get("impliedVolatility") or 0)
                if iv <= 0:
                    continue

                short_mid = _mid(float(short_row["bid"]), float(short_row["ask"]))
                if short_mid < 0.05:
                    continue

                for width in [2.5, 5.0, 10.0]:
                    long_target = short_strike - width
                    long_rows = otm[abs(otm["strike"] - long_target) <= 1.0]
                    if long_rows.empty:
                        continue

                    long_row = long_rows.iloc[0]
                    long_mid = _mid(float(long_row["bid"]), float(long_row["ask"]))
                    if long_mid <= 0:
                        continue

                    spread = build_spread(
                        ticker=ticker,
                        category=category,
                        current_price=current_price,
                        short_strike=short_strike,
                        long_strike=float(long_row["strike"]),
                        short_mid=short_mid,
                        long_mid=long_mid,
                        iv=iv,
                        dte=dte,
                        expiration=exp,
                        r=RISK_FREE_RATE,
                    )
                    if spread and spread["return_on_risk"] >= 10:
                        spreads.append(spread)

    except Exception as e:
        logger.error(f"yfinance error for {ticker}: {e}")

    return spreads


# ─────────────────────────────────────────────
# Public API: scan one ticker
# ─────────────────────────────────────────────

async def scan_ticker(ticker: str, client: httpx.AsyncClient) -> list[dict]:
    """Try Massive.com first; fall back to yfinance."""
    result = await _fetch_massive(ticker, client)
    if result is not None:
        return result

    # Fallback: run yfinance in a thread so we don't block the event loop
    return await asyncio.to_thread(_fetch_yfinance, ticker)


# ─────────────────────────────────────────────
# Public API: scan all tickers
# ─────────────────────────────────────────────

async def scan_all(tickers: list[str]) -> list[dict]:
    """Scan all tickers concurrently (batched to be polite to APIs)."""
    all_spreads: list[dict] = []
    batch_size = 8

    async with httpx.AsyncClient() as client:
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i : i + batch_size]
            results = await asyncio.gather(
                *[scan_ticker(t, client) for t in batch],
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, list):
                    all_spreads.extend(r)

    # Best trades first: highest return on risk
    all_spreads.sort(key=lambda x: x["return_on_risk"], reverse=True)
    return all_spreads
