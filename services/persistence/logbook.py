"""LogbookService — append-only daily logbook over the record tables.

Writes each day's recommendations, decisions, risk vetoes, recommended changes,
paper fills, alerts, portfolio snapshots, user executions, and llm_runs; reads a
day back; and reconstructs a single recommendation end to end. Append-only: nothing
is ever updated after the fact.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from .db import session_factory, session_scope
from .models import (
    AlertDelivery,
    DailyPortfolioPlan,
    DecisionLog,
    EvaluationOutcome,
    HoldingSnapshot,
    LLMRun,
    PaperFill,
    PortfolioSnapshot,
    Recommendation,
    RecommendedChange,
    RiskVeto,
    UserExecutionLog,
)
from .repositories import repo


def _ser(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def row_to_dict(obj) -> dict:
    return {c.name: _ser(getattr(obj, c.name)) for c in obj.__table__.columns}


class LogbookService:
    def __init__(self, engine) -> None:
        self._factory = session_factory(engine)

    # -- writes ----------------------------------------------------------------

    def _add(self, model, **fields) -> str:
        with session_scope(self._factory) as s:
            return repo(s, model).add(**fields).id

    def record_recommendation(self, **fields) -> str:
        return self._add(Recommendation, **fields)

    def record_risk_veto(self, **fields) -> str:
        return self._add(RiskVeto, **fields)

    def record_decision(self, **fields) -> str:
        return self._add(DecisionLog, **fields)

    def record_alert(self, **fields) -> str:
        return self._add(AlertDelivery, **fields)

    def record_paper_fill(self, **fields) -> str:
        return self._add(PaperFill, **fields)

    def record_llm_run(self, **fields) -> str:
        return self._add(LLMRun, **fields)

    def record_user_execution(self, **fields) -> str:
        return self._add(UserExecutionLog, **fields)

    def record_evaluation_outcome(self, **fields) -> str:
        return self._add(EvaluationOutcome, **fields)

    def record_daily_plan(self, *, plan_date: date, summary: str = "",
                          changes: list[dict] | None = None, data: dict | None = None) -> str:
        with session_scope(self._factory) as s:
            plan = repo(s, DailyPortfolioPlan).add(plan_date=plan_date, summary=summary,
                                                   data=data or {})
            for ch in (changes or []):
                repo(s, RecommendedChange).add(plan_id=plan.id, **ch)
            return plan.id

    def record_portfolio_snapshot(self, *, as_of: date, nav: float, cash: float,
                                  invested: float, holdings: list[dict] | None = None,
                                  data: dict | None = None) -> str:
        with session_scope(self._factory) as s:
            snap = repo(s, PortfolioSnapshot).add(as_of=as_of, nav=nav, cash=cash,
                                                  invested=invested, data=data or {})
            for h in (holdings or []):
                repo(s, HoldingSnapshot).add(snapshot_id=snap.id, **h)
            return snap.id

    # -- reads -----------------------------------------------------------------

    def _list(self, s: Session, model, **filters) -> list[dict]:
        return [row_to_dict(o) for o in repo(s, model).list(limit=500, **filters)]

    def day(self, as_of: date) -> dict:
        """Everything logged for a trading day, reconstructable from the ledger."""
        with session_scope(self._factory) as s:
            plans = repo(s, DailyPortfolioPlan).list(plan_date=as_of)
            plan_rows = []
            for p in plans:
                d = row_to_dict(p)
                d["changes"] = self._list(s, RecommendedChange, plan_id=p.id)
                plan_rows.append(d)
            return {
                "as_of": as_of.isoformat(),
                "recommendations": self._list(s, Recommendation, as_of=as_of),
                "risk_vetoes": self._list(s, RiskVeto, as_of=as_of),
                "decisions": self._list(s, DecisionLog, as_of=as_of),
                "paper_fills": self._list(s, PaperFill, session_date=as_of),
                "plans": plan_rows,
            }

    def reconstruct_recommendation(self, rec_id: str) -> dict:
        """A single recommendation with the veto, outcome, and llm_runs behind it."""
        with session_scope(self._factory) as s:
            rec = repo(s, Recommendation).get(rec_id)
            if rec is None:
                return {"error": "not found", "recommendation_id": rec_id}
            rec_d = row_to_dict(rec)
            vetoes = [row_to_dict(v) for v in repo(s, RiskVeto).list(
                instrument_id=rec.instrument_id, as_of=rec.as_of)]
            outcomes = [row_to_dict(o) for o in repo(s, EvaluationOutcome).list(
                recommendation_id=rec_id)]
            runs = [row_to_dict(r) for r in repo(s, LLMRun).list(limit=500)
                    if r.data.get("rec_id") == rec_id]
            return {"recommendation": rec_d, "risk_vetoes": vetoes,
                    "evaluation_outcomes": outcomes, "llm_runs": runs,
                    "reconstructable": bool(rec_d.get("target") is not None
                                            and rec_d.get("model_version"))}
