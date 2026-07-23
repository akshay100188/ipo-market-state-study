# References

Every published claim traces to a row here: **claim → source → URL → retrieval
date**. This appendix renders visibly on the artifact (§6) — its visibility is
part of the argument. The fabrication lint (§5) asserts every numeric token in
the report traces to derived data or an entry in this file.

Retrieval dates are UTC. Machine-fetched series also carry a timestamped
provenance record in `data/raw/manifest.json`.

---

## Market-state layer (§3.1)

| Series | Source of record | URL | Coverage | Retrieved |
|---|---|---|---|---|
| Nifty 50 (India index) | `core.curveiq_nifty50` — **niftyindices.com, NSE official** (via am-ai-engine) | https://www.niftyindices.com/reports/historical-data | 1995-01-01 → 2026-07-01 | 2026-07-22 |
| S&P 500 (US index) | `core.curveiq_sp500` — FRED `SP500` (official) + Yahoo `^GSPC` (via am-ai-engine) | https://fred.stlouisfed.org/series/SP500 | 1995-01-03 → 2026-07-21 | 2026-07-22 |
| India VIX | `core.macro_daily.india_vix` (via am-ai-engine) | https://www.nseindia.com/reports-indices-historical-india-vix | 2008-03-03 → 2026-07-22 | 2026-07-22 |
| CBOE VIX (US) | Yahoo Finance `^VIX` | https://finance.yahoo.com/quote/%5EVIX/history | 2004-01-02 → 2026-07-22 | 2026-07-22 |
| Nasdaq Composite (US alt) | Yahoo Finance `^IXIC` | https://finance.yahoo.com/quote/%5EIXIC/history | 2004-01-02 → 2026-07-22 | 2026-07-22 |
| BSE Sensex (India alt) | Yahoo Finance `^BSESN` | https://finance.yahoo.com/quote/%5EBSESN/history | 2004-01-02 → 2026-07-22 | 2026-07-22 |

**India pre-2008 volatility (§2, ADR-009):** India VIX begins 2008-03-03. For
listings before that date, volatility is the annualised 21-day realised
volatility of the Nifty 50, in the same percentage-point units as a VIX. The
substitution window is disclosed at every point of use.

---

## Aggregate IPO-activity layer (§3.2)

| Claim | Source | URL | Retrieved |
|---|---|---|---|
| US annual IPO counts + mean first-day returns, 2005–2025 | Jay Ritter (Univ. of Florida), **IPOALL.xlsx** — monthly IPO counts + average first-day returns, 1960–2025 (net-count definition). Annual figures are aggregated from his monthly rows (sum of net counts; net-count-weighted mean first-day return). Validated against his published annual figures (1999→476/71.0%, 2020→165/41.6%, 2021→309/32.0%). | https://site.warrington.ufl.edu/ritter/files/IPOALL.xlsx | 2026-07-23 |

_India annual activity: pending ADR-003 decision + cross-checked acquisition
(≥2 sources per year, or year dropped)._

## Curated IPO case dataset (§3.3)
_To be populated in Phase 2. Each row's `offer_price`, `ipo_date`,
`day1_return_pct` carries a working `source_url` and `retrieval_date` before it
enters any published figure._
