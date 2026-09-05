"""Corporate-action price adjustment tests."""

from datetime import date

from services.ingestion import Bar, CorporateAction, InMemoryBarRepository, adjust_bars


def _bars():
    return [
        Bar(instrument_id="INST", session_date=date(2026, 1, 1), open=100, high=101,
            low=99, close=100, volume=1000, source="raw"),
        Bar(instrument_id="INST", session_date=date(2026, 1, 2), open=100, high=102,
            low=99, close=100, volume=1000, source="raw"),
        Bar(instrument_id="INST", session_date=date(2026, 1, 3), open=100, high=101,
            low=99, close=100, volume=1000, source="raw"),
    ]


def test_split_back_adjusts_history_only():
    action = CorporateAction.split("INST", date(2026, 1, 3), old=1, new=2)  # 1-for-2
    adj = adjust_bars(_bars(), [action])

    assert float(adj[0].close) == 50.0 and adj[0].volume == 2000     # pre-ex halved
    assert float(adj[1].close) == 50.0 and adj[1].volume == 2000
    assert float(adj[2].close) == 100.0 and adj[2].volume == 1000    # ex-day unchanged
    assert all(b.adjusted for b in adj)


def test_dividend_uses_prior_close():
    action = CorporateAction.dividend("INST", date(2026, 1, 3), amount=2)   # factor (100-2)/100
    adj = adjust_bars(_bars(), [action])
    assert float(adj[0].close) == 98.0
    assert float(adj[2].close) == 100.0


def test_adjustment_does_not_mutate_raw():
    raw = _bars()
    adjust_bars(raw, [CorporateAction.split("INST", date(2026, 1, 3), old=1, new=2)])
    assert float(raw[0].close) == 100.0        # originals untouched


def test_raw_and_adjusted_coexist_in_repo():
    repo = InMemoryBarRepository()
    raw = _bars()
    for b in raw:
        repo.upsert(b)
    for b in adjust_bars(raw, [CorporateAction.split("INST", date(2026, 1, 3), old=1, new=2)]):
        repo.upsert(b)
    assert len(repo) == 6                       # 3 raw + 3 adjusted (distinct keys)
