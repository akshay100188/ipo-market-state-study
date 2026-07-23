"""Language lint — §8.3 (advisory) + §8.4 (causal).

Ported from the existing portfolio pattern (CurveIQ `lib/forbidden.js`) rather
than invented fresh: this study takes the same descriptive-not-prescriptive
posture. Patterns are deliberately tight so legitimate descriptive terms
("buyers", "the offer was priced to fall short", "long-term") do not trip.

  ADVISORY (§8.3) -> ERROR, fails the build. Prescriptive advice + the brief's
                     explicit forbidden list (should buy/apply, recommend,
                     avoid, target price, will rise/fall, expected to, good bet,
                     opportunity).
  CAUSAL   (§8.4) -> WARNING only. Regime->outcome causal verbs (because,
                     caused, drove, due to). Flagged for manual PO review at the
                     report gate, not auto-failed.

Run:  python -m src.lint_language --report report/ipo_market_state_study.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .config import REPORT

# --- Advisory / prescriptive / forward-looking (ERROR) -------------------
ADVISORY_PATTERNS = [
    r"\byou should\b",
    r"\b(should|must|ought to)\s+(buy|sell|hold|consider|avoid|own|reduce|add|apply|subscribe)\b",
    r"\bgo (long|short)\b",
    r"\b(buy|sell|short|overweight|underweight)\s+(the\s+)?(ipo|issue|stock|shares|equities)\b",
    r"\b(recommend|recommendation|advise|advice|suggest you)\b",
    r"\btarget price\b",
    r"\bgood bet\b",
    r"\b(a|an|the)\s+(buying|investment)\s+opportunity\b",
    # forward-looking / prediction
    r"\b(will|won't|is going to|are going to)\s+(rise|fall|increase|decrease|drop|climb|rally|crash|pop|surge)\b",
    r"\b(forecast|predict|prediction|projected to|likely to)\b",
    r"\bexpect(s|ed)?\s+to\s+(rise|fall|increase|decrease|drop|climb|pop|surge|outperform)\b",
    r"\b(guarantee|certain to|bound to|set to)\b",
]

# --- Causal regime->outcome (WARNING) ------------------------------------
CAUSAL_PATTERNS = [
    r"\bbecause\s+(of\s+)?the\s+(bull|bear|regime|market)\b",
    r"\b(caused|drove|led to|resulted in)\b",
    r"\bdue to the (bull|bear|regime|market|turbulent|recovery)\b",
    r"\bthanks to the (bull|bear|regime|rally)\b",
]

_ADV = [re.compile(p, re.I) for p in ADVISORY_PATTERNS]
_CAU = [re.compile(p, re.I) for p in CAUSAL_PATTERNS]


def lint_text(text: str) -> tuple[list[str], list[str]]:
    """Return (advisory_hits, causal_hits) as matched substrings."""
    advisory = [m.group(0) for re_ in _ADV for m in re_.finditer(text)]
    causal = [m.group(0) for re_ in _CAU for m in re_.finditer(text)]
    return advisory, causal


def run(report_path: Path) -> int:
    if not report_path.exists():
        print(f"lint_language: no report at {report_path} yet (Phase 4).", file=sys.stderr)
        return 0
    text = report_path.read_text(encoding="utf-8", errors="ignore")
    advisory, causal = lint_text(text)

    if causal:
        print(f"lint_language: {len(causal)} causal-language WARNING(s) for PO review:")
        for h in causal:
            print(f"  ~ '{h}'")

    if advisory:
        print(f"\n{len(advisory)} ADVISORY-language violation(s):", file=sys.stderr)
        for h in advisory:
            print(f"  - '{h}'", file=sys.stderr)
        print("\nBUILD FAILS: the study describes; it never advises (section 8.3).", file=sys.stderr)
        return 1

    print("OK: no advisory language.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Advisory + causal language lint (§8.3/§8.4).")
    ap.add_argument("--report", type=Path, default=REPORT / "ipo_market_state_study.md")
    args = ap.parse_args()
    return run(args.report)


if __name__ == "__main__":
    raise SystemExit(main())
