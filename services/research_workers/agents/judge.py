"""Agent 9 — Judge / Decision. Synthesize into a structured thesis via the gateway.

Consumes the analyst outputs + Bull/Bear cases over the SAME evidence, resolves
contradictions, lists unknowns/invalidation, and recommends one action
(BUY/SELL/HOLD/ROTATE/NO_TRADE). The Judge does NOT produce probabilities, expected
return, sizing, or risk vetoes, and CANNOT override the independent risk engine —
the pipeline applies the risk gate after the Judge.
"""

from __future__ import annotations

from ..llm_gateway import LLMGateway, LLMTask
from .base import AgentResult, Evidence


class JudgeAgent:
    name = "judge"

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self.gateway = gateway

    async def run(self, instrument_id: str, evidence: list[dict],
                  summaries: dict | None = None) -> AgentResult:
        if self.gateway is None:
            raise RuntimeError("JudgeAgent requires an LLMGateway")

        summary_text = "; ".join(f"{k}: {v}" for k, v in (summaries or {}).items() if v)
        instruction = (
            "Synthesize the analyst views into a structured thesis and recommend one action "
            "(BUY, SELL, HOLD, ROTATE, NO_TRADE). Cite source ids; list unknowns and what "
            f"would invalidate the thesis. Analyst views — {summary_text}"
        )
        result = await self.gateway.request(
            agent=self.name, task=LLMTask.RESEARCH_SYNTHESIS,
            payload={"instruction": instruction, "sources": evidence})
        if not result.ok:
            return AgentResult(agent=self.name, ticker=instrument_id, confidence=0.0,
                               data={"available": False, "action": "NO_TRADE"})

        data = result.data or {}
        claims = data.get("claims", [])
        ev = [Evidence(source=str(eid), claim=c.get("claim", ""))
              for c in claims for eid in c.get("evidence_ids", [])]
        return AgentResult(
            agent=self.name, ticker=instrument_id, thesis=data.get("thesis", ""),
            confidence=0.0, evidence=ev,
            data={"action": data.get("action", "NO_TRADE"), "unknowns": data.get("unknowns", []),
                  "claims": claims, "citations": data.get("citations", [])})
