"""Event-study abnormal/cumulative returns."""

from datetime import date, timedelta

from services.ingestion import Bar, InMemoryBarRepository
from services.quant import EventStudy

START = date(2026, 1, 1)


def _series(repo, iid, closes):
    for i, c in enumerate(closes):
        prev = closes[i - 1] if i > 0 else c
        repo.upsert(Bar(instrument_id=iid, session_date=START + timedelta(days=i),
                        open=round(prev, 2), high=round(max(prev, c) * 1.001, 2),
                        low=round(min(prev, c) * 0.999, 2), close=round(c, 2),
                        volume=1000, source="syn"))


def _universe():
    repo = InMemoryBarRepository()
    a = [100.0] * 5 + [100 * (1.02 ** k) for k in range(1, 11)]   # flat then +2%/session
    _series(repo, "A", a)
    _series(repo, "B", [50.0] * 15)                               # flat benchmark (ret 0)
    return repo


def test_event_study_positive_abnormal_return():
    study = EventStudy(_universe(), ["A", "B"])
    res = study.study("A", event_date=START + timedelta(days=4))
    assert res.ar_1d > 0.015                        # ~+2% abnormal on day 1
    assert res.car[5] > res.car[1] > 0              # cumulative and rising
    assert res.mfe > 0 and res.mae <= 0
    assert res.n_sessions == 10


def test_aggregate_positive_rate():
    study = EventStudy(_universe(), ["A", "B"])
    agg = study.aggregate([("A", START + timedelta(days=4))])
    assert agg.n == 1
    assert agg.positive_rate[5] == 1.0
    assert agg.mean_car[5] > 0
