"""Agent 8 — Bear. Construct the strongest opposing case.

Searches for already-priced-in risk, weak fundamentals, misleading headlines, poor
liquidity, circuit/manipulation risk, valuation risk, catalyst decay and historical
failure cases. Equal access to the same evidence as Bull.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class BearAgent(Agent):
    name = "bear"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: build bear case over shared evidence set.")
