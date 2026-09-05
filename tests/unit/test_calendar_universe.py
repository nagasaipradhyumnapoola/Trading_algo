"""Trading calendar and point-in-time universe membership tests."""

from datetime import date

from services.ingestion import Bar, Membership, TradingCalendar, UniverseHistory


def _bars():
    return [
        Bar(instrument_id="X", session_date=d, open=1, high=1, low=1, close=1,
            volume=1, source="raw")
        for d in (date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 5))
    ]


def test_calendar_from_bars():
    cal = TradingCalendar.from_bars(_bars())
    assert cal.is_session(date(2026, 1, 2))
    assert not cal.is_session(date(2026, 1, 3))     # a holiday/weekend gap
    assert cal.next_session(date(2026, 1, 2)) == date(2026, 1, 5)
    assert cal.prev_session(date(2026, 1, 5)) == date(2026, 1, 2)
    assert cal.sessions_between(date(2026, 1, 1), date(2026, 1, 2)) == [
        date(2026, 1, 1), date(2026, 1, 2)]


def test_point_in_time_membership_excludes_removed_names():
    hist = UniverseHistory([
        Membership(instrument_id="CURR", index_name="NIFTY", start_date=date(2026, 1, 1)),
        Membership(instrument_id="GONE", index_name="NIFTY",
                   start_date=date(2020, 1, 1), end_date=date(2026, 1, 1)),
    ])
    on = date(2026, 1, 2)
    members = hist.members_asof("NIFTY", on)
    assert members == {"CURR"}                       # GONE left before this date
    assert hist.is_member("NIFTY", "CURR", on)
    assert not hist.is_member("NIFTY", "GONE", on)
    # But GONE WAS a member historically (survivorship-correct):
    assert "GONE" in hist.members_asof("NIFTY", date(2025, 6, 1))
