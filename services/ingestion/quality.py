"""Data-quality suite.

Detects duplicates, missing sessions, stale feeds, price outliers, and non-positive
prices. Findings are reported and ERROR-level rows are *quarantined* (excluded)
rather than silently corrected — signals must never change because of an unflagged
data mutation.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from .calendar import TradingCalendar
from .models import Bar


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class QualityIssue(BaseModel):
    instrument_id: str
    code: str
    severity: Severity
    detail: str = ""
    session_date: date | None = None


class DataQualityReport(BaseModel):
    issues: list[QualityIssue] = Field(default_factory=list)

    def errors(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    def warnings(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity is Severity.WARN]

    @property
    def ok(self) -> bool:
        return not self.errors()

    def quarantine_keys(self) -> set[tuple[str, date]]:
        return {(i.instrument_id, i.session_date) for i in self.errors() if i.session_date}


def run_quality(
    bars: list[Bar],
    *,
    calendar: TradingCalendar | None = None,
    as_of: date | None = None,
    max_stale_days: int = 4,
    outlier_return: float = 0.5,
) -> DataQualityReport:
    issues: list[QualityIssue] = []
    by_instrument: dict[str, list[Bar]] = {}
    for b in bars:
        by_instrument.setdefault(b.instrument_id, []).append(b)

    for iid, group in by_instrument.items():
        group = sorted(group, key=lambda x: x.session_date)

        # duplicates (same content key seen twice)
        seen: set[tuple] = set()
        for b in group:
            if b.value_key in seen:
                issues.append(QualityIssue(instrument_id=iid, code="DUPLICATE",
                    severity=Severity.ERROR, session_date=b.session_date,
                    detail="duplicate bar for session"))
            seen.add(b.value_key)

        # non-positive prices
        for b in group:
            if min(b.open, b.high, b.low, b.close) <= 0:
                issues.append(QualityIssue(instrument_id=iid, code="NONPOSITIVE_PRICE",
                    severity=Severity.ERROR, session_date=b.session_date))

        # outliers (unexplained large moves — often an unadjusted corporate action)
        for prev, cur in zip(group, group[1:]):
            if float(prev.close) > 0:
                ret = abs(float(cur.close) / float(prev.close) - 1.0)
                if ret > outlier_return:
                    issues.append(QualityIssue(instrument_id=iid, code="OUTLIER",
                        severity=Severity.WARN, session_date=cur.session_date,
                        detail=f"{ret:.0%} move vs prior close"))

        # missing sessions within the instrument's own range
        if calendar is not None and group:
            present = {b.session_date for b in group}
            for d in calendar.sessions_between(group[0].session_date, group[-1].session_date):
                if d not in present:
                    issues.append(QualityIssue(instrument_id=iid, code="MISSING_SESSION",
                        severity=Severity.WARN, session_date=d))

        # stale feed
        if as_of is not None and group:
            gap = (as_of - group[-1].session_date).days
            if gap > max_stale_days:
                issues.append(QualityIssue(instrument_id=iid, code="STALE",
                    severity=Severity.WARN, session_date=group[-1].session_date,
                    detail=f"{gap} days since last session"))

    return DataQualityReport(issues=issues)
