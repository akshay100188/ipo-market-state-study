"""Build the curated IPO seed — §3.3 (anchor core, ~8-12 names; ADR-010).

Each case below carries HAND-VERIFIED raw facts (offer price, listing date,
day-1 close) with a working citation. The day-1 return is **computed here in
Python** from offer + close, never hand-typed — the same L1/L2 discipline as the
rest of the portfolio (deterministic numbers; prose may narrate them, never
produce them). Every day-1 close is on the same *unadjusted, as-traded* basis as
its offer price: split-adjusted feeds (yfinance shows Visa 14.12, IRCTC 145.55)
and outright-wrong feeds (yfinance shows LIC 437) are deliberately NOT used —
that mismatch is the study's own thesis in miniature.

Regime-spanning anchor core (SC-2 is the point — bull-market listings that flew
AND flopped in the *same* regime, isolating idiosyncratic factors from regime):
  US:  Meta/Facebook (broken-hot), Visa (turbulent pop), Uber (bull flop)
  IN:  IRCTC (bull pop), SBI Cards (turbulent discount), Zomato + Nykaa (bull
       pops), Paytm (bull flop), LIC (mega-issue discount)

Run:  python -m src.build_seed   # writes data/ipo_seed.csv
Then: python -m src.verify       # gate must exit 0
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .config import DATA
from .verify import REQUIRED_COLUMNS

RETRIEVED = "2026-07-23"

# ticker, name, market, ipo_date, offer_price, currency, day1_open, day1_close,
# source_url, source_type, notes (offer + secondary sources)
CASES = [
    dict(
        ticker="META", name="Meta Platforms (Facebook)", market="US",
        ipo_date="2012-05-18", offer_price=38.00, currency="USD",
        day1_open=42.05, day1_close=38.23,
        source_url="https://abcnews.com/Business/facebook-ipo-nasdaq-fb-stock-closes-ipo-price/story?id=16376373",
        source_type="news",
        notes="Offer $38 (SEC 424B4). Closed $38.23 (+0.6%), then ~-50% within four "
              "months on aggressive pricing, late size/price increase, Nasdaq open "
              "systems failure -- listing outcome decoupled from company outcome.",
    ),
    dict(
        ticker="V", name="Visa Inc.", market="US",
        ipo_date="2008-03-19", offer_price=44.00, currency="USD",
        day1_open="", day1_close=56.50,
        source_url="https://www.cnbc.com/2008/03/19/visa-shares-soar-in-first-day-of-trading.html",
        source_type="news",
        notes="Offer $44 per Visa press release (investor.visa.com) and SEC 424B4; "
              "closed $56.50 (+28%). Popped despite pre-GFC stress (turbulent tape).",
    ),
    dict(
        ticker="UBER", name="Uber Technologies", market="US",
        ipo_date="2019-05-10", offer_price=45.00, currency="USD",
        day1_open=42.00, day1_close=41.57,
        source_url="https://www.cnbc.com/2019/05/10/uber-ipo-stock-starts-trading-on-the-new-york-stock-exchange.html",
        source_type="news",
        notes="Offer $45 (Uber press release). Closed $41.57 (-7.6%) -- a bull-market "
              "listing that fell on debut: scale-vs-profitability scepticism + Lyft's "
              "weak debut + trade-war jitters. SC-2 (US).",
    ),
    dict(
        ticker="IRCTC", name="Indian Railway Catering & Tourism Corp", market="IN",
        ipo_date="2019-10-14", offer_price=320.0, currency="INR",
        day1_open="", day1_close=727.75,
        source_url="https://www.businesstoday.in/markets/company-stock/story/irctc-share-price-listing-on-nse-bse-irctc-share-closing-234142-2019-10-14",
        source_type="news",
        notes="Offer Rs 320 (upper band). NSE close Rs 727.75 (+127%). Conservative "
              "PSU pricing + small float + scarcity -> large pop.",
    ),
    dict(
        ticker="SBICARD", name="SBI Cards & Payment Services", market="IN",
        ipo_date="2020-03-16", offer_price=755.0, currency="INR",
        day1_open=661.0, day1_close=683.0,
        source_url="https://www.business-standard.com/article/news-cm/sbi-cards-ends-with-9-5-discount-on-debut-120031600978_1.html",
        source_type="news",
        notes="Offer Rs 755. Listed Rs 661 (-12.5%), ended Rs 683 on BSE (-9.5%); "
              "NSE close ~Rs 681. Listed into the COVID crash (turbulent).",
    ),
    dict(
        ticker="ZOMATO", name="Zomato Ltd", market="IN",
        ipo_date="2021-07-23", offer_price=76.0, currency="INR",
        day1_open=116.0, day1_close=125.30,
        source_url="https://www.business-standard.com/amp/article/markets/zomato-lists-53-higher-on-nse-market-cap-crosses-rs-1-trillion-mark-121072300290_1.html",
        source_type="news",
        notes="Offer Rs 76. NSE close Rs 125.30 (+65%). Bull-market pop -- pairs "
              "against Paytm's bull-market flop four months later (same regime).",
    ),
    dict(
        ticker="NYKAA", name="FSN E-Commerce Ventures (Nykaa)", market="IN",
        ipo_date="2021-11-10", offer_price=1125.0, currency="INR",
        day1_open=2001.0, day1_close=2208.0,
        source_url="https://www.india.com/business/nykaa-share-price-ipo-listing-date-bse-nse-link-allotment-details-fsn-e-commerce-ventures-ltd-5089813/",
        source_type="news",
        notes="Offer Rs 1125. NSE close Rs 2208 (+96%). Bull-market pop, days before "
              "Paytm's flop. (5:1 bonus Oct-2022 is post-listing; day-1 unaffected.)",
    ),
    dict(
        ticker="PAYTM", name="One97 Communications (Paytm)", market="IN",
        ipo_date="2021-11-18", offer_price=2150.0, currency="INR",
        day1_open=1950.0, day1_close=1564.0,
        source_url="https://www.business-standard.com/amp/article/markets/paytm-shares-partly-pare-losses-after-disappointing-initial-performance-121112600995_1.html",
        source_type="news",
        notes="Offer Rs 2150. NSE close Rs 1564 (-27%). The bull-market failure: rich "
              "pricing, path-to-profit scepticism, huge size. SC-2 flagship (IN).",
    ),
    dict(
        ticker="LICI", name="Life Insurance Corp of India", market="IN",
        ipo_date="2022-05-17", offer_price=949.0, currency="INR",
        day1_open=872.0, day1_close=875.25,
        source_url="https://www.zeebiz.com/market-news/live-updates-lic-ipo-listing-live-updates-shares-to-make-debut-on-nse-bse-today-all-you-need-to-know-184887",
        source_type="news + exchange",
        notes="Offer Rs 949. NSE close Rs 875.25 (-7.8%) per official NSE "
              "(core.nse_daily_prices, am-ai-engine DB); press: '~8% discount'. "
              "Richly-priced mega-issue into a weak tape.",
    ),
]


def build() -> pd.DataFrame:
    rows = []
    for c in CASES:
        offer = float(c["offer_price"])
        close = float(c["day1_close"])
        day1_return_pct = round((close / offer - 1.0) * 100.0, 2)   # computed, not typed
        rows.append({
            "ticker": c["ticker"], "name": c["name"], "market": c["market"],
            "ipo_date": c["ipo_date"], "offer_price": offer, "currency": c["currency"],
            "day1_open": c["day1_open"], "day1_close": close,
            "day1_return_pct": day1_return_pct,
            "source_url": c["source_url"], "source_type": c["source_type"],
            "retrieval_date": RETRIEVED, "verify_status": "VERIFIED",
            "notes": c["notes"],
        })
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def main() -> int:
    df = build()
    out = DATA / "ipo_seed.csv"
    df.to_csv(out, index=False)
    print(f"wrote {out.name}: {len(df)} curated rows")
    print(df[["ticker", "market", "ipo_date", "offer_price", "day1_close",
              "day1_return_pct"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
