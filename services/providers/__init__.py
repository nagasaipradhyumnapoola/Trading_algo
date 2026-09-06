"""providers — provider-agnostic adapter interfaces + config-driven selection.

Real NSE/BSE market data, news, and filings plug in behind these Protocols without
touching the quant engine. Demo uses sample implementations of the same interfaces.
"""

from .factory import (
    get_filings_provider,
    get_market_data_provider,
    get_news_provider,
    load_market_data,
    persist_items,
    provider_report,
    register_filings,
    register_market_data,
    register_news,
)
from .interfaces import (
    FilingsProvider,
    MarketDataProvider,
    NewsProvider,
    NotConfigured,
    RawItem,
)
from .sample import (
    SampleFilingsProvider,
    SampleMarketDataProvider,
    SampleNewsProvider,
)

__all__ = [
    "MarketDataProvider",
    "NewsProvider",
    "FilingsProvider",
    "RawItem",
    "NotConfigured",
    "SampleMarketDataProvider",
    "SampleNewsProvider",
    "SampleFilingsProvider",
    "get_market_data_provider",
    "get_news_provider",
    "get_filings_provider",
    "register_market_data",
    "register_news",
    "register_filings",
    "load_market_data",
    "persist_items",
    "provider_report",
]
