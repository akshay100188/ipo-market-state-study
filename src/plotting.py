"""Light-theme, navy/blue plotting palette (§6).

One palette constant, used everywhere. No default matplotlib colours, no
dark-mode figures. Import ``apply_house_style()`` at the top of any plotting
routine and pull colours from ``PALETTE``.
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# Navy/blue on light, matching akshaybhatnagar.me accents.
PALETTE = {
    "bg": "#ffffff",
    "fg": "#1a2233",        # near-navy text
    "grid": "#e4e8f0",
    "navy": "#1f3a5f",      # primary
    "blue": "#2f6fb0",      # secondary
    "sky": "#7fb2e0",       # tertiary / light fill
    "accent": "#c0392b",    # sparingly, for negative / highlight
    "muted": "#8a95a5",
}

# Ordered series colours for categorical charts (regimes, markets).
SERIES = [PALETTE["navy"], PALETTE["blue"], PALETTE["sky"], PALETTE["muted"]]

# Stable regime → colour mapping so regimes read the same across every figure.
REGIME_COLORS = {
    "BULL": PALETTE["navy"],
    "RECOVERY": PALETTE["blue"],
    "TURBULENT": "#e08a3c",   # warm amber = stress
    "BEAR": PALETTE["accent"],
    "NEUTRAL": PALETTE["muted"],
}


def apply_house_style() -> None:
    """Set global rcParams to the light navy/blue house style."""
    mpl.rcParams.update(
        {
            "figure.facecolor": PALETTE["bg"],
            "axes.facecolor": PALETTE["bg"],
            "savefig.facecolor": PALETTE["bg"],
            "axes.edgecolor": PALETTE["muted"],
            "axes.labelcolor": PALETTE["fg"],
            "axes.titlecolor": PALETTE["fg"],
            "text.color": PALETTE["fg"],
            "xtick.color": PALETTE["fg"],
            "ytick.color": PALETTE["fg"],
            "grid.color": PALETTE["grid"],
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 11,
            "figure.dpi": 130,
            "savefig.dpi": 130,
            "savefig.bbox": "tight",
        }
    )


def caption(fig, text: str) -> None:
    """Attach a source/retrieval caption beneath a figure (§6 requirement)."""
    fig.text(
        0.01,
        -0.02,
        text,
        ha="left",
        va="top",
        fontsize=8,
        color=PALETTE["muted"],
        wrap=True,
    )
