from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider
from dishka import Scope
from dishka import provide
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.postgres import AsyncSessionLocal
from core.storage.persistence.repositories.postgres_agent_signal_persistence_repository import (
    PostgresAgentSignalPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_ai_observability_export_job_repository import (
    PostgresAiObservabilityExportJobRepository,
)
from core.storage.persistence.repositories.postgres_ai_artifact_persistence_repository import (
    PostgresAiArtifactPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_backtest_persistence_repository import (
    PostgresBacktestPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_evaluation_persistence_repository import (
    PostgresEvaluationPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_macro_persistence_repository import (
    PostgresMacroPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_market_persistence_repository import (
    PostgresMarketPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_news_persistence_repository import (
    PostgresNewsPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_expansion_persistence_repository import (
    PostgresPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_rag_persistence_repository import (
    PostgresRagPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_recommendation_persistence_repository import (
    PostgresRecommendationPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_report_persistence_repository import (
    PostgresReportPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_sentiment_persistence_repository import (
    PostgresSentimentPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_workflow_output_projection_job_repository import (
    PostgresWorkflowOutputProjectionJobRepository,
)
from core.storage.persistence.ai_artifacts import AiArtifactPersistenceRepository
from core.storage.persistence.ai_observability import AiObservabilityExportJobRepository
from core.storage.persistence.evaluation import EvaluationPersistenceRepository
from core.storage.persistence.portfolio import (
    PortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.projections import WorkflowOutputProjectionJobRepository
from core.storage.persistence.rag import RagPersistenceRepository


class RagPersistenceDIProvider(Provider):
    """Request-scoped PostgreSQL composition for canonical RAG operations."""

    scope = Scope.REQUEST

    @provide
    async def provide_rag_session(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSessionLocal() as session:
            yield session

    @provide
    def provide_rag_repository(
        self,
        session: AsyncSession,
    ) -> RagPersistenceRepository:
        return PostgresRagPersistenceRepository(session)

    @provide
    def provide_report_repository(
        self,
        session: AsyncSession,
    ) -> PostgresReportPersistenceRepository:
        return PostgresReportPersistenceRepository(session)

    @provide
    def provide_agent_signal_repository(
        self,
        session: AsyncSession,
    ) -> PostgresAgentSignalPersistenceRepository:
        return PostgresAgentSignalPersistenceRepository(session)

    @provide
    def provide_recommendation_repository(
        self,
        session: AsyncSession,
    ) -> PostgresRecommendationPersistenceRepository:
        return PostgresRecommendationPersistenceRepository(session)

    @provide
    def provide_macro_repository(
        self,
        session: AsyncSession,
    ) -> PostgresMacroPersistenceRepository:
        return PostgresMacroPersistenceRepository(session)

    @provide
    def provide_market_repository(
        self,
        session: AsyncSession,
    ) -> PostgresMarketPersistenceRepository:
        return PostgresMarketPersistenceRepository(session)

    @provide
    def provide_news_repository(
        self,
        session: AsyncSession,
    ) -> PostgresNewsPersistenceRepository:
        return PostgresNewsPersistenceRepository(session)

    @provide
    def provide_sentiment_repository(
        self,
        session: AsyncSession,
    ) -> PostgresSentimentPersistenceRepository:
        return PostgresSentimentPersistenceRepository(session)

    @provide
    def provide_portfolio_repository(
        self,
        session: AsyncSession,
    ) -> PostgresPortfolioExpansionPersistenceRepository:
        return PostgresPortfolioExpansionPersistenceRepository(session)

    @provide
    def provide_portfolio_expansion_repository(
        self,
        repository: PostgresPortfolioExpansionPersistenceRepository,
    ) -> PortfolioExpansionPersistenceRepository:
        return repository

    @provide
    def provide_backtest_repository(
        self,
        session: AsyncSession,
    ) -> PostgresBacktestPersistenceRepository:
        return PostgresBacktestPersistenceRepository(session)

    @provide
    def provide_workflow_output_projection_job_repository(
        self,
        session: AsyncSession,
    ) -> WorkflowOutputProjectionJobRepository:
        return PostgresWorkflowOutputProjectionJobRepository(session)

    @provide
    def provide_ai_observability_export_job_repository(
        self,
        session: AsyncSession,
    ) -> AiObservabilityExportJobRepository:
        return PostgresAiObservabilityExportJobRepository(session)

    @provide
    def provide_evaluation_repository(
        self,
        session: AsyncSession,
    ) -> EvaluationPersistenceRepository:
        return PostgresEvaluationPersistenceRepository(session)

    @provide
    def provide_ai_artifact_repository(
        self,
        session: AsyncSession,
    ) -> AiArtifactPersistenceRepository:
        return PostgresAiArtifactPersistenceRepository(session)
