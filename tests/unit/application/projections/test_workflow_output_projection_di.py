from __future__ import annotations

from typing import cast

from application.persistence.agent_signals import AgentSignalPersistenceService
from application.persistence.macro import MacroPersistenceService
from application.persistence.market import MarketPersistenceService
from application.persistence.news import NewsPersistenceService
from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.sentiment import SentimentPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.projections.workflow_outputs import WorkflowOutputProjectionDIProvider
from application.projections.workflow_outputs import WorkflowOutputProjectionService
from core.storage.persistence.agent_signals import AgentSignalPersistenceRepository
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.macro import MacroPersistenceRepository
from core.storage.persistence.market import MarketPersistenceRepository
from core.storage.persistence.news import NewsPersistenceRepository
from core.storage.persistence.projections import WorkflowOutputProjectionJobRepository
from core.storage.persistence.recommendations import RecommendationPersistenceRepository
from core.storage.persistence.sentiment import SentimentPersistenceRepository
from core.storage.persistence.strategy import StrategyPersistenceRepository
from core.telemetry.observability.observability_manager import ObservabilityManager


class _FakeCompletedRunArchive:
    pass


class _FakeProjectionJobRepository:
    pass


class _FakeAgentSignalRepository:
    pass


class _FakeMacroRepository:
    pass


class _FakeMarketRepository:
    pass


class _FakeNewsRepository:
    pass


class _FakeRecommendationRepository:
    pass


class _FakeSentimentRepository:
    pass


class _FakeStrategyRepository:
    pass


def test_projection_di_provider_builds_typed_projection_service() -> None:
    provider = WorkflowOutputProjectionDIProvider()
    agent_signal_persistence_service = AgentSignalPersistenceService(
        cast(AgentSignalPersistenceRepository, _FakeAgentSignalRepository()),
    )
    macro_persistence_service = MacroPersistenceService(
        cast(MacroPersistenceRepository, _FakeMacroRepository()),
    )
    market_persistence_service = MarketPersistenceService(
        cast(MarketPersistenceRepository, _FakeMarketRepository()),
    )
    news_persistence_service = NewsPersistenceService(
        cast(NewsPersistenceRepository, _FakeNewsRepository()),
    )
    recommendation_persistence_service = RecommendationPersistenceService(
        cast(RecommendationPersistenceRepository, _FakeRecommendationRepository()),
    )
    sentiment_persistence_service = SentimentPersistenceService(
        cast(SentimentPersistenceRepository, _FakeSentimentRepository()),
    )
    strategy_persistence_service = StrategyPersistenceService(
        cast(StrategyPersistenceRepository, _FakeStrategyRepository()),
    )
    registry = provider.provide_workflow_output_projection_registry(
        agent_signal_persistence_service,
        macro_persistence_service,
        market_persistence_service,
        news_persistence_service,
        recommendation_persistence_service,
        sentiment_persistence_service,
        strategy_persistence_service,
    )
    policy = provider.provide_workflow_output_projection_policy()
    observability = ObservabilityManager()

    service = provider.provide_workflow_output_projection_service(
        completed_run_archive=cast(CompletedRunArchive, _FakeCompletedRunArchive()),
        projection_job_repository=cast(
            WorkflowOutputProjectionJobRepository,
            _FakeProjectionJobRepository(),
        ),
        registry=registry,
        eligibility_policy=policy,
        observability_manager=observability,
    )

    assert isinstance(service, WorkflowOutputProjectionService)
    assert service._registry is registry
    assert registry.supported_schema_versions("polaris.macro.analysis") == (1,)
    assert registry.supported_schema_versions("polaris.market.technical_analysis") == (
        1,
    )
    assert registry.supported_schema_versions("polaris.news.analysis") == (1,)
    assert registry.supported_schema_versions("polaris.sentiment.snapshot") == (1,)
    assert registry.supported_schema_versions("polaris.risk.drawdown_signal") == (1,)
    assert registry.supported_schema_versions("polaris.strategy.synthesis") == (1,)
    assert registry.supported_schema_versions(
        "polaris.portfolio.allocation_intent"
    ) == (1,)
    assert registry.supported_schema_versions("polaris.trade.recommendation") == (1,)
    assert service._eligibility_policy is policy
    assert service._observability_manager is observability
