"""
Quarterly Result Dates
=======================
Har stock ke pichhle quarterly result dates chahiye (strategy ke Q1/Q2/Q3 ke liye).
Chain: NSE corporate results API -> Yahoo Finance earnings dates -> None
"""

import requests
import pandas as pd
import yfinance as yf


def get_result_dates_nse(symbol: str, count: int = 4) -> list[pd.Timestamp] | None:
    """NSE 'Financial Results' corporate announcement history."""
    try:
        session = requests.Session()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        session.get("https://www.nseindia.com", headers=headers, timeout=10)

        url = f"https://www.nseindia.com/api/corporate-results?index=equities&symbol={symbol}"
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        dates = []
        for item in data:
            d = item.get("re_broadcast_dt") or item.get("bDate") or item.get("date")
            if d:
                try:
                    dates.append(pd.to_datetime(d, dayfirst=True))
                except Exception:
                    continue

        dates = sorted(set(dates))
        if len(dates) >= 2:
            return dates[-count:]
        return None

    except Exception as e:
        print(f"[NSE results] failed for {symbol}: {e}")
        return None


def get_result_dates_yfinance(symbol: str, count: int = 4) -> list[pd.Timestamp] | None:
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        cal = ticker.get_earnings_dates(limit=count + 4)
        if cal is None or cal.empty:
            return None
        dates = sorted(pd.to_datetime(cal.index).tolist())
        # keep only past dates (already-reported results)
        past = [d for d in dates if d <= pd.Timestamp.today()]
        if len(past) >= 2:
            return past[-count:]
        return None
    except Exception as e:
        print(f"[yfinance earnings] failed for {symbol}: {e}")
        return None


def get_result_dates(symbol: str, count: int = 3) -> list[pd.Timestamp]:
    """
    Returns last `count` quarterly result dates, oldest first.
    e.g. [Q1_date, Q2_date, Q3_date]
    """
    dates = get_result_dates_nse(symbol, count)
    if not dates:
        dates = get_result_dates_yfinance(symbol, count)
    if not dates:
        return []
    return dates
