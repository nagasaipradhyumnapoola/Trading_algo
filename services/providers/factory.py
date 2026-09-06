"""Provider registries + config-driven selection + the provider→quant bridge.

Real providers register a factory under their name; `get_*_provider(settings)` returns
the configured one. In real mode a blank/unknown provider fails fast (NotConfigured) —
never a silent fall back to sample data.
"""

from __future__ import annotations

from typing import Callable

from services.config import AppMode
from services.ingestion.document_store import RawDocumentStore, SourceDocument
from services.ingestion.instruments import InstrumentMaster
from services.ingestion.repository import InMemoryBarRepository

from .interfaces import FilingsProvider, MarketDataProvider, NewsProvider, NotConfigured, RawItem
from .sample import SampleFilingsProvider, SampleMarketDataProvider, SampleNewsProvider

_MARKET: dict[str, Callable[[], MarketDataProvider]] = {"sample": SampleMarketDataProvider}
_NEWS: dict[str, Callable[[], NewsProvider]] = {"sample": SampleNewsProvider}
_FILINGS: dict[str, Callable[[], FilingsProvider]] = {"sample": SampleFilingsProvider}


def register_market_data(name: str, factory: Callable[[], MarketDataProvider]) -> None:
    _MARKET[name] = factory


def register_news(name: str, factory: Callable[[], NewsProvider]) -> None:
    _NEWS[name] = factory


def register_filings(name: str, factory: Callable[[], FilingsProvider]) -> None:
    _FILINGS[name] = factory


def _select(kind: str, registry: dict, settings, configured: str):
    if settings.app_mode is not AppMode.REAL:
        return registry["sample"]()
    name = configured
    if not name or name not in registry:
        raise NotConfigured(
            f"{kind} provider '{name or '(blank)'}' is not configured/registered. "
            f"Set it in .env and register an adapter, or run APP_MODE=demo. "
            f"Registered: {sorted(registry)}"
        )
    return registry[name]()


def get_market_data_provider(settings) -> MarketDataProvider:
    return _select("market-data", _MARKET, settings, settings.market_data_provider)


def get_news_provider(settings) -> NewsProvider:
    return _select("news", _NEWS, settings, settings.news_provider)


def get_filings_provider(settings) -> FilingsProvider:
    return _select("filings", _FILINGS, settings, settings.exchange_filings_provider)


def provider_report(settings) -> dict[str, object]:
    def row(configured: str, registry: dict) -> dict:
        name = "sample" if settings.app_mode is not AppMode.REAL else (configured or "")
        return {"configured": name or "MISSING", "available": name in registry}
    return {
        "app_mode": settings.app_mode.value,
        "market_data": row(settings.market_data_provider, _MARKET),
        "news": row(settings.news_provider, _NEWS),
        "filings": row(settings.exchange_filings_provider, _FILINGS),
    }


def load_market_data(provider: MarketDataProvider) -> tuple[InMemoryBarRepository, InstrumentMaster]:
    """Bridge: provider -> repository + instrument master consumed by the quant engine."""
    repo = InMemoryBarRepository()
    instruments = provider.instruments()
    for inst in instruments:
        for bar in provider.eod_bars(inst.instrument_id):
            repo.upsert(bar)
    return repo, InstrumentMaster(instruments)


def persist_items(store: RawDocumentStore, items: list[RawItem]) -> list[SourceDocument]:
    """Store fetched news/filings items (content-addressed, de-duplicated)."""
    return [store.store(content=it.content, source=it.source, url=it.url, title=it.title,
                        tier=it.tier, published_at=it.published_at, rights=it.rights)
            for it in items]
