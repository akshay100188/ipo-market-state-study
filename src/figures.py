"""Figure generation — §4, §6. Light theme, navy/blue palette, every figure
captioned with source + retrieval date and regenerable from derived CSVs.

Run after analysis:  python -m src.analysis && python -m src.figures
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .config import DERIVED, FIGURES
from .plotting import PALETTE, REGIME_COLORS, apply_house_style, caption

RETRIEVED = "2026-07-23"
SRC_RITTER = "Source: Jay Ritter (UF) IPOALL.xlsx; S&P 500 & VIX via core.* / Yahoo. Retrieved 2026-07-23."
SRC_CURATED = "Source: hand-verified curated set (see references.md). Retrieved 2026-07-23."


def fig_aggregate() -> None:
    """SC-1: US IPO volume + mean first-day return vs market state, by year."""
    df = pd.read_csv(DERIVED / "aggregate_us.csv")
    apply_house_style()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1.4]})

    # Panel 1: IPO count bars, coloured by S&P annual return sign; VIX line.
    colors = [PALETTE["navy"] if r >= 0 else PALETTE["accent"] for r in df["index_ret_pct"]]
    ax1.bar(df["year"], df["n_ipos"], color=colors, width=0.7,
            label="IPO count (navy=S&P up year, red=down)")
    ax1.set_ylabel("US IPOs (net count)")
    axv = ax1.twinx()
    axv.plot(df["year"], df["mean_vix"], color=PALETTE["blue"], marker="o", ms=3, lw=1.6)
    axv.set_ylabel("Mean VIX", color=PALETTE["blue"])
    axv.tick_params(axis="y", labelcolor=PALETTE["blue"])
    axv.grid(False)
    ax1.set_title("IPO volume collapses when volatility spikes (2008, 2022); booms when calm (2021)",
                  fontsize=11)

    # Panel 2: mean first-day return line (the nuance: not tracking index return).
    ax2.plot(df["year"], df["mean_first_day_return_pct"], color=PALETTE["navy"],
             marker="o", ms=3, lw=1.6)
    ax2.axhline(0, color=PALETTE["muted"], lw=0.8)
    ax2.set_ylabel("Mean first-day\nreturn (%)")
    ax2.set_xlabel("Year")
    ax2.set_title("Mean first-day return spikes in hot-issue windows (2020-21), "
                  "not simply 'up' years", fontsize=10)

    caption(fig, SRC_RITTER + "  Observational; associations, not causation.")
    fig.tight_layout()
    fig.savefig(FIGURES / "aggregate_us.png")
    plt.close(fig)


def fig_curated_scatter() -> None:
    """SC-2: day-1 return by regime — same regime, opposite outcomes."""
    df = pd.read_csv(DERIVED / "ipo_labelled.csv")
    apply_house_style()
    order = ["BULL", "RECOVERY", "TURBULENT", "NEUTRAL", "BEAR"]
    present = [r for r in order if r in set(df["regime"])]
    xpos = {r: i for i, r in enumerate(present)}
    fig, ax = plt.subplots(figsize=(9, 5.2))

    # Deterministic spread within each regime column so labels don't collide.
    df = df.copy()
    df["_x"] = [float(xpos[r]) for r in df["regime"]]
    for reg, grp in df.groupby("regime"):
        k = len(grp)
        offs = ([0.0] if k == 1 else list(__import__("numpy").linspace(-0.16, 0.16, k)))
        for off, idx in zip(offs, grp.index):
            df.at[idx, "_x"] = xpos[reg] + off

    for _, r in df.iterrows():
        x, y = r["_x"], float(r["day1_return_pct"])
        us = r["market"] == "US"
        ax.scatter(x, y, s=95, marker="s" if us else "o",
                   color=PALETTE["navy"] if y >= 0 else PALETTE["accent"],
                   edgecolor="white", linewidth=1, zorder=3)
        ax.annotate(r["ticker"], (x, y), fontsize=8,
                    ha="center", va="bottom" if y >= 0 else "top",
                    xytext=(0, 7 if y >= 0 else -8), textcoords="offset points")
    ax.axhline(0, color=PALETTE["muted"], lw=1)
    ax.set_xticks(range(len(present)))
    ax.set_xticklabels(present)
    ax.set_xlim(-0.5, len(present) - 0.5)
    ax.set_ylabel("First-day return (%)")
    ax.set_title("Same regime, opposite outcomes: in the 2021 BULL, Zomato/Nykaa flew, "
                 "Paytm fell", fontsize=11)
    ax.text(0.99, 0.97, "square = US, circle = India;\nnavy = pop, red = fell",
            transform=ax.transAxes, fontsize=8, color=PALETTE["muted"],
            ha="right", va="top")
    caption(fig, SRC_CURATED + "  Marquee-name selection bias applies; illustrative, not a random sample.")
    fig.tight_layout()
    fig.savefig(FIGURES / "curated_regime_scatter.png")
    plt.close(fig)


def fig_sensitivity() -> None:
    """§4.5: per-name label under +/-20% threshold perturbation."""
    df = pd.read_csv(DERIVED / "sensitivity.csv")
    apply_house_style()
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.axis("off")
    cols = ["ticker", "market", "regime_minus20", "regime_base", "regime_plus20", "fragile"]
    headers = ["Name", "Mkt", "-20%", "base", "+20%", "fragile?"]
    table = ax.table(cellText=df[cols].values, colLabels=headers,
                     cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    for (row, col), cell in table.get_cells().items() if hasattr(table, "get_cells") else table.get_celld().items():
        if row == 0:
            cell.set_facecolor(PALETTE["navy"])
            cell.set_text_props(color="white", fontweight="bold")
        elif col == 5:
            frag = str(df.iloc[row - 1]["fragile"]) == "True"
            cell.set_facecolor("#f6e2c8" if frag else "#e5efe0")
    ax.set_title("Regime labels under +/-20% threshold perturbation "
                 "(fragile = flips; SC-2 BULL trio is robust)", fontsize=11)
    caption(fig, SRC_RITTER + "  Fragile labels are reported as fragile, not as findings.")
    fig.tight_layout()
    fig.savefig(FIGURES / "sensitivity_table.png")
    plt.close(fig)


def fig_pipeline() -> None:
    """§5: acquisition -> verification -> analysis -> narrative."""
    apply_house_style()
    fig, ax = plt.subplots(figsize=(9, 2.8))
    ax.axis("off")
    stages = [
        ("ACQUISITION", "Ritter, official NSE/\nFRED, cited curated set"),
        ("VERIFICATION", "verify.py gate +\nfabrication lint"),
        ("ANALYSIS", "regime labels,\naggregate, sensitivity"),
        ("NARRATIVE", "report; LLM narrates,\nnever produces numbers"),
    ]
    n = len(stages)
    for i, (title, sub) in enumerate(stages):
        x = i / n + 0.02
        w = 1 / n - 0.06
        ax.add_patch(plt.Rectangle((x, 0.3), w, 0.4, transform=ax.transAxes,
                                   facecolor=PALETTE["sky"], edgecolor=PALETTE["navy"], lw=1.5))
        ax.text(x + w / 2, 0.58, title, transform=ax.transAxes, ha="center",
                fontsize=10, fontweight="bold", color=PALETTE["navy"])
        ax.text(x + w / 2, 0.42, sub, transform=ax.transAxes, ha="center",
                fontsize=8, color=PALETTE["fg"])
        if i < n - 1:
            ax.annotate("", xy=(x + w + 0.02, 0.5), xytext=(x + w, 0.5),
                        xycoords="axes fraction",
                        arrowprops=dict(arrowstyle="->", color=PALETTE["navy"], lw=1.5))
    ax.set_title("Pipeline: every number is deterministic; the gate sits before the analysis",
                 fontsize=11)
    fig.savefig(FIGURES / "pipeline.png")
    plt.close(fig)


def run() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig_aggregate()
    fig_curated_scatter()
    fig_sensitivity()
    fig_pipeline()
    print(f"wrote figures to {FIGURES}/: aggregate_us.png, curated_regime_scatter.png, "
          f"sensitivity_table.png, pipeline.png")


if __name__ == "__main__":
    run()
