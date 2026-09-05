"""EOD load orchestration: idempotent ingest + freshness reporting.

Re-running the same feed produces no changes (idempotent). Corrections append a
new version rather than overwriting. Freshness compares the latest session against
an `as_of` date so stale feeds are visible, not silent.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from .adapters import SourceAdapter
from .repository import BarRepository


class LoadReport(BaseModel):
    source: str
    added: int = 0
    skipped: int = 0
    corrected: int = 0
    total_seen: int = 0
    last_session_date: date | None = None
    as_of: date | None = None
    max_age_days: int = 4
    is_stale: bool = False

    @property
    def changed(self) -> int:
        return self.added + self.corrected


def load_eod(
    adapter: SourceAdapter,
    repo: BarRepository,
    *,
    as_of: date | None = None,
    max_age_days: int = 4,
) -> LoadReport:
    counts = {"added": 0, "skipped": 0, "corrected": 0}
    last_session: date | None = None
    total = 0

    for bar in adapter.bars():
        total += 1
        counts[repo.upsert(bar)] += 1
        if last_session is None or bar.session_date > last_session:
            last_session = bar.session_date

    is_stale = False
    if as_of is not None and last_session is not None:
        is_stale = (as_of - last_session).days > max_age_days

    return LoadReport(
        source=getattr(adapter, "name", "unknown"),
        added=counts["added"], skipped=counts["skipped"], corrected=counts["corrected"],
        total_seen=total, last_session_date=last_session,
        as_of=as_of, max_age_days=max_age_days, is_stale=is_stale,
    )
