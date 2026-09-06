"""Structured output schemas for LLM tasks + the event taxonomy.

Every task maps to a Pydantic model. The gateway validates raw model output against
these before anything flows downstream, and pulls the cited evidence ids out for
citation validation. Free-form prose never reaches the feature store.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from .contracts import LLMTask


class EventType(str, Enum):
    CONTRACT_ORDER = "contract_order"
    GOVERNMENT_ORDER = "government_order"
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    PROMOTER_HOLDING = "promoter_holding"
    MA = "m_and_a"
    CAPACITY = "capacity_expansion"
    REGULATORY_APPROVAL = "regulatory_approval"
    REGULATORY_ACTION = "regulatory_action"
    MANAGEMENT_GOVERNANCE = "management_governance"
    CREDIT_RATING = "credit_rating"
    BUYBACK = "buyback"
    DIVIDEND = "dividend"
    FUNDRAISING = "fundraising"
    PRODUCT_LAUNCH = "product_launch"
    INDEX_CHANGE = "index_change"
    BLOCK_DEAL = "block_deal"
    COMMODITY_SHOCK = "commodity_shock"
    POLICY_SHOCK = "policy_shock"
    SECTOR_SHOCK = "sector_shock"
    LITIGATION = "litigation"
    OTHER = "other"


class CitedModel(BaseModel):
    """Base for every structured result. Exposes the evidence ids it relies on."""

    citations: list[str] = Field(default_factory=list)

    def cited_ids(self) -> set[str]:
        return set(self.citations)


class Claim(CitedModel):
    claim: str
    polarity: Literal["positive", "negative", "neutral"] = "neutral"
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)  # extraction confidence, NOT trade-win

    def cited_ids(self) -> set[str]:
        return set(self.citations) | set(self.evidence_ids)


class EventCandidate(BaseModel):
    type: EventType
    materiality: float = Field(default=0.0, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    surprise: float = Field(default=0.0, ge=0.0, le=1.0)


class ExtractionResult(CitedModel):
    schema_version: str = "1.0"
    instrument_ids: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    event_candidates: list[EventCandidate] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    def cited_ids(self) -> set[str]:
        ids = set(self.citations)
        for c in self.claims:
            ids |= c.cited_ids()
        return ids


class ThesisResult(CitedModel):
    thesis: str
    claims: list[Claim] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    def cited_ids(self) -> set[str]:
        ids = set(self.citations)
        for c in self.claims:
            ids |= c.cited_ids()
        return ids


class SummaryResult(CitedModel):
    summary: str


class ChatAnswer(CitedModel):
    answer: str


class EntityResolutionResult(CitedModel):
    resolved: dict[str, str] = Field(default_factory=dict)   # mention -> instrument_id


class SentimentResult(CitedModel):
    sentiment: float = Field(default=0.0, ge=-1.0, le=1.0)
    label: Literal["positive", "negative", "neutral"] = "neutral"
    rationale: str = ""
    sources_considered: int = 0
    manipulation_flags: list[str] = Field(default_factory=list)


class JudgeResult(CitedModel):
    action: Literal["BUY", "SELL", "HOLD", "ROTATE", "NO_TRADE"] = "NO_TRADE"
    thesis: str = ""
    unknowns: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)

    def cited_ids(self) -> set[str]:
        ids = set(self.citations)
        for c in self.claims:
            ids |= c.cited_ids()
        return ids


_MODELS: dict[LLMTask, type[CitedModel]] = {
    LLMTask.EVENT_EXTRACTION: ExtractionResult,
    LLMTask.RESEARCH_SYNTHESIS: JudgeResult,
    LLMTask.ENTITY_RESOLUTION: EntityResolutionResult,
    LLMTask.DOCUMENT_SUMMARY: SummaryResult,
    LLMTask.SENTIMENT: SentimentResult,
    LLMTask.BULL_CASE: ThesisResult,
    LLMTask.BEAR_CASE: ThesisResult,
    LLMTask.CHAT_ANSWER: ChatAnswer,
}


def response_model_for(task: LLMTask) -> type[CitedModel]:
    return _MODELS[task]
