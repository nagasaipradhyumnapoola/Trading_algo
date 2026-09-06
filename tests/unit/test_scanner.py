"""Scanner tests on a synthetic 30-session universe.

Verifies liquidity + abnormal-volume + momentum gates, relative-strength ranking,
NO_TRADE (empty) behavior, and point-in-time correctness.
"""

from datetime import date, timedelta

from services.ingestion import (
    Bar,
    InMemoryBarRepository,
    Instrument,
    InstrumentMaster,
)
from services.quant import ScanConfig, scan

START = date(2026, 1, 1)


def _series(repo, instrument_id, closes, volumes):
    for i, (c, v) in enumerate(zip(closes, volumes)):
        prev = closes[i - 1] if i > 0 else c
        hi = max(prev, c) * 1.005
        lo = min(prev, c) * 0.995
        repo.upsert(Bar(
            instrument_id=instrument_id, session_date=START + timedelta(days=i),
            open=round(prev, 2), high=round(hi, 2), low=round(lo, 2), close=round(c, 2),
            volume=v, source="synthetic",
        ))


def _ramp(start, end, n=30):
    return [start + (end - start) * i / (n - 1) for i in range(n)]


def _vol(base, n=30):
    return [base] * (n - 1) + [base * 2]      # last-day volume spike


def _universe():
    repo = InMemoryBarRepository()
    _series(repo, "A", _ramp(100, 150), _vol(20000))   # strong momentum, liquid
    _series(repo, "B", _ramp(100, 115), _vol(20000))   # mild momentum, liquid
    _series(repo, "C", _ramp(100, 150), _vol(40))      # strong but ILLIQUID
    _series(repo, "D", [100.0] * 30, _vol(20000))      # flat -> no momentum
    master = InstrumentMaster([
        Instrument(instrument_id=x, symbol=x, name=x) for x in ("A", "B", "C", "D")
    ])
    return repo, master


def test_scan_ranks_and_filters():
    repo, master = _universe()
    out = scan(repo, master, date(2026, 1, 30))
    ids = [c.instrument_id for c in out]

    assert ids[:2] == ["A", "B"]      # A ranks above B on relative strength
    assert "C" not in ids             # illiquid filtered
    assert "D" not in ids             # flat momentum filtered
    assert out[0].score >= out[1].score


def test_no_trade_when_nothing_clears_gates():
    repo, master = _universe()
    strict = ScanConfig(min_momentum=1.0)   # require +100% momentum: nobody qualifies
    assert scan(repo, master, date(2026, 1, 30), strict) == []


def test_scan_is_point_in_time():
    repo, master = _universe()
    # Only ~10 sessions known: not enough history for the 20-day lookback -> no candidates.
    early = scan(repo, master, date(2026, 1, 10))
    assert early == []
