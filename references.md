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

**India annual activity — count series deliberately not published (ADR-003).**
Cross-checking surfaced a ~3x disagreement between reputable compilers on India
mainboard IPO *counts* (PRIME Database 40 vs EY 138 for CY2022) driven by
mainboard-vs-SME definition; *funds raised* roughly reconcile but counts do not,
so the count claim is dropped per the brief's "reconcile or drop and say so."
India's aggregate evidence is limited to activity *direction* (2021 boom → 2022
collapse) and the curated set's first-day returns (n stated). Sources consulted:
[EY India IPO Trends](https://www.ey.com/en_in/services/ipo/india-ipo-trends-report),
PRIME Database (reported via Business Standard). Both primary trackers 403
automated fetches (Cloudflare), a further reason for exclusion.

## Curated IPO case dataset (§3.3)

Anchor core of 9 (ADR-010). Each day-1 close is on the same **unadjusted** basis
as its offer price; the day-1 return is computed in Python (`src/build_seed.py`),
never hand-typed. Full provenance is enforced by `verify.py` and lives in
`data/ipo_seed.csv` (`source_url`, `source_type`, `retrieval_date`, `notes`).
All retrieved 2026-07-23.

| Name | Offer | Day-1 close | Day-1 | Source |
|---|---|---|---|---|
| Meta / Facebook (2012-05-18) | $38.00 | $38.23 | +0.6% | [ABC News](https://abcnews.com/Business/facebook-ipo-nasdaq-fb-stock-closes-ipo-price/story?id=16376373) |
| Visa (2008-03-19) | $44.00 | $56.50 | +28.4% | [CNBC](https://www.cnbc.com/2008/03/19/visa-shares-soar-in-first-day-of-trading.html) · offer per Visa PR / SEC 424B4 |
| Uber (2019-05-10) | $45.00 | $41.57 | −7.6% | [CNBC](https://www.cnbc.com/2019/05/10/uber-ipo-stock-starts-trading-on-the-new-york-stock-exchange.html) |
| IRCTC (2019-10-14) | ₹320 | ₹727.75 | +127.4% | [Business Today](https://www.businesstoday.in/markets/company-stock/story/irctc-share-price-listing-on-nse-bse-irctc-share-closing-234142-2019-10-14) |
| SBI Cards (2020-03-16) | ₹755 | ₹683.00 | −9.5% | [Business Standard](https://www.business-standard.com/article/news-cm/sbi-cards-ends-with-9-5-discount-on-debut-120031600978_1.html) |
| Zomato (2021-07-23) | ₹76 | ₹125.30 | +64.9% | [Business Standard](https://www.business-standard.com/amp/article/markets/zomato-lists-53-higher-on-nse-market-cap-crosses-rs-1-trillion-mark-121072300290_1.html) |
| Nykaa / FSN (2021-11-10) | ₹1125 | ₹2208.00 | +96.3% | [India.com](https://www.india.com/business/nykaa-share-price-ipo-listing-date-bse-nse-link-allotment-details-fsn-e-commerce-ventures-ltd-5089813/) |
| Paytm / One97 (2021-11-18) | ₹2150 | ₹1564.00 | −27.3% | [Business Standard](https://www.business-standard.com/amp/article/markets/paytm-shares-partly-pare-losses-after-disappointing-initial-performance-121112600995_1.html) |
| LIC (2022-05-17) | ₹949 | ₹875.25 | −7.8% | [Zee Business](https://www.zeebiz.com/market-news/live-updates-lic-ipo-listing-live-updates-shares-to-make-debut-on-nse-bse-today-all-you-need-to-know-184887) · close per official NSE (`core.nse_daily_prices`) |

Post-listing trajectories (+1M/3M/6M/12M, absolute + excess vs home index) are
in `data/derived/post_listing_returns.csv`; fetch gaps/survivorship in
`data/derived/price_fetch_log.csv`.
