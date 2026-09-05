"""The nine-agent AI research floor.

LLMs analyze evidence; deterministic code (services/quant, services/ml) computes
numbers. Bull and Bear see the same evidence. Risk keeps an independent veto.
"""

from .base import Agent, AgentResult, Candidate, Evidence
from .bear import BearAgent
from .bull import BullAgent
from .discovery import DiscoveryAgent
from .fundamental import FundamentalAgent
from .historical import HistoricalAgent
from .judge import JudgeAgent
from .market import MarketAgent
from .news import NewsAgent
from .sentiment import SentimentAgent

__all__ = [
    "Agent",
    "AgentResult",
    "Candidate",
    "Evidence",
    "DiscoveryAgent",
    "NewsAgent",
    "MarketAgent",
    "FundamentalAgent",
    "SentimentAgent",
    "HistoricalAgent",
    "BullAgent",
    "BearAgent",
    "JudgeAgent",
]
