"""Phase 1 data-spine tests: instrument master + EOD ingestion.

Covers idempotency, correction history, freshness, point-in-time leakage guard,
OHLC validation, and optional-field parsing.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from services.ingestion import (
    Bar,
    CsvEodAdapter,
    InMemoryBarRepository,
    InstrumentMaster,
    InstrumentStatus,
    Timeframe,
    load_eod,
)

FIXTURES = Path(__file__).parents[1] / "fixtures"
INSTRUMENTS = FIXTURES / "sample_instruments.csv"
EOD = FIXTURES / "sample_eod.csv"


# --- instrument master ---------------------------------------------------------

def test_instrument_master_loads_and_indexes():
    master = InstrumentMaster.from_csv(INSTRUMENTS)
    assert len(master) == 4
    assert master.get("INDA0001").symbol == "RELIANCE"
    assert master.by_symbol("TCS").instrument_id == "INDA0002"


def test_tradable_excludes_delisted():
    master = InstrumentMaster.from_csv(INSTRUMENTS)
    tradable = {i.instrument_id for i in master.tradable()}
    assert "INDA0004" not in tradable          # OLDCO is DELISTED
    assert master.get("INDA0004").status is InstrumentStatus.DELISTED
    assert len(tradable) == 3


# --- adapter + validation ------------------------------------------------------

def test_adapter_parses_bars_and_optional_turnover():
    bars = list(CsvEodAdapter(EOD, source="csv").bars())
    assert len(bars) == 9
    reliance = [b for b in bars if b.instrument_id == "INDA0001"]
    assert reliance[0].turnover == Decimal("3498000000")
    tcs = [b for b in bars if b.instrument_id == "INDA0002"]
    assert tcs[0].turnover is None            # blank turnover -> None


def test_bad_ohlc_is_rejected():
    with pytest.raises(ValidationError):
        Bar(
            instrument_id="X", session_date=date(2026, 9, 1),
            open=10, high=9, low=8, close=8, volume=1, source="csv",  # high < open
        )


# --- idempotency + corrections -------------------------------------------------

def test_load_is_idempotent():
    repo = InMemoryBarRepository()
    first = load_eod(CsvEodAdapter(EOD), repo)
    assert first.added == 9 and first.skipped == 0
    assert len(repo) == 9

    second = load_eod(CsvEodAdapter(EOD), repo)
    assert second.added == 0
    assert second.skipped == 9            # nothing new on a re-run
    assert len(repo) == 9                 # no duplicate keys


def test_correction_appends_version_without_overwrite():
    repo = InMemoryBarRepository()
    load_eod(CsvEodAdapter(EOD), repo)

    key = ("INDA0001", Timeframe.EOD, date(2026, 9, 3), "csv", False)
    original = repo.latest(key)
    assert original.correction_version == 0

    corrected = original.model_copy(update={"close": Decimal("2999")})
    assert repo.upsert(corrected) == "corrected"

    latest = repo.latest(key)
    assert latest.close == Decimal("2999")
    assert latest.correction_version == 1     # history advanced, not overwritten


# --- freshness -----------------------------------------------------------------

def test_freshness_flags_stale_feed():
    repo = InMemoryBarRepository()
    stale = load_eod(CsvEodAdapter(EOD), repo, as_of=date(2026, 9, 30), max_age_days=4)
    assert stale.last_session_date == date(2026, 9, 3)
    assert stale.is_stale is True

    fresh = load_eod(CsvEodAdapter(EOD), repo, as_of=date(2026, 9, 4), max_age_days=4)
    assert fresh.is_stale is False


# --- point-in-time leakage guard ----------------------------------------------

def test_as_of_excludes_future_bars():
    repo = InMemoryBarRepository()
    load_eod(CsvEodAdapter(EOD), repo)

    # Inject a bar dated in the future relative to the decision time.
    future = Bar(
        instrument_id="INDA0003", session_date=date(2026, 9, 10),
        open=123, high=130, low=122, close=129, volume=500000, source="csv",
    )
    repo.upsert(future)

    visible = repo.as_of("INDA0003", Timeframe.EOD, date(2026, 9, 3))
    dates = [b.session_date for b in visible]
    assert date(2026, 9, 10) not in dates          # no look-ahead
    assert dates == [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)]
