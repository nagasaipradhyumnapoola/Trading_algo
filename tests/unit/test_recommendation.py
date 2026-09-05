"""Recommendation completeness gate."""

from datetime import date

from services.risk_portfolio import RecAction, Recommendation, build_recommendation


def _rec(**kw):
    base = dict(action=RecAction.BUY, instrument_id="A", as_of=date(2026, 1, 1),
                entry=100, stop_pct=0.03, target_pct=0.06, horizon_sessions=5,
                quantity=10, calibrated_probability=0.7, historical_sample_size=143,
                risk_verdict="PASS", evidence_ids=["doc1"], model_version="logistic-0.1")
    base.update(kw)
    return build_recommendation(**base)


def test_complete_recommendation():
    rec = _rec()
    assert rec.is_complete
    assert rec.target == 106.0 and rec.invalidation == 97.0
    assert rec.risk_reward == 2.0
    assert rec.allocation == 1000.0
    assert rec.expires_on is not None


def test_missing_quantity_is_incomplete():
    rec = _rec(quantity=0)
    assert not rec.is_complete
    assert "quantity" in rec.missing_fields()


def test_missing_evidence_is_incomplete():
    rec = _rec(evidence_ids=[])
    assert "evidence_ids" in rec.missing_fields()


def test_no_trade_needs_no_fields():
    rec = Recommendation(action=RecAction.NO_TRADE, instrument_id="-", as_of=date(2026, 1, 1))
    assert rec.is_complete                       # NO_TRADE is always "complete"
