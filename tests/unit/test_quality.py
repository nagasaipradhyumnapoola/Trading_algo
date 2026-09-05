"""Data-quality suite tests."""

from datetime import date

from services.ingestion import Bar, TradingCalendar, run_quality


def _bar(iid, d, c, v=1000, source="raw"):
    return Bar(instrument_id=iid, session_date=d, open=c, high=c * 1.01,
               low=c * 0.99, close=c, volume=v, source=source)


def test_clean_data_has_no_errors():
    bars = [_bar("A", date(2026, 1, 1), 100), _bar("A", date(2026, 1, 2), 101)]
    rep = run_quality(bars)
    assert rep.ok and not rep.issues


def test_duplicate_is_error_and_quarantined():
    d = date(2026, 1, 1)
    rep = run_quality([_bar("A", d, 100), _bar("A", d, 100)])
    assert not rep.ok
    assert rep.errors()[0].code == "DUPLICATE"
    assert ("A", d) in rep.quarantine_keys()


def test_missing_session_flagged_against_calendar():
    cal = TradingCalendar([date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)])
    bars = [_bar("A", date(2026, 1, 1), 100), _bar("A", date(2026, 1, 3), 101)]
    rep = run_quality(bars, calendar=cal)
    codes = {(i.code, i.session_date) for i in rep.warnings()}
    assert ("MISSING_SESSION", date(2026, 1, 2)) in codes


def test_outlier_move_flagged():
    bars = [_bar("A", date(2026, 1, 1), 100), _bar("A", date(2026, 1, 2), 200)]  # +100%
    rep = run_quality(bars)
    assert any(i.code == "OUTLIER" for i in rep.warnings())


def test_stale_feed_flagged():
    bars = [_bar("A", date(2026, 1, 1), 100)]
    rep = run_quality(bars, as_of=date(2026, 1, 30), max_stale_days=4)
    assert any(i.code == "STALE" for i in rep.warnings())
