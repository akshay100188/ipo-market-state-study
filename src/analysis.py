"""Analysis — §4.1–4.5. Deterministic; runs only on VERIFIED data.

Outputs (data/derived/):
  ipo_labelled.csv     curated IPOs + regime label + signals + post-listing
  coverage.csv         regime x market counts (small cells flagged)
  bull_failures.csv    regime in {BULL,RECOVERY} AND day-1 < 0  (SC-2)
  sensitivity.csv      per-name label under thresholds perturbed +/-20% (§4.5)
  aggregate_us.csv     US Ritter activity vs annual S&P return + mean VIX (SC-1)

Figures (figures/, light navy theme, captioned):
  aggregate_us.png, curated_regime_scatter.png, sensitivity_table.png
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DATA, DERIVED, FIGURES
from .fetch_market import load_market_frames
from .regime import (
    DEFAULT_THRESHOLDS,
    compute_signals,
    label_date,
    label_from_signals,
)

RETRIEVED = "2026-07-23"


# --- §4.1 regime labelling ------------------------------------------------

def label_curated(frames=None) -> pd.DataFrame:
    frames = frames or load_market_frames()
    cur = pd.read_csv(DATA / "ipo_curated.csv")
    prices = pd.read_csv(DERIVED / "post_listing_returns.csv")
    out = []
    for _, r in cur.iterrows():
        m = "us" if r["market"] == "US" else "in"
        s = compute_signals(frames[m], r["ipo_date"])
        row = {
            "ticker": r["ticker"], "name": r["name"], "market": r["market"],
            "ipo_date": r["ipo_date"], "day1_return_pct": r["day1_return_pct"],
            "regime": label_from_signals(s),
            "ret_6m_signal": round(s["ret_6m"], 4) if s["ret_6m"] is not None else "",
            "drawdown_1y": round(s["drawdown_1y"], 4) if s["drawdown_1y"] is not None else "",
            "vol_pct_2y": round(s["vol_pct_2y"], 4) if s["vol_pct_2y"] is not None else "",
        }
        pr = prices[prices["ticker"] == r["ticker"]]
        for h in ["1M", "3M", "6M", "12M"]:
            col = f"ret_{h}"
            row[f"post_{col}"] = pr.iloc[0][col] if len(pr) and col in pr else ""
        out.append(row)
    df = pd.DataFrame(out)
    df.to_csv(DERIVED / "ipo_labelled.csv", index=False)
    return df


def coverage_table(labelled: pd.DataFrame) -> pd.DataFrame:
    cov = (labelled.groupby(["market", "regime"]).size()
           .rename("n").reset_index().sort_values(["market", "regime"]))
    cov["small_cell"] = cov["n"] < 3      # flag cells too small to be estimates
    cov.to_csv(DERIVED / "coverage.csv", index=False)
    return cov


# --- §4.4 bull-market failures (SC-2) ------------------------------------

def bull_failures(labelled: pd.DataFrame) -> pd.DataFrame:
    bf = labelled[
        labelled["regime"].isin(["BULL", "RECOVERY"])
        & (labelled["day1_return_pct"].astype(float) < 0)
    ].copy()
    bf.to_csv(DERIVED / "bull_failures.csv", index=False)
    return bf


# --- §4.5 sensitivity (+/-20% on every threshold) ------------------------

def sensitivity(frames=None) -> pd.DataFrame:
    frames = frames or load_market_frames()
    cur = pd.read_csv(DATA / "ipo_curated.csv")
    scenarios = {
        "base": DEFAULT_THRESHOLDS,
        "minus20": DEFAULT_THRESHOLDS.perturb(-0.20),
        "plus20": DEFAULT_THRESHOLDS.perturb(0.20),
    }
    rows = []
    for _, r in cur.iterrows():
        m = "us" if r["market"] == "US" else "in"
        s = compute_signals(frames[m], r["ipo_date"])
        labels = {name: label_from_signals(s, t) for name, t in scenarios.items()}
        rows.append({
            "ticker": r["ticker"], "market": r["market"], "ipo_date": r["ipo_date"],
            **{f"regime_{k}": v for k, v in labels.items()},
            "fragile": len(set(labels.values())) > 1,
        })
    df = pd.DataFrame(rows)
    df.to_csv(DERIVED / "sensitivity.csv", index=False)
    return df


# --- §4.2 aggregate cut (SC-1, US) ---------------------------------------

def annual_market_signals(frames, market: str) -> pd.DataFrame:
    df = frames[market]
    idx = df["index_close"].dropna()
    vix = df["vix_close"].dropna()
    rows = []
    for year in range(2005, 2026):
        yr = idx[(idx.index >= f"{year}-01-01") & (idx.index <= f"{year}-12-31")]
        if yr.empty:
            continue
        vy = vix[(vix.index >= f"{year}-01-01") & (vix.index <= f"{year}-12-31")]
        rows.append({
            "year": year,
            "index_ret_pct": round((yr.iloc[-1] / yr.iloc[0] - 1) * 100, 2),
            "mean_vix": round(vy.mean(), 2) if len(vy) else np.nan,
        })
    return pd.DataFrame(rows)


def aggregate_cut(frames=None) -> tuple[pd.DataFrame, dict]:
    frames = frames or load_market_frames()
    act = pd.read_csv(DATA / "ipo_activity.csv")
    us = act[act["market"] == "US"].copy()
    us["year"] = us["year"].astype(int)
    sig = annual_market_signals(frames, "us")
    m = us.merge(sig, on="year", how="inner")
    for c in ["n_ipos", "mean_first_day_return_pct"]:
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m.to_csv(DERIVED / "aggregate_us.csv", index=False)

    n = len(m)
    corr = {
        "n_years": n,
        "corr_count_vs_index_ret": round(m["n_ipos"].corr(m["index_ret_pct"]), 3),
        "corr_meanret_vs_index_ret": round(m["mean_first_day_return_pct"].corr(m["index_ret_pct"]), 3),
        "corr_count_vs_meanvix": round(m["n_ipos"].corr(m["mean_vix"]), 3),
    }
    return m, corr


def write_summary(labelled, cov, bf, sens, corr) -> pd.DataFrame:
    """Key derived stats, at the precision the report cites them, so the
    fabrication lint (§8.2) can trace every number in the prose."""
    us = labelled[labelled["market"] == "US"]
    ind = labelled[labelled["market"] == "IN"]
    rows = {
        "n_curated": len(labelled),
        "n_us": len(us),
        "n_india": len(ind),
        "n_regimes_used": labelled["regime"].nunique(),
        "n_fragile": int(sens["fragile"].sum()),
        "n_robust": int((~sens["fragile"]).sum()),
        "n_bull_failures": len(bf),
        "agg_n_years": corr["n_years"],
        "corr_count_index_ret": corr["corr_count_vs_index_ret"],
        "corr_meanret_index_ret": corr["corr_meanret_vs_index_ret"],
        "corr_count_meanvix": corr["corr_count_vs_meanvix"],
        "n_bull_curated": int((labelled["regime"] == "BULL").sum()),
        "sensitivity_perturbation_pct": 20,
    }
    df = pd.DataFrame([{"metric": k, "value": v} for k, v in rows.items()])
    df.to_csv(DERIVED / "summary.csv", index=False)
    return df


def run() -> dict:
    frames = load_market_frames()
    labelled = label_curated(frames)
    cov = coverage_table(labelled)
    bf = bull_failures(labelled)
    sens = sensitivity(frames)
    agg, corr = aggregate_cut(frames)
    write_summary(labelled, cov, bf, sens, corr)

    print("== curated regimes ==")
    print(labelled[["ticker", "market", "regime", "day1_return_pct"]].to_string(index=False))
    print("\n== coverage (small_cell = n<3) ==")
    print(cov.to_string(index=False))
    print("\n== bull-market failures (SC-2) ==")
    print(bf[["ticker", "market", "regime", "day1_return_pct"]].to_string(index=False))
    print("\n== sensitivity (fragile = label flips under +/-20%) ==")
    print(sens.to_string(index=False))
    print(f"\n== aggregate (SC-1, US, n={corr['n_years']}) ==")
    print(f"  corr(IPO count, S&P annual return)      = {corr['corr_count_vs_index_ret']}")
    print(f"  corr(mean first-day ret, S&P ann ret)   = {corr['corr_meanret_vs_index_ret']}")
    print(f"  corr(IPO count, mean VIX)               = {corr['corr_count_vs_meanvix']}")
    return {"corr": corr, "n_fragile": int(sens["fragile"].sum())}


if __name__ == "__main__":
    run()
