"""Extraction evaluation harness.

Scores an extraction agent against a held-out, human-labeled sample: precision and
recall of event types, per type and overall. The acceptance gate for Phase 3 is
measured here (real thresholds need a real model + real labels; the harness is the
instrument that measures them).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LabeledExample(BaseModel):
    instrument_id: str
    sources: list[dict]
    expected_types: set[str] = Field(default_factory=set)


class TypeScore(BaseModel):
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0


class EvalReport(BaseModel):
    n: int = 0
    per_type: dict[str, TypeScore] = Field(default_factory=dict)
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0


async def evaluate(agent, examples: list[LabeledExample]) -> EvalReport:
    report = EvalReport(n=len(examples))
    for ex in examples:
        result = await agent.run(ex.instrument_id, ex.sources)
        predicted = {e.get("type") for e in (result.data or {}).get("event_candidates", [])}
        expected = ex.expected_types

        for t in expected & predicted:
            report.per_type.setdefault(t, TypeScore()).tp += 1
            report.tp += 1
        for t in predicted - expected:
            report.per_type.setdefault(t, TypeScore()).fp += 1
            report.fp += 1
        for t in expected - predicted:
            report.per_type.setdefault(t, TypeScore()).fn += 1
            report.fn += 1
    return report
