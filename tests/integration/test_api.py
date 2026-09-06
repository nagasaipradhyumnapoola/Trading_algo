"""API endpoint tests over the Phase 6 terminal service (sample data)."""

from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["data"] == "sample" and "as_of" in r


def test_recommendations_are_complete_and_calibrated():
    r = client.get("/recommendations").json()
    assert r["action"] in ("BUY", "NO_TRADE")
    for rec in r["recommendations"]:
        assert 0.0 <= rec["calibrated_probability"] <= 1.0
        assert rec["risk_verdict"] in ("PASS", "REVIEW")     # a VETO can never be a recommendation
        assert rec["complete"] is True
        assert rec["target"] and rec["invalidation"] and rec["quantity"] > 0


def test_no_execution_endpoints_exist():
    paths = set(app.openapi()["paths"])
    for forbidden in ("/order", "/place_order", "/execute", "/trade", "/withdraw"):
        assert forbidden not in paths


def test_portfolio_and_performance():
    pf = client.get("/portfolio").json()
    assert pf["nav"] > 0 and "moves" in pf
    perf = client.get("/performance").json()
    assert perf["n"] >= 0 and "max_drawdown" in perf


def test_bars_and_evidence():
    bars = client.get("/bars/MOMO").json()["bars"]
    assert bars and {"open", "high", "low", "close"} <= set(bars[0])
    ev = client.get("/evidence/MOMO").json()["evidence"]
    assert ev and ev[0]["id"].startswith("nse_")


def test_chat_is_grounded():
    r = client.post("/chat", json={"question": "what is the catalyst?", "instrument_id": "MOMO"}).json()
    assert r["grounded"] is True and r["citations"]


def test_chat_refuses_without_evidence():
    r = client.post("/chat", json={"question": "unrelated", "instrument_id": "NOPE"}).json()
    assert r["grounded"] is False
