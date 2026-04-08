"""
Bull Put Credit Spread calculator.

Terminology:
  Short Put  = the higher-strike put you SELL (collect premium)
  Long Put   = the lower-strike put you BUY  (pay premium)
  Net Credit = Short Put premium - Long Put premium
  Spread Width = Short Strike - Long Strike
  Max Loss   = (Spread Width - Net Credit) × 100 per contract
"""

import math
from scipy.stats import norm


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float):
    """Return (d1, d2) from Black-Scholes."""
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def put_delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes delta for a European put (always negative)."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return float(norm.cdf(d1) - 1)


def prob_of_assignment(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Risk-neutral probability that the stock finishes below K at expiration
    (i.e., probability of assignment for a short put).
    = N(-d2)
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    _, d2 = _d1_d2(S, K, T, r, sigma)
    return float(norm.cdf(-d2))


def build_spread(
    ticker: str,
    category: str,
    current_price: float,
    short_strike: float,
    long_strike: float,
    short_mid: float,   # mid-price of the short (sell) put
    long_mid: float,    # mid-price of the long  (buy) put
    iv: float,          # implied volatility of the short put (annualised, e.g. 0.35)
    dte: int,
    expiration: str,
    r: float = 0.052,
) -> dict | None:
    """
    Compute every metric required for the SpreadHunter table.
    Returns None if the spread is not valid / profitable.
    """
    net_credit = round(short_mid - long_mid, 2)
    spread_width = round(short_strike - long_strike, 2)

    if net_credit <= 0 or spread_width <= 0:
        return None

    max_loss_per_contract = round((spread_width - net_credit) * 100, 2)
    if max_loss_per_contract <= 0:
        return None

    T = dte / 365.0

    delta = round(put_delta(current_price, short_strike, T, r, iv), 4)
    prob_assign = round(prob_of_assignment(current_price, short_strike, T, r, iv) * 100, 2)

    return_on_risk = round(net_credit / (spread_width - net_credit) * 100, 2)
    distance_from_danger = round((current_price - short_strike) / current_price * 100, 2)
    total_profit = round(net_credit * 100, 2)  # per contract (100 shares)

    # Broken Nose Ratio — proprietary metric:
    # Net credit collected per percentage-point of assignment probability.
    # Measures how efficiently you are being compensated for the risk of assignment.
    # Higher = better trade.
    broken_nose_ratio = round(net_credit / (prob_assign / 100), 2) if prob_assign > 0 else 0.0

    return {
        "ticker": ticker,
        "category": category,
        "expiration": expiration,
        "dte": dte,
        "current_price": round(current_price, 2),
        # Core spread legs
        "short_strike": short_strike,           # sell put strike
        "long_strike": long_strike,             # buy put strike
        "short_put_premium": round(short_mid, 2),
        "long_put_premium": round(long_mid, 2),
        # Greeks / probability
        "delta": delta,
        "prob_assignment": prob_assign,         # %
        "iv": round(iv * 100, 1),              # %
        # P&L metrics
        "net_credit": net_credit,               # $
        "max_loss_per_contract": max_loss_per_contract,  # $
        "return_on_risk": return_on_risk,       # %
        "broken_nose_ratio": broken_nose_ratio,
        "distance_from_danger": distance_from_danger,   # %
        "total_profit": total_profit,           # $ per contract
    }
