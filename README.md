# Impact of Market State on IPO Outcomes — US & India, 2005–2026

An **AI-systems artifact whose subject matter is IPOs.** The finance study is
the substrate; the point is the pipeline that produces numbers you can trust —
citation-gated data, a verification step that fails the build on any unverified
figure, and a fabrication lint that ties every number in the report back to
derived data. See the full brief in `IPO_MarketState_Study_BuildPlan.md`.

> Observational study. Not investment advice, not a prediction model, not a
> screener. It describes what happened; it never tells a reader what to do.

## Thesis

Market *state* strongly shapes IPO **activity** and **average** first-day
performance — but it does not determine the fate of any individual IPO.
Idiosyncratic factors (pricing vs fundamentals, float, anchor demand, listing
mechanics) routinely sink individual IPOs in bull markets and occasionally lift
them in stressed ones.

- **SC-1** — IPO volume and mean first-day returns rise in bull/hot regimes and
  collapse in bear/turbulent ones (US + India).
- **SC-2** — Specific bull-market IPOs failed on debut, attributable to pricing
  and fundamentals, not regime. (The more interesting half.)

## Layout

```
src/
  config.py         paths, tickers, window constants
  db.py             read-only Supabase core.* access (market-state source)
  fetch_market.py   §3.1 six index/vol series, DB-primary + yfinance fallback, cached
  regime.py         §2/§4.1 market-state labelling + India realised-vol fallback
  plotting.py       §6 light theme, navy/blue palette
  verify.py         §3.3/§8.1 citation gate — fails the build on any unverified row
  lint_fabrication.py §8.2 orphan-number lint — every number must trace to data
  lint_language.py  §8.3/§8.4 advisory (fail) + causal (warn) language lint
  # analysis.py — Phase 3
data/raw/           timestamped raw pulls + manifest.json (provenance)
data/derived/       labelled + computed outputs
tests/              regime logic + anchor-date integration tests
report/             the publishable Markdown artifact (Phase 4)
social/             LinkedIn drafts (Phase 5)
decisions.md        ADR log
references.md       claim -> source -> URL -> retrieval date
```

## Run

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows path
python -m src.fetch_market        # build the data/raw cache (uses cache if present)
python -m pytest -q               # 18 tests incl. hand-checked anchor dates
```

`make help` lists the phase targets. `make all` (Phase 4) will reproduce every
figure and number from a clean clone using the committed cache — no credentials
needed. The Supabase DB is touched **only** on `--refresh`; copy `.env.example`
to `.env` and set `DATABASE_URL` if you want to re-pull raw data.

## Data provenance (§3.1, ADR-008)

Index history comes from the local Supabase `core.*` schema — **official NSE
Nifty** (niftyindices.com) back to 1995 and **FRED** S&P 500 — not a raw web
scrape. yfinance supplies only what the DB lacks (US VIX, Nasdaq, Sensex) and
acts as the automatic fallback. Every series' source and retrieval time is
recorded in `data/raw/manifest.json` and surfaced in `references.md`.

## Status

- [x] **Phase 0** — scaffold, market-state layer, regime labeller + tests
- [x] **Phase 1** — verification gate + fabrication/advisory lints (built before the data)
- [x] **Phase 2** — US Ritter aggregate, 9-name verified curated core, post-listing series (India count series dropped by design — sources disagree 3x)
- [x] **Phase 3** — regime labels, aggregate cut (SC-1), bull-failures (SC-2), ±20% sensitivity, 4 light-theme figures
- [x] **Phase 4** — 2,300-word report ([`report/`](report/ipo_market_state_study.md)); fabrication + advisory lints pass; `make all` reproduces from cache
- [ ] **Phase 5** — publication package
