from __future__ import annotations

from inspect import Parameter
from inspect import signature
from typing import Callable
from typing import cast
import pytest

from integration.providers.backtesting.macro.simulated_macro_provider import (
    SimulatedMacroProvider,
)
from integration.providers.backtesting.market_data.simulated_data_provider import (
    SimulatedDataProvider,
)
from integration.providers.backtesting.market_events.simulated_events_provider import (
    SimulatedEventsProvider,
)
from integration.providers.backtesting.news.simulated_news_provider import (
    SimulatedNewsProvider,
)
from integration.providers.backtesting.portfolio.simulated_portfolio_provider import (
    SimulatedPortfolioProvider,
)
from integration.providers.backtesting.sentiment.simulated_sentiment_provider import (
    SimulatedSentimentProvider,
)
from integration.providers.macro.macro_provider import MacroProvider
from integration.providers.market_data.market_data_provider import MarketDataProvider
from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)
from integration.providers.news.news_provider import NewsProvider
from integration.providers.portfolio.portfolio_provider import PortfolioProvider
from integration.providers.sentiment.sentiment_provider import SentimentProvider


@pytest.mark.parametrize(
    ("provider", "contract", "method_names"),
    (
        (SimulatedMacroProvider(), MacroProvider, ("get_macro_snapshot",)),
        (
            SimulatedDataProvider(),
            MarketDataProvider,
            ("get_symbol_data", "get_vix_data", "get_vvix_data", "get_sp500_data"),
        ),
        (
            SimulatedEventsProvider(),
            MarketEventsProvider,
            ("get_fed_events", "get_economic_events", "get_earnings_events"),
        ),
        (
            SimulatedNewsProvider(),
            NewsProvider,
            ("get_financial_news", "get_market_news"),
        ),
        (
            SimulatedPortfolioProvider(),
            PortfolioProvider,
            ("get_account", "get_positions", "get_portfolio_history"),
        ),
        (
            SimulatedSentimentProvider(),
            SentimentProvider,
            ("get_news_sentiment", "get_fear_greed_sentiment"),
        ),
    ),
)
def test_simulated_provider_matches_canonical_async_contract(
    provider: object,
    contract: type[object],
    method_names: tuple[str, ...],
) -> None:
    assert isinstance(provider, contract)
    for method_name in method_names:
        assert _parameter_contract(
            getattr(provider, method_name)
        ) == _parameter_contract(getattr(contract, method_name))


def test_simulated_portfolio_provider_exposes_canonical_source_property() -> None:
    provider = SimulatedPortfolioProvider()

    assert provider.source == "simulated"
    assert isinstance(provider, PortfolioProvider)


def _parameter_contract(
    callable_object: object,
) -> tuple[tuple[str, object, object], ...]:
    parameters = signature(
        cast(Callable[..., object], callable_object)
    ).parameters.values()
    return tuple(
        (parameter.name, parameter.kind, parameter.default)
        for parameter in parameters
        if parameter.name != "self" and parameter.kind is not Parameter.VAR_KEYWORD
    )
