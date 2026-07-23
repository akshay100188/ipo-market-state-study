# LinkedIn drafts — for PO review

Two drafts, per the build brief §7. **Do not schedule or publish.** Both point
at the website artifact (blog-first). Restrained register, matching the
Adjudicator arc. No hashtag spam, no rocket emojis. Replace the link with the
final `akshaybhatnagar.me` URL before posting.

---

## Post 1 — the finding (this is the one that travels)

Over eight days in November 2021, two Indian companies listed into the same bull
market. Nykaa closed its first day up 96%. Paytm closed down 27%.

Same tape. Same week. Opposite fates.

I spent some time on a question that sounds simple: does the market's mood decide
an IPO's outcome? The aggregate answer is "partly." Across 2005–2025, US IPO
volume tracks the regime cleanly — 309 listings in the calm of 2021, then 38 in
the volatile 2022. When the VIX spikes, issuance dries up.

But the *individual* outcome is a different story. In that 2021 bull market,
Zomato and Nykaa flew on debut and Paytm fell hard — and the regime was, by
construction, identical for all three. What separated them wasn't the market.
It was pricing, float, and how much profitability investors were willing to take
on faith. The market sets the weather; the company still has to fly the plane.

The counterintuitive half: a company's first-day result tells you almost nothing
about the company. Facebook broke on debut in 2012 and fell ~50% in four months
before becoming one of the decade's great compounders. Debut direction and
one-year direction turned out to be close to independent.

Full write-up, with the matched pairs and the data: [link]

---

## Post 2 — the method (this is the one that serves the thesis)

Here's how I built an AI-assisted research pipeline that produces numbers I'd
put my name on.

The subject was IPOs and market regimes. But the real problem was trust: offer
prices and listing-day closes are exactly the kind of specific, plausible number
an AI will confidently get wrong — and a casual data pull will get subtly wrong.
I hit both. A common free price feed reported Visa's and IRCTC's debut prices on
a later split-adjusted basis, and reported LIC's listing price at roughly half
its true value. A naïve pipeline would have shipped those.

So the machinery is the product, and the finance is the demonstration:

— A verification gate, as running code. No IPO enters a chart unless its offer
price, date and first-day return each carry a working source link and a
retrieval date. Unverified rows fail the build. No override flag. That's why the
case set is 9 rock-solid names, not a shakier 30.

— A fabrication lint. Every number in the final write-up is traced back to the
data or a citation; an invented figure fails the build. On the last run it
checked 40 numeric claims and found zero orphans.

— Determinism. Every number is produced by Python. The language model drafts
prose around numbers it's handed; it never produces one.

And the part I'm most deliberate about: the limitations are stated flatly, not
smoothed over. A lint proves a number came from the dataset — not that the
dataset is right about the world. The curated set is a marquee sample, not a
random one. I dropped the India IPO-count series entirely, because two reputable
sources disagreed threefold on the definition — cutting the claim was the honest
call.

Code and data are public and run end-to-end: [repo link]
Write-up: [site link]
