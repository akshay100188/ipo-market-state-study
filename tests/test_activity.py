"""US aggregate (Ritter) tests: lock the annual aggregation to his published
figures so a bad parse or a units drift can never slip into SC-1.

Skips if the Ritter xlsx has not been downloaded yet.
"""
import pytest

from src.fetch_activity import RITTER_XLSX, us_annual_activity

pytestmark = pytest.mark.skipif(
    not RITTER_XLSX.exists(),
    reason="Ritter IPOALL.xlsx not cached; run `python -m src.fetch_activity`",
)


@pytest.fixture(scope="module")
def ann():
    df = us_annual_activity().set_index("year")
    return df


# Known Ritter annual figures (net-count definition). Tolerances allow for the
# occasional late data revision without letting a real parse error through.
@pytest.mark.parametrize("year,exp_n,exp_ret,n_tol,ret_tol", [
    (1999, 476, 71.0, 3, 2.0),
    (2000, 381, 56.3, 3, 2.0),
    (2008, 21, 6.4, 2, 2.0),
    (2020, 165, 41.6, 4, 2.0),
    (2021, 309, 32.0, 4, 2.0),
])
def test_matches_published_annual(ann, year, exp_n, exp_ret, n_tol, ret_tol):
    assert abs(ann.loc[year, "n_ipos"] - exp_n) <= n_tol
    assert abs(ann.loc[year, "mean_first_day_return_pct"] - exp_ret) <= ret_tol


def test_no_missing_returns_in_study_window(ann):
    window = ann.loc[2005:2025, "mean_first_day_return_pct"]
    assert window.notna().all(), "a study-window year has no first-day return"


def test_activity_shows_regime_signal(ann):
    # SC-1 sanity: the 2021 boom dwarfs the 2008 GFC and 2022 collapse in counts.
    assert ann.loc[2021, "n_ipos"] > 250
    assert ann.loc[2008, "n_ipos"] < 40
    assert ann.loc[2022, "n_ipos"] < 60
