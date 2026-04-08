"""
Data service: fetches live option chain snapshots from Massive.com
using the official `massive` Python SDK.  Falls back to Yahoo Finance
(yfinance) if the API call fails or returns no data.

Massive.com SDK docs mirror the Polygon.io client interface.
Key call:
    client.list_snapshot_options_chain(ticker, params={...})
Returns an iterator of OptionContractSnapshot objects with fields:
    .details.strike_price, .details.expiration_date
    .greeks.delta / .greeks.gamma / .greeks.theta / .greeks.vega
    .implied_volatility
    .last_quote.bid  / .last_quote.ask  / .last_quote.midpoint
    .underlying_asset.price  (current stock price)
    .open_interest
"""

import asyncio
import logging
from datetime import date, datetime, timedelta

import yfinance as yf
from massive import RESTClient

from calculator import build_spread
from config import MASSIVE_API_KEY, MIN_DTE, MAX_DTE, RISK_FREE_RATE
from tickers import TICKER_CATEGORIES

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Massive.com — primary data source
# ─────────────────────────────────────────────────────────────────────────────

def _scan_ticker_massive(ticker: str) -> list[dict]:
    """
    Fetch the full OTM put chain snapshot for `ticker` from Massive.com,
    then construct every valid bull put credit spread.
    """
    spreads: list[dict] = []
    category = TICKER_CATEGORIES.get(ticker, "Stock")
    today = date.today()
    min_exp = (today + timedelta(days=MIN_DTE)).strftime("%Y-%m-%d")
    max_exp = (today + timedelta(days=MAX_DTE)).strftime("%Y-%m-%d")

    try:
        client = RESTClient(MASSIVE_API_KEY)
        chain = list(
            client.list_snapshot_options_chain(
                ticker,
                params={
                    "expiration_date.gte": min_exp,
                    "expiration_date.lte": max_exp,
                    "contract_type": "put",
                    "limit": 250,
                },
            )
        )
    except Exception as e:
        logger.warning(f"Massive.com API error for {ticker}: {e}")
        return spreads

    if not chain:
        logger.debug(f"No options data returned for {ticker}")
        return spreads

    # ── Current underlying price ───────────────────────────────────────────
    current_price: float | None = None
    for snap in chain:
        if snap.underlying_asset and snap.underlying_asset.price:
            current_price = float(snap.underlying_asset.price)
            break

    if not current_price:
        logger.warning(f"Could not determine price for {ticker}")
        return spreads

    # ── Group puts by expiration ───────────────────────────────────────────
    by_exp: dict[str, list] = {}
    for snap in chain:
        if not snap.details or not snap.last_quote:
            continue
        exp = snap.details.expiration_date
        if not exp:
            continue
        try:
            dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
        except ValueError:
            continue
        if not (MIN_DTE <= dte <= MAX_DTE):
            continue
        by_exp.setdefault(exp, []).append(snap)

    # ── Build spreads ──────────────────────────────────────────────────────
    for exp, opts in by_exp.items():
        dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days

        # Sort highest strike first (most ITM → most OTM)
        opts.sort(key=lambda o: o.details.strike_price or 0, reverse=True)

        for snap in opts:
            short_strike = float(snap.details.strike_price or 0)
            if not short_strike or short_strike >= current_price:
                continue

            distance_pct = (current_price - short_strike) / current_price * 100
            if not (2.0 <= distance_pct <= 20.0):
                continue

            iv = float(snap.implied_volatility or 0)
            if iv <= 0:
                continue

            # Prefer SDK midpoint; fallback to (bid+ask)/2
            q = snap.last_quote
            if q and q.midpoint:
                short_mid = float(q.midpoint)
            elif q and q.bid is not None and q.ask is not None:
                short_mid = (float(q.bid) + float(q.ask)) / 2
            else:
                continue

            if short_mid < 0.05:
                continue

            # API-provided delta (negative for puts)
            api_delta = float(snap.greeks.delta) if snap.greeks and snap.greeks.delta is not None else None

            # Try different spread widths
            for width in [2.5, 5.0, 10.0]:
                long_target = short_strike - width
                long_candidates = [
                    o for o in opts
                    if o.details.strike_price is not None
                    and abs(float(o.details.strike_price) - long_target) <= 1.0
                    and float(o.details.strike_price) < short_strike
                ]
                if not long_candidates:
                    continue

                lo = long_candidates[0]
                lq = lo.last_quote
                if not lq:
                    continue
                if lq.midpoint:
                    long_mid = float(lq.midpoint)
                elif lq.bid is not None and lq.ask is not None:
                    long_mid = (float(lq.bid) + float(lq.ask)) / 2
                else:
                    continue
                if long_mid <= 0:
                    continue

                spread = build_spread(
                    ticker=ticker,
                    category=category,
                    current_price=current_price,
                    short_strike=short_strike,
                    long_strike=float(lo.details.strike_price),
                    short_mid=short_mid,
                    long_mid=long_mid,
                    iv=iv,
                    dte=dte,
                    expiration=exp,
                    r=RISK_FREE_RATE,
                )

                if spread is None or spread["return_on_risk"] < 10:
                    continue

                # Use live API Greeks when available (more accurate than BS)
                if api_delta is not None:
                    spread["delta"] = round(api_delta, 4)
                if snap.greeks and snap.greeks.theta is not None:
                    spread["theta"] = round(float(snap.greeks.theta), 4)

                spreads.append(spread)

    logger.info(f"Massive.com: {ticker} → {len(spreads)} spreads")
    return spreads


# ─────────────────────────────────────────────────────────────────────────────
# Yahoo Finance — fallback
# ─────────────────────────────────────────────────────────────────────────────

def _scan_ticker_yfinance(ticker: str) -> list[dict]:
    """Fallback: build spreads from yfinance option chains."""
    spreads: list[dict] = []
    category = TICKER_CATEGORIES.get(ticker, "Stock")

    try:
        yft = yf.Ticker(ticker)
        current_price = float(yft.fast_info.last_price or 0)
        if current_price <= 0:
            return spreads

        today = date.today()
        valid_exps = [
            exp for exp in (yft.options or [])
            if MIN_DTE <= (datetime.strptime(exp, "%Y-%m-%d").date() - today).days <= MAX_DTE
        ]

        for exp in valid_exps:
            dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
            try:
                chain = yft.option_chain(exp)
                puts = chain.puts
            except Exception:
                continue

            if puts is None or puts.empty:
                continue

            otm = puts[
                (puts["strike"] < current_price) &
                (puts["bid"] > 0) &
                (puts["ask"] > 0)
            ].sort_values("strike", ascending=False)

            for _, short_row in otm.iterrows():
                short_strike = float(short_row["strike"])
                dist = (current_price - short_strike) / current_price * 100
                if not (2.0 <= dist <= 20.0):
                    continue

                iv = float(short_row.get("impliedVolatility") or 0)
                if iv <= 0:
                    continue

                short_mid = (float(short_row["bid"]) + float(short_row["ask"])) / 2
                if short_mid < 0.05:
                    continue

                for width in [2.5, 5.0, 10.0]:
                    long_target = short_strike - width
                    long_rows = otm[abs(otm["strike"] - long_target) <= 1.0]
                    if long_rows.empty:
                        continue

                    long_row = long_rows.iloc[0]
                    long_mid = (float(long_row["bid"]) + float(long_row["ask"])) / 2
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


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def _scan_ticker(ticker: str) -> list[dict]:
    """Try Massive.com first; fall back to yfinance if no data returned."""
    result = _scan_ticker_massive(ticker)
    if result:
        return result
    logger.info(f"Falling back to yfinance for {ticker}")
    return _scan_ticker_yfinance(ticker)


async def scan_all(tickers: list[str]) -> list[dict]:
    """Scan all tickers concurrently (batched) and return sorted spreads."""
    all_spreads: list[dict] = []
    batch_size = 8

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        results = await asyncio.gather(
            *[asyncio.to_thread(_scan_ticker, t) for t in batch],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, list):
                all_spreads.extend(r)

    all_spreads.sort(key=lambda x: x["return_on_risk"], reverse=True)
    return all_spreads
