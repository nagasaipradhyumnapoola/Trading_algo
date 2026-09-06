"""Grounded chat — answers only from stored, timestamped evidence.

Runs through the LLMGateway (CHAT_ANSWER task): the answer is citation-validated
against the evidence provided, and if the LLM is unavailable or the answer is not
grounded, chat refuses rather than inventing. It explains data and workflow; it
cannot place a trade or bypass a risk gate.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .llm_gateway import LLMGateway, LLMTask


class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[str] = Field(default_factory=list)
    run_id: str | None = None


_REFUSAL = ("I can only answer from stored, timestamped evidence, and none is "
            "available or grounded for that question.")


class GroundedChat:
    def __init__(self, gateway: LLMGateway) -> None:
        self.gateway = gateway

    async def answer(self, question: str, evidence: list[dict]) -> ChatResponse:
        if not evidence:
            return ChatResponse(answer=_REFUSAL, grounded=False)

        result = await self.gateway.request(
            agent="chat", task=LLMTask.CHAT_ANSWER,
            payload={"instruction": question, "sources": evidence},
        )
        if not result.ok or not result.data:
            return ChatResponse(answer=_REFUSAL, grounded=False,
                                run_id=result.run.run_id if result.run else None)

        return ChatResponse(
            answer=result.data.get("answer", ""), grounded=True,
            citations=result.data.get("citations", []),
            run_id=result.run.run_id if result.run else None,
        )
