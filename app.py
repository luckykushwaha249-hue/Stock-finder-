"""
Stock AI Pro v5
================
Super simple mobile app (Streamlit):
  1. App khulta hai
  2. "Search Stocks" button dabao
  3. Nifty 500 mein se jo bhi stock strategy match karte hain, wo list mein aa jaate hain

Run:
    streamlit run app.py
Phone pe dekhne ke liye: same wifi pe laptop pe run karo, phone browser mein
laptop ka IP:8501 kholo (e.g. http://192.168.1.5:8501) — ya Streamlit Cloud pe deploy karo.
"""

import streamlit as st
import pandas as pd
import time

from nifty500_list import get_nifty500_symbols
from data_sources import get_stock_history
from results_calendar import get_result_dates
from strategy import evaluate_stock

st.set_page_config(page_title="Stock AI Pro v5", page_icon="📈", layout="centered")

# ---------------- Simple, clean mobile-first styling ----------------
st.markdown("""
<style>
    .stButton>button {
        width: 100%; height: 3em; font-size: 1.1em; font-weight: 600;
        border-radius: 10px;
    }
    .stock-card {
        padding: 14px; border-radius: 12px; background: #f4f9f4;
        border: 1px solid #d9ecd9; margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Stock AI Pro")
st.caption("v5 — Quarterly Result Support-Resistance Strategy")

with st.expander("⚙️ Settings"):
    max_stocks = st.slider("Kitne stocks scan karein (Nifty500 mein se)", 20, 500, 100, step=20)
    show_rejected = st.checkbox("Reject hue stocks bhi dikhao (debug)", value=False)

st.divider()

if st.button("🔍 SEARCH STOCKS"):
    progress = st.progress(0, text="Nifty 500 list load ho rahi hai...")

    try:
        symbols = get_nifty500_symbols()
    except Exception as e:
        st.error(f"Nifty 500 list nahi mil payi: {e}")
        st.stop()

    symbols = symbols[:max_stocks]
    total = len(symbols)

    matched_results = []
    rejected_results = []

    status_box = st.empty()

    for i, symbol in enumerate(symbols):
        status_box.text(f"Scanning {symbol} ({i+1}/{total})...")
        progress.progress((i + 1) / total, text=f"Scanning {symbol} ({i+1}/{total})")

        try:
            df, source = get_stock_history(symbol, days=400)
            if df is None:
                rejected_results.append((symbol, "none", "Koi bhi data source se price data nahi mila"))
                continue

            result_dates = get_result_dates(symbol, count=3)
            res = evaluate_stock(symbol, df, source, result_dates)

            if res.matched:
                matched_results.append(res)
            else:
                rejected_results.append((symbol, source, res.reason))

        except Exception as e:
            rejected_results.append((symbol, "error", str(e)))

        time.sleep(0.05)  # be gentle with free/unofficial APIs

    progress.empty()
    status_box.empty()

    st.success(f"Scan complete ✅  |  Matched: {len(matched_results)}  |  Scanned: {total}")

    if matched_results:
        st.subheader("🎯 Strategy Matched Stocks")
        for r in matched_results:
            st.markdown(f"""
<div class="stock-card">
<b>{r.symbol}</b> &nbsp;<span style="color:gray;">(source: {r.source})</span><br>
CMP: ₹{r.current_price:.2f} &nbsp;|&nbsp; Support: ₹{r.support_level:.2f}<br>
🎯 Target: ₹{r.target_price:.2f} &nbsp;(<span style="color:green;">+{r.upside_pct:.1f}%</span>)<br>
<small>Q1 ({r.q1_date}) high: ₹{r.q1_high:.2f} | Q2 ({r.q2_date}) high: ₹{r.q2_high:.2f}</small>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("Abhi koi stock strategy match nahi kar raha. Settings mein zyada stocks scan karke try karo.")

    if show_rejected and rejected_results:
        st.subheader("❌ Rejected (debug)")
        rej_df = pd.DataFrame(rejected_results, columns=["Symbol", "Source", "Reason"])
        st.dataframe(rej_df, use_container_width=True, hide_index=True)

else:
    st.info("👆 Button dabao aur Nifty 500 scan shuru karo.")

st.divider()
st.caption("⚠️ Yeh sirf ek pattern-based screener hai, financial advice nahi. "
           "Apna risk management aur research khud karo.")
