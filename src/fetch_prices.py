"""Post-listing price series — §3.4 (survivorship: ADR-006).

For every VERIFIED curated name, fetch the daily series from its listing date
and compute +1M/+3M/+6M/+12M returns, both absolute and **excess** vs the home
index over the same window. Horizon returns are ratios on a single series, so
stock splits cancel (unlike the offer->close day-1 return, which must be on the
unadjusted basis — see build_seed.py).

Source per name:
  - India names inside the DB range (listing >= 2022): core.nse_daily_prices
    (official NSE), because some yfinance India feeds are unreliable (LIC).
  - otherwise yfinance (US: ticker; India: ticker.NS).

Delisted / acquired names, or names younger than a horizon, will not have every
horizon. Every such gap is logged explicitly to data/derived/price_fetch_log.csv
and reported as survivorship, never silently dropped (ADR-006).

Run:  python -m src.fetch_prices
"""
from __future__ import annotations

import sys
from datetime import date

import pandas as pd

from .config import DATA, DERIVED
from .fetch_market import load_market_frames

HORIZONS = {"1M": 1, "3M": 3, "6M": 6, "12M": 12}
RETURNS_OUT = DERIVED / "post_listing_returns.csv"
LOG_OUT = DERIVED / "price_fetch_log.csv"

# yfinance symbol overrides for post-listing renames (survivorship, ADR-006).
# Zomato renamed to Eternal (ETERNAL.NS) in 2025; ZOMATO.NS no longer resolves.
YF_OVERRIDE = {"ZOMATO": "ETERNAL"}


def _asof(series: pd.Series, when: pd.Timestamp):
    s = series.dropna()
    s = s[s.index <= when]
    return (float(s.iloc[-1]), s.index[-1]) if len(s) else (None, None)


def _first_on_or_after(series: pd.Series, when: pd.Timestamp):
    s = series.dropna()
    s = s[s.index >= when]
    return (float(s.iloc[0]), s.index[0]) if len(s) else (None, None)


def _yf_series(symbol: str, start: str) -> pd.Series:
    import yfinance as yf

    df = yf.download(symbol, start=start, auto_adjust=False, progress=False,
                     multi_level_index=False)
    if df is None or df.empty or "Close" not in df:
        return pd.Series(dtype="float64")
    s = df["Close"].dropna()
    s.index = pd.to_datetime(s.index)
    return s


def _price_series(ticker: str, market: str, ipo_date: str) -> tuple[pd.Series, str]:
    """Return (daily close series from ipo_date, source label)."""
    if market == "IN" and ipo_date >= "2022-01-01":
        try:
            from .db import fetch_nse_close
            s = fetch_nse_close(ticker, ipo_date)
            if not s.empty:
                return s, "core.nse_daily_prices (official NSE, am-ai-engine)"
        except Exception as e:
            print(f"  {ticker}: DB series unavailable ({e.__class__.__name__})", file=sys.stderr)
    base = YF_OVERRIDE.get(ticker, ticker)
    symbol = base if market == "US" else f"{base}.NS"
    note = f"Yahoo Finance {symbol}"
    if base != ticker:
        note += f" (renamed from {ticker})"
    return _yf_series(symbol, ipo_date), note


def compute() -> tuple[pd.DataFrame, pd.DataFrame]:
    curated = pd.read_csv(DATA / "ipo_curated.csv", dtype=str, keep_default_na=False)
    frames = load_market_frames()
    rows, log = [], []

    for _, r in curated.iterrows():
        ticker, market, ipo_date = r["ticker"], r["market"], r["ipo_date"]
        series, source = _price_series(ticker, market, ipo_date)
        if series.empty:
            log.append({"ticker": ticker, "event": "FETCH_FAILED", "detail": source})
            continue

        idx = frames["us" if market == "US" else "in"]["index_close"]
        list_px, list_dt = _first_on_or_after(series, pd.Timestamp(ipo_date))
        idx_list, _ = _asof(idx, pd.Timestamp(list_dt)) if list_dt is not None else (None, None)
        if list_px is None:
            log.append({"ticker": ticker, "event": "NO_LISTING_PX", "detail": source})
            continue

        # Note: horizon returns are ratios on this series, so splits/bonuses cancel;
        # we do not emit the raw anchor price (it is split-adjusted for some feeds,
        # which would contradict the unadjusted day-1 close in ipo_curated.csv).
        row = {"ticker": ticker, "name": r["name"], "market": market,
               "ipo_date": ipo_date, "source": source}
        last_dt = series.dropna().index[-1]
        for label, months in HORIZONS.items():
            target = pd.Timestamp(list_dt) + pd.DateOffset(months=months)
            if target > last_dt:
                row[f"ret_{label}"] = ""
                row[f"excess_{label}"] = ""
                log.append({"ticker": ticker, "event": f"NO_{label}",
                            "detail": f"series ends {last_dt.date()} < {target.date()} "
                                      f"(delisted/acquired/too-young -- survivorship)"})
                continue
            px, _ = _asof(series, target)
            ret = px / list_px - 1.0
            row[f"ret_{label}"] = round(ret * 100, 2)
            if idx_list:
                idx_t, _ = _asof(idx, target)
                row[f"excess_{label}"] = round((ret - (idx_t / idx_list - 1.0)) * 100, 2)
            else:
                row[f"excess_{label}"] = ""
        rows.append(row)

    return pd.DataFrame(rows), pd.DataFrame(log)


def main() -> int:
    DERIVED.mkdir(parents=True, exist_ok=True)
    returns, log = compute()
    returns.to_csv(RETURNS_OUT, index=False)
    log.to_csv(LOG_OUT, index=False)
    print(f"wrote {RETURNS_OUT.name}: {len(returns)} names; "
          f"{LOG_OUT.name}: {len(log)} log event(s)")
    show = [c for c in ["ticker", "market",
                        "ret_1M", "ret_3M", "ret_6M", "ret_12M"] if c in returns.columns]
    if not returns.empty:
        print(returns[show].to_string(index=False))
    if not log.empty:
        print("\nfetch log (survivorship / gaps):")
        print(log.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
