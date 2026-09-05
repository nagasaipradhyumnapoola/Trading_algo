"""Agent 9 — Judge / Decision. Resolve the debate into a structured thesis.

Consumes all analyst outputs, Bull/Bear cases, historical analogues, quant + ML
features and regime info. Resolves contradictions, ranks evidence, flags
uncertainty, and recommends BUY / SELL / HOLD / ROTATE / NO_TRADE.

The Judge is NOT allowed to override the independent Risk Engine.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class JudgeAgent(Agent):
    name = "judge"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: synthesize thesis; defer final gate to risk engine.")
