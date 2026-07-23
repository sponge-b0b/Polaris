from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from core.storage.persistence.portfolio import (
    InMemoryPortfolioExpansionPersistenceRepository,
    PortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.portfolio.in_memory_portfolio_state_repository import (
    InMemoryPortfolioStateRepository,
)
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_state_repository import (
    PostgresPortfolioStateRepository,
)


class CoreStorageDIProvider(Provider):
    """PostgreSQL-backed storage for async application request scopes."""

    scope = Scope.REQUEST

    @provide
    def provide_portfolio_state_repository(
        self,
        session: AsyncSession,
    ) -> PortfolioStateRepository:
        return PostgresPortfolioStateRepository(session=session)


class InMemoryCoreStorageDIProvider(Provider):
    """In-memory storage for synchronous invocation-scoped runtimes."""

    scope = Scope.APP

    @provide
    def provide_portfolio_state_repository(self) -> PortfolioStateRepository:
        return InMemoryPortfolioStateRepository()

    @provide
    def provide_portfolio_expansion_repository(
        self,
    ) -> PortfolioExpansionPersistenceRepository:
        return InMemoryPortfolioExpansionPersistenceRepository()
