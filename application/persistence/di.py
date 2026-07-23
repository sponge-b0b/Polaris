from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from application.persistence.agent_signals import AgentSignalPersistenceService
from application.persistence.backtesting import BacktestPersistenceService
from application.persistence.macro import MacroPersistenceService
from application.persistence.market import MarketPersistenceService
from application.persistence.news import NewsPersistenceService
from application.persistence.portfolio import PortfolioPersistenceService
from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.sentiment import SentimentPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.reports import MorningReportPersistenceService
from core.storage.persistence.portfolio import (
    PortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
)
from core.storage.persistence.repositories import (
    PostgresAgentSignalPersistenceRepository,
    PostgresBacktestPersistenceRepository,
    PostgresMacroPersistenceRepository,
    PostgresMarketPersistenceRepository,
    PostgresNewsPersistenceRepository,
    PostgresRecommendationPersistenceRepository,
    PostgresReportPersistenceRepository,
    PostgresSentimentPersistenceRepository,
    PostgresStrategyPersistenceRepository,
)


class ApplicationPersistenceDIProvider(Provider):
    """Request-scoped application persistence orchestration."""

    scope = Scope.REQUEST

    @provide
    def provide_portfolio_persistence_service(
        self,
        expansion_repository: PortfolioExpansionPersistenceRepository,
        state_repository: PortfolioStateRepository,
    ) -> PortfolioPersistenceService:
        return PortfolioPersistenceService(
            expansion_repository,
            state_repository,
        )

    @provide
    def provide_market_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresMarketPersistenceRepository:
        return PostgresMarketPersistenceRepository(session)

    @provide
    def provide_market_persistence_service(
        self,
        repository: PostgresMarketPersistenceRepository,
    ) -> MarketPersistenceService:
        return MarketPersistenceService(repository)

    @provide
    def provide_macro_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresMacroPersistenceRepository:
        return PostgresMacroPersistenceRepository(session)

    @provide
    def provide_macro_persistence_service(
        self,
        repository: PostgresMacroPersistenceRepository,
    ) -> MacroPersistenceService:
        return MacroPersistenceService(repository)

    @provide
    def provide_news_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresNewsPersistenceRepository:
        return PostgresNewsPersistenceRepository(session)

    @provide
    def provide_news_persistence_service(
        self,
        repository: PostgresNewsPersistenceRepository,
    ) -> NewsPersistenceService:
        return NewsPersistenceService(repository)

    @provide
    def provide_sentiment_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresSentimentPersistenceRepository:
        return PostgresSentimentPersistenceRepository(session)

    @provide
    def provide_sentiment_persistence_service(
        self,
        repository: PostgresSentimentPersistenceRepository,
    ) -> SentimentPersistenceService:
        return SentimentPersistenceService(repository)

    @provide
    def provide_agent_signal_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresAgentSignalPersistenceRepository:
        return PostgresAgentSignalPersistenceRepository(session)

    @provide
    def provide_agent_signal_persistence_service(
        self,
        repository: PostgresAgentSignalPersistenceRepository,
    ) -> AgentSignalPersistenceService:
        return AgentSignalPersistenceService(repository)

    @provide
    def provide_strategy_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresStrategyPersistenceRepository:
        return PostgresStrategyPersistenceRepository(session)

    @provide
    def provide_strategy_persistence_service(
        self,
        repository: PostgresStrategyPersistenceRepository,
    ) -> StrategyPersistenceService:
        return StrategyPersistenceService(repository)

    @provide
    def provide_recommendation_persistence_repository(
        self,
        session: AsyncSession,
    ) -> PostgresRecommendationPersistenceRepository:
        return PostgresRecommendationPersistenceRepository(session)

    @provide
    def provide_recommendation_persistence_service(
        self,
        repository: PostgresRecommendationPersistenceRepository,
    ) -> RecommendationPersistenceService:
        return RecommendationPersistenceService(repository)

    @provide
    def provide_backtest_persistence_service(
        self,
        repository: PostgresBacktestPersistenceRepository,
    ) -> BacktestPersistenceService:
        return BacktestPersistenceService(repository)

    @provide
    def provide_morning_report_persistence_service(
        self,
        repository: PostgresReportPersistenceRepository,
    ) -> MorningReportPersistenceService:
        return MorningReportPersistenceService(repository)
