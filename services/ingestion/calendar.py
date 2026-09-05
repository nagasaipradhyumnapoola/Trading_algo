"""Trading calendar.

Phase 2 minimal: a calendar is an explicit set of trading sessions. It can be
derived from observed bars (a session is any date the market traded) or supplied
from a licensed holiday calendar later. Used for missing-bar detection and for
resolving "next/previous session".
"""

from __future__ import annotations

from datetime import date
from typing import Iterable

from .models import Bar


class TradingCalendar:
    def __init__(self, sessions: Iterable[date]) -> None:
        self._sessions = sorted(set(sessions))
        self._set = set(self._sessions)

    @classmethod
    def from_bars(cls, bars: Iterable[Bar]) -> "TradingCalendar":
        return cls(b.session_date for b in bars)

    def is_session(self, d: date) -> bool:
        return d in self._set

    def sessions_between(self, start: date, end: date) -> list[date]:
        return [d for d in self._sessions if start <= d <= end]

    def next_session(self, d: date) -> date | None:
        return next((s for s in self._sessions if s > d), None)

    def prev_session(self, d: date) -> date | None:
        return next((s for s in reversed(self._sessions) if s < d), None)

    @property
    def sessions(self) -> list[date]:
        return list(self._sessions)

    def __len__(self) -> int:
        return len(self._sessions)
