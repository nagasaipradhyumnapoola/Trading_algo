"""Alert engine: dedupe, quiet hours, audit log."""

from datetime import datetime, timezone

from services.alerts import (
    AlertEngine,
    Severity,
    make_new_opportunity,
    make_risk_veto,
    make_thesis_invalidated,
)


def _at(hour):
    return datetime(2026, 1, 1, hour, 0, tzinfo=timezone.utc)


def test_delivers_then_dedupes():
    eng = AlertEngine()
    a = make_new_opportunity("MOMO", 0.8, "2026-01-01")
    assert eng.emit(a, now=_at(10)) is not None
    dup = make_new_opportunity("MOMO", 0.8, "2026-01-01")     # same dedupe_key
    assert eng.emit(dup, now=_at(11)) is None
    assert len(eng.delivered) == 1
    assert [e.action for e in eng.audit] == ["delivered", "deduped"]


def test_quiet_hours_hold_non_critical():
    eng = AlertEngine(quiet_hours=(22, 6))                    # 22:00-06:00 UTC
    held = eng.emit(make_risk_veto("X", "liquidity"), now=_at(2))
    assert held is None and eng.audit[-1].action == "quiet"


def test_critical_ignores_quiet_hours():
    eng = AlertEngine(quiet_hours=(22, 6))
    crit = make_thesis_invalidated("X", price=97.0, invalidation=98.0)
    assert crit.severity is Severity.CRITICAL
    assert eng.emit(crit, now=_at(2)) is not None             # delivered despite quiet


def test_audit_persists(tmp_path):
    eng = AlertEngine(audit_path=tmp_path / "alerts.jsonl")
    eng.emit(make_new_opportunity("A", 0.7, "2026-01-01"), now=_at(9))
    assert (tmp_path / "alerts.jsonl").exists()
