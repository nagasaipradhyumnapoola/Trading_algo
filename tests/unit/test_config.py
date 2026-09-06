"""Configuration contract + demo/real boundary."""

import pytest

from services.config import AppMode, ConfigError, load_settings

# Isolate from any local .env so tests are deterministic.
_NO_ENV = {"_env_file": None}
_REAL_OK = dict(
    app_mode="real", database_url="postgresql+psycopg://u:p@db:5432/x",
    market_data_provider="acme", market_data_base_url="https://api.acme",
    market_data_api_key="k", freellm_api_base="https://llm", freellm_api_key="k2",
    **_NO_ENV,
)


def test_default_mode_is_demo():
    s = load_settings(**_NO_ENV)
    assert s.app_mode is AppMode.DEMO and s.data_mode == "DEMO" and not s.is_real


def test_real_mode_missing_config_fails_fast():
    with pytest.raises(ConfigError) as exc:
        load_settings(app_mode="real", **_NO_ENV)
    assert "DATABASE_URL" in str(exc.value) and "FREELLM_API_KEY" in str(exc.value)


def test_real_mode_with_required_config_ok():
    s = load_settings(**_REAL_OK)
    assert s.is_real and s.data_mode == "REAL" and s.missing_real_config() == []


def test_broker_write_is_refused():
    with pytest.raises(ConfigError):
        load_settings(broker_write_enabled=True, **_NO_ENV)


def test_startup_report_hides_secrets():
    s = load_settings(**_REAL_OK)
    report = s.startup_report()
    assert report["app_mode"] == "real"
    assert report["config"]["FREELLM_API_KEY"] == "SET"       # presence, not value
    assert report["config"]["NEWS_PROVIDER"] == "MISSING"
    flat = str(report)
    assert "k2" not in flat and "postgresql" not in flat       # no secret values leak
