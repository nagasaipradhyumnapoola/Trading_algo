"""Versioned system templates per task.

The system role comes ONLY from here — never from source content. Bump
TEMPLATE_VERSION when a template changes; it is logged in every llm_run.
"""

from __future__ import annotations

from .contracts import LLMTask

TEMPLATE_VERSION = "tpl-0.1"

_SYSTEM: dict[LLMTask, str] = {
    LLMTask.EVENT_EXTRACTION: (
        "You extract market-relevant events from Indian equity disclosures and news. "
        "Return only structured JSON. Every claim must cite a provided source id. "
        "Do not invent facts, sources, probabilities, or price targets."
    ),
    LLMTask.ENTITY_RESOLUTION: (
        "You map company mentions to the provided instrument ids. Return only JSON."
    ),
    LLMTask.DOCUMENT_SUMMARY: (
        "You summarize a single document faithfully. Cite the source id. Return only JSON."
    ),
    LLMTask.BULL_CASE: (
        "You build the strongest evidence-grounded long case. Cite sources; list "
        "assumptions; never fabricate evidence. Return only JSON."
    ),
    LLMTask.BEAR_CASE: (
        "You build the strongest evidence-grounded bear case: priced-in risk, weak "
        "fundamentals, liquidity/governance/execution risk. Cite sources. Return only JSON."
    ),
    LLMTask.RESEARCH_SYNTHESIS: (
        "You synthesize analyst outputs into a structured view. Cite sources. "
        "Numbers (probability, expected return, risk) are NOT yours to produce. Return only JSON."
    ),
    LLMTask.CHAT_ANSWER: (
        "You answer only from the provided, timestamped evidence. If unknown, say so. "
        "Return only JSON."
    ),
}


def system_for(task: LLMTask) -> str:
    return _SYSTEM[task]
