"""Shared configuration: paths, tickers, and the trading-window constants.

Single source of truth so every stage of the pipeline resolves the same
directories and the same market-data symbols. No secrets live here.
"""
from __future__ import annotations

from pathlib import Path

# --- Repo layout ---------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
DERIVED = DATA / "derived"
FIGURES = ROOT / "figures"
REPORT = ROOT / "report"

# --- Market-state series (§3.1) -----------------------------------------
# Yahoo Finance symbols. India VIX history only starts ~2008-09; the
# realised-vol fallback in regime.py covers 2005-2008 (see ADR-002 note).
US_INDEX = "^GSPC"          # S&P 500
US_INDEX_ALT = "^IXIC"      # Nasdaq Composite (secondary, US)
US_VIX = "^VIX"

IN_INDEX = "^NSEI"          # Nifty 50
IN_INDEX_ALT = "^BSESN"     # BSE Sensex (secondary, India)
IN_VIX = "^INDIAVIX"

MARKET_SYMBOLS = {
    "us_index": US_INDEX,
    "us_index_alt": US_INDEX_ALT,
    "us_vix": US_VIX,
    "in_index": IN_INDEX,
    "in_index_alt": IN_INDEX_ALT,
    "in_vix": IN_VIX,
}

# Start early enough that 2005 listings have full trailing windows (§3.1).
HISTORY_START = "2004-01-01"

# Trading-day approximations for realised-vol windows.
TRADING_DAYS_YEAR = 252
REALISED_VOL_WINDOW = 21    # 21-day realised vol for the India pre-2008 fallback
