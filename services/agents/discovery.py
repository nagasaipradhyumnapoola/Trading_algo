"""Agent 1 — Discovery. Find opportunities the user did not ask for.

Generates dynamic search queries, investigates unusual activity, creates and
prioritizes candidate opportunities, and can initiate follow-up searches.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class DiscoveryAgent(Agent):
    name = "discovery"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: wire scanner + web search + follow-up queries.")
