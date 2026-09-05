"""Point-in-time universe membership — the survivorship-bias guard.

Backtests must use the universe as it existed at the decision date, including names
later delisted or removed from an index. A membership is a half-open window
[start_date, end_date); end_date=None means still a member.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Membership(BaseModel):
    instrument_id: str
    index_name: str
    start_date: date
    end_date: date | None = None      # None = still a member

    def active_on(self, d: date) -> bool:
        return self.start_date <= d and (self.end_date is None or d < self.end_date)


class UniverseHistory:
    def __init__(self, memberships: list[Membership]) -> None:
        self._memberships = list(memberships)

    def members_asof(self, index_name: str, d: date) -> set[str]:
        return {
            m.instrument_id for m in self._memberships
            if m.index_name == index_name and m.active_on(d)
        }

    def is_member(self, index_name: str, instrument_id: str, d: date) -> bool:
        return any(
            m.index_name == index_name and m.instrument_id == instrument_id and m.active_on(d)
            for m in self._memberships
        )

    def indices(self) -> set[str]:
        return {m.index_name for m in self._memberships}
