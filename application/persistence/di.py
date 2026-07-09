from dishka import Provider
from dishka import Scope
from dishka import provide

from application.persistence.backtesting import BacktestPersistenceService
from application.persistence.portfolio import PortfolioPersistenceService
from application.reports import MorningReportPersistenceService
from core.storage.persistence.repositories import (
    PostgresBacktestPersistenceRepository,
)
from core.storage.persistence.repositories import PostgresReportPersistenceRepository
from core.storage.persistence.portfolio import (
    PortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
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
