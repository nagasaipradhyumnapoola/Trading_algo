"""Position sizing.

Turns an entry + invalidation into a quantity that respects per-trade risk, max
allocation, a liquidity/participation cap, a cash reserve, a sector cap, and a
drawdown throttle. Never sizes on probability alone — risk of ruin is the binding
constraint. Reports which limit bound the size.
"""

from __future__ import annotations

import math

from pydantic import BaseModel


class SizingConfig(BaseModel):
    capital: float = 100_000.0
    per_trade_risk: float = 0.005         # fraction of capital risked to the stop
    max_allocation_pct: float = 0.10      # max fraction of capital in one position
    cash_reserve_pct: float = 0.05
    max_participation: float = 0.10       # max fraction of a day's turnover
    sector_cap_pct: float = 0.35


class SizingResult(BaseModel):
    quantity: int
    allocation: float
    risk_amount: float
    throttle: float
    capped_by: str


def _throttle(drawdown: float) -> float:
    if drawdown <= -0.10:
        return 0.25
    if drawdown <= -0.05:
        return 0.5
    return 1.0


def size_position(
    entry: float, stop: float, config: SizingConfig | None = None, *,
    avg_turnover: float | None = None, current_drawdown: float = 0.0,
    sector_value: float = 0.0,
) -> SizingResult:
    cfg = config or SizingConfig()
    risk_per_share = entry - stop
    if risk_per_share <= 0 or entry <= 0:
        return SizingResult(quantity=0, allocation=0.0, risk_amount=0.0,
                            throttle=1.0, capped_by="invalid")

    throttle = _throttle(current_drawdown)
    caps: dict[str, float] = {
        "risk": (cfg.capital * cfg.per_trade_risk * throttle) / risk_per_share,
        "allocation": (cfg.capital * cfg.max_allocation_pct) / entry,
        "cash": (cfg.capital * (1 - cfg.cash_reserve_pct)) / entry,
        "sector": max(0.0, cfg.sector_cap_pct * cfg.capital - sector_value) / entry,
    }
    if avg_turnover is not None:
        caps["liquidity"] = (cfg.max_participation * avg_turnover) / entry

    capped_by = min(caps, key=caps.get)
    quantity = int(math.floor(caps[capped_by]))
    if quantity <= 0:
        return SizingResult(quantity=0, allocation=0.0, risk_amount=0.0,
                            throttle=throttle, capped_by=capped_by)

    return SizingResult(
        quantity=quantity, allocation=quantity * entry,
        risk_amount=quantity * risk_per_share, throttle=throttle, capped_by=capped_by,
    )
