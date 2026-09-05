"""Agent 2 — News/Event. Understand catalysts and whether they are priced in.

Classifies event type, assesses novelty/materiality/surprise, detects conflicting
reports, and ranks source quality. Dedup happens upstream in the news service.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class NewsAgent(Agent):
    name = "news"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: event taxonomy + materiality/novelty scoring.")
