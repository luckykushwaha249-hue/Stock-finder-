"""
Data Sources — Fallback Chain
==============================
Order: Dhan API -> NSE -> BSE -> Yahoo Finance (yfinance) -> AngelOne -> Groww/Other

Har function try karta hai pehla source; fail hone par agla try karta hai.
Sab functions same shape ka data return karte hain (pandas DataFrame):
    columns = ['date', 'open', 'high', 'low', 'close', 'volume']
"""

import time
import pandas as pd
import requests
import yfinance as yf

from config import (
    DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN,
    ANGEL_API_KEY, ANGEL_CLIENT_CODE, ANGEL_PASSWORD, ANGEL_TOTP_SECRET,
)

STANDARD_COLS = ["date", "open", "high", "low", "close", "volume"]


# =========================================================
# 1. DHAN API
# =========================================================
def get_history_dhan(symbol: str, security_id: str = None, days: int = 400) -> pd.DataFrame | None:
    """
    Dhan Historical Data API.
    Docs: https://dhanhq.co/docs/v2/historical-data/
    Note: Dhan needs 'security_id' (not plain symbol) — map it via Dhan's
    instrument master CSV (https://images.dhan.co/api-data/api-scrip-master.csv)
    """
    if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
        return None  # keys missing -> skip to next source

    if not security_id:
        return None  # caller must resolve security_id first (see resolve_dhan_security_id)

    try:
        url = "https://api.dhan.co/v2/charts/historical"
        headers = {
            "access-token": DHAN_ACCESS_TOKEN,
            "client-id": DHAN_CLIENT_ID,
            "Content-Type": "application/json",
        }
        payload = {
            "securityId": security_id,
            "exchangeSegment": "NSE_EQ",
            "instrument": "EQUITY",
            "expiryCode": 0,
            "fromDate": (pd.Timestamp.today() - pd.Timedelta(days=days)).strftime("%Y-%m-%d"),
            "toDate": pd.Timestamp.today().strftime("%Y-%m-%d"),
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        df = pd.DataFrame({
            "date": pd.to_datetime(data["timestamp"], unit="s"),
            "open": data["open"],
            "high": data["high"],
            "low": data["low"],
            "close": data["close"],
            "volume": data["volume"],
        })
        return df[STANDARD_COLS]

    except Exception as e:
        print(f"[Dhan] failed for {symbol}: {e}")
        return None


_dhan_master_cache = None


def resolve_dhan_security_id(symbol: str) -> str | None:
    """Downloads Dhan's instrument master once and caches it, to map NSE symbol -> securityId."""
    global _dhan_master_cache
    if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
        return None
    try:
        if _dhan_master_cache is None:
            url = "https://images.dhan.co/api-data/api-scrip-master.csv"
            _dhan_master_cache = pd.read_csv(url, low_memory=False)
        row = _dhan_master_cache[
            (_dhan_master_cache["SEM_TRADING_SYMBOL"] == symbol)
            & (_dhan_master_cache["SEM_EXM_EXCH_ID"] == "NSE")
            & (_dhan_master_cache["SEM_SEGMENT"] == "E")
        ]
        if not row.empty:
            return str(row.iloc[0]["SEM_SMST_SECURITY_ID"])
        return None
    except Exception as e:
        print(f"[Dhan master] failed: {e}")
        return None


# =========================================================
# 2. NSE (direct, unofficial endpoints)
# =========================================================
def get_history_nse(symbol: str, days: int = 400) -> pd.DataFrame | None:
    try:
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "*/*",
        }
        session.get("https://www.nseindia.com", headers=headers, timeout=10)

        to_date = pd.Timestamp.today()
        from_date = to_date - pd.Timedelta(days=days)
        url = (
            "https://www.nseindia.com/api/historical/cm/equity"
            f"?symbol={symbol}&series=[%22EQ%22]"
            f"&from={from_date.strftime('%d-%m-%Y')}&to={to_date.strftime('%d-%m-%Y')}"
        )
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return None

        df = pd.DataFrame(data)
        df = df.rename(columns={
            "CH_TIMESTAMP": "date",
            "CH_OPENING_PRICE": "open",
            "CH_TRADE_HIGH_PRICE": "high",
            "CH_TRADE_LOW_PRICE": "low",
            "CH_CLOSING_PRICE": "close",
            "CH_TOT_TRADED_QTY": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        return df[STANDARD_COLS]

    except Exception as e:
        print(f"[NSE] failed for {symbol}: {e}")
        return None


# =========================================================
# 3. BSE (direct, unofficial endpoints)
# =========================================================
def get_bse_scrip_code(symbol: str) -> str | None:
    """BSE needs numeric scrip code. Simple lookup via BSE search API."""
    try:
        url = f"https://api.bseindia.com/BseIndiaAPI/api/PeerSmartSearch/w?Type=SS&text={symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        results = resp.json()
        if results:
            return str(results[0].get("scrip_id") or results[0].get("Scrip_Cd"))
        return None
    except Exception as e:
        print(f"[BSE lookup] failed for {symbol}: {e}")
        return None


def get_history_bse(symbol: str, days: int = 400) -> pd.DataFrame | None:
    try:
        scrip_code = get_bse_scrip_code(symbol)
        if not scrip_code:
            return None

        to_date = pd.Timestamp.today()
        from_date = to_date - pd.Timedelta(days=days)
        url = (
            "https://api.bseindia.com/BseIndiaAPI/api/StockPrTrend/w"
            f"?scripcode={scrip_code}"
            f"&fromdate={from_date.strftime('%Y%m%d')}"
            f"&todate={to_date.strftime('%Y%m%d')}"
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None

        df = pd.DataFrame(data)
        # BSE trend API field names vary; adjust mapping if BSE changes response shape
        df = df.rename(columns={
            "dttm": "date", "OpenPr": "open", "HighPr": "high",
            "LowPr": "low", "ClosePr": "close", "TotTrdQty": "volume",
        })
        if "date" not in df.columns:
            return None
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        return df[STANDARD_COLS]

    except Exception as e:
        print(f"[BSE] failed for {symbol}: {e}")
        return None


# =========================================================
# 4. YAHOO FINANCE (most reliable free fallback)
# =========================================================
def get_history_yfinance(symbol: str, days: int = 400) -> pd.DataFrame | None:
    try:
        ticker = f"{symbol}.NS"
        df = yf.download(
            ticker,
            period=f"{days}d",
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        if df is None or df.empty:
            # try BSE listing suffix as backup
            df = yf.download(f"{symbol}.BO", period=f"{days}d", interval="1d",
                              progress=False, auto_adjust=False)
        if df is None or df.empty:
            return None

        df = df.reset_index()
        df.columns = [str(c).lower() for c in df.columns]
        df = df.rename(columns={"date": "date", "adj close": "adj_close"})
        return df[STANDARD_COLS]

    except Exception as e:
        print(f"[yfinance] failed for {symbol}: {e}")
        return None


# =========================================================
# 5. ANGEL ONE (SmartAPI) — needs login session
# =========================================================
def get_history_angelone(symbol: str, days: int = 400) -> pd.DataFrame | None:
    if not (ANGEL_API_KEY and ANGEL_CLIENT_CODE and ANGEL_PASSWORD and ANGEL_TOTP_SECRET):
        return None
    try:
        from SmartApi import SmartConnect  # pip install smartapi-python
        import pyotp

        obj = SmartConnect(api_key=ANGEL_API_KEY)
        totp = pyotp.TOTP(ANGEL_TOTP_SECRET).now()
        obj.generateSession(ANGEL_CLIENT_CODE, ANGEL_PASSWORD, totp)

        # NOTE: AngelOne needs symbol-token mapping (from their instrument master JSON)
        # this is left as a simplified placeholder — resolve token before calling.
        return None  # implement token resolution + getCandleData() as needed

    except Exception as e:
        print(f"[AngelOne] failed for {symbol}: {e}")
        return None


# =========================================================
# 6. GROWW / OTHER — placeholder for future source
# =========================================================
def get_history_other(symbol: str, days: int = 400) -> pd.DataFrame | None:
    # Groww ka koi stable public API nahi hai. Yahan future source plug kar sakte ho.
    return None


# =========================================================
# MASTER FALLBACK CHAIN
# =========================================================
def get_stock_history(symbol: str, days: int = 400, sleep_between: float = 0.0) -> tuple[pd.DataFrame | None, str]:
    """
    Tries: Dhan -> NSE -> BSE -> Yahoo Finance -> AngelOne -> Other
    Returns (DataFrame, source_name_used) or (None, 'none') if all fail.
    """
    sources = [
        ("Dhan", lambda: get_history_dhan(symbol, resolve_dhan_security_id(symbol), days)),
        ("NSE", lambda: get_history_nse(symbol, days)),
        ("BSE", lambda: get_history_bse(symbol, days)),
        ("YahooFinance", lambda: get_history_yfinance(symbol, days)),
        ("AngelOne", lambda: get_history_angelone(symbol, days)),
        ("Other", lambda: get_history_other(symbol, days)),
    ]

    for name, fn in sources:
        try:
            df = fn()
        except Exception as e:
            print(f"[{name}] unexpected error for {symbol}: {e}")
            df = None

        if df is not None and not df.empty:
            return df, name

        if sleep_between:
            time.sleep(sleep_between)

    return None, "none"
