"""SQLAlchemy ORM models — the append-only record tables (upgrade directive §6).

Every table is append-only: rows are inserted, never updated or deleted, so the
daily logbook and audit trail are reconstructable and yesterday's recommendation is
never overwritten after seeing today's prices. Money uses Numeric; flexible payloads
use JSON. Works on SQLite (dev/test) and Postgres/TimescaleDB (deployment).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Record(Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class PortfolioSnapshot(Record):
    __tablename__ = "portfolio_snapshot"
    as_of: Mapped[date] = mapped_column(Date, index=True)
    nav: Mapped[float] = mapped_column(Numeric(18, 4))
    cash: Mapped[float] = mapped_column(Numeric(18, 4))
    invested: Mapped[float] = mapped_column(Numeric(18, 4))
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class HoldingSnapshot(Record):
    __tablename__ = "holding_snapshot"
    snapshot_id: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    avg_cost: Mapped[float] = mapped_column(Numeric(18, 4))
    last_price: Mapped[float] = mapped_column(Numeric(18, 4))
    sector: Mapped[str | None] = mapped_column(String(64))


class DailyPortfolioPlan(Record):
    __tablename__ = "daily_portfolio_plan"
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    summary: Mapped[str] = mapped_column(String, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Recommendation(Record):
    __tablename__ = "recommendation"
    as_of: Mapped[date] = mapped_column(Date, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(16))
    entry_low: Mapped[float | None] = mapped_column(Numeric(18, 4))
    entry_high: Mapped[float | None] = mapped_column(Numeric(18, 4))
    target: Mapped[float | None] = mapped_column(Numeric(18, 4))
    invalidation: Mapped[float | None] = mapped_column(Numeric(18, 4))
    max_holding_sessions: Mapped[int | None] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    allocation: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    calibrated_probability: Mapped[float | None] = mapped_column(Numeric(6, 4))
    expected_net_return: Mapped[float | None] = mapped_column(Numeric(8, 4))
    risk_verdict: Mapped[str] = mapped_column(String(16), default="")
    model_version: Mapped[str] = mapped_column(String(64), default="")
    expires_on: Mapped[date | None] = mapped_column(Date)
    horizon_kind: Mapped[str] = mapped_column(String(16), default="swing")   # intraday|1d|swing
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class RecommendedChange(Record):
    __tablename__ = "recommended_change"
    plan_id: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(16))
    from_instrument: Mapped[str | None] = mapped_column(String(32))
    rupees: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    reason: Mapped[str] = mapped_column(String, default="")


class DecisionLog(Record):
    __tablename__ = "decision_log"
    as_of: Mapped[date] = mapped_column(Date, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    decision: Mapped[str] = mapped_column(String(16))
    rationale: Mapped[str] = mapped_column(String, default="")
    data_version: Mapped[str] = mapped_column(String(64), default="")
    model_version: Mapped[str] = mapped_column(String(64), default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class UserExecutionLog(Record):
    __tablename__ = "user_execution_log"
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String, default="")


class PaperSignal(Record):
    __tablename__ = "paper_signal"
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    horizon_kind: Mapped[str] = mapped_column(String(16), default="swing")
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class PaperFill(Record):
    __tablename__ = "paper_fill"
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(18, 4))
    cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[str] = mapped_column(String(8))                              # ENTRY|EXIT


class EvaluationOutcome(Record):
    __tablename__ = "evaluation_outcome"
    recommendation_id: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    success: Mapped[bool] = mapped_column(Boolean)
    realized_net: Mapped[float] = mapped_column(Numeric(8, 4))
    outcome: Mapped[str] = mapped_column(String(16))
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RiskVeto(Record):
    __tablename__ = "risk_veto"
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    verdict: Mapped[str] = mapped_column(String(16))
    flags: Mapped[dict] = mapped_column(JSON, default=dict)


class AlertDelivery(Record):
    __tablename__ = "alert_delivery"
    alert_type: Mapped[str] = mapped_column(String(32), index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    channel: Mapped[str] = mapped_column(String(16), default="in_app")
    delivered: Mapped[bool] = mapped_column(Boolean, default=True)
    message: Mapped[str] = mapped_column(String, default="")


class LLMRun(Record):
    __tablename__ = "llm_run"
    agent: Mapped[str] = mapped_column(String(32), index=True)
    task: Mapped[str] = mapped_column(String(32), index=True)
    policy_version: Mapped[str] = mapped_column(String(32), default="")
    selected_route: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


ALL_TABLES = [
    PortfolioSnapshot, HoldingSnapshot, DailyPortfolioPlan, Recommendation,
    RecommendedChange, DecisionLog, UserExecutionLog, PaperSignal, PaperFill,
    EvaluationOutcome, RiskVeto, AlertDelivery, LLMRun,
]
