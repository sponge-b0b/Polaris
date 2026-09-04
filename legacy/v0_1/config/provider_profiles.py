from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from config.settings import Settings

ProviderProfileName = Literal[
    "live",
    "backtest_synthetic",
    "backtest_postgres",
]


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderProfile:
    """
    Named provider selection profile for runtime composition.

    Provider profiles are configuration-level shortcuts. They select the
    provider implementations that Dishka wires during CLI/bootstrap assembly;
    runtime nodes, intelligence agents, and application services should not
    branch on these names.
    """

    name: ProviderProfileName
    macro_provider: str
    market_data_provider: str
    market_events_provider: str
    news_provider: str
    portfolio_provider: str
    sentiment_provider: str

    def to_settings_update(
        self,
    ) -> dict[str, str]:
        return {
            "PROVIDER_PROFILE": self.name,
            "MACRO_PROVIDER": self.macro_provider,
            "MARKET_DATA_PROVIDER": self.market_data_provider,
            "MARKET_EVENTS_PROVIDER": self.market_events_provider,
            "NEWS_PROVIDER": self.news_provider,
            "PORTFOLIO_PROVIDER": self.portfolio_provider,
            "SENTIMENT_PROVIDER": self.sentiment_provider,
        }

    def to_env(
        self,
    ) -> dict[str, str]:
        return self.to_settings_update()

    def to_dict(
        self,
    ) -> dict[str, str]:
        return {
            "name": self.name,
            **self.to_settings_update(),
        }


LIVE_PROVIDER_PROFILE: ProviderProfileName = "live"
BACKTEST_SYNTHETIC_PROVIDER_PROFILE: ProviderProfileName = "backtest_synthetic"
BACKTEST_POSTGRES_PROVIDER_PROFILE: ProviderProfileName = "backtest_postgres"

SUPPORTED_PROVIDER_PROFILES: Mapping[str, ProviderProfile] = {
    LIVE_PROVIDER_PROFILE: ProviderProfile(
        name=LIVE_PROVIDER_PROFILE,
        macro_provider=Settings.LIVE_MACRO_PROVIDER,
        market_data_provider=Settings.LIVE_DATA_PROVIDER,
        market_events_provider=Settings.LIVE_EVENTS_PROVIDER,
        news_provider=Settings.LIVE_NEWS_PROVIDER,
        portfolio_provider=Settings.LIVE_PORTFOLIO_PROVIDER,
        sentiment_provider=Settings.LIVE_SENTIMENT_PROVIDER,
    ),
    BACKTEST_SYNTHETIC_PROVIDER_PROFILE: ProviderProfile(
        name=BACKTEST_SYNTHETIC_PROVIDER_PROFILE,
        macro_provider=Settings.BACKTEST_MACRO_PROVIDER,
        market_data_provider=Settings.BACKTEST_DATA_PROVIDER,
        market_events_provider=Settings.BACKTEST_EVENTS_PROVIDER,
        news_provider=Settings.BACKTEST_NEWS_PROVIDER,
        portfolio_provider=Settings.BACKTEST_PORTFOLIO_PROVIDER,
        sentiment_provider=Settings.BACKTEST_SENTIMENT_PROVIDER,
    ),
    BACKTEST_POSTGRES_PROVIDER_PROFILE: ProviderProfile(
        name=BACKTEST_POSTGRES_PROVIDER_PROFILE,
        macro_provider=Settings.BACKTEST_MACRO_PROVIDER,
        market_data_provider=Settings.BACKTEST_POSTGRES_DATA_PROVIDER,
        market_events_provider=Settings.BACKTEST_EVENTS_PROVIDER,
        news_provider=Settings.BACKTEST_NEWS_PROVIDER,
        portfolio_provider=Settings.BACKTEST_PORTFOLIO_PROVIDER,
        sentiment_provider=Settings.BACKTEST_SENTIMENT_PROVIDER,
    ),
}


def get_provider_profile(
    profile_name: str,
) -> ProviderProfile:
    normalized_profile_name = profile_name.strip()

    profile = SUPPORTED_PROVIDER_PROFILES.get(
        normalized_profile_name,
    )
    if profile is not None:
        return profile

    supported_profiles = ", ".join(
        sorted(SUPPORTED_PROVIDER_PROFILES),
    )
    raise ValueError(
        f"Unsupported provider profile: {profile_name}. "
        f"Supported profiles: {supported_profiles}."
    )


def apply_provider_profile(
    settings: Settings,
    profile_name: str | None,
) -> Settings:
    if profile_name is None or not profile_name.strip():
        return settings

    profile = get_provider_profile(
        profile_name,
    )
    return settings.model_copy(
        update=profile.to_settings_update(),
    )
