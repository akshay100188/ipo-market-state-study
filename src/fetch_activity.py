"""Aggregate IPO-activity layer — §3.2 (evidences SC-1).

US: Jay Ritter's (University of Florida) monthly IPO file `IPOALL.xlsx` —
counts and average first-day returns, 1960–2025, the authoritative source. We
download his table and aggregate his own monthly numbers to annual (sum of net
counts; net-count-weighted mean first-day return over months with a reported
return). We do **not** recompute his first-day returns from raw data — the
methodology (net-count definition: excludes SPACs, penny stocks, CEFs, ADRs,
units, banks/S&Ls) is his. The annual aggregation is validated against his
published annual figures (see tests): 1999 -> 476 net / 71.0%, 2020 -> 165 /
41.6%, 2021 -> 309 / 32.0%.

India: no clean public equivalent of Ritter exists (ADR-003). India activity is
acquired separately and cross-checked (§3.2); India first-day returns are NOT
taken from an aggregate series — they are computed from the curated set with the
sample size stated. This module owns only the US aggregate; India rows are
merged in from `data/india_activity.csv` when present.

Run:  python -m src.fetch_activity            # use cached xlsx if present
      python -m src.fetch_activity --refresh  # re-download Ritter
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .config import DATA, RAW

RITTER_URL = "https://site.warrington.ufl.edu/ritter/files/IPOALL.xlsx"
RITTER_XLSX = RAW / "ritter_IPOALL.xlsx"
MANIFEST = RAW / "manifest.json"

ACTIVITY_OUT = DATA / "ipo_activity.csv"
INDIA_ACTIVITY = DATA / "india_activity.csv"   # optional, cross-checked (§3.2)

ACTIVITY_COLUMNS = [
    "market", "year", "n_ipos", "gross_ipos", "mean_first_day_return_pct",
    "funds_raised", "currency", "source", "source_url", "source_type",
    "retrieval_date", "verify_status", "notes",
]


def download_ritter(refresh: bool = False) -> Path:
    """Download IPOALL.xlsx to the cache (only if missing or --refresh)."""
    if RITTER_XLSX.exists() and not refresh:
        return RITTER_XLSX
    import urllib.request

    RAW.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(RITTER_URL, RITTER_XLSX)

    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    man["ritter_IPOALL"] = {
        "source": "Jay Ritter (Univ. of Florida) IPOALL.xlsx — monthly IPO counts + first-day returns, 1960-2025",
        "source_url": RITTER_URL,
        "retrieved_utc": date.today().isoformat(),
        "cache_file": RITTER_XLSX.name,
    }
    MANIFEST.write_text(json.dumps(man, indent=2, sort_keys=True))
    return RITTER_XLSX


def _decode_year(y2: pd.Series) -> pd.Series:
    """Ritter's 2-digit year: 60-99 -> 1960-1999, 00-25 -> 2000-2025."""
    return np.where(y2 >= 60, 1900 + y2, 2000 + y2).astype(int)


def us_annual_activity(path: Path = RITTER_XLSX) -> pd.DataFrame:
    """Aggregate Ritter's monthly IPOALL to annual US activity."""
    df = pd.read_excel(path, header=None, usecols=[0, 1, 2, 3, 4, 5])
    df.columns = ["m", "y", "ret", "gross", "net", "above_mid"]
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["m"].between(1, 12) & df["y"].notna()].copy()
    df["year"] = _decode_year(df["y"])

    def agg(g: pd.DataFrame) -> pd.Series:
        v = g.dropna(subset=["ret"])
        v = v[v["net"] > 0]
        wr = np.average(v["ret"], weights=v["net"]) if len(v) else np.nan
        return pd.Series({
            "n_ipos": int(g["net"].sum()),
            "gross_ipos": int(g["gross"].sum()),
            "mean_first_day_return_pct": round(wr, 1) if not np.isnan(wr) else np.nan,
        })

    ann = df.groupby("year").apply(agg, include_groups=False).reset_index()
    return ann


def build_activity(refresh: bool = False) -> pd.DataFrame:
    """US (Ritter) + India (cross-checked, if present) annual activity table."""
    download_ritter(refresh=refresh)
    us = us_annual_activity()
    us = us[us["year"].between(2005, 2026)].copy()
    for c in ("year", "n_ipos", "gross_ipos"):
        us[c] = us[c].astype(int)
    us["market"] = "US"
    us["funds_raised"] = ""
    us["currency"] = "USD"
    us["source"] = "Jay Ritter (UF) IPOALL.xlsx, annual aggregation of monthly net counts + returns"
    us["source_url"] = RITTER_URL
    us["source_type"] = "academic dataset (authoritative)"
    us["retrieval_date"] = date.today().isoformat()
    us["verify_status"] = "VERIFIED"
    us["notes"] = "net-count definition; annual = sum(net), net-count-weighted mean first-day return"
    us = us[ACTIVITY_COLUMNS]

    frames = [us]
    if INDIA_ACTIVITY.exists():
        india = pd.read_csv(INDIA_ACTIVITY, dtype=str, keep_default_na=False)
        # Only keep the published schema columns that exist; fill the rest.
        for c in ACTIVITY_COLUMNS:
            if c not in india.columns:
                india[c] = ""
        frames.append(india[ACTIVITY_COLUMNS])

    return pd.concat(frames, ignore_index=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate IPO-activity layer (§3.2).")
    ap.add_argument("--refresh", action="store_true", help="re-download Ritter xlsx")
    args = ap.parse_args()

    act = build_activity(refresh=args.refresh)
    ACTIVITY_OUT.parent.mkdir(parents=True, exist_ok=True)
    act.to_csv(ACTIVITY_OUT, index=False)
    us = act[act["market"] == "US"]
    print(f"wrote {ACTIVITY_OUT.name}: {len(act)} rows "
          f"({len(us)} US years {us['year'].min()}-{us['year'].max()}, "
          f"{len(act) - len(us)} India rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
