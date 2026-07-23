"""Verification-gate tests — the gate must fail on a deliberately broken row."""
import pandas as pd

from src.verify import REQUIRED_COLUMNS, verify_frame


def row(**over):
    base = {
        "ticker": "TEST", "name": "Test Co", "market": "US",
        "ipo_date": "2012-05-18", "offer_price": "38", "currency": "USD",
        "day1_open": "42.05", "day1_close": "38.23", "day1_return_pct": "0.61",
        "source_url": "https://example.com/prospectus",
        "source_type": "prospectus", "retrieval_date": "2026-07-22",
        "verify_status": "VERIFIED", "notes": "",
    }
    base.update(over)
    return base


def frame(*rows):
    return pd.DataFrame(list(rows), columns=REQUIRED_COLUMNS)


def test_clean_verified_row_passes():
    ok, errs, curated, excluded = verify_frame(frame(row()))
    assert ok, errs
    assert len(curated) == 1 and len(excluded) == 0


def test_verified_missing_source_url_fails():
    ok, errs, *_ = verify_frame(frame(row(source_url="")))
    assert not ok
    assert any("source_url" in e for e in errs)


def test_verified_nonnumeric_offer_price_fails():
    ok, errs, *_ = verify_frame(frame(row(offer_price="thirty-eight")))
    assert not ok
    assert any("offer_price" in e for e in errs)


def test_verified_bad_date_fails():
    ok, errs, *_ = verify_frame(frame(row(ipo_date="May 18 2012")))
    assert not ok
    assert any("ipo_date" in e for e in errs)


def test_to_verify_row_fails_the_gate():
    ok, errs, curated, excluded = verify_frame(frame(row(verify_status="TO_VERIFY")))
    assert not ok
    assert any("TO_VERIFY" in e for e in errs)
    assert len(curated) == 0 and len(excluded) == 1


def test_excluded_without_reason_fails():
    ok, errs, *_ = verify_frame(frame(row(verify_status="EXCLUDED", notes="")))
    assert not ok
    assert any("EXCLUDED" in e for e in errs)


def test_excluded_with_reason_passes_and_is_partitioned():
    ok, errs, curated, excluded = verify_frame(
        frame(row(verify_status="EXCLUDED", notes="SpaceX: figures TO_VERIFY, cut (ADR-007)"))
    )
    assert ok, errs
    assert len(curated) == 0 and len(excluded) == 1


def test_unknown_status_fails():
    ok, errs, *_ = verify_frame(frame(row(verify_status="MAYBE")))
    assert not ok


def test_missing_column_fails():
    df = frame(row()).drop(columns=["source_url"])
    ok, errs, *_ = verify_frame(df)
    assert not ok
    assert any("missing required columns" in e for e in errs)


def test_mixed_frame_partitions_correctly():
    df = frame(
        row(ticker="A"),
        row(ticker="B", verify_status="EXCLUDED", notes="dropped, unverifiable"),
    )
    ok, errs, curated, excluded = verify_frame(df)
    assert ok, errs
    assert list(curated["ticker"]) == ["A"]
    assert list(excluded["ticker"]) == ["B"]
