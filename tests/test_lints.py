"""Fabrication + language lint tests — each must fail on a broken input."""
from src.lint_fabrication import (
    _signature,
    build_allowed_set,
    extract_numbers,
    lint_text as lint_numbers,
)
from src.lint_language import lint_text as lint_language


# --- fabrication: scope (ADR-005) ----------------------------------------

def sigs(text):
    return {t["signature"] for t in extract_numbers(text)}


def test_percentage_currency_decimal_and_big_int_in_scope():
    got = sigs("Mean day-1 return was 48.2%, offer $38, raised 1,024 crore, ratio 1.85.")
    assert _signature("48.2") in got      # percentage
    assert _signature("38") in got        # currency
    assert _signature("1024") in got      # >= 100 integer
    assert _signature("1.85") in got      # decimal with fraction


def test_years_dates_refs_and_small_ints_exempt():
    got = sigs("In 2012 (see §4.2, Figure 3, ADR-002) we picked 4 pairs across 5 regimes on 2020-03-19.")
    assert got == set(), f"expected all-exempt, got {got}"


def test_signature_matches_fraction_and_percent_forms():
    assert _signature("48.2") == _signature("0.482")
    assert _signature("38.00") == _signature("38")
    assert _signature("1,234") == _signature("1234")


def test_orphan_number_is_flagged():
    allowed = {_signature("48.2"), _signature("38")}
    orphans, checked = lint_numbers("Return was 48.2% on a $38 offer, but 97.3% is invented.", allowed)
    assert checked == 3
    raws = {o["num"] for o in orphans}
    assert "97.3" in raws
    assert "48.2" not in raws and "38" not in raws


def test_traceable_numbers_pass():
    allowed = {_signature("48.2"), _signature("38")}
    orphans, checked = lint_numbers("Return 48.2% on a $38 offer.", allowed)
    assert orphans == []


def test_build_allowed_set_reads_derived_csv(tmp_path):
    d = tmp_path / "derived"
    d.mkdir()
    (d / "x.csv").write_text("name,day1_return_pct\nFoo,0.482\nBar,-0.11\n")
    allowed = build_allowed_set(d, extra_files=[])
    assert _signature("48.2") in allowed
    assert _signature("11") in allowed


# --- language: advisory (fail) vs causal (warn) --------------------------

def test_advisory_language_detected():
    adv, cau = lint_language("Investors should buy this IPO; it is a good bet.")
    assert adv
    assert any("should buy" in h.lower() for h in adv)


def test_forward_looking_detected():
    adv, _ = lint_language("The stock will rise and is expected to outperform.")
    assert adv


def test_causal_is_warning_only():
    adv, cau = lint_language("Volume collapsed because of the bear regime.")
    assert adv == []          # not an advisory failure
    assert cau                # but flagged as a causal warning


def test_clean_descriptive_text_is_silent():
    adv, cau = lint_language(
        "In BULL regimes, mean first-day returns were higher; several bull-market "
        "listings still fell on debut, associated with aggressive pricing."
    )
    assert adv == [] and cau == []
