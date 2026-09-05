"""Portfolio state + rotation recommender.

Holdings are user-entered (no broker link). The recommender compares hold vs
trim/exit vs rotate using expected net edge, respecting a position cap and a
rotation margin that must clear turnover cost — it never forces a trade.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PortfolioAction(str, Enum):
    HOLD = "HOLD"
    BUY = "BUY"
    REDUCE = "REDUCE"
    EXIT = "EXIT"
    ROTATE = "ROTATE"
    NO_TRADE = "NO_TRADE"


class Holding(BaseModel):
    instrument_id: str
    quantity: int
    avg_cost: float
    last_price: float
    sector: str | None = None

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price


class Portfolio(BaseModel):
    cash: float = 0.0
    holdings: list[Holding] = Field(default_factory=list)

    @property
    def invested(self) -> float:
        return sum(h.market_value for h in self.holdings)

    @property
    def nav(self) -> float:
        return self.cash + self.invested

    def sector_weights(self) -> dict[str, float]:
        nav = self.nav or 1.0
        out: dict[str, float] = {}
        for h in self.holdings:
            out[h.sector or "?"] = out.get(h.sector or "?", 0.0) + h.market_value / nav
        return out

    def holding(self, instrument_id: str) -> Holding | None:
        return next((h for h in self.holdings if h.instrument_id == instrument_id), None)


class RotationConfig(BaseModel):
    min_edge: float = 0.01
    exit_edge: float = 0.0
    rotation_margin: float = 0.01         # new edge must beat held edge by this (turnover cost)
    max_positions: int = 5
    target_weight: float = 0.10


class Move(BaseModel):
    action: PortfolioAction
    instrument_id: str
    from_instrument: str | None = None
    rupees: float = 0.0
    reason: str = ""


def recommend_rotation(
    portfolio: Portfolio,
    edges: dict[str, float],                       # instrument_id -> expected net edge
    candidates: list[tuple[str, float, bool]],     # (instrument_id, edge, risk_pass)
    config: RotationConfig | None = None,
) -> list[Move]:
    cfg = config or RotationConfig()
    held = {h.instrument_id for h in portfolio.holdings}
    moves: list[Move] = []

    # 1) exits: held names whose edge has decayed below the exit threshold
    exited: set[str] = set()
    for h in portfolio.holdings:
        e = edges.get(h.instrument_id, 0.0)
        if e < cfg.exit_edge:
            moves.append(Move(action=PortfolioAction.EXIT, instrument_id=h.instrument_id,
                              rupees=h.market_value, reason=f"edge {e:.2%} < exit"))
            exited.add(h.instrument_id)

    remaining = [h for h in portfolio.holdings if h.instrument_id not in exited]
    open_slots = cfg.max_positions - len(remaining)

    # 2) new candidates by descending edge
    for iid, edge, risk_pass in sorted(candidates, key=lambda c: c[1], reverse=True):
        if iid in held or not risk_pass or edge < cfg.min_edge:
            continue
        if open_slots > 0:
            moves.append(Move(action=PortfolioAction.BUY, instrument_id=iid,
                              rupees=min(portfolio.cash, portfolio.nav * cfg.target_weight),
                              reason=f"edge {edge:.2%}"))
            open_slots -= 1
        else:
            weakest = min(remaining, key=lambda h: edges.get(h.instrument_id, 0.0), default=None)
            if weakest and edge > edges.get(weakest.instrument_id, 0.0) + cfg.rotation_margin:
                moves.append(Move(action=PortfolioAction.ROTATE, instrument_id=iid,
                                  from_instrument=weakest.instrument_id, rupees=weakest.market_value,
                                  reason=(f"edge {edge:.2%} > held "
                                          f"{edges.get(weakest.instrument_id, 0.0):.2%} + margin")))
                remaining.remove(weakest)

    if not moves:
        moves.append(Move(action=PortfolioAction.NO_TRADE, instrument_id="-",
                          reason="no move clears the thresholds"))
    return moves
