"""Pure-logic tests for the regime labeller — no network, no data files."""
import numpy as np
import pandas as pd

from src.regime import (
    DEFAULT_THRESHOLDS,
    RegimeThresholds,
    build_vol_series,
    label_from_signals,
    realised_vol,
)


def sig(**kw):
    """Build a full signal dict, defaulting unmentioned signals to None."""
    base = dict(ret_3m=None, ret_6m=None, vol_level=None, vol_pct_2y=None, drawdown_1y=None)
    base.update(kw)
    return base


def test_bull():
    s = sig(ret_6m=0.10, ret_3m=0.05, vol_pct_2y=0.30, drawdown_1y=0.02)
    assert label_from_signals(s) == "BULL"


def test_bear():
    s = sig(ret_6m=-0.15, ret_3m=-0.08, vol_pct_2y=0.40, drawdown_1y=0.10)
    assert label_from_signals(s) == "BEAR"


def test_turbulent_via_drawdown_beats_bear():
    # 6m return clears BEAR, but a >15% drawdown makes it TURBULENT (precedence).
    s = sig(ret_6m=-0.20, ret_3m=-0.12, vol_pct_2y=0.50, drawdown_1y=0.30)
    assert label_from_signals(s) == "TURBULENT"


def test_turbulent_via_vol():
    s = sig(ret_6m=0.03, ret_3m=0.01, vol_pct_2y=0.90, drawdown_1y=0.04)
    assert label_from_signals(s) == "TURBULENT"


def test_recovery():
    # Rising but still >10% below the 1y high, not enough drawdown for turbulent.
    s = sig(ret_6m=0.02, ret_3m=0.08, vol_pct_2y=0.60, drawdown_1y=0.15)
    assert label_from_signals(s) == "RECOVERY"


def test_neutral_fallback():
    s = sig(ret_6m=0.02, ret_3m=0.01, vol_pct_2y=0.60, drawdown_1y=0.03)
    assert label_from_signals(s) == "NEUTRAL"


def test_missing_signals_are_neutral():
    assert label_from_signals(sig()) == "NEUTRAL"


def test_bull_requires_all_three_conditions():
    # Good return + low vol but a >5% drawdown disqualifies BULL.
    s = sig(ret_6m=0.10, ret_3m=0.05, vol_pct_2y=0.30, drawdown_1y=0.08)
    assert label_from_signals(s) != "BULL"


def test_thresholds_perturb_preserves_sign_and_clamps():
    up = DEFAULT_THRESHOLDS.perturb(0.2)
    assert abs(up.bull_6m_return - 0.06) < 1e-9
    assert up.bear_6m_return < 0                 # sign preserved
    assert abs(up.bear_6m_return - (-0.12)) < 1e-9
    hi = RegimeThresholds(turbulent_vol_pct=0.9).perturb(0.2)  # 0.9*1.2=1.08 -> clamp
    assert 0.0 < hi.turbulent_vol_pct < 1.0


def test_perturbation_can_flip_a_borderline_label():
    # ret_6m = 0.055 is BULL at the default +5% cut but not at +20% (0.06).
    s = sig(ret_6m=0.055, ret_3m=0.03, vol_pct_2y=0.30, drawdown_1y=0.02)
    assert label_from_signals(s, DEFAULT_THRESHOLDS) == "BULL"
    assert label_from_signals(s, DEFAULT_THRESHOLDS.perturb(0.2)) != "BULL"


def test_realised_vol_is_annualised_percent():
    # ~1% daily moves -> annualised vol near 1%*sqrt(252) ~ 15.9 (percent points).
    idx = pd.date_range("2010-01-01", periods=120, freq="B")
    rng = np.random.default_rng(0)
    px = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, len(idx))), index=idx)
    rv = realised_vol(px)
    assert 8 < rv.dropna().iloc[-1] < 30


def test_build_vol_series_fills_gap_with_realised_vol():
    idx = pd.date_range("2006-01-01", periods=800, freq="B")
    rng = np.random.default_rng(1)
    px = pd.Series(1000 * np.cumprod(1 + rng.normal(0, 0.012, len(idx))), index=idx)
    # VIX only exists for the back half.
    vix = pd.Series(np.nan, index=idx)
    vix.iloc[400:] = 18.0
    vol = build_vol_series(px, vix)
    assert vol.iloc[500] == 18.0            # VIX used where present
    assert not np.isnan(vol.iloc[300])      # realised-vol fallback fills the gap
