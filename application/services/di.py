from dishka import Provider, Scope, provide

from integration.providers.macro.macro_provider import MacroProvider
from integration.providers.market_data.market_data_provider import MarketDataProvider
from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)
from integration.providers.news.news_provider import NewsProvider
from integration.providers.portfolio.portfolio_provider import PortfolioProvider
from integration.providers.sentiment.sentiment_provider import SentimentProvider
from core.runtime.policies.policy_engine import PolicyEngine
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.observability.observability_manager import (
    ObservabilityManager,
)
from application.services.base import ServiceRunner
from application.services.backtesting import BacktestApplicationService

from application.services.macro.macro_service import MacroService
from application.services.market_events.market_events_service import MarketEventsService
from application.services.news.news_service import NewsService
from application.services.portfolio.portfolio_service import PortfolioService
from application.services.sentiment.sentiment_service import SentimentService
from application.services.technical.technical_analysis_service import (
    TechnicalAnalysisService,
)
from core.workflow.execution.workflow_facade import WorkflowFacade


class AppServicesDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # ====================================================
    # Base Service Orchestration
    # ====================================================

    @provide
    def provide_application_service_telemetry(
        self,
        observability_manager: ObservabilityManager,
    ) -> ApplicationServiceTelemetry:
        return ApplicationServiceTelemetry(
            observability_manager=observability_manager,
        )

    @provide
    def provide_application_rag_telemetry(
        self,
        observability_manager: ObservabilityManager,
    ) -> ApplicationRagTelemetry:
        return ApplicationRagTelemetry(
            observability_manager=observability_manager,
        )

    @provide
    def provide_service_runner(
        self,
        application_service_telemetry: ApplicationServiceTelemetry,
        policy_engine: PolicyEngine,
    ) -> ServiceRunner:
        return ServiceRunner(
            telemetry=application_service_telemetry,
            policy_engine=policy_engine,
        )

    @provide
    def provide_backtest_application_service(
        self,
        workflow_facade: WorkflowFacade,
    ) -> BacktestApplicationService:
        return BacktestApplicationService(
            workflow_facade=workflow_facade,
        )

    # ====================================================
    # Macro Services
    # ====================================================

    # Macro Service
    @provide
    def provide_macro_service(
        self,
        macro_provider: MacroProvider,
    ) -> MacroService:

        return MacroService(macro_provider=macro_provider)

    # ====================================================
    # Market Events Services
    # ====================================================

    # Market Events Service
    @provide
    def provide_market_events_service(
        self,
        events_provider: MarketEventsProvider,
    ) -> MarketEventsService:

        return MarketEventsService(events_provider=events_provider)

    # ====================================================
    # News Services
    # ====================================================

    # News Service
    @provide
    def provide_news_service(
        self,
        news_provider: NewsProvider,
    ) -> NewsService:

        return NewsService(news_provider=news_provider)

    # ====================================================
    # Portfolio Services
    # ====================================================

    # Portfolio Service
    @provide(scope=Scope.REQUEST)
    def provide_portfolio_service(
        self,
        portfolio_provider: PortfolioProvider,
    ) -> PortfolioService:

        return PortfolioService(
            portfolio_provider=portfolio_provider,
        )

    # ====================================================
    # Sentiment Services
    # ====================================================

    # Sentiment Service
    @provide
    def provide_sentiment_service(
        self,
        sentiment_provider: SentimentProvider,
    ) -> SentimentService:

        return SentimentService(sentiment_provider=sentiment_provider)

    # ====================================================
    # Technical Services
    # ====================================================

    # Technical Service
    @provide
    def provide_technical_service(
        self,
        data_provider: MarketDataProvider,
    ) -> TechnicalAnalysisService:

        return TechnicalAnalysisService(data_provider=data_provider)
