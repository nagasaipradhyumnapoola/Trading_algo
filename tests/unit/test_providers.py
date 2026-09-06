"""Provider-agnostic interfaces: selection, fail-fast, and the provider->quant bridge."""

from datetime import timedelta

import pytest

from services.config import load_settings
from services.ingestion import RawDocumentStore
from services.ingestion.sample import SAMPLE_START
from services.providers import (
    MarketDataProvider,
    NotConfigured,
    SampleMarketDataProvider,
    get_market_data_provider,
    get_news_provider,
    load_market_data,
    persist_items,
    provider_report,
    register_market_data,
)
from services.quant import ScanConfig, scan

_NO_ENV = {"_env_file": None}
_REAL = dict(app_mode="real", database_url="postgresql://u:p@d/x",
             market_data_provider="acme", market_data_base_url="https://a",
             market_data_api_key="k", freellm_api_base="https://l", freellm_api_key="k2",
             **_NO_ENV)


def test_sample_market_data_conforms_to_interface():
    p = SampleMarketDataProvider(n=60)
    assert isinstance(p, MarketDataProvider)                 # runtime Protocol check
    assert p.instruments() and p.eod_bars("MOMO")
    assert p.corporate_actions("MOMO") == []


def test_demo_selects_sample():
    s = load_settings(**_NO_ENV)
    assert get_market_data_provider(s).name == "sample"
    assert get_news_provider(s).name == "sample"


def test_real_mode_unknown_provider_fails_fast():
    s = load_settings(**_REAL)
    with pytest.raises(NotConfigured) as exc:
        get_market_data_provider(s)                          # 'acme' not registered
    assert "market-data" in str(exc.value)


def test_registered_real_provider_resolves():
    register_market_data("acme", lambda: SampleMarketDataProvider(n=60))
    s = load_settings(**_REAL)
    assert get_market_data_provider(s).name == "sample"      # our stub factory


def test_bridge_feeds_quant_engine_unchanged():
    repo, master = load_market_data(SampleMarketDataProvider(n=160))
    cands = scan(repo, master, SAMPLE_START + timedelta(days=119), ScanConfig(top_k=5))
    assert isinstance(cands, list) and len(cands) >= 1       # quant runs on provider data


def test_news_items_persist_and_dedup(tmp_path):
    store = RawDocumentStore(tmp_path / "docs")
    items = get_news_provider(load_settings(**_NO_ENV)).search("MOMO order")
    docs = persist_items(store, items)
    assert docs and len(store) == len(docs)
    again = persist_items(store, items)                      # same content -> dedup
    assert again[0].content_hash == docs[0].content_hash and len(store) == len(docs)


def test_provider_report_demo():
    rep = provider_report(load_settings(**_NO_ENV))
    assert rep["market_data"]["configured"] == "sample" and rep["market_data"]["available"]
