"""Smoke tests for the Phase 1 skeleton."""

from services.agents import (
    BearAgent,
    BullAgent,
    DiscoveryAgent,
    JudgeAgent,
    MarketAgent,
    NewsAgent,
)


def test_nine_agents_importable():
    agents = [
        DiscoveryAgent(),
        NewsAgent(),
        MarketAgent(),
        BullAgent(),
        BearAgent(),
        JudgeAgent(),
    ]
    names = {a.name for a in agents}
    assert {"discovery", "news", "market", "bull", "bear", "judge"} <= names


def test_api_imports():
    from apps.api.app.main import app

    assert app.title == "Indian Alpha API"
