"""Audit export, feedback store, model rollback."""

from services.monitoring import (
    Feedback,
    FeedbackLabel,
    FeedbackStore,
    build_audit_bundle,
)
from services.quant import Approval, ModelCard, ModelRegistry

_REC = {
    "instrument_id": "MOMO", "as_of": "2026-05-10", "target": 184.89,
    "invalidation": 169.19, "calibrated_probability": 0.806, "risk_verdict": "PASS",
    "model_version": "logistic-0.1",
}
_EVIDENCE = [{"id": "nse_MOMO", "text": "NSE filing"}]


def test_audit_bundle_reconstructable():
    b = build_audit_bundle(_REC, evidence=_EVIDENCE, llm_runs=[{"run_id": "run_1"}],
                           model_version="logistic-0.1", data_snapshot="sample-seed-7")
    assert b.is_reconstructable()


def test_audit_bundle_missing_evidence_not_reconstructable():
    b = build_audit_bundle(_REC, evidence=[], model_version="logistic-0.1",
                           data_snapshot="sample-seed-7")
    assert not b.is_reconstructable()


def test_feedback_is_recorded_and_separated():
    store = FeedbackStore()
    store.record(Feedback(instrument_id="MOMO", rec_id="r1", label=FeedbackLabel.USEFUL))
    store.record(Feedback(instrument_id="MOMO", rec_id="r1", label=FeedbackLabel.EXECUTED))
    labels = {f.label for f in store.by_instrument("MOMO")}
    assert labels == {FeedbackLabel.USEFUL, FeedbackLabel.EXECUTED}


def test_model_rollback_restores_previous_champion():
    reg = ModelRegistry()
    a = reg.register(ModelCard(name="v1"))
    b = reg.register(ModelCard(name="v2"))
    reg.set_champion(a.model_id)
    reg.set_champion(b.model_id)
    assert reg.champion().model_id == b.model_id
    reg.rollback()
    assert reg.champion().model_id == a.model_id      # reverted, no data migration
    assert reg.get(b.model_id).approval is Approval.APPROVED
