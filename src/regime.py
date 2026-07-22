"""Market-state (regime) labelling — §2, §4.1.

A regime label is computed *in code* at a given date from index and
volatility history. Never eyeballed, never hand-assigned.

Signals, all as-of and trailing to the target date:
  - index trailing 3m and 6m return
  - volatility level and its percentile vs trailing 2y
  - drawdown from the trailing-1y index high

Labels (thresholds are a decision — logged as ADR-002 and perturbed ±20% in
the sensitivity analysis, §4.5):
  - BULL       6m return > +5%, vol below its 2y median, drawdown < 5%
  - RECOVERY   index rising but still > 10% below its trailing-1y high
  - TURBULENT  vol in the top quartile of trailing 2y  OR  drawdown > 15%
  - BEAR       6m return < -10%
  - NEUTRAL    fallback when no labelled condition holds

Precedence when conditions collide (ADR-002): TURBULENT > BEAR > BULL >
RECOVERY > NEUTRAL. Stress states win — a date that is both down >10% over 6m
*and* in a volatility spike is TURBULENT, not BEAR. This is what makes the
hand-checked anchor Mar-2020 → TURBULENT hold even though its 6m return also
clears the BEAR threshold.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

import numpy as np
import pandas as pd

from .config import REALISED_VOL_WINDOW, TRADING_DAYS_YEAR


@dataclass(frozen=True)
class RegimeThresholds:
    """All numeric knobs in one place so §4.5 can perturb them ±20%."""

    bull_6m_return: float = 0.05
    bull_vol_pct_max: float = 0.50      # "below 2y median" = below 50th pct
    bull_drawdown_max: float = 0.05
    recovery_below_high: float = 0.10
    turbulent_vol_pct: float = 0.75     # "top quartile"
    turbulent_drawdown: float = 0.15
    bear_6m_return: float = -0.10

    def perturb(self, factor: float) -> "RegimeThresholds":
        """Scale every threshold by (1 + factor). factor=+0.2 → +20%.

        Signs are preserved (bear_6m_return stays negative). Percentile knobs
        are clamped to (0, 1) so a perturbation can never leave the unit range.
        """
        def clamp01(x: float) -> float:
            return min(max(x, 1e-6), 1 - 1e-6)

        return RegimeThresholds(
            bull_6m_return=self.bull_6m_return * (1 + factor),
            bull_vol_pct_max=clamp01(self.bull_vol_pct_max * (1 + factor)),
            bull_drawdown_max=self.bull_drawdown_max * (1 + factor),
            recovery_below_high=self.recovery_below_high * (1 + factor),
            turbulent_vol_pct=clamp01(self.turbulent_vol_pct * (1 + factor)),
            turbulent_drawdown=self.turbulent_drawdown * (1 + factor),
            bear_6m_return=self.bear_6m_return * (1 + factor),
        )


DEFAULT_THRESHOLDS = RegimeThresholds()

# Precedence order, most-severe first (ADR-002).
PRECEDENCE = ["TURBULENT", "BEAR", "BULL", "RECOVERY", "NEUTRAL"]


# --- Vol series construction (India pre-2008 fallback, §2) ----------------

def realised_vol(index_close: pd.Series, window: int = REALISED_VOL_WINDOW) -> pd.Series:
    """Annualised rolling realised volatility, in the same % units as a VIX.

    A VIX quotes annualised vol in percentage points (e.g. 20.0 = 20%). We
    match that: stdev of daily log returns * sqrt(252) * 100.
    """
    log_ret = np.log(index_close / index_close.shift(1))
    rv = log_ret.rolling(window).std() * np.sqrt(TRADING_DAYS_YEAR) * 100.0
    return rv


def build_vol_series(index_close: pd.Series, vix_close: Optional[pd.Series]) -> pd.Series:
    """Return a continuous vol series, filling any VIX gap with realised vol.

    Used for India: India VIX only starts ~2008-09, so 2005-2008 listings fall
    back to annualised 21-day realised Nifty volatility. Wherever the VIX is
    present it takes priority; realised vol only fills the gaps. The caller is
    responsible for disclosing the substitution at the point of use.
    """
    rv = realised_vol(index_close)
    if vix_close is None or vix_close.dropna().empty:
        return rv.rename("vol")
    combined = vix_close.reindex(index_close.index)
    combined = combined.where(combined.notna(), rv)
    return combined.rename("vol")


# --- Signal computation ---------------------------------------------------

def _asof(series: pd.Series, date: pd.Timestamp) -> Optional[float]:
    """Most recent value at or before ``date`` (None if series starts later)."""
    s = series.dropna()
    s = s[s.index <= date]
    if s.empty:
        return None
    return float(s.iloc[-1])


def compute_signals(
    market: pd.DataFrame,
    date,
    vol_col: str = "vol",
    index_col: str = "index_close",
) -> dict:
    """Compute the regime signals as-of ``date``.

    ``market`` is a daily DataFrame indexed by date, with at least an index
    close column and a vol column (see build_vol_series). Windows are
    calendar-based (nearest prior trading day), which is robust to holidays.

    Returns a dict of signals; any that cannot be computed (insufficient
    history) are None, and the labeller treats a None as "condition not met".
    """
    date = pd.Timestamp(date)
    idx = market[index_col].dropna()
    vol = market[vol_col].dropna()

    px_now = _asof(idx, date)
    signals: dict = {
        "date": date,
        "index_level": px_now,
        "ret_3m": None,
        "ret_6m": None,
        "vol_level": _asof(vol, date),
        "vol_pct_2y": None,
        "drawdown_1y": None,
    }
    if px_now is None:
        return signals

    px_3m = _asof(idx, date - pd.DateOffset(months=3))
    px_6m = _asof(idx, date - pd.DateOffset(months=6))
    if px_3m:
        signals["ret_3m"] = px_now / px_3m - 1.0
    if px_6m:
        signals["ret_6m"] = px_now / px_6m - 1.0

    # Drawdown from trailing-1y high.
    window_1y = idx[(idx.index > date - pd.DateOffset(years=1)) & (idx.index <= date)]
    if not window_1y.empty:
        signals["drawdown_1y"] = 1.0 - px_now / float(window_1y.max())

    # Vol percentile vs trailing 2y.
    vol_now = signals["vol_level"]
    window_2y = vol[(vol.index > date - pd.DateOffset(years=2)) & (vol.index <= date)]
    if vol_now is not None and len(window_2y) >= 20:
        signals["vol_pct_2y"] = float((window_2y <= vol_now).mean())

    return signals


# --- Labelling ------------------------------------------------------------

def _conditions(signals: dict, t: RegimeThresholds) -> dict:
    """Boolean truth of each regime's defining condition. Missing signal → False."""
    ret_6m = signals.get("ret_6m")
    vol_pct = signals.get("vol_pct_2y")
    dd = signals.get("drawdown_1y")

    bull = (
        ret_6m is not None and ret_6m > t.bull_6m_return
        and vol_pct is not None and vol_pct < t.bull_vol_pct_max
        and dd is not None and dd < t.bull_drawdown_max
    )
    recovery = dd is not None and dd > t.recovery_below_high and (
        # "index rising": positive over the shorter 3m window if available,
        # else non-negative 6m.
        (signals.get("ret_3m") is not None and signals["ret_3m"] > 0)
        or (signals.get("ret_3m") is None and ret_6m is not None and ret_6m >= 0)
    )
    turbulent = (
        (vol_pct is not None and vol_pct >= t.turbulent_vol_pct)
        or (dd is not None and dd > t.turbulent_drawdown)
    )
    bear = ret_6m is not None and ret_6m < t.bear_6m_return

    return {"BULL": bull, "RECOVERY": recovery, "TURBULENT": turbulent, "BEAR": bear}


def label_from_signals(signals: dict, thresholds: RegimeThresholds = DEFAULT_THRESHOLDS) -> str:
    """Resolve a single regime label using the precedence order (ADR-002)."""
    cond = _conditions(signals, thresholds)
    for label in PRECEDENCE:
        if label == "NEUTRAL":
            return "NEUTRAL"
        if cond.get(label):
            return label
    return "NEUTRAL"


def label_date(
    market: pd.DataFrame,
    date,
    thresholds: RegimeThresholds = DEFAULT_THRESHOLDS,
    vol_col: str = "vol",
    index_col: str = "index_close",
) -> str:
    """Convenience: signals → label for a single date."""
    return label_from_signals(
        compute_signals(market, date, vol_col=vol_col, index_col=index_col),
        thresholds,
    )
