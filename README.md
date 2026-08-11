# Stock AI Pro v5 📈

Nifty 500 stocks ko tumhari **Quarterly Result Support-Resistance Strategy** ke hisaab se
screen karne wala simple app.

## Strategy (recap)
- Q1 (purana result) → Q2 (beech wala) → Q3 (jiske liye prediction)
- Q1 result din ka high mark hota hai
- Uske baad correction + support level banta hai
- Q2 result ke time stock Q1 high ke paas wapas jata hai (agar result achha ho)
- Q2 ke baad jab stock support ke paas aaye → **BUY signal**, target = Q1/Q2 high
- Filter: result ke baad 2-3 din stock crash nahi hona chahiye, Q1 & Q2 dono result achhe hone chahiye

## Setup

```bash
git clone <tumhara-repo>
cd stock_ai_pro
pip install -r requirements.txt
```

### API Keys (optional — jo nahi doge, wo source skip ho jayega)

`config.py` mein directly daal sakte ho, ya environment variables set karo:

```bash
export DHAN_CLIENT_ID="xxxx"
export DHAN_ACCESS_TOKEN="xxxx"

export ANGEL_API_KEY="xxxx"
export ANGEL_CLIENT_CODE="xxxx"
export ANGEL_PASSWORD="xxxx"
export ANGEL_TOTP_SECRET="xxxx"
```

**Dhan API kaise le:** Dhan web app → Profile → DhanHQ Trading APIs → generate access token.
Docs: https://dhanhq.co/docs/v2/

Agar koi key nahi dete ho, app automatically **Yahoo Finance** (yfinance) use karega —
woh bina key ke free chalta hai, isliye app "out of the box" kaam karega.

## Run

```bash
streamlit run app.py
```

Phone pe kholne ke liye:
1. Laptop aur phone same WiFi pe hone chahiye
2. Terminal mein laptop ka local IP dekho (`ipconfig` / `ifconfig`)
3. Phone browser mein kholo: `http://<laptop-ip>:8501`

Ya phir **Streamlit Community Cloud** pe free deploy kar do (GitHub repo se) — tab
seedha URL phone pe khulega, laptop bhi chalu rakhne ki zaroorat nahi.

## Data Source Priority Chain

```
Dhan API → NSE → BSE → Yahoo Finance → AngelOne (SmartAPI) → Other
```

Har stock ke liye pehla source try hota hai; fail ho to agla try hota hai
(`data_sources.py` mein `get_stock_history()`).

## File Structure

```
stock_ai_pro/
├── app.py                # Streamlit UI (main entry point)
├── config.py              # API keys & strategy tolerances
├── data_sources.py        # Dhan/NSE/BSE/Yahoo/AngelOne fallback chain
├── nifty500_list.py       # Nifty 500 symbol list loader
├── results_calendar.py    # Quarterly result date fetcher
├── strategy.py             # Core screening logic
└── requirements.txt
```

## Known Limitations (important — sach-sach bata raha hoon)

- **BSE/NSE unofficial endpoints**: NSE/BSE ke public APIs official nahi hain — kabhi
  block/rate-limit ho sakte hain. Isliye Yahoo Finance ko reliable fallback rakha hai.
- **AngelOne**: token resolution (symbol → instrument token) abhi placeholder hai —
  full use ke liye unka instrument master JSON map karna padega.
- **Groww**: koi stable public API nahi hai, isliye abhi chain mein sirf placeholder hai.
- **Result dates**: NSE corporate-results API se try hota hai, fail hone par yfinance
  ke earnings dates se — kabhi 1-2 stocks ke result date match na ho to woh skip ho jayenge.
- Tolerance % (support nearness, Q1≈Q2 high match) `config.py` mein adjust kar sakte ho.

## Disclaimer

Yeh sirf ek rule-based screener hai, financial advice nahi hai. Trading se pehle khud
backtest aur risk-management (stop-loss) zaroor add karo.
