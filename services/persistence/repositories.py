"""Append-only repositories.

Deliberately expose only add / get / list / count — there is NO update or delete.
This enforces the immutable logbook: a recommendation, decision, or fill is never
rewritten after the fact.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Record

T = TypeVar("T", bound=Record)


class AppendOnlyRepository(Generic[T]):
    def __init__(self, session: Session, model: type[T]) -> None:
        self.session = session
        self.model = model

    def add(self, **fields) -> T:
        obj = self.model(**fields)
        self.session.add(obj)
        self.session.flush()               # assign id without committing
        return obj

    def get(self, record_id: str) -> T | None:
        return self.session.get(self.model, record_id)

    def list(self, *, limit: int = 100, **filters) -> list[T]:
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        stmt = stmt.order_by(self.model.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def count(self, **filters) -> int:
        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        return int(self.session.scalar(stmt) or 0)


def repo(session: Session, model: type[T]) -> AppendOnlyRepository[T]:
    return AppendOnlyRepository(session, model)
