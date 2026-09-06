"""Immutable daily logbook: record, read a day, reconstruct a recommendation."""

from datetime import date, datetime, timezone

from services.persistence import LogbookService, init_db, make_engine

AS_OF = date(2026, 5, 10)


def _logbook():
    engine = make_engine("sqlite://")
    init_db(engine)
    return LogbookService(engine)


def _seed(lb):
    rec_id = lb.record_recommendation(
        as_of=AS_OF, instrument_id="MOMO", action="BUY", target=184.89,
        invalidation=169.19, quantity=57, allocation=9942, calibrated_probability=0.806,
        risk_verdict="PASS", model_version="logistic-0.1", horizon_kind="swing")
    lb.record_risk_veto(instrument_id="ILLQ", as_of=AS_OF, verdict="VETO",
                        flags={"codes": ["LIQUIDITY"]})
    lb.record_llm_run(agent="news", task="event_extraction", state="validated",
                      data={"rec_id": rec_id})
    lb.record_evaluation_outcome(recommendation_id=rec_id, instrument_id="MOMO",
                                 success=True, realized_net=0.031, outcome="TARGET",
                                 measured_at=datetime.now(timezone.utc))
    lb.record_paper_fill(instrument_id="MOMO", side="BUY", quantity=57, price=174.4,
                         cost=12.5, session_date=AS_OF, kind="ENTRY")
    lb.record_daily_plan(plan_date=AS_OF, summary="1 BUY, 1 VETO",
                         changes=[{"instrument_id": "CHOP", "action": "EXIT", "rupees": 4000,
                                   "reason": "edge decayed"}])
    lb.record_portfolio_snapshot(as_of=AS_OF, nav=101986, cash=60000, invested=41986,
                                 holdings=[{"instrument_id": "MOMO", "quantity": 50,
                                            "avg_cost": 150, "last_price": 174.4, "sector": "X"}])
    return rec_id


def test_day_reconstructs_everything():
    lb = _logbook()
    _seed(lb)
    day = lb.day(AS_OF)
    assert len(day["recommendations"]) == 1 and day["recommendations"][0]["instrument_id"] == "MOMO"
    assert len(day["risk_vetoes"]) == 1 and day["risk_vetoes"][0]["verdict"] == "VETO"
    assert len(day["paper_fills"]) == 1
    assert day["plans"][0]["changes"][0]["action"] == "EXIT"


def test_reconstruct_recommendation_links():
    lb = _logbook()
    rec_id = _seed(lb)
    bundle = lb.reconstruct_recommendation(rec_id)
    assert bundle["reconstructable"] is True
    assert bundle["evaluation_outcomes"][0]["success"] is True
    assert bundle["llm_runs"][0]["data"]["rec_id"] == rec_id


def test_reconstruct_missing_is_explicit():
    lb = _logbook()
    assert "error" in lb.reconstruct_recommendation("nope")
