"""Agent 7 — Bull. Construct the strongest evidence-based long case.

Cites evidence, identifies catalysts, quantifies upside where possible, explains
why the market may be underpricing the information, and lists assumptions.
Cannot invent evidence.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class BullAgent(Agent):
    name = "bull"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: build long case over shared evidence set.")
