"""Independent risk engine vetoes."""

from services.risk_portfolio import RiskInputs, RiskVerdict, assess_risk


def _ok(**kw):
    base = dict(instrument_id="A", avg_turnover=5_000_000, spread_bps=20,
                realized_vol=0.02, manipulation_score=0.1, event_uncertainty=0.2,
                data_quality_ok=True, signal_age_days=1, signal_expiry_days=5)
    base.update(kw)
    return RiskInputs(**base)


def test_clean_passes():
    assert assess_risk(_ok()).verdict is RiskVerdict.PASS


def test_illiquid_vetoes():
    r = assess_risk(_ok(avg_turnover=100))
    assert r.verdict is RiskVerdict.VETO
    assert any(f.code == "LIQUIDITY" for f in r.flags)


def test_manipulation_vetoes():
    assert assess_risk(_ok(manipulation_score=0.9)).verdict is RiskVerdict.VETO


def test_stale_signal_vetoes():
    assert assess_risk(_ok(signal_age_days=9)).verdict is RiskVerdict.VETO


def test_data_quality_vetoes():
    assert assess_risk(_ok(data_quality_ok=False)).verdict is RiskVerdict.VETO


def test_high_vol_is_review_not_veto():
    r = assess_risk(_ok(realized_vol=0.12))
    assert r.verdict is RiskVerdict.REVIEW
    assert any(f.code == "VOLATILITY" for f in r.flags)
