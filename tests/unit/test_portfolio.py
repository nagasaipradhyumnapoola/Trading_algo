"""Portfolio NAV + rotation recommendations."""

from services.risk_portfolio import (
    Holding,
    Portfolio,
    PortfolioAction,
    RotationConfig,
    recommend_rotation,
)


def _pf(cash=10_000, holdings=None):
    return Portfolio(cash=cash, holdings=holdings or [])


def test_nav_and_sector_weights():
    pf = _pf(cash=5_000, holdings=[
        Holding(instrument_id="A", quantity=10, avg_cost=100, last_price=110, sector="IT"),
        Holding(instrument_id="B", quantity=5, avg_cost=200, last_price=200, sector="Energy"),
    ])
    assert pf.nav == 5_000 + 1_100 + 1_000
    weights = pf.sector_weights()
    assert round(sum(weights.values()), 6) == round(pf.invested / pf.nav, 6)


def test_buy_into_open_slot():
    moves = recommend_rotation(_pf(cash=10_000), edges={},
                               candidates=[("X", 0.05, True)])
    assert moves[0].action is PortfolioAction.BUY and moves[0].instrument_id == "X"


def test_risk_vetoed_candidate_is_skipped():
    moves = recommend_rotation(_pf(cash=10_000), edges={},
                               candidates=[("X", 0.05, False)])          # risk_pass False
    assert moves[0].action is PortfolioAction.NO_TRADE


def test_weak_holding_exits():
    pf = _pf(holdings=[Holding(instrument_id="OLD", quantity=10, avg_cost=100, last_price=90)])
    moves = recommend_rotation(pf, edges={"OLD": -0.02}, candidates=[])
    assert any(m.action is PortfolioAction.EXIT and m.instrument_id == "OLD" for m in moves)


def test_rotation_when_full():
    pf = _pf(cash=0, holdings=[
        Holding(instrument_id="H1", quantity=10, avg_cost=100, last_price=100),
    ])
    cfg = RotationConfig(max_positions=1, rotation_margin=0.01)
    moves = recommend_rotation(pf, edges={"H1": 0.01}, candidates=[("NEW", 0.08, True)], config=cfg)
    rot = [m for m in moves if m.action is PortfolioAction.ROTATE]
    assert rot and rot[0].instrument_id == "NEW" and rot[0].from_instrument == "H1"
