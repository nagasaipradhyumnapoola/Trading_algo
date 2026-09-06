"""Typed settings + demo/real boundary.

`APP_MODE=demo` (default) permits the synthetic universe and mock LLM.
`APP_MODE=real` requires real data + LLM configuration and fails fast without it —
it must never silently fall back to sample data, synthetic evidence, or mock LLM.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppMode(str, Enum):
    DEMO = "demo"
    REAL = "real"


class ConfigError(RuntimeError):
    """Raised when required configuration for the selected APP_MODE is missing/unsafe."""


# Fields that must be present and non-empty when APP_MODE=real.
_REQUIRED_IN_REAL = [
    "database_url",
    "market_data_provider", "market_data_base_url", "market_data_api_key",
    "freellm_api_base", "freellm_api_key",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # --- App ---
    app_mode: AppMode = AppMode.DEMO
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: str = "info"

    # --- Datastores ---
    database_url: str = ""
    redis_url: str = ""
    object_store_endpoint: str = ""
    object_store_bucket: str = ""
    object_store_access_key: str = ""
    object_store_secret_key: str = ""

    # --- Market data ---
    market_data_provider: str = ""
    market_data_base_url: str = ""
    market_data_api_key: str = ""
    market_data_ws_url: str = ""
    market_data_symbol_format: str = ""

    # --- Research sources ---
    news_provider: str = ""
    news_api_key: str = ""
    web_search_provider: str = ""
    web_search_api_key: str = ""
    exchange_filings_provider: str = ""
    exchange_filings_api_key: str = ""

    # --- FreeLLMAPI ---
    freellm_api_base: str = ""
    freellm_api_key: str = ""
    freellm_model_fast: str = ""
    freellm_model_reasoning: str = ""
    freellm_model_judge: str = ""

    # --- Alerts ---
    alerts_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    email_smtp_url: str = ""
    email_from: str = ""
    email_to: str = ""

    # --- Risk / sizing policy ---
    default_capital: float | None = None
    max_position_pct: float | None = None
    max_portfolio_risk_pct: float | None = None
    max_sector_pct: float | None = None
    max_daily_loss_pct: float | None = None
    min_avg_daily_turnover: float | None = None
    max_spread_bps: float | None = None

    # --- Safety (never enable) ---
    broker_write_enabled: bool = False

    # -- validation ------------------------------------------------------------

    @model_validator(mode="after")
    def _enforce_mode(self) -> "Settings":
        if self.broker_write_enabled:
            raise ConfigError("BROKER_WRITE_ENABLED must be false — no broker-write path is permitted.")
        if self.app_mode is AppMode.REAL:
            missing = [f.upper() for f in _REQUIRED_IN_REAL if not getattr(self, f)]
            if missing:
                raise ConfigError(
                    "APP_MODE=real requires: " + ", ".join(missing)
                    + ". Set them in .env or run APP_MODE=demo."
                )
        return self

    # -- reporting -------------------------------------------------------------

    @property
    def is_real(self) -> bool:
        return self.app_mode is AppMode.REAL

    @property
    def data_mode(self) -> str:
        return "REAL" if self.is_real else "DEMO"

    def missing_real_config(self) -> list[str]:
        return [f.upper() for f in _REQUIRED_IN_REAL if not getattr(self, f)]

    def startup_report(self) -> dict[str, object]:
        """Presence-only report — never exposes secret values."""
        watched = _REQUIRED_IN_REAL + [
            "redis_url", "object_store_endpoint", "news_provider",
            "web_search_provider", "exchange_filings_provider",
        ]
        return {
            "app_mode": self.app_mode.value,
            "app_env": self.app_env,
            "broker_write_enabled": self.broker_write_enabled,
            "config": {f.upper(): ("SET" if getattr(self, f) else "MISSING") for f in watched},
        }


def load_settings(**overrides) -> Settings:
    """Build settings (optionally overriding for tests). Raises ConfigError if invalid."""
    return Settings(**overrides)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
