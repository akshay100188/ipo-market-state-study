"""Verification gate — §3.3 hard rule, §5, §8.1.

A blocking build step, not a checklist. Every curated IPO row that is allowed
into published output must be `VERIFIED` and carry the receipts for its three
load-bearing facts (offer_price, ipo_date, day1_return_pct): a working
`source_url`, a `source_type`, and a `retrieval_date`.

Row status semantics:
  VERIFIED   -> must have full provenance, else the build FAILS.
  EXCLUDED   -> a deliberate drop; must state a reason in `notes` (ADR-007),
                else FAILS. Kept out of the published set, listed in an appendix.
  TO_VERIFY  -> unresolved. FAILS the gate (the study is not done until every
                row is VERIFIED or explicitly EXCLUDED).
  anything else -> FAILS (unknown status).

There is deliberately **no override flag** (§8.1). Exit non-zero == build fails.

Run:  python -m src.verify              # uses data/ipo_seed.csv
      python -m src.verify --seed X.csv
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import DATA, DERIVED

REQUIRED_COLUMNS = [
    "ticker", "name", "market", "ipo_date", "offer_price", "currency",
    "day1_open", "day1_close", "day1_return_pct",
    "source_url", "source_type", "retrieval_date", "verify_status", "notes",
]

# The three facts whose provenance is non-negotiable (§3.3).
LOAD_BEARING = ["offer_price", "ipo_date", "day1_return_pct"]

VALID_STATUS = {"VERIFIED", "EXCLUDED", "TO_VERIFY"}

_URL_RE = re.compile(r"^https?://\S+$", re.I)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

SEED_DEFAULT = DATA / "ipo_seed.csv"
CURATED_OUT = DATA / "ipo_curated.csv"
EXCLUDED_OUT = DERIVED / "excluded_unverified.csv"


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""


def _is_number(v) -> bool:
    if _blank(v):
        return False
    try:
        float(str(v).replace(",", ""))
        return True
    except ValueError:
        return False


def verify_frame(df: pd.DataFrame) -> tuple[bool, list[str], pd.DataFrame, pd.DataFrame]:
    """Validate a seed frame. Returns (ok, errors, curated, excluded).

    ``ok`` is False (build should fail) if any row is invalid per the status
    semantics above. ``curated`` is the VERIFIED-only publishable set;
    ``excluded`` is the deliberately-dropped rows with their reason.
    """
    errors: list[str] = []

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"seed is missing required columns: {missing_cols}")
        return False, errors, df.iloc[0:0], df.iloc[0:0]

    def rid(row) -> str:
        return f"row {row.name} ({str(row.get('ticker') or row.get('name') or '?')})"

    for _, row in df.iterrows():
        status = str(row["verify_status"]).strip().upper()
        if status not in VALID_STATUS:
            errors.append(f"{rid(row)}: invalid verify_status '{row['verify_status']}'")
            continue

        if status == "TO_VERIFY":
            errors.append(f"{rid(row)}: still TO_VERIFY -- resolve to VERIFIED or EXCLUDED")
            continue

        if status == "EXCLUDED":
            if _blank(row["notes"]):
                errors.append(f"{rid(row)}: EXCLUDED but no reason in notes (ADR-007)")
            continue

        # status == VERIFIED: full provenance required.
        for f in LOAD_BEARING:
            if _blank(row[f]):
                errors.append(f"{rid(row)}: VERIFIED but '{f}' is blank")
        if not _is_number(row["offer_price"]):
            errors.append(f"{rid(row)}: offer_price is not numeric ('{row['offer_price']}')")
        if not _is_number(row["day1_return_pct"]):
            errors.append(f"{rid(row)}: day1_return_pct is not numeric ('{row['day1_return_pct']}')")
        if not _DATE_RE.match(str(row["ipo_date"]).strip()):
            errors.append(f"{rid(row)}: ipo_date not ISO YYYY-MM-DD ('{row['ipo_date']}')")
        if _blank(row["source_url"]) or not _URL_RE.match(str(row["source_url"]).strip()):
            errors.append(f"{rid(row)}: VERIFIED but source_url is missing/invalid")
        if _blank(row["source_type"]):
            errors.append(f"{rid(row)}: VERIFIED but source_type is blank")
        if _blank(row["retrieval_date"]) or not _DATE_RE.match(str(row["retrieval_date"]).strip()):
            errors.append(f"{rid(row)}: VERIFIED but retrieval_date missing/invalid")

    status_up = df["verify_status"].astype(str).str.strip().str.upper()
    curated = df[status_up == "VERIFIED"].copy()
    excluded = df[status_up != "VERIFIED"].copy()
    return (len(errors) == 0), errors, curated, excluded


def run(seed_path: Path, write: bool = True) -> int:
    if not seed_path.exists():
        print(f"FAIL: seed not found: {seed_path}", file=sys.stderr)
        print("      (expected in Phase 2; nothing to verify yet)", file=sys.stderr)
        return 1

    df = pd.read_csv(seed_path, dtype=str, keep_default_na=False)
    ok, errors, curated, excluded = verify_frame(df)

    print(f"verify: {len(df)} seed rows -> {len(curated)} VERIFIED, {len(excluded)} excluded")
    if errors:
        print(f"\n{len(errors)} verification error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    if write and ok:
        CURATED_OUT.parent.mkdir(parents=True, exist_ok=True)
        EXCLUDED_OUT.parent.mkdir(parents=True, exist_ok=True)
        curated.to_csv(CURATED_OUT, index=False)
        excluded.to_csv(EXCLUDED_OUT, index=False)
        print(f"wrote {CURATED_OUT.relative_to(DATA.parent)} and "
              f"{EXCLUDED_OUT.relative_to(DATA.parent)}")

    if not ok:
        print("\nGATE FAILED: no unverified number ships (section 8.1).", file=sys.stderr)
        return 1
    print("GATE PASSED.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Verification gate (§3.3, §8.1).")
    ap.add_argument("--seed", type=Path, default=SEED_DEFAULT)
    ap.add_argument("--no-write", action="store_true", help="validate only, don't emit CSVs")
    args = ap.parse_args()
    return run(args.seed, write=not args.no_write)


if __name__ == "__main__":
    raise SystemExit(main())
