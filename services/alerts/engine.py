"""Alert engine: dedupe, quiet hours, and an append-only audit log."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AlertType(str, Enum):
    NEW_OPPORTUNITY = "new_opportunity"
    THESIS_INVALIDATED = "thesis_invalidated"
    TARGET_HIT = "target_hit"
    RISK_VETO = "risk_veto"
    DATA_STALE = "data_stale"
    SCORE_CHANGED = "score_changed"
    ROTATION = "rotation"


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class Alert(BaseModel):
    model_config = ConfigDict(frozen=True)

    alert_id: str = Field(default_factory=lambda: f"alert_{uuid.uuid4().hex[:12]}")
    type: AlertType
    instrument_id: str
    message: str
    severity: Severity = Severity.INFO
    dedupe_key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)


class AlertEvent(BaseModel):
    alert: Alert
    action: str                    # "delivered" | "deduped" | "quiet"
    at: datetime


class AlertEngine:
    def __init__(self, *, quiet_hours: tuple[int, int] | None = None,
                 audit_path: str | Path | None = None) -> None:
        self.quiet_hours = quiet_hours          # (start_hour, end_hour) UTC, non-critical held
        self._delivered_keys: set[str] = set()
        self.audit: list[AlertEvent] = []
        self.delivered: list[Alert] = []
        self._path = Path(audit_path) if audit_path else None

    def _is_quiet(self, when: datetime) -> bool:
        if self.quiet_hours is None:
            return False
        start, end = self.quiet_hours
        h = when.hour
        return start <= h < end if start <= end else (h >= start or h < end)

    def emit(self, alert: Alert, *, now: datetime | None = None) -> Alert | None:
        when = now or datetime.now(timezone.utc)
        if alert.dedupe_key in self._delivered_keys:
            action = "deduped"
        elif self._is_quiet(when) and alert.severity is not Severity.CRITICAL:
            action = "quiet"
        else:
            action = "delivered"
            self._delivered_keys.add(alert.dedupe_key)
            self.delivered.append(alert)

        event = AlertEvent(alert=alert, action=action, at=when)
        self.audit.append(event)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(event.model_dump_json() + "\n")
        return alert if action == "delivered" else None


# --- condition -> alert builders ---------------------------------------------

def make_new_opportunity(instrument_id: str, score: float, as_of: str) -> Alert:
    return Alert(type=AlertType.NEW_OPPORTUNITY, instrument_id=instrument_id,
                 severity=Severity.INFO, message=f"New approved opportunity (score {score:.2f})",
                 dedupe_key=f"new:{instrument_id}:{as_of}", data={"score": score})


def make_thesis_invalidated(instrument_id: str, price: float, invalidation: float) -> Alert:
    return Alert(type=AlertType.THESIS_INVALIDATED, instrument_id=instrument_id,
                 severity=Severity.CRITICAL,
                 message=f"Thesis invalidated: {price:.2f} <= stop {invalidation:.2f}",
                 dedupe_key=f"invalidated:{instrument_id}:{invalidation:.2f}",
                 data={"price": price, "invalidation": invalidation})


def make_target_hit(instrument_id: str, price: float, target: float) -> Alert:
    return Alert(type=AlertType.TARGET_HIT, instrument_id=instrument_id, severity=Severity.INFO,
                 message=f"Target reached: {price:.2f} >= {target:.2f}",
                 dedupe_key=f"target:{instrument_id}:{target:.2f}",
                 data={"price": price, "target": target})


def make_risk_veto(instrument_id: str, reason: str) -> Alert:
    return Alert(type=AlertType.RISK_VETO, instrument_id=instrument_id, severity=Severity.WARN,
                 message=f"Risk veto: {reason}", dedupe_key=f"veto:{instrument_id}:{reason}",
                 data={"reason": reason})
