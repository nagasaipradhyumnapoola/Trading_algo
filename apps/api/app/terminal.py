"""TerminalService — builds the Phase 6 terminal's data once, from the engines.

Trains the calibrated model, computes live recommendations (probability from the
calibrated quant system, risk from the independent engine, sizing deterministic),
runs an out-of-sample paper track for the performance dashboard, seeds alerts, and
holds evidence for the grounded chat. SAMPLE data — clearly labelled. No broker.
"""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

import numpy as np

from services.alerts import AlertEngine, make_new_opportunity, make_risk_veto
from services.evaluation import (
    CostModel,
    LabelConfig,
    PaperBroker,
    TradeSignal,
    compute_performance,
    label_signal,
    precision_by_bucket,
)
from services.ingestion.models import Timeframe
from services.ingestion.sample import SAMPLE_START
from services.monitoring import (
    Feedback,
    FeedbackLabel,
    FeedbackStore,
    HealthInputs,
    MetricsRegistry,
    RateLimiter,
    build_audit_bundle,
    evaluate_health,
)
from services.persistence import LogbookService, init_db, make_engine
from services.providers import SampleMarketDataProvider, load_market_data
from services.quant import ScanConfig, compute_features, scan
from services.quant.calibration import IsotonicCalibrator
from services.quant.ml import DEFAULT_FEATURES, LogisticModel
from services.research_workers.chat import GroundedChat
from services.research_workers.floor import ResearchFloor
from services.research_workers.llm_gateway import (
    DataClass,
    LLMGateway,
    MockProvider,
    ModelCapabilityRegistry,
    ModelRoute,
    build_real_registry,
)
from services.research_workers.llm_gateway.policies import MID
from services.risk_portfolio import (
    Holding,
    Portfolio,
    RecAction,
    RiskInputs,
    assess_risk,
    build_recommendation,
    recommend_rotation,
    size_position,
)

_N = 160
_CAPITAL = 100_000.0


def _chat_responder(call: dict) -> str:
    sid = (re.search(r'id="([^"]+)"', call["user"]) or [None, "unknown"])[1]
    snippet = call["user"].split("</source>")[0].split(">")[-1].strip()[:180]
    return json.dumps({"answer": f"Based on {sid}: {snippet}", "citations": [sid]})


def _floor_responder(call: dict) -> str:
    """Mock FreeLLMAPI response valid across every floor task, grounded to the source id."""
    sid = (re.search(r'id="([^"]+)"', call["user"]) or [None, "doc"])[1]
    return json.dumps({
        "sentiment": 0.55, "label": "positive", "rationale": "constructive flow",
        "manipulation_flags": [], "thesis": "Grounded catalyst; momentum + volume support.",
        "assumptions": ["order executes on schedule"], "action": "BUY",
        "unknowns": ["contract margin not disclosed"],
        "event_candidates": [{"type": "contract_order", "materiality": 0.8, "novelty": 0.7}],
        "claims": [{"claim": "Government order awarded", "polarity": "positive",
                    "evidence_ids": [sid], "confidence": 0.8}],
        "citations": [sid],
    })


class TerminalService:
    def __init__(self) -> None:
        # Demo runs through the SAME provider interface a real feed will implement.
        provider = SampleMarketDataProvider(n=_N)
        self.repo, self.master = load_market_data(provider)
        self.last = SAMPLE_START + timedelta(days=_N - 1)
        self._train()
        self._paper_track()
        self._current_recs()
        self._portfolio()
        self._alerts()
        self._chat_setup()
        self._observability()
        self._logbook_setup()
        self._floor_setup()

    # -- build steps -----------------------------------------------------------

    def _feat(self, values: dict) -> np.ndarray:
        return np.array([[values.get(f, 0.0) for f in DEFAULT_FEATURES]])

    def _prob(self, values: dict) -> float:
        return float(self.cal.transform(self.model.predict_proba(self._feat(values)))[0])

    def _train(self) -> None:
        pairs = []
        for day in range(25, 56):
            as_of = SAMPLE_START + timedelta(days=day)
            for inst in self.master.tradable():
                bars = self.repo.as_of(inst.instrument_id, Timeframe.EOD, as_of)
                if len(bars) < 22:
                    continue
                snap = compute_features(bars, as_of)
                if not all(f in snap.values for f in DEFAULT_FEATURES):
                    continue
                lbl = label_signal(inst.instrument_id, as_of, self.repo, LabelConfig())
                if lbl:
                    pairs.append((snap, lbl))
        X = np.array([[p[0].values[f] for f in DEFAULT_FEATURES] for p in pairs])
        y = np.array([p[1].y for p in pairs], int)
        self.model = LogisticModel().fit(X, y)
        self.cal = IsotonicCalibrator().fit(self.model.predict_proba(X), y)
        self.n_train = len(pairs)

    def _paper_track(self) -> None:
        broker = PaperBroker(_CAPITAL, CostModel())
        probs, succ = [], []
        self.current_as_of = self.last
        for day in range(60, _N - 8):
            as_of = SAMPLE_START + timedelta(days=day)
            cands = scan(self.repo, self.master, as_of, ScanConfig(top_k=1))
            if not cands:
                continue
            self.current_as_of = as_of
            c = cands[0]
            prob = self._prob(c.features.values)
            entry = c.features.values["last_close"]
            sz = size_position(entry, entry * 0.97, avg_turnover=c.avg_turnover)
            if sz.quantity <= 0:
                continue
            closed = broker.execute(TradeSignal(instrument_id=c.instrument_id, signal_date=as_of),
                                    sz.quantity, self.repo)
            if closed:
                probs.append(prob)
                succ.append(int(closed.net_return > 0))
        self.broker = broker
        perf = compute_performance([t.net_return for t in broker.trades])
        self.perf = perf.model_dump()
        self.perf["nav"] = round(broker.cash, 2)
        self.perf["equity_curve"] = self._equity_curve(broker)
        self.perf["buckets"] = [b.model_dump() for b in precision_by_bucket(probs, succ)]

    def _equity_curve(self, broker) -> list[dict]:
        equity = _CAPITAL
        curve = [{"i": 0, "nav": round(equity, 2)}]
        for i, t in enumerate(broker.trades, 1):
            equity += t.realized_pnl
            curve.append({"i": i, "nav": round(equity, 2)})
        return curve

    def _current_recs(self) -> None:
        self.recs, self.vetoed, self.evidence_by_id = [], [], {}
        cands = scan(self.repo, self.master, self.current_as_of, ScanConfig(top_k=5))
        for c in cands:
            prob = self._prob(c.features.values)
            entry = c.features.values["last_close"]
            risk = assess_risk(RiskInputs(
                instrument_id=c.instrument_id, avg_turnover=c.avg_turnover, spread_bps=20,
                realized_vol=c.features.values.get("realized_vol", 0.02),
                manipulation_score=0.1, event_uncertainty=0.3, signal_age_days=0))
            sz = size_position(entry, entry * 0.97, avg_turnover=c.avg_turnover)
            sid = f"nse_{c.instrument_id}"
            self.evidence_by_id[c.instrument_id] = [{
                "id": sid, "tier": 1, "source": "NSE",
                "published_at": self.current_as_of.isoformat(),
                "text": f"NSE filing ({self.current_as_of}): {c.instrument_id} — {c.reason}. "
                        f"Order/catalyst noted; momentum and volume elevated."}]
            if risk.verdict.value == "VETO" or sz.quantity <= 0:
                self.vetoed.append({"instrument_id": c.instrument_id,
                                    "risk_verdict": risk.verdict.value,
                                    "flags": [f.code for f in risk.flags]})
                continue
            rec = build_recommendation(
                action=RecAction.BUY, instrument_id=c.instrument_id, as_of=self.current_as_of,
                entry=entry, stop_pct=0.03, target_pct=0.06, horizon_sessions=5,
                quantity=sz.quantity, calibrated_probability=prob,
                historical_sample_size=self.n_train, risk_verdict=risk.verdict.value,
                evidence_ids=[sid], model_version="logistic-0.1",
                thesis=f"{c.instrument_id}: {c.reason}")
            row = rec.model_dump(mode="json")
            row["score"] = round(c.score, 3)
            row["risk_flags"] = [f.code for f in risk.flags]
            row["complete"] = rec.is_complete
            self.recs.append(row)

    def _portfolio(self) -> None:
        last_price = {i.instrument_id: self.repo.as_of(
            i.instrument_id, Timeframe.EOD, self.current_as_of)[-1].close for i in self.master}
        pf = Portfolio(cash=60_000.0, holdings=[
            Holding(instrument_id="MOMO", quantity=50, avg_cost=150,
                    last_price=float(last_price["MOMO"]), sector="Sample"),
            Holding(instrument_id="CHOP", quantity=20, avg_cost=200,
                    last_price=float(last_price["CHOP"]), sector="Sample"),
        ])
        edges = {r["instrument_id"]: r["expected_net_return"] for r in self.recs}
        edges.setdefault("MOMO", 0.02)
        edges.setdefault("CHOP", -0.01)
        cands = [(r["instrument_id"], r["expected_net_return"], True) for r in self.recs]
        moves = recommend_rotation(pf, edges, cands)
        self.portfolio_data = {
            "cash": pf.cash, "nav": round(pf.nav, 2), "invested": round(pf.invested, 2),
            "sector_weights": {k: round(v, 3) for k, v in pf.sector_weights().items()},
            "holdings": [{"instrument_id": h.instrument_id, "quantity": h.quantity,
                          "avg_cost": h.avg_cost, "last_price": float(h.last_price),
                          "market_value": round(h.market_value, 2), "sector": h.sector}
                         for h in pf.holdings],
            "moves": [m.model_dump(mode="json") for m in moves],
        }

    def _alerts(self) -> None:
        eng = AlertEngine()
        for r in self.recs:
            eng.emit(make_new_opportunity(r["instrument_id"], r["score"],
                                          self.current_as_of.isoformat()))
        for v in self.vetoed:
            eng.emit(make_risk_veto(v["instrument_id"], ", ".join(v["flags"]) or "veto"))
        self.alert_rows = [a.model_dump(mode="json") for a in eng.delivered]

    def _chat_setup(self) -> None:
        reg = ModelCapabilityRegistry()
        reg.register(ModelRoute(name=MID, healthy=True,
                                permitted_data_classification=DataClass.USER))
        self._chat = GroundedChat(LLMGateway(MockProvider(_chat_responder), reg))

    def _observability(self) -> None:
        self.metrics = MetricsRegistry()
        self.metrics.incr("candidates", len(self.recs) + len(self.vetoed))
        self.metrics.incr("recommendations", len(self.recs))
        self.metrics.incr("risk_vetoes", len(self.vetoed))
        self.metrics.incr("alerts_delivered", len(self.alert_rows))
        self.feedback = FeedbackStore()
        self.rate = RateLimiter(limit=30, window_s=10.0)
        self.data_snapshot = "sample-seed-7"

    def _logbook_setup(self) -> None:
        """Persist the day's plan to the append-only logbook (in-memory SQLite in demo)."""
        engine = make_engine("sqlite://")
        init_db(engine)
        self.logbook = LogbookService(engine)
        as_of = self.current_as_of
        pd = self.portfolio_data

        self.logbook.record_portfolio_snapshot(
            as_of=as_of, nav=pd["nav"], cash=pd["cash"], invested=pd["invested"],
            holdings=[{"instrument_id": h["instrument_id"], "quantity": h["quantity"],
                       "avg_cost": h["avg_cost"], "last_price": h["last_price"],
                       "sector": h.get("sector")} for h in pd["holdings"]])

        self.rec_ids: dict[str, str] = {}
        for r in self.recs:
            rid = self.logbook.record_recommendation(
                as_of=date.fromisoformat(r["as_of"]), instrument_id=r["instrument_id"],
                action=r["action"], entry_low=r["entry_low"], entry_high=r["entry_high"],
                target=r["target"], invalidation=r["invalidation"],
                max_holding_sessions=r["max_holding_sessions"], quantity=r["quantity"],
                allocation=r["allocation"], calibrated_probability=r["calibrated_probability"],
                expected_net_return=r["expected_net_return"], risk_verdict=r["risk_verdict"],
                model_version=r["model_version"],
                expires_on=date.fromisoformat(r["expires_on"]) if r.get("expires_on") else None,
                horizon_kind="swing",
                data={"score": r.get("score"), "risk_flags": r.get("risk_flags"),
                      "evidence_ids": r.get("evidence_ids"), "thesis": r.get("thesis")})
            r["logbook_id"] = rid
            self.rec_ids[r["instrument_id"]] = rid
            self.logbook.record_decision(as_of=as_of, instrument_id=r["instrument_id"],
                                         decision=r["action"], rationale=r.get("thesis", ""),
                                         model_version=r["model_version"])

        for v in self.vetoed:
            self.logbook.record_risk_veto(instrument_id=v["instrument_id"], as_of=as_of,
                                          verdict=v["risk_verdict"], flags={"codes": v["flags"]})

        self.logbook.record_daily_plan(
            plan_date=as_of, summary=f"{len(self.recs)} rec, {len(self.vetoed)} veto",
            changes=[{"instrument_id": m["instrument_id"], "action": m["action"],
                      "from_instrument": m.get("from_instrument"), "rupees": m.get("rupees", 0),
                      "reason": m.get("reason", "")} for m in pd["moves"]])

        for f in self.broker.fills:
            self.logbook.record_paper_fill(
                instrument_id=f.instrument_id, side=f.side.value, quantity=f.quantity,
                price=float(f.price), cost=float(f.cost), session_date=f.session_date, kind=f.kind)

        for a in self.alert_rows:
            self.logbook.record_alert(alert_type=a["type"], instrument_id=a["instrument_id"],
                                      severity=a["severity"], channel="in_app", delivered=True,
                                      message=a["message"])

    def _floor_setup(self) -> None:
        gw = LLMGateway(MockProvider(_floor_responder), build_real_registry())
        self._floor = ResearchFloor(gw, self.repo, [i.instrument_id for i in self.master])
        self._floor_cache: dict[str, dict] = {}

    # -- API surface -----------------------------------------------------------

    async def floor_for(self, instrument_id: str) -> dict:
        """Run the 9-agent floor for one instrument (cached). Async: endpoints await it."""
        if instrument_id in self._floor_cache:
            return self._floor_cache[instrument_id]
        bars = self.repo.as_of(instrument_id, Timeframe.EOD, self.current_as_of)
        if not bars:
            return {"available": False}
        features = compute_features(bars, self.current_as_of)
        evidence = self.evidence_by_id.get(instrument_id) or [
            {"id": f"nse_{instrument_id}",
             "text": f"NSE filing ({self.current_as_of}): {instrument_id} catalyst noted."}]
        res = await self._floor.investigate(instrument_id, self.current_as_of, features, evidence)
        out = {a: {"agent": r.agent, "thesis": r.thesis, "confidence": round(r.confidence, 3),
                   "evidence": [e.source for e in r.evidence], "data": r.data}
               for a, r in res.items()}
        self._floor_cache[instrument_id] = out
        return out

    def logbook_day(self, as_of: str | None = None) -> dict:
        d = date.fromisoformat(as_of) if as_of else self.current_as_of
        return self.logbook.day(d)

    def logbook_reconstruct(self, rec_id: str) -> dict:
        return self.logbook.reconstruct_recommendation(rec_id)

    def record_user_execution(self, *, instrument_id: str, side: str, quantity: int,
                              price: float, note: str = "") -> dict:
        from datetime import datetime, timezone
        rid = self.logbook.record_user_execution(
            instrument_id=instrument_id, side=side, quantity=quantity, price=price,
            executed_at=datetime.now(timezone.utc), note=note)
        return {"recorded": True, "id": rid}

    def metrics_snapshot(self) -> dict:
        runs = self._chat.gateway.runs
        failures = sum(1 for r in runs if r.state.value == "failed")
        self.metrics.set_gauge("llm_runs", len(runs))
        self.metrics.set_gauge("llm_failures", failures)
        snap = self.metrics.snapshot()
        snap["derived"]["llm_failure_rate"] = failures / len(runs) if runs else 0.0
        return snap

    def health_dict(self) -> dict:
        # sample feed is always fresh; a real feed passes its true age + LLM health here
        rep = evaluate_health(HealthInputs(feed_age_days=0.0, llm_available=True))
        out = rep.model_dump(mode="json")
        out["as_of"] = self.current_as_of.isoformat()
        return out

    def chat_allowed(self) -> bool:
        return self.rate.allow("chat")

    def audit(self, instrument_id: str) -> dict:
        rec = next((r for r in self.recs if r["instrument_id"] == instrument_id), None)
        if rec is None:
            return {"error": "no recommendation", "instrument_id": instrument_id}
        bundle = build_audit_bundle(
            rec, evidence=self.evidence_by_id.get(instrument_id, []),
            llm_runs=[r.model_dump(mode="json") for r in self._chat.gateway.runs],
            model_version=rec["model_version"], data_snapshot=self.data_snapshot)
        out = bundle.model_dump(mode="json")
        out["reconstructable"] = bundle.is_reconstructable()
        return out

    def record_feedback(self, instrument_id: str, label: str, rec_id: str = "",
                        note: str = "") -> dict:
        fb = self.feedback.record(Feedback(instrument_id=instrument_id, rec_id=rec_id,
                                           label=FeedbackLabel(label), note=note))
        return {"recorded": True, "label": fb.label.value, "total": len(self.feedback.items())}

    def instruments(self) -> list[dict]:
        return [{"instrument_id": i.instrument_id, "symbol": i.symbol, "name": i.name,
                 "sector": i.sector, "status": i.status.value} for i in self.master]

    def bars(self, instrument_id: str, limit: int = 60) -> list[dict]:
        bars = self.repo.as_of(instrument_id, Timeframe.EOD, self.current_as_of)[-limit:]
        return [{"date": b.session_date.isoformat(), "open": float(b.open), "high": float(b.high),
                 "low": float(b.low), "close": float(b.close), "volume": b.volume} for b in bars]

    def evidence(self, instrument_id: str) -> list[dict]:
        return self.evidence_by_id.get(instrument_id, [])

    async def chat(self, question: str, instrument_id: str | None = None) -> dict:
        evidence = self.evidence_by_id.get(instrument_id, []) if instrument_id else \
            [d for docs in self.evidence_by_id.values() for d in docs]
        res = await self._chat.answer(question, evidence)
        return res.model_dump()
