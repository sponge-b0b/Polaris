from dishka import Provider, Scope, provide

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


class BacktestingProvidersDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # ====================================================
    # Simulated Macro Providers
    # ====================================================

    # Simulated Macro Provider Interface.
    @provide
    def provide_simulated_macro_provider(self) -> SimulatedMacroProvider:
        return SimulatedMacroProvider()

    # ====================================================
    # SimulatedMarket Data Providers
    # ====================================================

    # Simulated Market Data Provider Interface.
    @provide
    def provide_simulated_market_data_provider(self) -> SimulatedDataProvider:
        return SimulatedDataProvider()

    # ====================================================
    # Simulated Market Events Providers
    # ====================================================

    # Simulated Market Events Provider Interface.
    @provide
    def provide_market_events_provider(self) -> SimulatedEventsProvider:
        return SimulatedEventsProvider()

    # ====================================================
    # Simulated News Providers
    # ====================================================

    # Simulated News Provider Interface.
    @provide
    def provide_simulated_news_provider(self) -> SimulatedNewsProvider:
        return SimulatedNewsProvider()

    # ====================================================
    # Simulated Portfolio Providers
    # ====================================================

    # Simulated Portfolio Provider Interface.
    @provide
    def provide_simulated_portfolio_provider(self) -> SimulatedPortfolioProvider:
        return SimulatedPortfolioProvider()

    # ====================================================
    # Simulated Sentiment Providers
    # ====================================================

    # Simulated Sentiment Provider Interface.
    @provide
    def provide_simulated_sentiment_provider(self) -> SimulatedSentimentProvider:
        return SimulatedSentimentProvider()
