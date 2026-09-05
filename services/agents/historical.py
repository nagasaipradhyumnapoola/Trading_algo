"""Agent 6 — Historical Analogue. Find similar past situations.

Matches on event type, sector, size, magnitude, price/volume reaction, regime,
valuation and novelty. Returns hit-rates and return distributions. Uses ONLY
information available at the historical decision timestamp (no look-ahead).
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class HistoricalAgent(Agent):
    name = "historical"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 2: event DB + point-in-time analogue retrieval.")
