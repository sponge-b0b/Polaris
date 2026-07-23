from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import AbstractAsyncContextManager
from weakref import WeakSet

from sqlalchemy.ext.asyncio import AsyncSession

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
from application.projections.workflow_outputs.projection_event_subscriber import (
    WorkflowOutputProjectionEventSubscriber,
    WorkflowOutputProjectionEventSubscriberConfig,
)
from application.projections.workflow_outputs.projection_models import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectorRegistration,
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
from core.runtime.events.event_bus import EventBus
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.storage.persistence.repositories.postgres_agent_signal_persistence_repository import (  # noqa: E501
    PostgresAgentSignalPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_macro_persistence_repository import (  # noqa: E501
    PostgresMacroPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_market_persistence_repository import (  # noqa: E501
    PostgresMarketPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_news_persistence_repository import (
    PostgresNewsPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_expansion_persistence_repository import (  # noqa: E501
    PostgresPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_state_repository import (
    PostgresPortfolioStateRepository,
)
from core.storage.persistence.repositories.postgres_recommendation_persistence_repository import (  # noqa: E501
    PostgresRecommendationPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_sentiment_persistence_repository import (  # noqa: E501
    PostgresSentimentPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_strategy_persistence_repository import (  # noqa: E501
    PostgresStrategyPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_workflow_output_projection_job_repository import (  # noqa: E501
    PostgresWorkflowOutputProjectionJobRepository,
)
from core.telemetry.observability.observability_manager import ObservabilityManager

ProjectionSessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]

_SUBSCRIBED_EVENT_BUSES: WeakSet[EventBus] = WeakSet()


class PostgresWorkflowOutputProjectionCoordinator:
    """Owns per-event PostgreSQL request/session scope for projection events."""

    def __init__(
        self,
        *,
        session_factory: ProjectionSessionFactory,
        registry: WorkflowOutputProjectionRegistry | None = None,
        projector_registrations: Iterable[WorkflowOutputProjectorRegistration] = (),
        eligibility_policy: WorkflowOutputProjectionEligibilityPolicy | None = None,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry
        self._projector_registrations = tuple(projector_registrations)
        self._eligibility_policy = (
            eligibility_policy or WorkflowOutputProjectionEligibilityPolicy()
        )
        self._observability_manager = observability_manager

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        """Project one completed run using a fresh PostgreSQL session."""
        async with self._session_factory() as session:
            service = WorkflowOutputProjectionService(
                completed_run_archive=PostgresCompletedRunArchive(
                    session_factory=self._session_factory,
                ),
                projection_job_repository=PostgresWorkflowOutputProjectionJobRepository(
                    session,
                ),
                registry=self._registry_for_session(session),
                eligibility_policy=self._eligibility_policy,
                observability_manager=self._observability_manager,
            )
            return await service.project_completed_run(request)

    def _registry_for_session(
        self,
        session: AsyncSession,
    ) -> WorkflowOutputProjectionRegistry:
        if self._registry is not None:
            return self._registry

        agent_signal_persistence_service = AgentSignalPersistenceService(
            PostgresAgentSignalPersistenceRepository(session),
        )
        macro_persistence_service = MacroPersistenceService(
            PostgresMacroPersistenceRepository(session),
        )
        market_persistence_service = MarketPersistenceService(
            PostgresMarketPersistenceRepository(session),
        )
        news_persistence_service = NewsPersistenceService(
            PostgresNewsPersistenceRepository(session),
        )
        portfolio_persistence_service = PortfolioPersistenceService(
            PostgresPortfolioExpansionPersistenceRepository(session),
            state_repository=PostgresPortfolioStateRepository(session),
        )
        recommendation_persistence_service = RecommendationPersistenceService(
            PostgresRecommendationPersistenceRepository(session),
        )
        sentiment_persistence_service = SentimentPersistenceService(
            PostgresSentimentPersistenceRepository(session),
        )
        strategy_persistence_service = StrategyPersistenceService(
            PostgresStrategyPersistenceRepository(session),
        )
        return WorkflowOutputProjectionRegistry(
            (
                *self._projector_registrations,
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


def build_default_workflow_output_projection_subscriber(
    *,
    session_factory: ProjectionSessionFactory | None = None,
    observability_manager: ObservabilityManager | None = None,
    config: WorkflowOutputProjectionEventSubscriberConfig | None = None,
) -> WorkflowOutputProjectionEventSubscriber:
    """Build the default application-owned projection event subscriber."""
    if session_factory is None:
        from core.database.postgres import AsyncSessionLocal

        session_factory = AsyncSessionLocal

    return WorkflowOutputProjectionEventSubscriber(
        PostgresWorkflowOutputProjectionCoordinator(
            session_factory=session_factory,
            observability_manager=observability_manager,
        ),
        config=config,
    )


def subscribe_workflow_output_projection_event_subscriber(
    *,
    event_bus: EventBus,
    subscriber: WorkflowOutputProjectionEventSubscriber,
) -> bool:
    """Subscribe once per EventBus and report whether a new subscription happened."""
    if event_bus in _SUBSCRIBED_EVENT_BUSES:
        return False
    subscriber.subscribe(event_bus)
    _SUBSCRIBED_EVENT_BUSES.add(event_bus)
    return True


def subscribe_default_workflow_output_projection(
    *,
    event_bus: EventBus,
    session_factory: ProjectionSessionFactory | None = None,
    observability_manager: ObservabilityManager | None = None,
    config: WorkflowOutputProjectionEventSubscriberConfig | None = None,
) -> bool:
    """Attach the canonical projection subscriber once to an application EventBus."""
    return subscribe_workflow_output_projection_event_subscriber(
        event_bus=event_bus,
        subscriber=build_default_workflow_output_projection_subscriber(
            session_factory=session_factory,
            observability_manager=observability_manager,
            config=config,
        ),
    )
