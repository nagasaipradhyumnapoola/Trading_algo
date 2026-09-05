"""Shared contracts for the AI research floor.

Spec §13: every agent returns machine-readable JSON validated with Pydantic.
Free-form agent prose must never flow directly into the ML engine.
"""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """One cited piece of evidence. Every material claim needs one."""

    source: str
    url: str | None = None
    timestamp: datetime | None = None
    claim: str
    tier: int = Field(default=3, ge=1, le=4, description="1=NSE/SEBI … 4=social")


class AgentResult(BaseModel):
    """Base structured output shared by all agents."""

    agent: str
    ticker: str
    thesis: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class Candidate(BaseModel):
    """A discovered opportunity flowing into the research floor."""

    ticker: str
    reason: str
    features: dict[str, float] = Field(default_factory=dict)


class Agent(abc.ABC):
    """Abstract async agent. Subclasses implement `run`."""

    name: str = "agent"

    @abc.abstractmethod
    async def run(self, candidate: Candidate) -> AgentResult:  # pragma: no cover
        ...
