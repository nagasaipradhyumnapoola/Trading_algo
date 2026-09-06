"""Agent 5 — Sentiment. Source-weighted sentiment via the gateway, with skepticism.

Never treats social chatter as fact; surfaces duplicated/coordinated/pump signals.
Runs through the mandatory gateway; degraded results are flagged, not invented.
"""

from __future__ import annotations

from ..llm_gateway import LLMGateway, LLMTask
from ..review_queue import ReviewItem, ReviewQueue, ReviewReason
from .base import AgentResult, Evidence

_INSTRUCTION = (
    "Summarize source-weighted sentiment for the referenced Indian equity. Down-weight "
    "duplicated/syndicated stories and coordinated/bot-like posts; flag pump behavior."
)


class SentimentAgent:
    name = "sentiment"

    def __init__(self, gateway: LLMGateway | None = None, *, review: ReviewQueue | None = None) -> None:
        self.gateway = gateway
        self.review = review

    async def run(self, instrument_id: str, sources: list[dict]) -> AgentResult:
        if self.gateway is None:
            raise RuntimeError("SentimentAgent requires an LLMGateway")

        result = await self.gateway.request(
            agent=self.name, task=LLMTask.SENTIMENT,
            payload={"instruction": _INSTRUCTION, "sources": sources})

        if not result.ok:
            if self.review is not None:
                self.review.enqueue(ReviewItem(instrument_id=instrument_id, task="sentiment",
                                               reason=ReviewReason.DEGRADED,
                                               detail=result.error or "llm unavailable"))
            return AgentResult(agent=self.name, ticker=instrument_id, confidence=0.0,
                               data={"available": False})

        data = result.data or {}
        flags = data.get("manipulation_flags", [])
        if flags and self.review is not None:
            self.review.enqueue(ReviewItem(instrument_id=instrument_id, task="sentiment",
                                           reason=ReviewReason.CONFLICT,
                                           detail=f"manipulation: {flags}", payload=data))
        label, score = data.get("label", "neutral"), data.get("sentiment", 0.0)
        thesis = f"sentiment {label} ({score:+.2f})" + (f", flags: {', '.join(flags)}" if flags else "")
        evidence = [Evidence(source=str(cid), claim="sentiment") for cid in data.get("citations", [])]
        return AgentResult(agent=self.name, ticker=instrument_id, thesis=thesis,
                           confidence=abs(float(score)), evidence=evidence, data=data)
