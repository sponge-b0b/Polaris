from __future__ import annotations

from dishka import Provider, Scope, provide

from application.persistence.agent_signals import AgentSignalPersistenceService
from application.persistence.macro import MacroPersistenceService
from application.persistence.market import MarketPersistenceService
from application.persistence.news import NewsPersistenceService
from application.persistence.portfolio import PortfolioPersistenceService
from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.sentiment import SentimentPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionEligibilityPolicy,
)
from application.projections.workflow_outputs.projection_operations import (
    WorkflowOutputProjectionOperationsService,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
)
from application.projections.workflow_outputs.projection_service import (
    WorkflowOutputProjectionService,
)
from application.projections.workflow_outputs.projectors import (
    build_macro_analysis_projector_registration,
    build_news_analysis_projector_registration,
    build_portfolio_state_projector_registration,
    build_recommendation_projector_registrations,
    build_risk_signal_projector_registrations,
    build_sentiment_snapshot_projector_registration,
    build_strategy_projector_registrations,
    build_technical_market_projector_registration,
)
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.projections import WorkflowOutputProjectionJobRepository
from core.telemetry.observability.observability_manager import ObservabilityManager


class WorkflowOutputProjectionDIProvider(Provider):
    """Dishka composition for canonical workflow-output projection services."""

    scope = Scope.REQUEST

    @provide
    def provide_workflow_output_projection_registry(
        self,
        agent_signal_persistence_service: AgentSignalPersistenceService,
        macro_persistence_service: MacroPersistenceService,
        market_persistence_service: MarketPersistenceService,
        news_persistence_service: NewsPersistenceService,
        portfolio_persistence_service: PortfolioPersistenceService,
        recommendation_persistence_service: RecommendationPersistenceService,
        sentiment_persistence_service: SentimentPersistenceService,
        strategy_persistence_service: StrategyPersistenceService,
    ) -> WorkflowOutputProjectionRegistry:
        """Return the request-scoped registry for domain projectors."""
        return WorkflowOutputProjectionRegistry(
            (
                build_macro_analysis_projector_registration(
                    macro_persistence_service,
                ),
                build_technical_market_projector_registration(
                    market_persistence_service,
                ),
                build_news_analysis_projector_registration(
                    news_persistence_service,
                ),
                build_sentiment_snapshot_projector_registration(
                    sentiment_persistence_service,
                ),
                build_portfolio_state_projector_registration(
                    portfolio_persistence_service,
                ),
                *build_risk_signal_projector_registrations(
                    agent_signal_persistence_service,
                ),
                *build_strategy_projector_registrations(
                    strategy_persistence_service=strategy_persistence_service,
                    recommendation_persistence_service=(
                        recommendation_persistence_service
                    ),
                ),
                *build_recommendation_projector_registrations(
                    recommendation_persistence_service,
                ),
            )
        )

    @provide(scope=Scope.APP)
    def provide_workflow_output_projection_policy(
        self,
    ) -> WorkflowOutputProjectionEligibilityPolicy:
        return WorkflowOutputProjectionEligibilityPolicy()

    @provide
    def provide_workflow_output_projection_service(
        self,
        completed_run_archive: CompletedRunArchive,
        projection_job_repository: WorkflowOutputProjectionJobRepository,
        registry: WorkflowOutputProjectionRegistry,
        eligibility_policy: WorkflowOutputProjectionEligibilityPolicy,
        observability_manager: ObservabilityManager,
    ) -> WorkflowOutputProjectionService:
        return WorkflowOutputProjectionService(
            completed_run_archive=completed_run_archive,
            projection_job_repository=projection_job_repository,
            registry=registry,
            eligibility_policy=eligibility_policy,
            observability_manager=observability_manager,
        )

    @provide
    def provide_workflow_output_projection_operations_service(
        self,
        projection_service: WorkflowOutputProjectionService,
        projection_job_repository: WorkflowOutputProjectionJobRepository,
    ) -> WorkflowOutputProjectionOperationsService:
        return WorkflowOutputProjectionOperationsService(
            projection_service=projection_service,
            projection_job_repository=projection_job_repository,
        )
