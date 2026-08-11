"""
Headless Stock Scanner (for scheduled automation, e.g. GitHub Actions)
========================================================================
Same strategy jo app.py mein hai, bas Streamlit UI ke bina.
Result ek CSV/JSON file mein save hote hain -> repo mein commit ho jaate hain
(GitHub Actions workflow ke through), taaki tum kabhi bhi results dekh sako
bina app open kiye.

Run manually:
    python scan.py
    python scan.py --max-stocks 200
"""

import argparse
import json
from datetime import datetime, timezone

import pandas as pd

from nifty500_list import get_nifty500_symbols
from data_sources import get_stock_history
from results_calendar import get_result_dates
from strategy import evaluate_stock


def run_scan(max_stocks: int = 500, sleep_between: float = 0.0) -> list[dict]:
    symbols = get_nifty500_symbols()[:max_stocks]
    total = len(symbols)
    matched = []

    for i, symbol in enumerate(symbols, start=1):
        print(f"[{i}/{total}] Scanning {symbol}...")
        try:
            df, source = get_stock_history(symbol, days=400, sleep_between=sleep_between)
            if df is None:
                continue

            result_dates = get_result_dates(symbol, count=3)
            res = evaluate_stock(symbol, df, source, result_dates)

            if res.matched:
                matched.append({
                    "symbol": res.symbol,
                    "source": res.source,
                    "current_price": round(res.current_price, 2),
                    "support_level": round(res.support_level, 2),
                    "target_price": round(res.target_price, 2),
                    "upside_pct": round(res.upside_pct, 2),
                    "q1_date": res.q1_date,
                    "q2_date": res.q2_date,
                    "q1_high": round(res.q1_high, 2),
                    "q2_high": round(res.q2_high, 2),
                })
                print(f"   ✅ MATCHED: {symbol}")

        except Exception as e:
            print(f"   ⚠️ Error on {symbol}: {e}")
            continue

    return matched


def save_results(matched: list[dict]):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    output = {
        "scan_time": timestamp,
        "matched_count": len(matched),
        "stocks": matched,
    }

    with open("results.json", "w") as f:
        json.dump(output, f, indent=2)

    if matched:
        df = pd.DataFrame(matched)
        df.to_csv("results.csv", index=False)
    else:
        pd.DataFrame(columns=[
            "symbol", "source", "current_price", "support_level",
            "target_price", "upside_pct", "q1_date", "q2_date", "q1_high", "q2_high"
        ]).to_csv("results.csv", index=False)

    print(f"\n📁 Saved results.json and results.csv | Matched: {len(matched)} | Time: {timestamp}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-stocks", type=int, default=500)
    parser.add_argument("--sleep", type=float, default=0.0, help="seconds between API calls")
    args = parser.parse_args()

    print(f"Starting scan of up to {args.max_stocks} Nifty500 stocks...")
    matched_stocks = run_scan(max_stocks=args.max_stocks, sleep_between=args.sleep)
    save_results(matched_stocks)
