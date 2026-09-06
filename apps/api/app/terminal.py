"""TerminalService — builds the Phase 6 terminal's data once, from the engines.

Trains the calibrated model, computes live recommendations (probability from the
calibrated quant system, risk from the independent engine, sizing deterministic),
runs an out-of-sample paper track for the performance dashboard, seeds alerts, and
holds evidence for the grounded chat. SAMPLE data — clearly labelled. No broker.
"""

from __future__ import annotations

import json
import re
from datetime import timedelta

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
from services.ingestion.sample import SAMPLE_START, build_sample_universe
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
from services.quant import ScanConfig, compute_features, scan
from services.quant.calibration import IsotonicCalibrator
from services.quant.ml import DEFAULT_FEATURES, LogisticModel
from services.research_workers.chat import GroundedChat
from services.research_workers.llm_gateway import (
    DataClass,
    LLMGateway,
    MockProvider,
    ModelCapabilityRegistry,
    ModelRoute,
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


class TerminalService:
    def __init__(self) -> None:
        self.repo, self.master, self.last = build_sample_universe(n=_N)
        self._train()
        self._paper_track()
        self._current_recs()
        self._portfolio()
        self._alerts()
        self._chat_setup()
        self._observability()

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

    # -- API surface -----------------------------------------------------------

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
