from dishka import Provider, Scope, provide

from config.settings import Settings
from core.database.postgres import AsyncSessionLocal
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from integration.clients.macro.fred_macro_client import FredMacroClient
from integration.clients.market_data.massive_data_client import MassiveDataClient
from integration.clients.market_data.yfinance_data_client import YFinanceDataClient
from integration.clients.market_events.alphavantage_events_client import (
    AlphaVantageEarningsClient,
)
from integration.clients.market_events.fed_events_client import FedEventsClient
from integration.clients.market_events.fred_events_client import FredEventsClient
from integration.clients.news.finnhub_news_client import FinnhubNewsClient
from integration.clients.news.newsapi_news_client import NewsApiNewsClient
from integration.clients.portfolio.alpaca_portfolio_client import AlpacaPortfolioClient
from integration.clients.sentiment.alphavantage_sentiment_client import (
    AlphaVantageSentimentClient,
)
from integration.clients.sentiment.fear_greed_sentiment_client import (
    FearGreedSentimentClient,
)
from integration.providers.backtesting.macro.simulated_macro_provider import (
    SimulatedMacroProvider,
)
from integration.providers.backtesting.market_data.postgres_historical_data_provider import (  # noqa: E501
    PostgresHistoricalDataProvider,
    PostgresHistoricalDataProviderConfig,
    postgres_market_repository_factory,
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
from integration.providers.macro.backtest_macro_provider import BacktestMacroProvider
from integration.providers.macro.live_macro_provider import LiveMacroProvider
from integration.providers.macro.macro_provider import MacroProvider
from integration.providers.market_data.backtest_data_provider import (
    BacktestDataProvider,
)
from integration.providers.market_data.live_data_provider import LiveDataProvider
from integration.providers.market_data.market_data_provider import MarketDataProvider
from integration.providers.market_events.backtest_events_provider import (
    BacktestEventsProvider,
)
from integration.providers.market_events.live_events_provider import LiveEventsProvider
from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)
from integration.providers.news.backtest_news_provider import BacktestNewsProvider
from integration.providers.news.live_news_provider import LiveNewsProvider
from integration.providers.news.news_provider import NewsProvider
from integration.providers.portfolio.backtest_portfolio_provider import (
    BacktestPortfolioProvider,
)
from integration.providers.portfolio.live_portfolio_provider import (
    LivePortfolioProvider,
)
from integration.providers.portfolio.portfolio_provider import PortfolioProvider
from integration.providers.sentiment.backtest_sentiment_provider import (
    BacktestSentimentProvider,
)
from integration.providers.sentiment.live_sentiment_provider import (
    LiveSentimentProvider,
)
from integration.providers.sentiment.sentiment_provider import SentimentProvider

# ====================================================
# Use Dishka Startup Switching method for dynamic
# initialization. To allow for dynamic initialization,
# each dynamic class needs to be declared using its
# own DI Provider class.
# ====================================================

# ====================================================
# Macro Providers
# ====================================================


class LiveMacroDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Live Macro Provider.
    @provide
    def provide_macro_provider(
        self,
        fred_client: FredMacroClient,
        integration_telemetry: IntegrationTelemetry,
    ) -> MacroProvider:  # Canonical macro provider interface.

        return LiveMacroProvider(
            macro_client=fred_client,
            telemetry=integration_telemetry,
        )


class BacktestMacroDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Backstest Macro Provider
    @provide
    def provide_macro_provider(
        self,
        macro_provider: SimulatedMacroProvider,
        integration_telemetry: IntegrationTelemetry,
    ) -> MacroProvider:  # Canonical macro provider interface.

        return BacktestMacroProvider(
            macro_provider=macro_provider,
            telemetry=integration_telemetry,
        )


# ====================================================
# Market Data Providers
# ====================================================


class LiveDataDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Live Market Data Provider
    @provide
    def provide_market_data_provider(
        self,
        massive_data_client: MassiveDataClient,
        yfinance_data_client: YFinanceDataClient,
        integration_telemetry: IntegrationTelemetry,
    ) -> MarketDataProvider:  # Canonical market data provider interface.

        return LiveDataProvider(
            massive_data_client=massive_data_client,
            yfinance_data_client=yfinance_data_client,
            telemetry=integration_telemetry,
        )


class BacktestDataDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Backstest Market Data Provider
    @provide
    def provide_market_data_provider(
        self,
        data_provider: SimulatedDataProvider,
        integration_telemetry: IntegrationTelemetry,
    ) -> MarketDataProvider:  # Canonical market data provider interface.

        return BacktestDataProvider(
            data_provider=data_provider,
            telemetry=integration_telemetry,
        )


class BacktestPostgresDataDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # PostgreSQL-backed historical market data provider for backtests.
    @provide
    def provide_market_data_provider(
        self,
        settings: Settings,
        integration_telemetry: IntegrationTelemetry,
    ) -> MarketDataProvider:  # Canonical market data provider interface.

        data_provider = PostgresHistoricalDataProvider(
            repository_factory=postgres_market_repository_factory(
                AsyncSessionLocal,
            ),
            config=PostgresHistoricalDataProviderConfig(
                source=settings.BACKTEST_POSTGRES_MARKET_DATA_SOURCE,
                sp500_universe=settings.BACKTEST_POSTGRES_SP500_UNIVERSE,
                missing_data_policy=settings.BACKTEST_POSTGRES_MISSING_DATA_POLICY,
            ),
        )
        return BacktestDataProvider(
            data_provider=data_provider,
            telemetry=integration_telemetry,
        )


# ====================================================
# Market Events Providers
# ====================================================


class LiveEventsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Live Market Events Provider
    @provide
    def provide_market_events_provider(
        self,
        fed_client: FedEventsClient,
        fred_client: FredEventsClient,
        earnings_client: AlphaVantageEarningsClient,
        integration_telemetry: IntegrationTelemetry,
    ) -> MarketEventsProvider:  # Canonical market events provider interface.

        return LiveEventsProvider(
            fed_client=fed_client,
            fred_client=fred_client,
            earnings_client=earnings_client,
            telemetry=integration_telemetry,
        )


class BacktestEventsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Backstest Market Events Provider
    @provide
    def provide_market_events_provider(
        self,
        events_provider: SimulatedEventsProvider,
        integration_telemetry: IntegrationTelemetry,
    ) -> MarketEventsProvider:  # Canonical market events provider interface.

        return BacktestEventsProvider(
            events_provider=events_provider,
            telemetry=integration_telemetry,
        )


# ====================================================
# News Providers
# ====================================================


class LiveNewsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Live News Provider
    @provide
    def provide_market_news_provider(
        self,
        finnhub_news_client: FinnhubNewsClient,
        newsapi_news_client: NewsApiNewsClient,
        integration_telemetry: IntegrationTelemetry,
    ) -> NewsProvider:  # Canonical news provider interface.

        return LiveNewsProvider(
            finnhub_news_client=finnhub_news_client,
            newsapi_news_client=newsapi_news_client,
            telemetry=integration_telemetry,
        )


class BacktestNewsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Backstest News Provider
    @provide
    def provide_market_data_provider(
        self,
        news_provider: SimulatedNewsProvider,
        integration_telemetry: IntegrationTelemetry,
    ) -> NewsProvider:  # Canonical news provider interface.

        return BacktestNewsProvider(
            news_provider=news_provider,
            telemetry=integration_telemetry,
        )


# ====================================================
# Portfolio Providers
# ====================================================


class LivePortfolioDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Live Portfolio Provider.
    @provide
    def provide_macro_provider(
        self,
        portfolio_client: AlpacaPortfolioClient,
        integration_telemetry: IntegrationTelemetry,
    ) -> PortfolioProvider:  # Canonical portfolio provider interface.

        return LivePortfolioProvider(
            portfolio_client=portfolio_client,
            telemetry=integration_telemetry,
        )


class BacktestPortfolioDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Backstest Portfolio Provider
    @provide
    def provide_portfolio_provider(
        self,
        portfolio_provider: SimulatedPortfolioProvider,
        integration_telemetry: IntegrationTelemetry,
    ) -> PortfolioProvider:  # Canonical portfolio provider interface.

        return BacktestPortfolioProvider(
            portfolio_provider=portfolio_provider,
            telemetry=integration_telemetry,
        )


# ====================================================
# Sentiment Providers
# ====================================================


class LiveSentimentDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Live Sentiment Provider
    @provide
    def provide_sentiment_provider(
        self,
        alphavantage_sentiment_client: AlphaVantageSentimentClient,
        fear_greed_sentiment_client: FearGreedSentimentClient,
        integration_telemetry: IntegrationTelemetry,
    ) -> SentimentProvider:  # Canonical sentiment provider interface.

        return LiveSentimentProvider(
            alphavantage_sentiment_client=alphavantage_sentiment_client,
            fear_greed_sentiment_client=fear_greed_sentiment_client,
            telemetry=integration_telemetry,
        )


class BacktestSentimentDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Backstest Sentiment Provider
    @provide
    def provide_sentiment_provider(
        self,
        sentiment_provider: SimulatedSentimentProvider,
        integration_telemetry: IntegrationTelemetry,
    ) -> SentimentProvider:  # Canonical sentiment provider interface.

        return BacktestSentimentProvider(
            sentiment_provider=sentiment_provider,
            telemetry=integration_telemetry,
        )


# ====================================================
# Traditional DI Provider
# ====================================================


class IntegrationProvidersDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    @provide
    def provide_integration_telemetry(
        self,
        observability_manager: ObservabilityManager,
    ) -> IntegrationTelemetry:
        return IntegrationTelemetry(
            observability_manager=observability_manager,
        )
