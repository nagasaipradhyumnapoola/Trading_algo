"""Model registry with approval state and champion/challenger.

A model is SHADOW until it beats the predefined baseline on untouched data after
costs; only then can it be APPROVED and promoted to CHAMPION. Everything needed to
reproduce it (feature/label versions, data snapshot, config, metrics) is recorded.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Approval(str, Enum):
    SHADOW = "shadow"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHAMPION = "champion"


class ModelCard(BaseModel):
    model_config = ConfigDict(frozen=False)

    model_id: str = Field(default_factory=lambda: f"mdl_{uuid.uuid4().hex[:12]}")
    name: str
    version: str = "0.1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    feature_set_version: str = ""
    label_version: str = ""
    data_snapshot: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    approval: Approval = Approval.SHADOW
    notes: str = ""


def beats_baseline(candidate: dict[str, float], baseline: dict[str, float],
                   *, key: str, margin: float = 0.0) -> bool:
    """True if candidate exceeds baseline on `key` by at least `margin`."""
    if key not in candidate or key not in baseline:
        return False
    return candidate[key] >= baseline[key] + margin


class ModelRegistry:
    def __init__(self, path: str | Path | None = None) -> None:
        self._cards: dict[str, ModelCard] = {}
        self._path = Path(path) if path else None

    def register(self, card: ModelCard) -> ModelCard:
        self._cards[card.model_id] = card
        self._persist()
        return card

    def get(self, model_id: str) -> ModelCard | None:
        return self._cards.get(model_id)

    def set_approval(self, model_id: str, approval: Approval) -> ModelCard:
        card = self._cards[model_id]
        card.approval = approval
        self._persist()
        return card

    def set_champion(self, model_id: str) -> ModelCard:
        for mid, card in self._cards.items():
            if card.approval is Approval.CHAMPION and mid != model_id:
                card.approval = Approval.APPROVED         # demote previous champion
        self._cards[model_id].approval = Approval.CHAMPION
        self._persist()
        return self._cards[model_id]

    def champion(self) -> ModelCard | None:
        return next((c for c in self._cards.values() if c.approval is Approval.CHAMPION), None)

    def by_state(self, approval: Approval) -> list[ModelCard]:
        return [c for c in self._cards.values() if c.approval is approval]

    def all(self) -> list[ModelCard]:
        return list(self._cards.values())

    def _persist(self) -> None:
        if self._path is not None:
            with self._path.open("w", encoding="utf-8") as fh:
                for card in self._cards.values():
                    fh.write(card.model_dump_json() + "\n")
