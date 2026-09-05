"""Parquet bar-repository round-trip and correction fidelity."""

from datetime import date
from decimal import Decimal

from services.ingestion import Bar, Timeframe
from services.ingestion.parquet_store import ParquetBarRepository


def _bars():
    return [
        Bar(instrument_id="A", session_date=date(2026, 1, 1), open=100, high=101,
            low=99, close=100, volume=1000, turnover=Decimal("100000"), source="raw"),
        Bar(instrument_id="A", session_date=date(2026, 1, 2), open=100, high=103,
            low=99, close=102, volume=1200, source="raw"),      # turnover None
    ]


def test_parquet_round_trip(tmp_path):
    path = tmp_path / "bars.parquet"
    repo = ParquetBarRepository(path)
    for b in _bars():
        repo.upsert(b)
    repo.save()

    reloaded = ParquetBarRepository.load(path)
    got = {b.session_date: b for b in reloaded.all_latest()}
    assert len(got) == 2
    assert got[date(2026, 1, 1)].close == Decimal("100")       # Decimal preserved
    assert got[date(2026, 1, 1)].turnover == Decimal("100000")
    assert got[date(2026, 1, 2)].turnover is None              # None preserved


def test_parquet_preserves_correction_history(tmp_path):
    path = tmp_path / "bars.parquet"
    repo = ParquetBarRepository(path)
    for b in _bars():
        repo.upsert(b)
    key = ("A", Timeframe.EOD, date(2026, 1, 2), "raw", False)
    repo.upsert(repo.latest(key).model_copy(update={"close": Decimal("101")}))  # within low/high
    repo.save()

    reloaded = ParquetBarRepository.load(path)
    latest = reloaded.latest(key)
    assert latest.close == Decimal("101")
    assert latest.correction_version == 1
