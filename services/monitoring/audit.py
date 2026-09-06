"""End-to-end audit export.

Bundles a recommendation with everything needed to reconstruct it: the evidence it
cited, the immutable llm_run records behind any extraction, the model version and
card, and the data snapshot. One bundle answers "why did the system say this, on
what information, with which model?" — the Phase 7 acceptance test.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AuditBundle(BaseModel):
    recommendation: dict
    evidence: list[dict] = Field(default_factory=list)
    llm_runs: list[dict] = Field(default_factory=list)
    model_version: str = ""
    model_card: dict | None = None
    data_snapshot: str = ""
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_reconstructable(self) -> bool:
        """A bundle can rebuild the decision iff the essentials are present."""
        rec = self.recommendation
        return bool(
            rec.get("instrument_id") and rec.get("as_of")
            and rec.get("target") is not None and rec.get("invalidation") is not None
            and rec.get("calibrated_probability") is not None
            and rec.get("risk_verdict") and self.model_version and self.data_snapshot
            and self.evidence
        )


def build_audit_bundle(
    recommendation: dict, *, evidence: list[dict], llm_runs: list[dict] | None = None,
    model_version: str = "", model_card: dict | None = None, data_snapshot: str = "",
) -> AuditBundle:
    return AuditBundle(
        recommendation=recommendation, evidence=evidence, llm_runs=llm_runs or [],
        model_version=model_version or recommendation.get("model_version", ""),
        model_card=model_card, data_snapshot=data_snapshot,
    )
