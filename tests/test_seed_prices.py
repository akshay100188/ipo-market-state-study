"""Curated seed + post-listing helpers. No network (pure logic only)."""
import pandas as pd

from src.build_seed import build
from src.fetch_prices import HORIZONS, _asof, _first_on_or_after
from src.verify import verify_frame


def test_seed_returns_are_computed_not_typed():
    df = build().set_index("ticker")
    # Recompute from offer + close and match the stored value.
    for tk in ["PAYTM", "IRCTC", "META", "V"]:
        r = df.loc[tk]
        expect = round((float(r["day1_close"]) / float(r["offer_price"]) - 1) * 100, 2)
        assert float(r["day1_return_pct"]) == expect


def test_seed_signs_match_known_outcomes():
    df = build().set_index("ticker")
    assert float(df.loc["PAYTM", "day1_return_pct"]) < 0     # bull-market flop
    assert float(df.loc["IRCTC", "day1_return_pct"]) > 100   # big PSU pop
    assert float(df.loc["UBER", "day1_return_pct"]) < 0      # bull-market flop (US)
    assert float(df.loc["V", "day1_return_pct"]) > 0         # turbulent pop


def test_built_seed_passes_the_gate():
    ok, errors, curated, excluded = verify_frame(build())
    assert ok, errors
    assert len(curated) == 9 and len(excluded) == 0


def test_seed_spans_both_markets_and_both_outcomes():
    df = build()
    assert set(df["market"]) == {"US", "IN"}
    assert (df["day1_return_pct"].astype(float) < 0).any()   # failures present
    assert (df["day1_return_pct"].astype(float) > 0).any()   # pops present


def test_horizons_are_the_four_required():
    assert set(HORIZONS) == {"1M", "3M", "6M", "12M"}


def test_price_asof_helpers():
    idx = pd.date_range("2020-01-01", periods=10, freq="D")
    s = pd.Series(range(10), index=idx, dtype="float64")
    val, when = _asof(s, pd.Timestamp("2020-01-05"))
    assert val == 4.0 and when == pd.Timestamp("2020-01-05")
    # as-of falls back to the last prior observation on a non-trading day
    val2, _ = _asof(s, pd.Timestamp("2020-01-15"))
    assert val2 == 9.0
    fval, fwhen = _first_on_or_after(s, pd.Timestamp("2020-01-04"))
    assert fval == 3.0 and fwhen == pd.Timestamp("2020-01-04")
