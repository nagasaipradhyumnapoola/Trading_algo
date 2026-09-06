"""Observability: metrics, health/degraded mode, rate limiting, drift."""

import numpy as np

from services.monitoring import (
    HealthInputs,
    HealthStatus,
    MetricsRegistry,
    RateLimiter,
    detect_drift,
    evaluate_health,
    population_stability_index,
)


def test_metrics_derived_rates():
    m = MetricsRegistry()
    m.incr("llm_runs", 10); m.incr("llm_failures", 2)
    m.incr("candidates", 100); m.incr("risk_vetoes", 25); m.incr("recommendations", 10)
    snap = m.snapshot()
    assert snap["derived"]["llm_failure_rate"] == 0.2
    assert snap["derived"]["risk_veto_rate"] == 0.25
    assert snap["derived"]["recommendation_coverage"] == 0.1


def test_health_ok():
    assert evaluate_health(HealthInputs()).status is HealthStatus.OK


def test_stale_feed_suppresses_recommendations():
    r = evaluate_health(HealthInputs(feed_age_days=10))
    assert r.status is HealthStatus.DEGRADED and r.suppress_recommendations
    assert "stale_feed" in r.degraded_reasons


def test_llm_outage_keeps_deterministic_recs():
    r = evaluate_health(HealthInputs(llm_available=False))
    assert r.status is HealthStatus.DEGRADED
    assert r.suppress_llm_features and not r.suppress_recommendations   # quant recs still valid


def test_bad_data_suppresses_recs():
    assert evaluate_health(HealthInputs(data_quality_ok=False)).suppress_recommendations


def test_rate_limiter_window():
    rl = RateLimiter(limit=2, window_s=1.0)
    assert rl.allow("k", now=0.0) and rl.allow("k", now=0.1)
    assert not rl.allow("k", now=0.2)              # third in window blocked
    assert rl.allow("k", now=1.5)                  # next window allowed


def test_drift_detection():
    rng = np.random.RandomState(0)
    ref = rng.normal(0, 1, 2000)
    assert not detect_drift(ref, rng.normal(0, 1, 2000)).drifted        # same dist
    shifted = detect_drift(ref, rng.normal(3, 1, 2000))
    assert shifted.drifted and shifted.psi > 0.25                       # mean shift
    assert population_stability_index(ref, ref) < 0.01
