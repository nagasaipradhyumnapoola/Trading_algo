"""Agent 3 — Market. Interpret price/volume/trend behavior.

The LLM interprets; it does NOT compute numbers. All numerical features come
from the deterministic feature engine in services/quant.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class MarketAgent(Agent):
    name = "market"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: consume precomputed features from services/quant.")
