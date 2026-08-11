"""
Stock AI Pro v5 - Config
========================
Yahan apni API keys daalo. Kisi bhi source ki key nahi hai to usko khali chhod do,
app automatically agle source pe fallback kar lega.

Priority chain (jaisa bataya gaya): Dhan > NSE > BSE > Yahoo Finance > Groww/AngelOne > Other
"""

import os

# ---------------- DHAN API ----------------
# https://dhanhq.co/docs/  -> Get from Dhan web -> DhanHQ Trading APIs
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

# ---------------- ANGEL ONE (SmartAPI) ----------------
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY", "")
ANGEL_CLIENT_CODE = os.getenv("ANGEL_CLIENT_CODE", "")
ANGEL_PASSWORD = os.getenv("ANGEL_PASSWORD", "")
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "")

# ---------------- GROWW ----------------
# Groww ka official public API nahi hai abhi (unofficial libs risky hain),
# isliye is chain mein woh sirf placeholder ki tarah rakha hai.
GROWW_ACCESS_TOKEN = os.getenv("GROWW_ACCESS_TOKEN", "")

# ---------------- GENERAL SETTINGS ----------------
# Kitne quarters peeche tak dekhna hai result ke liye
QUARTERS_TO_ANALYZE = 3   # Q1, Q2, Q3(current/predicted)

# Support level tolerance (% ) - stock support ke kitna paas ho to "near support" maanein
SUPPORT_TOLERANCE_PCT = 2.0

# Q1/Q2 high match tolerance (% ) - Q2 ka high Q1 ke high ke kitna paas hona chahiye
HIGH_MATCH_TOLERANCE_PCT = 5.0

# Result ke baad kitne din tak stock negative fall nahi hona chahiye
POST_RESULT_WATCH_DAYS = 3
POST_RESULT_MAX_FALL_PCT = -5.0  # isse zyada gira to "negative result reaction" maanenge

# Local cache folder (Nifty500 list, price history cache)
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
