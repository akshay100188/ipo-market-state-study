"""Integration tests: regime labels on real cached market data.

Exercises the hand-checked anchor dates from the build brief (§9, Phase 0) and
the India pre-2008 realised-vol fallback. Skips cleanly if the data/raw cache
is absent (e.g. a fresh clone before `python -m src.fetch_market`).
"""
import math

import pytest

from src.fetch_market import load_market_frames
from src.regime import compute_signals, label_date

try:
    FRAMES = load_market_frames()
    _HAVE_DATA = all(not FRAMES[m]["index_close"].dropna().empty for m in ("us", "in"))
except Exception:
    _HAVE_DATA = False

pytestmark = pytest.mark.skipif(
    not _HAVE_DATA, reason="market cache missing; run `python -m src.fetch_market`"
)


def test_covid_crash_is_turbulent_both_markets():
    assert label_date(FRAMES["us"], "2020-03-20") == "TURBULENT"
    assert label_date(FRAMES["in"], "2020-03-20") == "TURBULENT"


def test_nov_2021_india_is_bull():
    # Brief's hand-checked anchor.
    assert label_date(FRAMES["in"], "2021-11-15") == "BULL"


def test_gfc_is_turbulent():
    assert label_date(FRAMES["us"], "2008-10-15") == "TURBULENT"


def test_calm_bull_us():
    assert label_date(FRAMES["us"], "2021-11-10") == "BULL"


def test_india_pre_2008_uses_realised_vol_fallback():
    # India VIX starts 2008-03; a 2006 date must have no raw VIX but a usable
    # vol from the realised-vol fallback, and still produce a label.
    df = FRAMES["in"]
    at = df[df.index <= "2006-06-15"].iloc[-1]
    assert math.isnan(at["vix_close"])          # no India VIX yet
    assert not math.isnan(at["vol"])            # realised-vol fallback filled it
    label = label_date(df, "2006-06-15")
    assert label in {"BULL", "RECOVERY", "TURBULENT", "BEAR", "NEUTRAL"}
    assert label != "NEUTRAL"                   # mid-2006 EM correction was real


def test_signals_present_for_recent_date():
    s = compute_signals(FRAMES["us"], "2023-06-15")
    assert s["ret_6m"] is not None
    assert s["drawdown_1y"] is not None
    assert s["vol_pct_2y"] is not None
