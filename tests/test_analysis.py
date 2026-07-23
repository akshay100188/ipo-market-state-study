"""Analysis tests — lock the headline findings and their robustness.

Runs on committed derived data + the market cache (no network). Skips if the
market cache is absent.
"""
import pytest

from src.analysis import (
    aggregate_cut,
    bull_failures,
    coverage_table,
    label_curated,
    sensitivity,
)
from src.fetch_market import load_market_frames

try:
    FRAMES = load_market_frames()
    _HAVE = not FRAMES["us"]["index_close"].dropna().empty
except Exception:
    _HAVE = False

pytestmark = pytest.mark.skipif(not _HAVE, reason="market cache missing")


@pytest.fixture(scope="module")
def labelled():
    return label_curated(FRAMES)


def test_sc2_bull_trio_is_robust(labelled):
    # The money finding: Zomato/Nykaa/Paytm all list in the SAME bull regime,
    # and that must survive +/-20% threshold perturbation.
    sens = sensitivity(FRAMES).set_index("ticker")
    for tk in ["ZOMATO", "NYKAA", "PAYTM"]:
        assert sens.loc[tk, "regime_base"] == "BULL"
        assert not sens.loc[tk, "fragile"], f"{tk} label should be robust"


def test_sc2_same_regime_opposite_outcomes(labelled):
    lab = labelled.set_index("ticker")
    bull = lab[lab["regime"] == "BULL"]
    assert (bull["day1_return_pct"].astype(float) > 0).any()   # Zomato/Nykaa flew
    assert (bull["day1_return_pct"].astype(float) < 0).any()   # Paytm fell


def test_paytm_is_a_bull_failure(labelled):
    bf = bull_failures(labelled)
    assert "PAYTM" in set(bf["ticker"])


def test_coverage_flags_small_cells(labelled):
    cov = coverage_table(labelled)
    # The curated set is illustrative; almost every cell is < 3 and must be flagged.
    assert cov["small_cell"].any()


def test_sc1_aggregate_signs(labelled):
    _, corr = aggregate_cut(FRAMES)
    assert corr["n_years"] == 21
    assert corr["corr_count_vs_index_ret"] > 0     # more IPOs when market rises
    assert corr["corr_count_vs_meanvix"] < 0       # fewer IPOs when VIX high


def test_fragile_labels_exist_and_are_named(labelled):
    # Honesty check: the vol-boundary names flip, and we record it.
    sens = sensitivity(FRAMES).set_index("ticker")
    assert sens.loc["IRCTC", "fragile"]
    assert bool(sens["fragile"].any())
