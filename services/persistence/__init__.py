"""persistence — append-only relational store for the logbook and audit trail.

SQLAlchemy models + repositories. SQLite for dev/test, Postgres/TimescaleDB for
deployment (Alembic migrations under migrations/). Append-only by design.
"""

from .db import init_db, make_engine, session_factory, session_scope
from .logbook import LogbookService, row_to_dict
from .models import (
    ALL_TABLES,
    AlertDelivery,
    Base,
    DailyPortfolioPlan,
    DecisionLog,
    EvaluationOutcome,
    HoldingSnapshot,
    LLMRun,
    PaperFill,
    PaperSignal,
    PortfolioSnapshot,
    Recommendation,
    RecommendedChange,
    RiskVeto,
    UserExecutionLog,
)
from .repositories import AppendOnlyRepository, repo

__all__ = [
    "Base",
    "ALL_TABLES",
    "make_engine",
    "init_db",
    "session_factory",
    "session_scope",
    "LogbookService",
    "row_to_dict",
    "AppendOnlyRepository",
    "repo",
    "PortfolioSnapshot",
    "HoldingSnapshot",
    "DailyPortfolioPlan",
    "Recommendation",
    "RecommendedChange",
    "DecisionLog",
    "UserExecutionLog",
    "PaperSignal",
    "PaperFill",
    "EvaluationOutcome",
    "RiskVeto",
    "AlertDelivery",
    "LLMRun",
]
