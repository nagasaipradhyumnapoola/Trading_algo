"""Agent 8 — Bear. Strongest opposing case via the gateway.

Searches for already-priced-in risk, weak fundamentals, misleading headlines, poor
liquidity, circuit/manipulation risk, valuation risk, catalyst decay, and historical
failure cases. Equal access to the SAME shared evidence pack as the Bull agent.
"""

from __future__ import annotations

from statistics import fmean

from ..llm_gateway import LLMGateway, LLMTask
from .base import AgentResult, Evidence

_INSTRUCTION = (
    "Build the strongest evidence-grounded BEAR case for the referenced Indian equity: "
    "priced-in risk, weak fundamentals, liquidity/circuit/manipulation risk, valuation "
    "risk, catalyst decay, historical failure cases. Cite source ids. Do not invent evidence."
)


class BearAgent:
    name = "bear"

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self.gateway = gateway

    async def run(self, instrument_id: str, evidence: list[dict]) -> AgentResult:
        if self.gateway is None:
            raise RuntimeError("BearAgent requires an LLMGateway")
        result = await self.gateway.request(
            agent=self.name, task=LLMTask.BEAR_CASE,
            payload={"instruction": _INSTRUCTION, "sources": evidence})
        if not result.ok:
            return AgentResult(agent=self.name, ticker=instrument_id, confidence=0.0,
                               data={"available": False})
        data = result.data or {}
        claims = data.get("claims", [])
        conf = fmean([c.get("confidence", 0.0) for c in claims]) if claims else 0.0
        ev = [Evidence(source=str(eid), claim=c.get("claim", ""))
              for c in claims for eid in c.get("evidence_ids", [])]
        return AgentResult(agent=self.name, ticker=instrument_id, thesis=data.get("thesis", ""),
                           confidence=conf, evidence=ev, data=data)
