from __future__ import annotations

from config.provider_profiles import apply_provider_profile
from config.provider_profiles import get_provider_profile
from config.settings import Settings


def test_backtest_synthetic_profile_maps_to_backtest_providers() -> None:
    profile = get_provider_profile(
        "backtest_synthetic",
    )

    assert profile.macro_provider == Settings.BACKTEST_MACRO_PROVIDER
    assert profile.market_data_provider == Settings.BACKTEST_DATA_PROVIDER
    assert profile.market_events_provider == Settings.BACKTEST_EVENTS_PROVIDER
    assert profile.news_provider == Settings.BACKTEST_NEWS_PROVIDER
    assert profile.portfolio_provider == Settings.BACKTEST_PORTFOLIO_PROVIDER
    assert profile.sentiment_provider == Settings.BACKTEST_SENTIMENT_PROVIDER


def test_apply_provider_profile_updates_settings_without_runtime_changes() -> None:
    settings = Settings()

    profiled_settings = apply_provider_profile(
        settings,
        "backtest_synthetic",
    )

    assert settings.MARKET_DATA_PROVIDER == Settings.LIVE_DATA_PROVIDER
    assert profiled_settings.PROVIDER_PROFILE == "backtest_synthetic"
    assert profiled_settings.MACRO_PROVIDER == Settings.BACKTEST_MACRO_PROVIDER
    assert profiled_settings.MARKET_DATA_PROVIDER == Settings.BACKTEST_DATA_PROVIDER
    assert profiled_settings.MARKET_EVENTS_PROVIDER == Settings.BACKTEST_EVENTS_PROVIDER
    assert profiled_settings.NEWS_PROVIDER == Settings.BACKTEST_NEWS_PROVIDER
    assert profiled_settings.PORTFOLIO_PROVIDER == Settings.BACKTEST_PORTFOLIO_PROVIDER
    assert profiled_settings.SENTIMENT_PROVIDER == Settings.BACKTEST_SENTIMENT_PROVIDER


def test_live_profile_maps_to_live_providers() -> None:
    settings = apply_provider_profile(
        Settings(),
        "live",
    )

    assert settings.PROVIDER_PROFILE == "live"
    assert settings.MACRO_PROVIDER == Settings.LIVE_MACRO_PROVIDER
    assert settings.MARKET_DATA_PROVIDER == Settings.LIVE_DATA_PROVIDER
    assert settings.MARKET_EVENTS_PROVIDER == Settings.LIVE_EVENTS_PROVIDER
    assert settings.NEWS_PROVIDER == Settings.LIVE_NEWS_PROVIDER
    assert settings.PORTFOLIO_PROVIDER == Settings.LIVE_PORTFOLIO_PROVIDER
    assert settings.SENTIMENT_PROVIDER == Settings.LIVE_SENTIMENT_PROVIDER


def test_backtest_postgres_profile_maps_to_postgres_market_data_provider() -> None:
    profile = get_provider_profile(
        "backtest_postgres",
    )

    assert profile.macro_provider == Settings.BACKTEST_MACRO_PROVIDER
    assert profile.market_data_provider == Settings.BACKTEST_POSTGRES_DATA_PROVIDER
    assert profile.market_events_provider == Settings.BACKTEST_EVENTS_PROVIDER
    assert profile.news_provider == Settings.BACKTEST_NEWS_PROVIDER
    assert profile.portfolio_provider == Settings.BACKTEST_PORTFOLIO_PROVIDER
    assert profile.sentiment_provider == Settings.BACKTEST_SENTIMENT_PROVIDER


def test_apply_backtest_postgres_profile_updates_market_data_provider() -> None:
    settings = apply_provider_profile(
        Settings(),
        "backtest_postgres",
    )

    assert settings.PROVIDER_PROFILE == "backtest_postgres"
    assert settings.MARKET_DATA_PROVIDER == Settings.BACKTEST_POSTGRES_DATA_PROVIDER
