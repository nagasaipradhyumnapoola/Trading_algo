"""Agent 4 — Fundamental. Extract reported financial facts via the gateway.

Pulls reported facts (growth, margins, debt, cash flow) as grounded claims and
flags what is missing. Numbers used for decisions still come from the deterministic
quant engine — this agent extracts and contextualizes evidence, it does not score.
"""

from __future__ import annotations

from statistics import fmean

from ..llm_gateway import LLMGateway, LLMTask
from ..review_queue import ReviewItem, ReviewQueue, ReviewReason
from .base import AgentResult, Evidence

_INSTRUCTION = (
    "Extract reported financial facts for the referenced Indian equity (growth, "
    "margins, ROE/ROCE, debt, cash flow, valuation) as grounded claims, and list "
    "what material information is missing. Cite a source id for every claim."
)


class FundamentalAgent:
    name = "fundamental"

    def __init__(self, gateway: LLMGateway | None = None, *,
                 review: ReviewQueue | None = None, min_confidence: float = 0.5) -> None:
        self.gateway = gateway
        self.review = review
        self.min_confidence = min_confidence

    async def run(self, instrument_id: str, sources: list[dict]) -> AgentResult:
        if self.gateway is None:
            raise RuntimeError("FundamentalAgent requires an LLMGateway")

        result = await self.gateway.request(
            agent=self.name, task=LLMTask.EVENT_EXTRACTION,
            payload={"instruction": _INSTRUCTION, "sources": sources},
        )

        if not result.ok:
            if self.review is not None:
                self.review.enqueue(ReviewItem(instrument_id=instrument_id, task="fundamental",
                                               reason=ReviewReason.DEGRADED,
                                               detail=result.error or "llm unavailable"))
            return AgentResult(agent=self.name, ticker=instrument_id, confidence=0.0,
                               data={"available": False})

        data = result.data or {}
        claims = data.get("claims", [])
        confidence = fmean([c.get("confidence", 0.0) for c in claims]) if claims else 0.0
        if confidence < self.min_confidence and self.review is not None:
            self.review.enqueue(ReviewItem(instrument_id=instrument_id, task="fundamental",
                                           reason=ReviewReason.LOW_CONFIDENCE,
                                           detail=f"conf={confidence:.2f}", payload=data))

        evidence = [Evidence(source=str(eid), claim=c.get("claim", ""))
                    for c in claims for eid in c.get("evidence_ids", [])]
        unknowns = data.get("unknowns", [])
        thesis = f"{len(claims)} facts, {len(unknowns)} gaps"
        return AgentResult(agent=self.name, ticker=instrument_id, thesis=thesis,
                           confidence=confidence, evidence=evidence, data=data)
