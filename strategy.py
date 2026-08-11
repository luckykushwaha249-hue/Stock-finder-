"""
Strategy Logic — Quarterly Result Support-Resistance Pattern
==============================================================
Q1 (purana) -> Q2 (beech wala) -> Q3 (recent/upcoming, jiske liye prediction)

Rules:
1. Q1 result din ka high mark karo.
2. Uske baad stock correct hoke ek support level banaye.
3. Q2 result ke time stock Q1 ke high ke approx (tolerance %) tak wapas jaye.
   - Result achha (positive) hona chahiye.
4. Q2 ke baad jab stock support ke paas aaye -> BUY signal.
   - Target = Q1 & Q2 result din ka high (jo approx barabar hai).
5. Result ke baad 2-3 din stock tezi se girna nahi chahiye (negative reaction filter).
6. Q1 aur Q2 dono result positive/achhe hone chahiye.
"""

import pandas as pd
from dataclasses import dataclass

from config import (
    SUPPORT_TOLERANCE_PCT,
    HIGH_MATCH_TOLERANCE_PCT,
    POST_RESULT_WATCH_DAYS,
    POST_RESULT_MAX_FALL_PCT,
)


@dataclass
class ScreenResult:
    symbol: str
    source: str
    matched: bool
    reason: str
    q1_date: str = ""
    q2_date: str = ""
    q1_high: float = 0.0
    q2_high: float = 0.0
    support_level: float = 0.0
    current_price: float = 0.0
    target_price: float = 0.0
    upside_pct: float = 0.0


def _high_around_date(df: pd.DataFrame, date: pd.Timestamp, window_days: int = 2) -> float | None:
    """Highest 'high' price within +/- window_days of the given date (handles weekends/holidays)."""
    mask = (df["date"] >= date - pd.Timedelta(days=window_days)) & \
           (df["date"] <= date + pd.Timedelta(days=window_days))
    sub = df.loc[mask]
    if sub.empty:
        return None
    return float(sub["high"].max())


def _post_result_reaction_ok(df: pd.DataFrame, result_date: pd.Timestamp) -> bool:
    """Check stock doesn't crash >POST_RESULT_MAX_FALL_PCT% in POST_RESULT_WATCH_DAYS after result."""
    before = df.loc[df["date"] <= result_date]
    after = df.loc[df["date"] > result_date].head(POST_RESULT_WATCH_DAYS)
    if before.empty or after.empty:
        return True  # not enough data to judge -> don't reject
    base_close = float(before.iloc[-1]["close"])
    min_after = float(after["low"].min())
    fall_pct = (min_after - base_close) / base_close * 100
    return fall_pct > POST_RESULT_MAX_FALL_PCT


def _find_support_after_q1(df: pd.DataFrame, q1_date: pd.Timestamp, q2_date: pd.Timestamp) -> float | None:
    """
    Support = lowest low in the correction phase between Q1 result and Q2 result
    (i.e. after the post-Q1 rally/correction, before Q2 run-up begins).
    Simplified: take the lowest low in the middle 60% of the Q1->Q2 window,
    to avoid picking the immediate result-day spike/dip.
    """
    window = df.loc[(df["date"] > q1_date) & (df["date"] < q2_date)]
    if window.empty or len(window) < 5:
        return None
    n = len(window)
    start = int(n * 0.2)
    end = int(n * 0.8)
    mid = window.iloc[start:end]
    if mid.empty:
        mid = window
    return float(mid["low"].min())


def evaluate_stock(symbol: str, df: pd.DataFrame, source: str,
                    result_dates: list[pd.Timestamp]) -> ScreenResult:
    """
    df: standardized OHLCV DataFrame (date, open, high, low, close, volume), sorted ascending.
    result_dates: [Q1_date, Q2_date, Q3_date_or_None] oldest first, at least Q1 & Q2 required.
    """
    if df is None or df.empty:
        return ScreenResult(symbol, source, False, "No price data")

    if not result_dates or len(result_dates) < 2:
        return ScreenResult(symbol, source, False, "Not enough result dates found")

    q1_date, q2_date = result_dates[0], result_dates[1]
    df = df.sort_values("date").reset_index(drop=True)

    q1_high = _high_around_date(df, q1_date)
    q2_high = _high_around_date(df, q2_date)

    if q1_high is None or q2_high is None:
        return ScreenResult(symbol, source, False, "Missing price data around result dates")

    # Rule: Q1 & Q2 highs should be approx equal (both "achhe result" runs to similar zone)
    high_diff_pct = abs(q2_high - q1_high) / q1_high * 100
    if high_diff_pct > HIGH_MATCH_TOLERANCE_PCT:
        return ScreenResult(
            symbol, source, False,
            f"Q1 high ({q1_high:.1f}) & Q2 high ({q2_high:.1f}) match nahi karte "
            f"(diff {high_diff_pct:.1f}% > {HIGH_MATCH_TOLERANCE_PCT}%)",
            q1_date=str(q1_date.date()), q2_date=str(q2_date.date()),
            q1_high=q1_high, q2_high=q2_high,
        )

    # Rule: no negative crash after Q1 or Q2 result
    if not _post_result_reaction_ok(df, q1_date):
        return ScreenResult(symbol, source, False, "Q1 result ke baad negative reaction (crash)",
                             q1_date=str(q1_date.date()), q2_date=str(q2_date.date()),
                             q1_high=q1_high, q2_high=q2_high)

    if not _post_result_reaction_ok(df, q2_date):
        return ScreenResult(symbol, source, False, "Q2 result ke baad negative reaction (crash)",
                             q1_date=str(q1_date.date()), q2_date=str(q2_date.date()),
                             q1_high=q1_high, q2_high=q2_high)

    # Find support level formed between Q1 and Q2
    support = _find_support_after_q1(df, q1_date, q2_date)
    if support is None:
        return ScreenResult(symbol, source, False, "Support level identify nahi ho payi",
                             q1_date=str(q1_date.date()), q2_date=str(q2_date.date()),
                             q1_high=q1_high, q2_high=q2_high)

    current_price = float(df.iloc[-1]["close"])
    target_price = max(q1_high, q2_high)

    # Rule: current price should be near the support level (buy zone)
    dist_from_support_pct = abs(current_price - support) / support * 100
    near_support = dist_from_support_pct <= SUPPORT_TOLERANCE_PCT

    if not near_support:
        return ScreenResult(
            symbol, source, False,
            f"Abhi support ({support:.1f}) ke paas nahi hai (CMP {current_price:.1f}, "
            f"diff {dist_from_support_pct:.1f}%)",
            q1_date=str(q1_date.date()), q2_date=str(q2_date.date()),
            q1_high=q1_high, q2_high=q2_high, support_level=support,
            current_price=current_price, target_price=target_price,
        )

    upside_pct = (target_price - current_price) / current_price * 100

    return ScreenResult(
        symbol=symbol, source=source, matched=True,
        reason="Buy zone: support ke paas, Q1/Q2 pattern match",
        q1_date=str(q1_date.date()), q2_date=str(q2_date.date()),
        q1_high=q1_high, q2_high=q2_high, support_level=support,
        current_price=current_price, target_price=target_price,
        upside_pct=upside_pct,
    )
