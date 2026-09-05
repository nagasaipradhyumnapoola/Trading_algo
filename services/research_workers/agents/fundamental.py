"""Agent 4 — Fundamental. Is the catalyst financially meaningful?

Analyzes growth, margins, ROE/ROCE, debt, cash flow, valuation, shareholding, and
explains event-to-revenue significance.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class FundamentalAgent(Agent):
    name = "fundamental"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: fundamentals lookup + event-to-revenue sizing.")
