from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence.attribution import AttributionPersistenceFilters
from application.persistence.attribution import AttributionPersistenceService
from application.persistence.attribution import (
    RecommendationAttributionPersistenceFilters,
)
from application.persistence.attribution import SignalAttributionPersistenceFilters
from core.storage.persistence.attribution import AttributionPersistenceBundle
from core.storage.persistence.attribution import AttributionPersistenceResult
from core.storage.persistence.attribution import AttributionRecord
from core.storage.persistence.attribution import RecommendationAttributionRecord
from core.storage.persistence.attribution import SignalAttributionRecord
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity


class FakeAttributionRepository:
    def __init__(
        self,
        *,
        attributions: Sequence[AttributionRecord] = (),
        signal_attributions: Sequence[SignalAttributionRecord] = (),
        recommendation_attributions: Sequence[RecommendationAttributionRecord] = (),
    ) -> None:
        self.bundle: AttributionPersistenceBundle | None = None
        self.attribution_records = tuple(attributions)
        self.signal_attribution_records = tuple(signal_attributions)
        self.recommendation_attribution_records = tuple(recommendation_attributions)
        self.attribution_filters: dict[str, str | datetime | None] | None = None
        self.signal_attribution_filters: dict[str, str | datetime | None] | None = None
        self.recommendation_attribution_filters: (
            dict[
                str,
                str | datetime | None,
            ]
            | None
        ) = None
        self.persisted_attribution: AttributionRecord | None = None
        self.persisted_signal_attribution: SignalAttributionRecord | None = None
        self.persisted_recommendation_attribution: (
            RecommendationAttributionRecord | None
        ) = None
        self.attribution_id: str | None = None
        self.signal_attribution_id: str | None = None
        self.recommendation_attribution_id: str | None = None

    async def persist_attribution_bundle(
        self,
        bundle: AttributionPersistenceBundle,
    ) -> AttributionPersistenceResult:
        self.bundle = bundle
        return AttributionPersistenceResult.succeeded(
            primary_record_id=_primary_record_id(bundle),
            records_persisted=(
                len(bundle.attribution_records)
                + len(bundle.signal_attributions)
                + len(bundle.recommendation_attributions)
            ),
        )

    async def persist_attribution(
        self,
        attribution: AttributionRecord,
    ) -> AttributionPersistenceResult:
        self.persisted_attribution = attribution
        return AttributionPersistenceResult.succeeded(
            primary_record_id=attribution.attribution_id,
        )

    async def persist_signal_attribution(
        self,
        attribution: SignalAttributionRecord,
    ) -> AttributionPersistenceResult:
        self.persisted_signal_attribution = attribution
        return AttributionPersistenceResult.succeeded(
            primary_record_id=attribution.signal_attribution_id,
        )

    async def persist_recommendation_attribution(
        self,
        attribution: RecommendationAttributionRecord,
    ) -> AttributionPersistenceResult:
        self.persisted_recommendation_attribution = attribution
        return AttributionPersistenceResult.succeeded(
            primary_record_id=attribution.recommendation_attribution_id,
        )

    async def get_attribution(
        self,
        attribution_id: str,
    ) -> AttributionRecord | None:
        self.attribution_id = attribution_id
        return self.attribution_records[0] if self.attribution_records else None

    async def get_signal_attribution(
        self,
        signal_attribution_id: str,
    ) -> SignalAttributionRecord | None:
        self.signal_attribution_id = signal_attribution_id
        return (
            self.signal_attribution_records[0]
            if self.signal_attribution_records
            else None
        )

    async def get_recommendation_attribution(
        self,
        recommendation_attribution_id: str,
    ) -> RecommendationAttributionRecord | None:
        self.recommendation_attribution_id = recommendation_attribution_id
        return (
            self.recommendation_attribution_records[0]
            if self.recommendation_attribution_records
            else None
        )

    async def list_attributions(
        self,
        *,
        target_record_type: str | None = None,
        target_record_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AttributionRecord]:
        self.attribution_filters = _attribution_filters_dict(
            target_record_type=target_record_type,
            target_record_id=target_record_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            start=start,
            end=end,
        )
        return self.attribution_records

    async def list_signal_attributions(
        self,
        *,
        signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[SignalAttributionRecord]:
        self.signal_attribution_filters = _scoped_filters_dict(
            signal_id=signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        )
        return self.signal_attribution_records

    async def list_recommendation_attributions(
        self,
        *,
        recommendation_id: str | None = None,
        signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[RecommendationAttributionRecord]:
        self.recommendation_attribution_filters = _recommendation_filters_dict(
            recommendation_id=recommendation_id,
            signal_id=signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        )
        return self.recommendation_attribution_records


@pytest.mark.asyncio
async def test_attribution_persistence_service_persists_existing_bundle() -> None:
    repository = FakeAttributionRepository()
    service = AttributionPersistenceService(repository)
    bundle = _bundle()

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 3
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_attribution_persistence_service_builds_typed_bundle() -> None:
    repository = FakeAttributionRepository()
    service = AttributionPersistenceService(repository)

    result = await service.persist_records(
        attributions=(_attribution(),),
        signal_attributions=(_signal_attribution(),),
        recommendation_attributions=(_recommendation_attribution(),),
    )

    assert result.success is True
    assert repository.bundle is not None
    assert repository.bundle.attribution_records[0].explanation == _full_explanation()
    assert repository.bundle.signal_attributions[0].signal_id == "agent-signal-1"
    assert (
        repository.bundle.recommendation_attributions[0].recommendation_id
        == "recommendation-1"
    )


@pytest.mark.asyncio
async def test_attribution_persistence_service_delegates_individual_persist_methods() -> (
    None
):
    repository = FakeAttributionRepository()
    service = AttributionPersistenceService(repository)

    attribution_result = await service.persist_attribution(_attribution())
    signal_result = await service.persist_signal_attribution(_signal_attribution())
    recommendation_result = await service.persist_recommendation_attribution(
        _recommendation_attribution()
    )

    assert attribution_result.primary_record_id == "attribution-1"
    assert signal_result.primary_record_id == "signal-attribution-1"
    assert recommendation_result.primary_record_id == "recommendation-attribution-1"
    assert repository.persisted_attribution is not None
    assert repository.persisted_signal_attribution is not None
    assert repository.persisted_recommendation_attribution is not None


@pytest.mark.asyncio
async def test_attribution_persistence_service_delegates_get_methods() -> None:
    repository = FakeAttributionRepository(
        attributions=(_attribution(),),
        signal_attributions=(_signal_attribution(),),
        recommendation_attributions=(_recommendation_attribution(),),
    )
    service = AttributionPersistenceService(repository)

    attribution = await service.get_attribution("attribution-1")
    signal_attribution = await service.get_signal_attribution("signal-attribution-1")
    recommendation_attribution = await service.get_recommendation_attribution(
        "recommendation-attribution-1"
    )

    assert attribution is not None
    assert signal_attribution is not None
    assert recommendation_attribution is not None
    assert repository.attribution_id == "attribution-1"
    assert repository.signal_attribution_id == "signal-attribution-1"
    assert repository.recommendation_attribution_id == "recommendation-attribution-1"


@pytest.mark.asyncio
async def test_attribution_persistence_service_uses_typed_filters() -> None:
    repository = FakeAttributionRepository(
        attributions=(_attribution(),),
        signal_attributions=(_signal_attribution(),),
        recommendation_attributions=(_recommendation_attribution(),),
    )
    service = AttributionPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)

    attributions = await service.list_attributions(
        AttributionPersistenceFilters(
            target_record_type=" recommendation ",
            target_record_id=" recommendation-1 ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            agent_name=" StrategySynthesisAgent ",
            agent_type=" strategy ",
            start=start,
            end=end,
        )
    )
    signal_attributions = await service.list_signal_attributions(
        SignalAttributionPersistenceFilters(
            signal_id=" agent-signal-1 ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            agent_name=" TechnicalAgent ",
            agent_type=" technical ",
            symbol=" spy ",
            universe=" us_equities ",
            start=start,
            end=end,
        )
    )
    recommendation_attributions = await service.list_recommendation_attributions(
        RecommendationAttributionPersistenceFilters(
            recommendation_id=" recommendation-1 ",
            signal_id=" agent-signal-1 ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            agent_name=" PortfolioManagerAgent ",
            agent_type=" portfolio ",
            symbol=" qqq ",
            universe=" us_equities ",
            start=start,
            end=end,
        )
    )

    assert len(attributions) == 1
    assert len(signal_attributions) == 1
    assert len(recommendation_attributions) == 1
    assert repository.attribution_filters == {
        "target_record_type": "recommendation",
        "target_record_id": "recommendation-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "agent_name": "StrategySynthesisAgent",
        "agent_type": "strategy",
        "start": start,
        "end": end,
    }
    assert repository.signal_attribution_filters == {
        "signal_id": "agent-signal-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "agent_name": "TechnicalAgent",
        "agent_type": "technical",
        "symbol": "SPY",
        "universe": "us_equities",
        "start": start,
        "end": end,
    }
    assert repository.recommendation_attribution_filters == {
        "recommendation_id": "recommendation-1",
        "signal_id": "agent-signal-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "agent_name": "PortfolioManagerAgent",
        "agent_type": "portfolio",
        "symbol": "QQQ",
        "universe": "us_equities",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_attribution_persistence_service_uses_default_filters() -> None:
    repository = FakeAttributionRepository(
        attributions=(_attribution(),),
        signal_attributions=(_signal_attribution(),),
        recommendation_attributions=(_recommendation_attribution(),),
    )
    service = AttributionPersistenceService(repository)

    attributions = await service.list_attributions()
    signal_attributions = await service.list_signal_attributions()
    recommendation_attributions = await service.list_recommendation_attributions()

    assert len(attributions) == 1
    assert len(signal_attributions) == 1
    assert len(recommendation_attributions) == 1
    assert repository.attribution_filters == _empty_attribution_filters()
    assert repository.signal_attribution_filters == _empty_scoped_filters()
    assert (
        repository.recommendation_attribution_filters == _empty_recommendation_filters()
    )


@pytest.mark.parametrize(
    "filters",
    [
        AttributionPersistenceFilters,
        SignalAttributionPersistenceFilters,
        RecommendationAttributionPersistenceFilters,
    ],
)
def test_attribution_time_window_filters_require_ordered_bounds(
    filters: type[
        AttributionPersistenceFilters
        | SignalAttributionPersistenceFilters
        | RecommendationAttributionPersistenceFilters
    ],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            start=start,
            end=end,
        )


def _bundle() -> AttributionPersistenceBundle:
    return AttributionPersistenceBundle(
        attribution_records=(_attribution(),),
        signal_attributions=(_signal_attribution(),),
        recommendation_attributions=(_recommendation_attribution(),),
    )


def _attribution() -> AttributionRecord:
    return AttributionRecord(
        attribution_id="attribution-1",
        target_record=PersistenceRecordIdentity(
            record_type="recommendation",
            record_id="recommendation-1",
        ),
        attribution_type="recommendation_support",
        contribution_type="positive",
        contribution_score=0.42,
        confidence=0.88,
        explanation=_full_explanation(),
        timestamp=_timestamp(),
        lineage=_lineage(),
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        source_records=(_agent_signal_identity(),),
        metadata={"source": "unit-test"},
    )


def _signal_attribution() -> SignalAttributionRecord:
    return SignalAttributionRecord(
        signal_attribution_id="signal-attribution-1",
        signal_id="agent-signal-1",
        attribution_type="signal_evidence",
        contribution_type="positive",
        contribution_score=0.55,
        confidence=0.86,
        explanation=_full_explanation(),
        timestamp=_timestamp(),
        lineage=_lineage(),
        signal_type="technical",
        agent_name="TechnicalAgent",
        agent_type="technical",
        symbol="spy",
        universe="us_equities",
        source_records=(
            PersistenceRecordIdentity(
                record_type="market_context_snapshot",
                record_id="market-1",
            ),
        ),
        metadata={"source": "unit-test"},
    )


def _recommendation_attribution() -> RecommendationAttributionRecord:
    return RecommendationAttributionRecord(
        recommendation_attribution_id="recommendation-attribution-1",
        recommendation_id="recommendation-1",
        attribution_type="recommendation_evidence",
        contribution_type="positive",
        contribution_score=0.61,
        confidence=0.91,
        explanation=_full_explanation(),
        timestamp=_timestamp(),
        lineage=_lineage(),
        signal_id="agent-signal-1",
        agent_name="PortfolioManagerAgent",
        agent_type="portfolio",
        symbol="qqq",
        universe="us_equities",
        source_records=(_agent_signal_identity(),),
        metadata={"source": "unit-test"},
    )


def _agent_signal_identity() -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type="agent_signal",
        record_id="agent-signal-1",
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="attribution_node",
    )


def _attribution_filters_dict(
    *,
    target_record_type: str | None,
    target_record_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    agent_name: str | None,
    agent_type: str | None,
    start: datetime | None,
    end: datetime | None,
) -> dict[str, str | datetime | None]:
    return {
        "target_record_type": target_record_type,
        "target_record_id": target_record_id,
        "workflow_name": workflow_name,
        "execution_id": execution_id,
        "agent_name": agent_name,
        "agent_type": agent_type,
        "start": start,
        "end": end,
    }


def _scoped_filters_dict(
    *,
    signal_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    agent_name: str | None,
    agent_type: str | None,
    symbol: str | None,
    universe: str | None,
    start: datetime | None,
    end: datetime | None,
) -> dict[str, str | datetime | None]:
    return {
        "signal_id": signal_id,
        "workflow_name": workflow_name,
        "execution_id": execution_id,
        "agent_name": agent_name,
        "agent_type": agent_type,
        "symbol": symbol,
        "universe": universe,
        "start": start,
        "end": end,
    }


def _recommendation_filters_dict(
    *,
    recommendation_id: str | None,
    signal_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    agent_name: str | None,
    agent_type: str | None,
    symbol: str | None,
    universe: str | None,
    start: datetime | None,
    end: datetime | None,
) -> dict[str, str | datetime | None]:
    filters = _scoped_filters_dict(
        signal_id=signal_id,
        workflow_name=workflow_name,
        execution_id=execution_id,
        agent_name=agent_name,
        agent_type=agent_type,
        symbol=symbol,
        universe=universe,
        start=start,
        end=end,
    )
    return {
        "recommendation_id": recommendation_id,
        **filters,
    }


def _empty_attribution_filters() -> dict[str, str | datetime | None]:
    return _attribution_filters_dict(
        target_record_type=None,
        target_record_id=None,
        workflow_name=None,
        execution_id=None,
        agent_name=None,
        agent_type=None,
        start=None,
        end=None,
    )


def _empty_scoped_filters() -> dict[str, str | datetime | None]:
    return _scoped_filters_dict(
        signal_id=None,
        workflow_name=None,
        execution_id=None,
        agent_name=None,
        agent_type=None,
        symbol=None,
        universe=None,
        start=None,
        end=None,
    )


def _empty_recommendation_filters() -> dict[str, str | datetime | None]:
    return _recommendation_filters_dict(
        recommendation_id=None,
        signal_id=None,
        workflow_name=None,
        execution_id=None,
        agent_name=None,
        agent_type=None,
        symbol=None,
        universe=None,
        start=None,
        end=None,
    )


def _primary_record_id(
    bundle: AttributionPersistenceBundle,
) -> str:
    if bundle.attribution_records:
        return bundle.attribution_records[0].attribution_id
    if bundle.signal_attributions:
        return bundle.signal_attributions[0].signal_attribution_id
    if bundle.recommendation_attributions:
        return bundle.recommendation_attributions[0].recommendation_attribution_id
    return "empty-attribution-persistence-bundle"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)


def _full_explanation() -> str:
    return ("Full attribution explanation must not be truncated. " * 200).strip()
