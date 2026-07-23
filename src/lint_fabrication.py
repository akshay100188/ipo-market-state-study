"""Fabrication lint — §5, §8.2 (scope: ADR-005).

Scans the final report for numeric tokens and asserts each in-scope number
traces to a value in the derived data or an entry in `references.md`. Any orphan
number fails the build. The count of numbers checked is reported — that count is
the single most persuasive line in the artifact.

This does not prove a number is *right about the world* — only that it came from
the dataset, not from thin air. That residual is named in the report's
limitations section.

ADR-005 — what is in scope:
  IN SCOPE  percentages (48.2%), currency amounts ($38, Rs 949, ₹1,027),
            decimals with a fractional part (1.85), and integers >= 100.
            These are how prices, returns and counts actually appear.
  EXEMPT    years / ISO dates (1900-2100), structural refs (§4.2, Figure 3,
            Table 1, ADR-002, SC-1, Phase 0, H1/H2), and bare integers < 100
            that are not a percentage or currency (meta-counts like "4-5 pairs",
            "250-350 words"). Exemptions are conservative by design and are
            revisited against the real report at Phase 4.

A number "traces" if its significant-digit signature matches a signature in the
allowed set (built from derived CSVs + references.md), so a report "48.2%"
matches a derived cell 0.482 or 48.2.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import DATA, DERIVED, REPORT, ROOT

# --- Number extraction ----------------------------------------------------

# A candidate numeric token: optional currency prefix, digits with optional
# thousands separators and decimal, optional percent.
_NUM_RE = re.compile(
    r"""(?P<cur>[$₹]|\bRs\.?\s?|\bUSD\s?|\bINR\s?)?      # optional currency
        (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)  # 1,234.5 or 1234.5
        (?P<pct>\s?%)?
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Structural reference prefixes whose trailing number is not a data claim.
_REF_PREFIX_RE = re.compile(
    r"(§|section|fig(?:ure)?|table|adr|sc|phase|h|footnote|note|eq(?:uation)?|ref)"
    r"[\s\-]?$",
    re.IGNORECASE,
)


def _signature(raw_num: str) -> str:
    """Significant-digit signature: strip commas, sign, decimal, trailing zeros.

    482%  -> from '48.2' -> '482';  '0.482' -> '482';  '38.00' -> '38'.
    """
    s = raw_num.replace(",", "").lstrip("+-")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    s = s.lstrip("0") or "0"
    # collapse a decimal point that survived (e.g. '4.5' -> '45')
    return s.replace(".", "")


def _is_year_or_date(raw_num: str, whole: str) -> bool:
    if re.fullmatch(r"(19|20)\d{2}", raw_num):
        return True
    # part of an ISO date like 2020-03-19
    if re.search(r"\d{4}-\d{2}-\d{2}", whole):
        return True
    return False


def extract_numbers(text: str) -> list[dict]:
    """Return in-scope numeric tokens with position and signature (ADR-005)."""
    tokens: list[dict] = []
    for m in _NUM_RE.finditer(text):
        raw = m.group("num")
        cur = m.group("cur")
        pct = m.group("pct")
        start = m.start()
        preceding = text[max(0, start - 12):start]

        # Exempt structural references (§4.2, Figure 3, ADR-002, ...).
        if _REF_PREFIX_RE.search(preceding):
            continue
        # Exempt years / dates.
        window = text[max(0, start - 5):m.end() + 5]
        if _is_year_or_date(raw, window):
            continue

        has_fraction = "." in raw
        is_pct = pct is not None
        is_cur = cur is not None
        try:
            magnitude = float(raw.replace(",", ""))
        except ValueError:
            continue

        in_scope = is_pct or is_cur or has_fraction or magnitude >= 100
        if not in_scope:
            continue

        tokens.append({
            "raw": m.group(0).strip(),
            "num": raw,
            "signature": _signature(raw),
            "pos": start,
        })
    return tokens


# --- Allowed set ----------------------------------------------------------

def _numbers_from_csv(path: Path) -> set[str]:
    out: set[str] = set()
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception:
        return out
    for val in df.to_numpy().ravel():
        s = str(val).strip()
        for m in _NUM_RE.finditer(s):
            out.add(_signature(m.group("num")))
    return out


def build_allowed_set(derived_dir: Path, extra_files: Iterable[Path] = ()) -> set[str]:
    """Signatures from every derived CSV, ipo_curated.csv, and references.md."""
    allowed: set[str] = set()
    for csv in sorted(derived_dir.glob("*.csv")):
        allowed |= _numbers_from_csv(csv)
    curated = DATA / "ipo_curated.csv"
    if curated.exists():
        allowed |= _numbers_from_csv(curated)
    for f in extra_files:
        if f and f.exists():
            for m in _NUM_RE.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                allowed.add(_signature(m.group("num")))
    return allowed


def lint_text(text: str, allowed: set[str]) -> tuple[list[dict], int]:
    """Return (orphans, checked_count) for a report body."""
    tokens = extract_numbers(text)
    orphans = [t for t in tokens if t["signature"] not in allowed]
    return orphans, len(tokens)


def run(report_path: Path, derived_dir: Path = DERIVED) -> int:
    if not report_path.exists():
        print(f"lint_fabrication: no report at {report_path} yet (Phase 4).", file=sys.stderr)
        return 0  # nothing to lint yet is not a failure

    references = ROOT / "references.md"
    allowed = build_allowed_set(derived_dir, extra_files=[references])
    text = report_path.read_text(encoding="utf-8", errors="ignore")
    orphans, checked = lint_text(text, allowed)

    print(f"lint_fabrication: checked {checked} in-scope numbers against "
          f"{len(allowed)} allowed signatures")
    if orphans:
        print(f"\n{len(orphans)} ORPHAN number(s) -- not traceable to data or references:",
              file=sys.stderr)
        for o in orphans:
            ctx = text[max(0, o["pos"] - 30):o["pos"] + 30].replace("\n", " ")
            print(f"  - '{o['raw']}'  ...{ctx}...", file=sys.stderr)
        print("\nBUILD FAILS: every number must trace to derived data or references (section 8.2).",
              file=sys.stderr)
        return 1
    print("OK: every in-scope number traces to the dataset.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Fabrication lint (§8.2).")
    ap.add_argument("--report", type=Path, default=REPORT / "ipo_market_state_study.md")
    ap.add_argument("--derived", type=Path, default=DERIVED)
    args = ap.parse_args()
    return run(args.report, derived_dir=args.derived)


if __name__ == "__main__":
    raise SystemExit(main())
