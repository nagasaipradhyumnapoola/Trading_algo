"""Append-only relational store + Alembic migration (SQLite)."""

from datetime import date, datetime, timezone

from sqlalchemy import inspect

from services.persistence import (
    AppendOnlyRepository,
    EvaluationOutcome,
    LLMRun,
    Recommendation,
    init_db,
    make_engine,
    repo,
    session_factory,
    session_scope,
)

_EXPECTED = {
    "portfolio_snapshot", "holding_snapshot", "daily_portfolio_plan", "recommendation",
    "recommended_change", "decision_log", "user_execution_log", "paper_signal",
    "paper_fill", "evaluation_outcome", "risk_veto", "alert_delivery", "llm_run",
}


def _mem():
    engine = make_engine("sqlite://")
    init_db(engine)
    return engine


def test_all_tables_created():
    engine = _mem()
    assert _EXPECTED <= set(inspect(engine).get_table_names())


def test_repository_is_append_only():
    # The contract: no update / delete anywhere on the repository.
    assert not hasattr(AppendOnlyRepository, "update")
    assert not hasattr(AppendOnlyRepository, "delete")


def test_insert_and_query_recommendation():
    factory = session_factory(_mem())
    with session_scope(factory) as s:
        rec = repo(s, Recommendation).add(
            as_of=date(2026, 5, 10), instrument_id="MOMO", action="BUY",
            target=184.89, invalidation=169.19, quantity=57, allocation=9942,
            calibrated_probability=0.806, risk_verdict="PASS", model_version="logistic-0.1")
        rec_id = rec.id
    with session_scope(factory) as s:
        r = repo(s, Recommendation)
        assert r.get(rec_id).instrument_id == "MOMO"
        assert r.count(instrument_id="MOMO") == 1


def test_logbook_reconstruction_links():
    factory = session_factory(_mem())
    with session_scope(factory) as s:
        rec = repo(s, Recommendation).add(as_of=date(2026, 5, 10), instrument_id="MOMO",
                                          action="BUY", quantity=10, model_version="logistic-0.1")
        repo(s, LLMRun).add(agent="news", task="event_extraction", state="validated",
                            data={"rec_id": rec.id})
        repo(s, EvaluationOutcome).add(recommendation_id=rec.id, instrument_id="MOMO",
                                       success=True, realized_net=0.031, outcome="TARGET",
                                       measured_at=datetime.now(timezone.utc))
        rec_id = rec.id
    with session_scope(factory) as s:
        outcome = repo(s, EvaluationOutcome).list(recommendation_id=rec_id)
        assert outcome and outcome[0].success is True      # reconstruct rec -> outcome


def test_alembic_migration_upgrades(tmp_path):
    from alembic import command
    from alembic.config import Config

    db = tmp_path / "t.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db}")
    command.upgrade(cfg, "head")

    engine = make_engine(f"sqlite:///{db}")
    tables = set(inspect(engine).get_table_names())
    assert _EXPECTED <= tables and "alembic_version" in tables
