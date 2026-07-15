from dishka import Provider, Scope, provide
from config.settings import Settings
from core.llm.llm_gateway import LLMGateway
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.llm import LiteLlmCoreGatewayAdapter
from integration.clients.llm import LiteLlmGatewayClient

from integration.clients.macro.fred_macro_client import FredMacroClient
from integration.clients.market_data.massive_data_client import MassiveDataClient
from integration.clients.market_data.yfinance_data_client import YFinanceDataClient
from integration.clients.market_events.fed_events_client import FedEventsClient
from integration.clients.market_events.fred_events_client import FredEventsClient
from integration.clients.market_events.alphavantage_events_client import (
    AlphaVantageEarningsClient,
)
from integration.clients.news.finnhub_news_client import FinnhubNewsClient
from integration.clients.news.newsapi_news_client import NewsApiNewsClient
from integration.clients.portfolio.alpaca_portfolio_client import AlpacaPortfolioClient
from integration.clients.sentiment.alphavantage_sentiment_client import (
    AlphaVantageSentimentClient,
)
from integration.clients.sentiment.fear_greed_sentiment_client import (
    FearGreedSentimentClient,
)


class IntegrationClientsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # ====================================================
    # LLM Gateway Clients
    # ====================================================

    @provide
    def provide_litellm_gateway_client(
        self,
        settings: Settings,
    ) -> LiteLlmGatewayClient:
        return LiteLlmGatewayClient.from_settings(settings)

    @provide
    def provide_llm_gateway(
        self,
        client: LiteLlmGatewayClient,
    ) -> LLMGateway:
        return LiteLlmCoreGatewayAdapter(client)

    # ====================================================
    # Macro Clients
    # ====================================================

    # FRED Macro Client
    @provide
    def provide_fred_macro_client(self, settings: Settings) -> FredMacroClient:
        return FredMacroClient(settings=settings)

    # ====================================================
    # Market Data Clients
    # ====================================================

    # Massive Data Client
    @provide
    def provide_massive_data_client(self, settings: Settings) -> MassiveDataClient:
        return MassiveDataClient(settings=settings)

    # Yahoo Finance Data Client
    @provide
    def provide_yfinance_data_client(
        self,
        integration_telemetry: IntegrationTelemetry,
    ) -> YFinanceDataClient:
        return YFinanceDataClient(telemetry=integration_telemetry)

    # ====================================================
    # Market Events Clients
    # ====================================================

    # FED Events Client
    @provide
    def provide_fed_events_client(self) -> FedEventsClient:
        return FedEventsClient()

    # FRED Events Client
    @provide
    def provide_fred_events_client(self, settings: Settings) -> FredEventsClient:
        return FredEventsClient(settings=settings)

    # Alpha Vantage Earnings Client
    @provide
    def provide_alphavantage_earnings_client(
        self,
        settings: Settings,
    ) -> AlphaVantageEarningsClient:
        return AlphaVantageEarningsClient(settings=settings)

    # ====================================================
    # News Clients
    # ====================================================

    # Finnhub News Client
    @provide
    def provide_finnhub_news_client(self, settings: Settings) -> FinnhubNewsClient:
        return FinnhubNewsClient(settings=settings)

    # NEWSAPI News Client
    @provide
    def provide_newsapi_client(self, settings: Settings) -> NewsApiNewsClient:
        return NewsApiNewsClient(settings=settings)

    # ====================================================
    # Portfolio Clients
    # ====================================================

    # Alpaca Client
    @provide
    def provide_alpaca_client(self, settings: Settings) -> AlpacaPortfolioClient:
        return AlpacaPortfolioClient(settings=settings)

    # ====================================================
    # Sentiment Clients
    # ====================================================

    # Alpha Avantage Client
    @provide
    def provide_alphavantage_sentiment_client(
        self, settings: Settings
    ) -> AlphaVantageSentimentClient:
        return AlphaVantageSentimentClient(settings=settings)

    # Fear Greed Client
    @provide
    def provide_fear_greed_client(self) -> FearGreedSentimentClient:
        return FearGreedSentimentClient()
