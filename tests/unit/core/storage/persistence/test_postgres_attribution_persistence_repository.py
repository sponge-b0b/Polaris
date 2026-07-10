from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.attribution import AttributionRecordModel
from core.database.models.attribution import RecommendationAttributionModel
from core.database.models.attribution import SignalAttributionModel
from core.storage.persistence.attribution import AttributionPersistenceBundle
from core.storage.persistence.attribution import AttributionRecord
from core.storage.persistence.attribution import RecommendationAttributionRecord
from core.storage.persistence.attribution import SignalAttributionRecord
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.repositories.postgres_attribution_persistence_repository import (
    PostgresAttributionPersistenceRepository,
)
from core.storage.persistence.serializers.attribution_persistence_serializer import (
    AttributionPersistenceSerializer,
)


class FakeScalarResult:
    def __init__(
        self,
        rows: Sequence[object],
    ) -> None:
        self._rows = list(rows)

    def all(
        self,
    ) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
    ) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None

        return self._rows[0]

    def scalars(
        self,
    ) -> FakeScalarResult:
        return FakeScalarResult(
            self._rows,
        )


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)

        if self.error is not None:
            raise self.error

        return self.result

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_attribution_bundle_upserts_without_deleting_siblings() -> None:
    session = FakeAsyncSession()
    repository = PostgresAttributionPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_attribution_bundle(_bundle())

    compiled = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in session.executed
    ]

    assert result.success is True
    assert result.primary_record_id == "attribution-1"
    assert result.records_persisted == 3
    assert session.commits == 1
    assert len(session.executed) == 3
    assert "attribution_records" in compiled[0]
    assert "ON CONFLICT" in compiled[0]
    assert "source_records" in compiled[0]
    assert "signal_attribution" in compiled[1]
    assert "ON CONFLICT" in compiled[1]
    assert "recommendation_attribution" in compiled[2]
    assert "ON CONFLICT" in compiled[2]


@pytest.mark.asyncio
async def test_persist_attribution_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresAttributionPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_attribution(_attribution())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_attribution_returns_typed_record() -> None:
    model = AttributionRecordModel(
        **AttributionPersistenceSerializer.attribution_values(_attribution())
    )
    repository = PostgresAttributionPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([model])))
    )

    record = await repository.get_attribution("attribution-1")

    assert record is not None
    assert record.attribution_id == "attribution-1"
    assert record.target_record.record_id == "recommendation-1"
    assert record.explanation == _full_explanation()
    assert record.source_records[0].record_type == "agent_signal"


@pytest.mark.asyncio
async def test_get_signal_attribution_returns_typed_record() -> None:
    model = SignalAttributionModel(
        **AttributionPersistenceSerializer.signal_attribution_values(
            _signal_attribution()
        )
    )
    repository = PostgresAttributionPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([model])))
    )

    record = await repository.get_signal_attribution("signal-attribution-1")

    assert record is not None
    assert record.signal_attribution_id == "signal-attribution-1"
    assert record.signal_id == "agent-signal-1"
    assert record.symbol == "SPY"
    assert record.explanation == _full_explanation()


@pytest.mark.asyncio
async def test_get_recommendation_attribution_returns_typed_record() -> None:
    model = RecommendationAttributionModel(
        **AttributionPersistenceSerializer.recommendation_attribution_values(
            _recommendation_attribution()
        )
    )
    repository = PostgresAttributionPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([model])))
    )

    record = await repository.get_recommendation_attribution(
        "recommendation-attribution-1"
    )

    assert record is not None
    assert record.recommendation_attribution_id == "recommendation-attribution-1"
    assert record.recommendation_id == "recommendation-1"
    assert record.signal_id == "agent-signal-1"
    assert record.explanation == _full_explanation()


@pytest.mark.asyncio
async def test_list_methods_return_ordered_typed_records_with_filters() -> None:
    attribution_model = AttributionRecordModel(
        **AttributionPersistenceSerializer.attribution_values(_attribution())
    )
    signal_model = SignalAttributionModel(
        **AttributionPersistenceSerializer.signal_attribution_values(
            _signal_attribution()
        )
    )
    recommendation_model = RecommendationAttributionModel(
        **AttributionPersistenceSerializer.recommendation_attribution_values(
            _recommendation_attribution()
        )
    )

    attributions = await PostgresAttributionPersistenceRepository(
        cast(
            AsyncSession,
            FakeAsyncSession(result=FakeExecuteResult([attribution_model])),
        )
    ).list_attributions(
        target_record_type="recommendation",
        target_record_id="recommendation-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        start=_timestamp(),
        end=_timestamp(),
    )
    signal_attributions = await PostgresAttributionPersistenceRepository(
        cast(
            AsyncSession,
            FakeAsyncSession(result=FakeExecuteResult([signal_model])),
        )
    ).list_signal_attributions(
        signal_id="agent-signal-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        agent_name="TechnicalAgent",
        agent_type="technical",
        symbol="spy",
        universe="us_equities",
        start=_timestamp(),
        end=_timestamp(),
    )
    recommendation_attributions = await PostgresAttributionPersistenceRepository(
        cast(
            AsyncSession,
            FakeAsyncSession(result=FakeExecuteResult([recommendation_model])),
        )
    ).list_recommendation_attributions(
        recommendation_id="recommendation-1",
        signal_id="agent-signal-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        agent_name="PortfolioManagerAgent",
        agent_type="portfolio",
        symbol="qqq",
        universe="us_equities",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert attributions[0].attribution_id == "attribution-1"
    assert signal_attributions[0].signal_attribution_id == "signal-attribution-1"
    assert (
        recommendation_attributions[0].recommendation_attribution_id
        == "recommendation-attribution-1"
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


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)


def _full_explanation() -> str:
    return ("Full attribution explanation must not be truncated. " * 200).strip()
