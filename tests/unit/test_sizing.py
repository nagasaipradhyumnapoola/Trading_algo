"""Position sizing constraints."""

from services.risk_portfolio import SizingConfig, size_position


def test_risk_based_quantity():
    cfg = SizingConfig(capital=100_000, per_trade_risk=0.005, max_allocation_pct=0.20)
    r = size_position(100, 95, cfg)                 # risk/share 5, budget 500 -> 100 shares
    assert r.quantity == 100
    assert r.risk_amount == 500.0
    assert r.capped_by == "risk"


def test_allocation_cap_binds():
    cfg = SizingConfig(capital=100_000, per_trade_risk=0.05, max_allocation_pct=0.10)
    r = size_position(100, 95, cfg)                 # risk allows 1000 sh, alloc cap 100 sh
    assert r.quantity == 100 and r.capped_by == "allocation"


def test_liquidity_cap_binds():
    cfg = SizingConfig(capital=100_000, per_trade_risk=0.05, max_participation=0.10)
    r = size_position(100, 95, cfg, avg_turnover=50_000)   # 10% of 50k / 100 = 50 sh
    assert r.quantity == 50 and r.capped_by == "liquidity"


def test_drawdown_throttles_size():
    cfg = SizingConfig(capital=100_000, per_trade_risk=0.005, max_allocation_pct=0.50)
    full = size_position(100, 95, cfg, current_drawdown=0.0).quantity
    throttled = size_position(100, 95, cfg, current_drawdown=-0.12).quantity
    assert throttled < full and throttled == full // 4


def test_invalid_stop_sizes_zero():
    assert size_position(100, 105, SizingConfig()).quantity == 0   # stop above entry
