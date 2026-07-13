from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Iterator
from collections.abc import Sequence
from contextlib import asynccontextmanager
from contextlib import contextmanager

from dishka import AsyncContainer
from dishka import Container
from dishka import Provider

from application.persistence.di import ApplicationPersistenceDIProvider
from application.projections.workflow_outputs.di import (
    WorkflowOutputProjectionDIProvider,
)
from application.services.di import AppServicesDIProvider
from config.settings import Settings
from core.bootstrap.app_container import build_app_container
from core.bootstrap.app_container import build_async_app_container
from core.bootstrap.workflow_providers import WorkflowInfrastructureProvider
from core.llm.di import CoreLLMsDIProvider
from core.storage.di import CoreStorageDIProvider
from core.storage.di import InMemoryCoreStorageDIProvider
from core.telemetry.emitters.bootstrap_configuration_telemetry import (
    emergency_log_configuration_failure,
)
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapConfig
from integration.clients.di import IntegrationClientsDIProvider
from integration.providers.backtesting.di import BacktestingProvidersDIProvider
from integration.providers.di import BacktestDataDIProvider
from integration.providers.di import BacktestEventsDIProvider
from integration.providers.di import BacktestMacroDIProvider
from integration.providers.di import BacktestNewsDIProvider
from integration.providers.di import BacktestPortfolioDIProvider
from integration.providers.di import BacktestPostgresDataDIProvider
from integration.providers.di import BacktestSentimentDIProvider
from integration.providers.di import IntegrationProvidersDIProvider
from integration.providers.di import LiveDataDIProvider
from integration.providers.di import LiveEventsDIProvider
from integration.providers.di import LiveMacroDIProvider
from integration.providers.di import LiveNewsDIProvider
from integration.providers.di import LivePortfolioDIProvider
from integration.providers.di import LiveSentimentDIProvider
from intelligence.analysts.di import IntelligenceAnalystsDIProvider
from intelligence.attribution.di import IntelligenceAttributionDIProvider
from intelligence.di import IntelligenceDIProvider
from intelligence.execution.di import IntelligenceExecutionDIProvider
from intelligence.portfolio.di import IntelligencePortfolioDIProvider
from intelligence.research.di import IntelligenceResearchDIProvider
from intelligence.risk.di import IntelligenceRiskDIProvider
from intelligence.strategy.di import IntelligenceStrategyDIProvider


def _base_providers(
    settings: Settings,
    *,
    storage_provider: Provider,
    workflow_provider: WorkflowInfrastructureProvider | None = None,
) -> list[Provider]:
    providers: list[Provider] = [
        workflow_provider or WorkflowInfrastructureProvider(),
        AppServicesDIProvider(),
        ApplicationPersistenceDIProvider(),
        WorkflowOutputProjectionDIProvider(),
        BacktestingProvidersDIProvider(),
        CoreLLMsDIProvider(),
        storage_provider,
        IntegrationClientsDIProvider(),
        IntegrationProvidersDIProvider(),
        IntelligenceDIProvider(),
        IntelligenceAnalystsDIProvider(),
        IntelligenceAttributionDIProvider(),
        IntelligenceExecutionDIProvider(),
        IntelligencePortfolioDIProvider(),
        IntelligenceResearchDIProvider(),
        IntelligenceRiskDIProvider(),
        IntelligenceStrategyDIProvider(),
    ]
    providers.extend(_selected_integration_providers(settings))
    return providers


def _selected_integration_providers(settings: Settings) -> tuple[Provider, ...]:
    return (
        _select_provider(
            setting_name="MACRO_PROVIDER",
            selected=settings.MACRO_PROVIDER,
            candidates={
                settings.LIVE_MACRO_PROVIDER: LiveMacroDIProvider,
                settings.BACKTEST_MACRO_PROVIDER: BacktestMacroDIProvider,
            },
        ),
        _select_provider(
            setting_name="MARKET_DATA_PROVIDER",
            selected=settings.MARKET_DATA_PROVIDER,
            candidates={
                settings.LIVE_DATA_PROVIDER: LiveDataDIProvider,
                settings.BACKTEST_DATA_PROVIDER: BacktestDataDIProvider,
                settings.BACKTEST_POSTGRES_DATA_PROVIDER: BacktestPostgresDataDIProvider,
            },
        ),
        _select_provider(
            setting_name="MARKET_EVENTS_PROVIDER",
            selected=settings.MARKET_EVENTS_PROVIDER,
            candidates={
                settings.LIVE_EVENTS_PROVIDER: LiveEventsDIProvider,
                settings.BACKTEST_EVENTS_PROVIDER: BacktestEventsDIProvider,
            },
        ),
        _select_provider(
            setting_name="NEWS_PROVIDER",
            selected=settings.NEWS_PROVIDER,
            candidates={
                settings.LIVE_NEWS_PROVIDER: LiveNewsDIProvider,
                settings.BACKTEST_NEWS_PROVIDER: BacktestNewsDIProvider,
            },
        ),
        _select_provider(
            setting_name="PORTFOLIO_PROVIDER",
            selected=settings.PORTFOLIO_PROVIDER,
            candidates={
                settings.LIVE_PORTFOLIO_PROVIDER: LivePortfolioDIProvider,
                settings.BACKTEST_PORTFOLIO_PROVIDER: BacktestPortfolioDIProvider,
            },
        ),
        _select_provider(
            setting_name="SENTIMENT_PROVIDER",
            selected=settings.SENTIMENT_PROVIDER,
            candidates={
                settings.LIVE_SENTIMENT_PROVIDER: LiveSentimentDIProvider,
                settings.BACKTEST_SENTIMENT_PROVIDER: BacktestSentimentDIProvider,
            },
        ),
    )


def _select_provider(
    *,
    setting_name: str,
    selected: str,
    candidates: dict[str, type[Provider]],
) -> Provider:
    provider_type = candidates.get(selected)
    if provider_type is None:
        error = ValueError(f"Invalid {setting_name} value.")
        emergency_log_configuration_failure(
            component="integration_provider_selection",
            invalid_setting_names=(setting_name,),
            error=error,
            details={"provider_setting": setting_name},
        )
        raise error
    return provider_type()


def get_di_container(
    settings: Settings | None = None,
    *,
    workflow_provider: WorkflowInfrastructureProvider | None = None,
    extra_providers: Sequence[Provider] = (),
) -> Container:
    """Build the existing synchronous application container."""

    resolved_settings = settings or Settings()
    providers = _base_providers(
        resolved_settings,
        storage_provider=InMemoryCoreStorageDIProvider(),
        workflow_provider=workflow_provider,
    )
    providers.extend(extra_providers)
    return build_app_container(
        *providers,
        include_workflow_provider=False,
        context={Settings: resolved_settings},
        skip_validation=True,
    )


@contextmanager
def application_sync_request_scope(
    settings: Settings | None = None,
    *,
    workflow_config: WorkflowBootstrapConfig | None = None,
) -> Iterator[Container]:
    """Own one canonical synchronous application container and request scope."""

    workflow_provider = WorkflowInfrastructureProvider(config=workflow_config)
    container = get_di_container(
        settings,
        workflow_provider=workflow_provider,
    )
    try:
        with container() as request_container:
            workflow_provider.bind_di_container(request_container)
            yield request_container
    finally:
        container.close()


def _rag_providers() -> tuple[Provider, ...]:
    from application.observability.di import ApplicationObservabilityDIProvider
    from application.rag.di import RagApplicationDIProvider
    from core.storage.rag_di import RagPersistenceDIProvider
    from integration.clients.rag.di import RagClientsDIProvider
    from integration.providers.rag.di import RagProvidersDIProvider

    return (
        RagPersistenceDIProvider(),
        RagClientsDIProvider(),
        RagProvidersDIProvider(),
        ApplicationObservabilityDIProvider(),
        RagApplicationDIProvider(),
    )


def get_async_di_container(
    settings: Settings | None = None,
    *,
    workflow_provider: WorkflowInfrastructureProvider | None = None,
    extra_providers: Sequence[Provider] = (),
) -> AsyncContainer:
    """Build the canonical async application container, including RAG resources."""

    resolved_settings = settings or Settings()
    providers = _base_providers(
        resolved_settings,
        storage_provider=CoreStorageDIProvider(),
        workflow_provider=workflow_provider,
    )
    providers.extend(_rag_providers())
    providers.extend(extra_providers)
    return build_async_app_container(
        *providers,
        include_workflow_provider=False,
        context={Settings: resolved_settings},
        skip_validation=True,
    )


@asynccontextmanager
async def application_request_scope(
    settings: Settings | None = None,
) -> AsyncIterator[AsyncContainer]:
    """Own one canonical async application container and request scope."""

    workflow_provider = WorkflowInfrastructureProvider()
    container = get_async_di_container(
        settings,
        workflow_provider=workflow_provider,
    )
    workflow_provider.bind_di_container(container)
    try:
        async with container() as request_container:
            yield request_container
    finally:
        await container.close()
