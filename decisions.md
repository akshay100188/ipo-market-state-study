# Decision log (ADRs)

Architecture Decision Records for the IPO market-state study. Each: what /
why / alternatives rejected / revisit condition. Numbers follow the brief §10;
ADR-008+ are decisions the brief left open to the developer.

Status legend: **ACCEPTED** · **PENDING** (not yet decided) · **SUPERSEDED**.

---

## ADR-001 — Curated-case + authoritative-aggregate hybrid over full-census scrape
**Status:** ACCEPTED (per brief §3, §10).
**What:** Evidence SC-1 (aggregate effect) from authoritative pre-computed
sources (Ritter for the US; cross-checked NSE/SEBI stats for India). Evidence
SC-2 (idiosyncratic failures) from a hand-verified curated case set of ~20–30
marquee IPOs. Do **not** attempt a full census of every IPO since 2005.
**Why:** There is no single reliable free source for "all IPOs since 2005 with
offer and listing prices" across US + India. A blind scrape yields confidently
wrong numbers — fatal for an artifact whose thesis is verifiable trust.
**Rejected:** (a) Full-census scrape — accuracy collapses, unbounded verification
cost. (b) Buy a commercial dataset — out of scope, not reproducible by a reader.
**Revisit:** If a single authoritative, free, reproducible census appears.

## ADR-002 — Regime thresholds and label precedence
**Status:** ACCEPTED.
**What:** Thresholds per brief §2, encoded in `RegimeThresholds`
(`src/regime.py`): BULL = 6m > +5% & vol < 2y median & drawdown < 5%;
RECOVERY = drawdown > 10% & rising; TURBULENT = vol in top quartile of 2y **or**
drawdown > 15%; BEAR = 6m < −10%. Fallback **NEUTRAL** when none hold.
**Precedence (collisions):** `TURBULENT > BEAR > BULL > RECOVERY > NEUTRAL`.
Stress states win.
**Why:** The brief fixes the thresholds and mandates an explicit precedence.
Stress-first precedence is what makes the hand-checked anchor **Mar-2020 →
TURBULENT** hold: its 6m return (−23%) also clears BEAR, but the volatility
spike (99th pct) and 32% drawdown are the more informative fact. Verified anchors:
Mar-2020 US/IN → TURBULENT; Nov-2021 IN → BULL; Oct-2008 US → TURBULENT
(`tests/test_regime_integration.py`).
**Consequence noted:** RECOVERY is a narrow band (drawdown 10–15% with calm vol
and no BULL/BEAR trigger); when drawdown > 15% or vol spikes, TURBULENT dominates.
This is intended and will be stated in the report.
**Rejected:** BEAR-first precedence — would mislabel Mar-2020 as BEAR, failing the
anchor and hiding the crisis character of the tape.
**Revisit:** §4.5 sensitivity (±20%) may demote any threshold-dependent finding
to "fragile."

## ADR-003 — India aggregate first-day-return approach
**Status:** PENDING (Phase 2). Compute from the curated India set with sample
size stated, **or** restrict India's aggregate claim to counts + funds raised.

## ADR-004 — Verification gate as a blocking build step
**Status:** ACCEPTED (built, Phase 1).
**What:** `src/verify.py` validates `data/ipo_seed.csv` and emits the
VERIFIED-only `data/ipo_curated.csv` plus `data/derived/excluded_unverified.csv`.
Row-status semantics: **VERIFIED** requires full provenance for the three
load-bearing facts (offer_price, ipo_date, day1_return_pct) — a working
`source_url`, a `source_type`, an ISO `retrieval_date` — else the build fails;
**EXCLUDED** requires a stated reason in `notes` (ADR-007); **TO_VERIFY** (or any
unknown status) fails the gate. Exit non-zero == build fails; **no override flag**
(§8.1).
**Why:** A gate is a script that exits non-zero, not a paragraph of good
intentions. Making a VERIFIED-without-receipts row a hard failure polices the
exact failure mode (a plausible hallucinated price with no source).
**Rejected:** (a) treating TO_VERIFY as a silent skip — lets an unfinished study
look done. (b) an `--allow-unverified` override — defeats the gate's purpose.
**Tested:** `tests/test_verify.py` (10 cases: broken row fails, clean passes).

## ADR-005 — Fabrication-lint scope
**Status:** ACCEPTED (built, Phase 1).
**What:** `src/lint_fabrication.py` scans the report for numeric tokens and
fails on any that do not trace to a derived CSV value or a `references.md`
entry, by significant-digit signature (so "48.2%" matches a derived 0.482).
**In scope:** percentages, currency amounts, decimals with a fractional part,
and integers >= 100 — how prices, returns and counts actually appear.
**Exempt:** years / ISO dates (1900–2100), structural refs (§4.2, Figure 3,
ADR-002, SC-1, Phase 0, H1/H2), and bare integers < 100 that are not a
percentage or currency (meta-counts like "4–5 pairs", "250–350 words").
**Why:** The value of the lint is catching an invented price/return, not
policing "we chose 5 pairs." A conservative exemption list keeps the signal.
**Residual (named in the report):** a lint proves a number came from the
dataset, not that the dataset is right about the world; and the signature match
can coincide. Scope is revisited against the real report at Phase 4.
**Rejected:** flagging *every* digit — would drown the real signal in §-refs and
word-count ranges, training the reader to ignore the lint.
**Tested:** `tests/test_lints.py` (scope, signature match, orphan detection).

## ADR-006 — Post-listing survivorship handling
**Status:** PENDING (Phase 2/3).

## ADR-007 — Curated names excluded and why
**Status:** PENDING (Phase 2). SpaceX (Jun 2026) likely lands here.

## ADR-008 — Market-state source: Supabase `core.*` primary, yfinance fallback
**Status:** ACCEPTED. (Developer decision; brief §3.1 assumed yfinance-only.)
**What:** Source the index and India-VIX history from the local Supabase
`core.*` schema (owned by am-ai-engine) rather than a raw yfinance pull:
- `us_index` ← `core.curveiq_sp500` (FRED SP500 official + Yahoo), 1995→present
- `in_index` ← `core.curveiq_nifty50` (**niftyindices.com, NSE official**), 1995→present
- `in_vix`   ← `core.macro_daily.india_vix` (2008-03→present)
yfinance remains the source for series the DB lacks — `us_vix` (^VIX),
`us_index_alt` (^IXIC Nasdaq), `in_index_alt` (^BSESN Sensex) — and the
automatic fallback if the DB is unreachable.
**Why:** (1) yfinance's `^NSEI` history only starts **2007-09-17**, which cannot
cover 2005–2007 India listings; `core.curveiq_nifty50` carries **official NSE**
Nifty back to 1995. (2) Better provenance — official NSE / FRED beats a raw
Yahoo scrape. (3) The data comes from the user's own governed pipeline.
**Reproducibility:** the DB is touched only on `--refresh`; normal runs read the
committed `data/raw` cache, so a clean clone reproduces every number with no
credentials (§8.5). Provenance for each series is recorded in
`data/raw/manifest.json` and surfaced in `references.md`.
**Rejected:** (a) yfinance-only — loses 2005–2007 India entirely. (b) Return-splice
Sensex→Nifty to backfill the yfinance gap — unnecessary once the DB supplies a
continuous official Nifty; added a splice artifact for no benefit. (c) Commit no
cache and require DB creds to reproduce — breaks the public-reader promise.
**Open sub-decision:** whether to commit the `data/raw` index parquets to the
public repo (they are public market data, ~0.5 MB) — deferred to Phase 5 / PO.
**Revisit:** if the DB provenance for `curveiq_sp500`'s Yahoo-sourced span proves
insufficient for a headline number, pin that span to FRED explicitly.

## ADR-009 — India pre-2008 volatility fallback (realised vol)
**Status:** ACCEPTED (implements brief §2).
**What:** For dates before India VIX begins (2008-03-03), substitute annualised
21-day realised volatility of the Nifty (`realised_vol()` in `src/regime.py`),
in the same percentage-point units as a VIX. `build_vol_series()` uses the VIX
where present and only fills gaps.
**Why:** Brief mandate; lets 2005–2008 India listings be regime-labelled at all.
**Disclosure:** the substitution window is disclosed at the point of use, not
only in a footnote (`vix_close` is retained alongside `vol` so the boundary is
detectable). Tested in `tests/test_regime_integration.py`.
**Revisit:** never for methodology; the disclosure text is a report-gate item.
