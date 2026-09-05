"""Discovery scoring: gates and ordering."""

from services.research_workers.discovery import (
    DiscoveryCandidate,
    DiscoverySignal,
    discovery_score,
    rank_discoveries,
)


def _sig(**kw):
    base = dict(instrument_id="A", source_tier=1, novelty=0.9, materiality=0.9,
                event_age_days=0.0, price_reacted=0.1, avg_turnover=5_000_000)
    base.update(kw)
    return DiscoverySignal(**base)


def test_strong_signal_scores_high():
    assert discovery_score(_sig()).score > 0.5


def test_illiquid_is_gated_to_zero():
    assert discovery_score(_sig(avg_turnover=100)).score == 0.0


def test_already_reacted_kills_opportunity():
    assert discovery_score(_sig(price_reacted=1.0)).score == 0.0


def test_stale_scores_below_fresh():
    fresh = discovery_score(_sig(event_age_days=0)).score
    stale = discovery_score(_sig(event_age_days=9)).score
    assert stale < fresh


def test_data_quality_gate():
    assert discovery_score(_sig(data_quality_ok=False)).score == 0.0


def test_ranking_orders_by_score():
    cands = [DiscoveryCandidate(instrument_id="A", score=0.2),
             DiscoveryCandidate(instrument_id="B", score=0.8)]
    assert [c.instrument_id for c in rank_discoveries(cands)] == ["B", "A"]
