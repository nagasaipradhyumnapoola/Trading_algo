"""Agent 5 — Sentiment. News/analyst/social sentiment — with skepticism.

Never treats 100 copied posts as 100 confirmations. Detects duplicated/syndicated
stories, coordinated posts, pump behavior, and bot-like activity. Social is
secondary evidence, not proof.
"""

from __future__ import annotations

from .base import Agent, AgentResult, Candidate


class SentimentAgent(Agent):
    name = "sentiment"

    async def run(self, candidate: Candidate) -> AgentResult:
        raise NotImplementedError("Phase 1: dedup-aware sentiment + manipulation signals.")
