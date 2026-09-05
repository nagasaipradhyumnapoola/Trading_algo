"""Corporate actions and point-in-time price adjustment.

Back-adjustment: the latest prices are kept as-is and history is scaled by the
cumulative factor of every action with an ex-date after the bar. Splits and bonus
issues are price-only; dividends need the close on the session before the ex-date.
Volume is scaled inversely so notional stays consistent.

Adjusted bars carry `adjusted=True` and never overwrite the raw series — both
coexist in the repository, keyed by the `adjusted` flag.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict

from .models import Bar


class CorporateActionType(str, Enum):
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    DIVIDEND = "DIVIDEND"


class CorporateAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: str
    ex_date: date
    type: CorporateActionType
    a: float = 0.0            # SPLIT: old shares | BONUS: new shares (a-for-b)
    b: float = 0.0            # SPLIT: new shares | BONUS: held shares
    amount: float = 0.0       # DIVIDEND: cash per share
    source: str | None = None

    @classmethod
    def split(cls, instrument_id: str, ex_date: date, old: float, new: float, **kw) -> "CorporateAction":
        return cls(instrument_id=instrument_id, ex_date=ex_date,
                   type=CorporateActionType.SPLIT, a=old, b=new, **kw)

    @classmethod
    def bonus(cls, instrument_id: str, ex_date: date, new: float, held: float, **kw) -> "CorporateAction":
        return cls(instrument_id=instrument_id, ex_date=ex_date,
                   type=CorporateActionType.BONUS, a=new, b=held, **kw)

    @classmethod
    def dividend(cls, instrument_id: str, ex_date: date, amount: float, **kw) -> "CorporateAction":
        return cls(instrument_id=instrument_id, ex_date=ex_date,
                   type=CorporateActionType.DIVIDEND, amount=amount, **kw)

    def price_factor(self, close_ref: float | None = None) -> float:
        """Multiplier applied to prices *before* the ex-date."""
        if self.type is CorporateActionType.SPLIT:
            return self.a / self.b                      # 1-for-2 split -> 0.5
        if self.type is CorporateActionType.BONUS:
            return self.b / (self.a + self.b)           # a new per b held
        # DIVIDEND
        if not close_ref:
            return 1.0
        return max(0.0, (close_ref - self.amount) / close_ref)


def _close_ref_for(bars: list[Bar], ex_date: date) -> float | None:
    prior = [b for b in bars if b.session_date < ex_date]
    return float(prior[-1].close) if prior else None


def adjust_bars(bars: list[Bar], actions: list[CorporateAction]) -> list[Bar]:
    """Return a back-adjusted copy of an ascending, single-instrument bar series."""
    if not bars:
        return []
    ordered = sorted(bars, key=lambda x: x.session_date)
    factors: list[tuple[date, float]] = [
        (act.ex_date, act.price_factor(_close_ref_for(ordered, act.ex_date)))
        for act in sorted(actions, key=lambda x: x.ex_date)
    ]

    out: list[Bar] = []
    for bar in ordered:
        cum = 1.0
        for ex_date, pf in factors:
            if bar.session_date < ex_date:
                cum *= pf
        cf = Decimal(str(cum))
        out.append(bar.model_copy(update={
            "open": bar.open * cf, "high": bar.high * cf,
            "low": bar.low * cf, "close": bar.close * cf,
            "volume": int(round(bar.volume / cum)) if cum else bar.volume,
            "turnover": bar.turnover, "adjusted": True, "correction_version": 0,
        }))
    return out
