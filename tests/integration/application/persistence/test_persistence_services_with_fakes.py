from __future__ import annotations

from typing import cast

import pytest

from application.persistence import (
    AgentIntelligencePersistenceService,
    AttributionPersistenceService,
    MacroPersistenceService,
    MarketPersistenceService,
    NewsPersistenceService,
    PortfolioPersistenceService,
    RecommendationPersistenceService,
    ReportPersistenceService,
    SentimentPersistenceService,
    TelemetryPersistenceService,
    WorkflowStateSnapshotPersistenceService,
)
from core.storage.persistence.agent_intelligence import (
    AgentIntelligencePersistenceRepository,
)
from core.storage.persistence.attribution import AttributionPersistenceRepository
from core.storage.persistence.macro import MacroPersistenceRepository
from core.storage.persistence.market import MarketPersistenceRepository
from core.storage.persistence.news import NewsPersistenceRepository
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceRepository
from core.storage.persistence.recommendations import (
    RecommendationPersistenceBundle,
    RecommendationPersistenceRepository,
)
from core.storage.persistence.reports import (
    ReportPersistenceBundle,
    ReportPersistenceRepository,
)
from core.storage.persistence.runtime import RuntimePersistenceRepository
from core.storage.persistence.sentiment import SentimentPersistenceRepository
from core.storage.persistence.telemetry import TelemetryPersistenceRepository
from tests.unit.application.persistence.agent_intelligence import (
    test_agent_intelligence_persistence_service as agent_intelligence_fakes,
)
from tests.unit.application.persistence.attribution import (
    test_attribution_persistence_service as attribution_fakes,
)
from tests.unit.application.persistence.macro import (
    test_macro_persistence_service as macro_fakes,
)
from tests.unit.application.persistence.market import (
    test_market_persistence_service as market_fakes,
)
from tests.unit.application.persistence.news import (
    test_news_persistence_service as news_fakes,
)
from tests.unit.application.persistence.portfolio import (
    test_portfolio_persistence_service as portfolio_fakes,
)
from tests.unit.application.persistence.recommendations import (
    test_recommendation_persistence_service as recommendation_fakes,
)
from tests.unit.application.persistence.reports import (
    test_report_persistence_service as report_fakes,
)
from tests.unit.application.persistence.sentiment import (
    test_sentiment_persistence_service as sentiment_fakes,
)
from tests.unit.application.persistence.telemetry import (
    test_telemetry_persistence_service as telemetry_fakes,
)
from tests.unit.application.persistence.workflow_audit import (
    test_workflow_state_snapshot_persistence_service as workflow_audit_fakes,
)


@pytest.mark.asyncio
async def test_all_application_persistence_services_accept_repository_fakes() -> None:
    """
    Exercise each application persistence service against its repository protocol.

    This is intentionally a cross-domain application integration test: it keeps
    repositories as injected infrastructure dependencies, verifies service
    construction does not rely on locators/global state, and confirms each
    service returns its typed persistence result object.
    """

    agent_intelligence_result = await AgentIntelligencePersistenceService(
        cast(
            AgentIntelligencePersistenceRepository,
            agent_intelligence_fakes.FakeAgentIntelligenceRepository(),
        )
    ).persist_bundle(agent_intelligence_fakes._bundle())
    attribution_result = await AttributionPersistenceService(
        cast(
            AttributionPersistenceRepository,
            attribution_fakes.FakeAttributionRepository(),
        )
    ).persist_bundle(attribution_fakes._bundle())
    macro_result = await MacroPersistenceService(
        cast(
            MacroPersistenceRepository,
            macro_fakes.FakeMacroRepository(),
        )
    ).persist_bundle(macro_fakes._bundle())
    market_result = await MarketPersistenceService(
        cast(
            MarketPersistenceRepository,
            market_fakes.FakeMarketRepository(),
        )
    ).persist_bundle(market_fakes._bundle())
    news_result = await NewsPersistenceService(
        cast(
            NewsPersistenceRepository,
            news_fakes.FakeNewsRepository(),
        )
    ).persist_bundle(news_fakes._bundle())
    portfolio_result = await PortfolioPersistenceService(
        cast(
            PortfolioExpansionPersistenceRepository,
            portfolio_fakes.FakePortfolioExpansionRepository(),
        )
    ).persist_expansion_records(
        position_history=(portfolio_fakes._position_history(),),
        position_latest=(portfolio_fakes._position_latest(),),
        exposure_snapshots=(portfolio_fakes._exposure_snapshot(),),
        risk_snapshots=(portfolio_fakes._risk_snapshot(),),
        allocation_snapshots=(portfolio_fakes._allocation_snapshot(),),
    )
    recommendation_result = await RecommendationPersistenceService(
        cast(
            RecommendationPersistenceRepository,
            recommendation_fakes.FakeRecommendationRepository(),
        )
    ).persist_bundle(
        RecommendationPersistenceBundle(
            recommendation=recommendation_fakes._recommendation(),
            rationales=(recommendation_fakes._rationale(),),
            outcomes=(recommendation_fakes._outcome(),),
            trade_setups=(recommendation_fakes._trade_setup(),),
            watchlist_items=(recommendation_fakes._watchlist_item(),),
        )
    )
    report_result = await ReportPersistenceService(
        cast(
            ReportPersistenceRepository,
            report_fakes.FakeReportRepository(),
        )
    ).persist_bundle(
        ReportPersistenceBundle(
            report=report_fakes._report(),
            sections=(report_fakes._section(),),
            artifacts=(report_fakes._artifact(),),
            versions=(report_fakes._version(),),
            publications=(report_fakes._publication(),),
        )
    )
    sentiment_result = await SentimentPersistenceService(
        cast(
            SentimentPersistenceRepository,
            sentiment_fakes.FakeSentimentRepository(),
        )
    ).persist_bundle(sentiment_fakes._bundle())
    telemetry_result = await TelemetryPersistenceService(
        cast(
            TelemetryPersistenceRepository,
            telemetry_fakes.FakeTelemetryRepository(),
        )
    ).persist_telemetry_bundle(telemetry_fakes._bundle())
    workflow_audit_result = await WorkflowStateSnapshotPersistenceService(
        cast(
            RuntimePersistenceRepository,
            workflow_audit_fakes.FakeRuntimePersistenceRepository(),
        )
    ).persist_snapshot(workflow_audit_fakes._snapshot())

    assert all(
        (
            agent_intelligence_result.success,
            attribution_result.success,
            macro_result.success,
            market_result.success,
            news_result.success,
            portfolio_result.success,
            recommendation_result.success,
            report_result.success,
            sentiment_result.success,
            telemetry_result.success,
            workflow_audit_result.success,
        )
    )
    assert all(
        records_persisted > 0
        for records_persisted in (
            agent_intelligence_result.records_persisted,
            attribution_result.records_persisted,
            macro_result.records_persisted,
            market_result.records_persisted,
            news_result.records_persisted,
            portfolio_result.records_persisted,
            recommendation_result.records_persisted,
            report_result.records_persisted,
            sentiment_result.records_persisted,
            telemetry_result.records_persisted,
            workflow_audit_result.records_persisted,
        )
    )
