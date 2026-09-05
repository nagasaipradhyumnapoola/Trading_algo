"""Agent 2 — News/Event. Extract catalysts via the gateway, with grounding.

Calls the mandatory LLMGateway (never a provider directly). Flags degraded,
low-confidence, and conflicting extractions to the human-review queue. Every claim
is citation-validated by the gateway before it reaches here, so nothing ungrounded
flows downstream.
"""

from __future__ import annotations

from statistics import fmean

from ..llm_gateway import LLMGateway, LLMTask
from ..review_queue import ReviewItem, ReviewQueue, ReviewReason
from .base import AgentResult, Evidence

_INSTRUCTION = (
    "Extract material market events for the referenced Indian equity. For each event "
    "give a type, materiality, novelty and surprise. Support every claim with a source id."
)


class NewsAgent:
    name = "news"

    def __init__(self, gateway: LLMGateway | None = None, *,
                 review: ReviewQueue | None = None, min_confidence: float = 0.5) -> None:
        self.gateway = gateway
        self.review = review
        self.min_confidence = min_confidence

    async def run(self, instrument_id: str, sources: list[dict]) -> AgentResult:
        if self.gateway is None:
            raise RuntimeError("NewsAgent requires an LLMGateway")

        result = await self.gateway.request(
            agent=self.name, task=LLMTask.EVENT_EXTRACTION,
            payload={"instruction": _INSTRUCTION, "sources": sources},
        )

        if not result.ok:
            self._flag(instrument_id, ReviewReason.DEGRADED, result.error or "llm unavailable")
            return AgentResult(agent=self.name, ticker=instrument_id, confidence=0.0,
                               data={"available": False})

        data = result.data or {}
        claims = data.get("claims", [])
        confidence = fmean([c.get("confidence", 0.0) for c in claims]) if claims else 0.0

        polarities = {c.get("polarity") for c in claims}
        if "positive" in polarities and "negative" in polarities:
            self._flag(instrument_id, ReviewReason.CONFLICT, "conflicting claim polarities", data)
        if confidence < self.min_confidence:
            self._flag(instrument_id, ReviewReason.LOW_CONFIDENCE, f"conf={confidence:.2f}", data)

        events = data.get("event_candidates", [])
        thesis = ", ".join(sorted({e.get("type", "?") for e in events})) or "no material event"
        evidence = [Evidence(source=str(eid), claim=c.get("claim", ""))
                    for c in claims for eid in c.get("evidence_ids", [])]

        return AgentResult(agent=self.name, ticker=instrument_id, thesis=thesis,
                           confidence=confidence, evidence=evidence, data=data)

    def _flag(self, instrument_id, reason, detail, payload=None) -> None:
        if self.review is not None:
            self.review.enqueue(ReviewItem(instrument_id=instrument_id, task="event_extraction",
                                           reason=reason, detail=detail, payload=payload or {}))
