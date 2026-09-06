"""Research floor orchestration.

Runs the analyst agents in parallel, builds a shared evidence pack, runs Bull and
Bear in parallel on the SAME evidence, then the Judge. LLMs analyze evidence;
deterministic engines (Market features, Historical analogues) produce their numbers.
The Judge's action is advisory — the risk engine gate is applied by the pipeline
afterwards and the Judge cannot override it.
"""

from __future__ import annotations

import asyncio
from datetime import date

from .agents import (
    BearAgent,
    BullAgent,
    FundamentalAgent,
    HistoricalAgent,
    JudgeAgent,
    MarketAgent,
    NewsAgent,
    SentimentAgent,
)
from .llm_gateway import LLMGateway
from .review_queue import ReviewQueue


class ResearchFloor:
    def __init__(self, gateway: LLMGateway, repo, universe_ids: list[str], *,
                 review: ReviewQueue | None = None) -> None:
        self.news = NewsAgent(gateway, review=review)
        self.fundamental = FundamentalAgent(gateway, review=review)
        self.sentiment = SentimentAgent(gateway, review=review)
        self.market = MarketAgent()
        self.historical = HistoricalAgent(repo, universe_ids)
        self.bull = BullAgent(gateway)
        self.bear = BearAgent(gateway)
        self.judge = JudgeAgent(gateway)

    async def investigate(self, instrument_id: str, as_of: date, features,
                          evidence: list[dict]) -> dict:
        news, fund, sent = await asyncio.gather(
            self.news.run(instrument_id, evidence),
            self.fundamental.run(instrument_id, evidence),
            self.sentiment.run(instrument_id, evidence))
        market = self.market.run(instrument_id, features)
        historical = self.historical.run(instrument_id, as_of)

        # Bull and Bear debate the SAME shared evidence pack, in parallel.
        bull, bear = await asyncio.gather(
            self.bull.run(instrument_id, evidence),
            self.bear.run(instrument_id, evidence))

        summaries = {"news": news.thesis, "market": market.thesis, "fundamental": fund.thesis,
                     "sentiment": sent.thesis, "historical": historical.thesis,
                     "bull": bull.thesis, "bear": bear.thesis}
        judge = await self.judge.run(instrument_id, evidence, summaries)

        return {"news": news, "market": market, "fundamental": fund, "sentiment": sent,
                "historical": historical, "bull": bull, "bear": bear, "judge": judge}


def floor_stats(results: list[dict]) -> dict[str, dict]:
    """Per-agent availability + grounding rate across a batch of investigations."""
    agents = ["news", "market", "fundamental", "sentiment", "historical", "bull", "bear", "judge"]
    stats: dict[str, dict] = {a: {"ran": 0, "available": 0, "grounded": 0} for a in agents}
    for res in results:
        for a in agents:
            r = res.get(a)
            if r is None:
                continue
            stats[a]["ran"] += 1
            if r.data.get("available", True):
                stats[a]["available"] += 1
            if r.evidence or r.data.get("point_in_time") or r.data.get("deterministic"):
                stats[a]["grounded"] += 1
    return stats
