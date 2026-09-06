"""API endpoint tests over the Phase 6 terminal service (sample data)."""

from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health").json()
    assert r["status"] in ("OK", "DEGRADED") and r["data"] == "sample" and "as_of" in r


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


def test_health_reports_degraded_fields():
    h = client.get("/health").json()
    assert h["status"] in ("OK", "DEGRADED")
    assert "suppress_recommendations" in h and "llm_available" in h


def test_metrics_expose_derived_rates():
    d = client.get("/metrics").json()["derived"]
    assert {"llm_failure_rate", "risk_veto_rate", "recommendation_coverage"} <= set(d)


def test_audit_bundle_is_reconstructable():
    a = client.get("/audit/MOMO").json()
    assert a["reconstructable"] is True
    assert a["recommendation"]["instrument_id"] == "MOMO" and a["evidence"]


def test_feedback_records_and_rejects_bad_label():
    ok = client.post("/feedback", json={"instrument_id": "MOMO", "label": "useful"})
    assert ok.status_code == 200 and ok.json()["recorded"] is True
    bad = client.post("/feedback", json={"instrument_id": "MOMO", "label": "bogus"})
    assert bad.status_code == 422


def test_data_mode_indicator_present():
    r = client.get("/health")
    assert r.headers["X-Data-Mode"] == "DEMO"          # header on every response
    assert r.json()["data_mode"] == "DEMO"             # and in the body
    assert client.get("/recommendations").json()["data_mode"] == "DEMO"


def test_config_report_is_presence_only():
    rep = client.get("/config/report").json()
    assert rep["app_mode"] == "demo" and "config" in rep
    assert rep["broker_write_enabled"] is False
    assert set(rep["config"].values()) <= {"SET", "MISSING"}   # never raw values


def test_logbook_day_is_populated():
    lb = client.get("/logbook").json()
    assert lb["data_mode"] == "DEMO"
    assert lb["recommendations"] and lb["plans"]               # the day was logged
    assert lb["plans"][0]["plan_date"] == lb["as_of"]


def test_logbook_reconstructs_a_recommendation():
    recs = client.get("/recommendations").json()["recommendations"]
    rid = recs[0]["logbook_id"]
    bundle = client.get(f"/logbook/recommendation/{rid}").json()
    assert bundle["reconstructable"] is True
    assert bundle["recommendation"]["instrument_id"] == recs[0]["instrument_id"]


def test_user_execution_is_recorded():
    r = client.post("/logbook/execution",
                    json={"instrument_id": "MOMO", "side": "BUY", "quantity": 10, "price": 174.4})
    assert r.status_code == 200 and r.json()["recorded"] is True
