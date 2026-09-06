"""In-process metrics registry (counters + gauges) with derived rates.

Tracks LLM structured-output failures, recommendation coverage, risk-veto rate,
alert delivery, and feed freshness. A real deployment scrapes these into
Prometheus; here they are exposed via the API /metrics endpoint.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetricsRegistry(BaseModel):
    counters: dict[str, float] = Field(default_factory=dict)
    gauges: dict[str, float] = Field(default_factory=dict)

    def incr(self, name: str, n: float = 1.0) -> None:
        self.counters[name] = self.counters.get(name, 0.0) + n

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def get(self, name: str) -> float:
        return self.counters.get(name, self.gauges.get(name, 0.0))

    def rate(self, numerator: str, denominator: str) -> float:
        den = self.counters.get(denominator, 0.0)
        return (self.counters.get(numerator, 0.0) / den) if den else 0.0

    def snapshot(self) -> dict[str, object]:
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "derived": {
                "llm_failure_rate": self.rate("llm_failures", "llm_runs"),
                "risk_veto_rate": self.rate("risk_vetoes", "candidates"),
                "recommendation_coverage": self.rate("recommendations", "candidates"),
            },
        }
