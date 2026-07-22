"""Market-state layer — §3.1 (ADR-008 hybrid source).

Six daily series feed the regime labeller. Provenance, best first:

  key            source of record                              fallback
  -----------    ------------------------------------------    -----------
  us_index       core.curveiq_sp500 (FRED / Yahoo)             yf ^GSPC
  us_index_alt   yf ^IXIC (Nasdaq Composite)                   —
  us_vix         yf ^VIX                                        —
  in_index       core.curveiq_nifty50 (niftyindices, official) yf ^NSEI
  in_index_alt   yf ^BSESN (BSE Sensex)                        —
  in_vix         core.macro_daily.india_vix                    yf ^INDIAVIX

Why DB-primary for the indices: the DB carries official NSE Nifty back to
1995 (yfinance ^NSEI only starts 2007-09) and FRED S&P — better provenance and
the history the 2005-onward study needs. The DB is only touched on --refresh;
normal runs read the committed data/raw cache, so a clean clone reproduces
every number with no credentials (§8.5).

Run:  python -m src.fetch_market            # use cache; fetch only if missing
      python -m src.fetch_market --refresh  # force re-pull from source
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from .config import HISTORY_START, RAW
from .regime import build_vol_series

MANIFEST = RAW / "manifest.json"

# --- Series specifications ------------------------------------------------
# Each spec: how to pull it (db table / macro column / yf symbol), a human
# source label for references.md + captions, and an optional yfinance fallback.
SPECS: dict[str, dict] = {
    "us_index": {
        "db_table": "curveiq_sp500",
        "yf": "^GSPC",
        "source": "core.curveiq_sp500 (FRED SP500 / Yahoo ^GSPC, via am-ai-engine)",
    },
    "us_index_alt": {"yf": "^IXIC", "source": "Yahoo Finance ^IXIC (Nasdaq Composite)"},
    "us_vix": {"yf": "^VIX", "source": "Yahoo Finance ^VIX (CBOE VIX)"},
    "in_index": {
        "db_table": "curveiq_nifty50",
        "yf": "^NSEI",
        "source": "core.curveiq_nifty50 (niftyindices.com, NSE official, via am-ai-engine)",
    },
    "in_index_alt": {"yf": "^BSESN", "source": "Yahoo Finance ^BSESN (BSE Sensex)"},
    "in_vix": {
        "db_macro": "india_vix",
        "yf": "^INDIAVIX",
        "source": "core.macro_daily.india_vix (via am-ai-engine)",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _latest_cache(key: str) -> Optional[Path]:
    matches = sorted(RAW.glob(f"{key}__*.parquet"))
    return matches[-1] if matches else None


def _read_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def _write_manifest(m: dict) -> None:
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True))


def _yf_close(symbol: str) -> pd.Series:
    import yfinance as yf

    df = yf.download(symbol, start=HISTORY_START, auto_adjust=False,
                     progress=False, multi_level_index=False)
    if df is None or df.empty or "Close" not in df:
        return pd.Series(dtype="float64")
    s = df["Close"].dropna()
    s.index = pd.to_datetime(s.index)
    return s


def _pull(key: str) -> tuple[pd.Series, str]:
    """Pull a series from its source of record, falling back to yfinance.

    Returns (series, resolved_source_label).
    """
    spec = SPECS[key]
    # Primary: DB.
    try:
        if "db_table" in spec:
            from .db import fetch_close
            s = fetch_close(spec["db_table"])
            if not s.empty:
                return s, spec["source"]
        elif "db_macro" in spec:
            from .db import fetch_macro_column
            s = fetch_macro_column(spec["db_macro"])
            if not s.empty:
                return s, spec["source"]
    except Exception as e:  # DBUnavailable or connection/query error
        print(f"  {key}: DB unavailable ({e.__class__.__name__}); trying yfinance", file=sys.stderr)

    # Fallback / primary-for-yf-only series.
    if "yf" in spec:
        s = _yf_close(spec["yf"])
        if not s.empty:
            label = spec["source"] if "db_table" not in spec and "db_macro" not in spec \
                else f"Yahoo Finance {spec['yf']} (fallback)"
            return s, label

    raise RuntimeError(f"could not fetch series '{key}' from any source")


def load_series(key: str, refresh: bool = False) -> pd.Series:
    """Cached daily close for a keyed series. Fetch + cache only if needed."""
    RAW.mkdir(parents=True, exist_ok=True)
    cache = None if refresh else _latest_cache(key)
    if cache is not None:
        s = pd.read_parquet(cache).iloc[:, 0]
        s.index = pd.to_datetime(s.index)
        s.name = key
        return s

    s, source = _pull(key)
    s = s.sort_index()
    s.name = key
    stamp = _now()
    out = RAW / f"{key}__{stamp}.parquet"
    s.to_frame(name="close").to_parquet(out)

    man = _read_manifest()
    man[key] = {
        "source": source,
        "retrieved_utc": stamp,
        "rows": int(s.notna().sum()),
        "start": str(s.first_valid_index().date()) if s.first_valid_index() is not None else None,
        "end": str(s.last_valid_index().date()) if s.last_valid_index() is not None else None,
        "cache_file": out.name,
    }
    _write_manifest(man)
    print(f"  cached {key}: {len(s)} rows [{source}] -> {out.name}")
    return s


def load_market_frames(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Return {'us': df, 'in': df}; each daily-indexed with columns:

        index_close, index_alt_close, vix_close, vol

    ``vol`` is the VIX where present, backfilled with annualised 21-day
    realised vol on the index (India pre-2008 gap; §2). ``vix_close`` keeps the
    raw VIX so callers can detect and disclose the substitution window.
    """
    keys = ["us_index", "us_index_alt", "us_vix", "in_index", "in_index_alt", "in_vix"]
    series = {k: load_series(k, refresh=refresh) for k in keys}
    frames: dict[str, pd.DataFrame] = {}
    for mkt, (idx_k, alt_k, vix_k) in {
        "us": ("us_index", "us_index_alt", "us_vix"),
        "in": ("in_index", "in_index_alt", "in_vix"),
    }.items():
        idx = series[idx_k]
        df = pd.DataFrame({"index_close": idx})
        df["index_alt_close"] = series[alt_k].reindex(idx.index)
        vix = series[vix_k].reindex(idx.index)
        df["vix_close"] = vix
        df["vol"] = build_vol_series(idx, vix)
        frames[mkt] = df.sort_index()
    return frames


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch/cache the market-state layer (§3.1).")
    ap.add_argument("--refresh", action="store_true", help="force re-pull, ignore cache")
    args = ap.parse_args()

    frames = load_market_frames(refresh=args.refresh)
    for mkt, df in frames.items():
        first = df["index_close"].first_valid_index()
        last = df["index_close"].last_valid_index()
        vix_first = df["vix_close"].first_valid_index()
        print(
            f"{mkt}: index {first.date() if first is not None else '-'} -> "
            f"{last.date() if last is not None else '-'}  "
            f"({int(df['index_close'].notna().sum())} days); "
            f"VIX from {vix_first.date() if vix_first is not None else '-'} "
            f"(pre-VIX uses realised-vol fallback)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
