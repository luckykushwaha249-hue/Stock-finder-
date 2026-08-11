"""
Nifty 500 list loader
======================
NSE archives se live list uthata hai. Agar internet fail ho ya NSE block kare,
to cache/nifty500.csv se fallback leta hai (agar pehle se saved hai).
"""

import os
import requests
import pandas as pd
from config import CACHE_DIR

NSE_NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
CACHE_FILE = os.path.join(CACHE_DIR, "nifty500.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def get_nifty500_symbols(force_refresh: bool = False) -> list[str]:
    """
    Returns list of NSE trading symbols (without .NS suffix), e.g. ['RELIANCE', 'TCS', ...]
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            df = pd.read_csv(CACHE_FILE)
            symbols = df["Symbol"].dropna().astype(str).tolist()
            if len(symbols) > 400:  # sanity check, nifty500 should have ~500
                return symbols
        except Exception:
            pass

    try:
        session = requests.Session()
        # NSE needs a homepage hit first to set cookies
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
        resp = session.get(NSE_NIFTY500_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        with open(CACHE_FILE, "wb") as f:
            f.write(resp.content)

        df = pd.read_csv(CACHE_FILE)
        symbols = df["Symbol"].dropna().astype(str).tolist()
        return symbols

    except Exception as e:
        print(f"[nifty500_list] NSE fetch failed: {e}")
        if os.path.exists(CACHE_FILE):
            df = pd.read_csv(CACHE_FILE)
            return df["Symbol"].dropna().astype(str).tolist()
        raise RuntimeError(
            "Nifty 500 list nahi mil payi (internet check karo ya cache/nifty500.csv "
            "manually daal do NSE website se download karke)."
        )


if __name__ == "__main__":
    syms = get_nifty500_symbols()
    print(f"Total symbols: {len(syms)}")
    print(syms[:10])
