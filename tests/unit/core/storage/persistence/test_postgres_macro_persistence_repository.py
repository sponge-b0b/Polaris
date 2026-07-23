from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.macro import (
    EconomicCalendarEventModel,
    MacroObservationModel,
    MacroRegimeSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.macro import (
    EconomicCalendarEventRecord,
    MacroObservationRecord,
    MacroPersistenceBundle,
    MacroRegimeSnapshotRecord,
)
from core.storage.persistence.repositories.postgres_macro_persistence_repository import (  # noqa: E501 - canonical module path
    PostgresMacroPersistenceRepository,
)
from core.storage.persistence.serializers.macro_persistence_serializer import (
    MacroPersistenceSerializer,
)


class FakeScalarResult:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(self, rows: Sequence[object] | None = None) -> None:
        self._rows = list(rows or [])

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._rows)


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

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        if self.error is not None:
            raise self.error
        return self.result

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_macro_bundle_upserts_facts_and_inserts_snapshots() -> None:
    session = FakeAsyncSession()
    repository = PostgresMacroPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_macro_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.primary_record_id == "observation-1"
    assert result.records_persisted == 3
    assert session.commits == 1
    assert len(session.executed) == 3
    assert "macro_observations" in compiled[0]
    assert "ON CONFLICT" in compiled[0]
    assert "indicator_name, observation_timestamp, source, region" in compiled[0]
    assert "macro_regime_snapshots" in compiled[1]
    assert "ON CONFLICT" not in compiled[1]
    assert "economic_calendar_events" in compiled[2]
    assert "ON CONFLICT" in compiled[2]
    assert "event_name, event_timestamp, source, region" in compiled[2]


@pytest.mark.asyncio
async def test_macro_idempotency_review_source_key_facts_and_append_snapshots() -> None:
    session = FakeAsyncSession()
    repository = PostgresMacroPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_macro_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert len(compiled) == 3
    assert "macro_observations" in compiled[0]
    assert (
        "ON CONFLICT (indicator_name, observation_timestamp, source, region)"
        in compiled[0]
    )
    assert "DO UPDATE" in compiled[0]
    assert "macro_regime_snapshots" in compiled[1]
    assert "ON CONFLICT" not in compiled[1]
    assert "economic_calendar_events" in compiled[2]
    assert "ON CONFLICT (event_name, event_timestamp, source, region)" in compiled[2]
    assert "DO UPDATE" in compiled[2]
    assert all("DELETE" not in statement.upper() for statement in compiled)


@pytest.mark.asyncio
async def test_persist_macro_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresMacroPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_macro_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_list_macro_fact_records_returns_typed_records() -> None:
    observation_model = MacroObservationModel(
        **MacroPersistenceSerializer.observation_values(_observation())
    )
    calendar_model = EconomicCalendarEventModel(
        **MacroPersistenceSerializer.calendar_event_values(_calendar_event())
    )

    observations = await PostgresMacroPersistenceRepository(
        cast(
            AsyncSession,
            FakeAsyncSession(result=FakeExecuteResult([observation_model])),
        )
    ).list_observations(
        indicator_name="CPI YoY",
        indicator_category="inflation",
        source="fred",
        region="US",
        start=_timestamp(),
        end=_timestamp(),
    )
    calendar_events = await PostgresMacroPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([calendar_model])))
    ).list_calendar_events(
        event_name="CPI Release",
        event_type="inflation",
        source="econoday",
        region="US",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert observations[0].observation_id == "observation-1"
    assert observations[0].indicator_name == "CPI YoY"
    assert observations[0].metadata == {"series_id": "CPIAUCSL"}
    assert calendar_events[0].event_id == "event-1"
    assert calendar_events[0].event_name == "CPI Release"
    assert calendar_events[0].metadata == {"calendar_id": "cpi-2026-05"}


@pytest.mark.asyncio
async def test_list_macro_regime_snapshots_returns_typed_records() -> None:
    regime_model = MacroRegimeSnapshotModel(
        **MacroPersistenceSerializer.regime_snapshot_values(_regime())
    )

    regimes = await PostgresMacroPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([regime_model])))
    ).list_regime_snapshots(
        region="US",
        source="macro-service",
        macro_regime="late_cycle",
        economic_regime="expansion",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert regimes[0].regime_snapshot_id == "regime-1"
    assert regimes[0].macro_regime == "late_cycle"
    assert regimes[0].yield_curve_regime == "inverted"
    assert regimes[0].outputs == {"summary": "late-cycle macro regime"}


def _bundle() -> MacroPersistenceBundle:
    return MacroPersistenceBundle(
        observations=(_observation(),),
        regime_snapshots=(_regime(),),
        calendar_events=(_calendar_event(),),
    )


def _observation() -> MacroObservationRecord:
    return MacroObservationRecord(
        observation_id="observation-1",
        indicator_name="CPI YoY",
        observation_timestamp=_timestamp(),
        source="fred",
        value=3.2,
        indicator_category="inflation",
        region="US",
        unit="percent",
        frequency="monthly",
        release_timestamp=_timestamp(),
        vintage_timestamp=_timestamp(),
        lineage=_lineage(),
        metadata={"series_id": "CPIAUCSL"},
    )


def _regime() -> MacroRegimeSnapshotRecord:
    return MacroRegimeSnapshotRecord(
        regime_snapshot_id="regime-1",
        timestamp=_timestamp(),
        source="macro-service",
        region="US",
        inflation_regime="disinflation",
        liquidity_regime="tightening",
        growth_regime="resilient",
        fed_stance="restrictive",
        yield_curve_regime="inverted",
        macro_regime="late_cycle",
        economic_regime="expansion",
        inflation_score=0.3,
        liquidity_score=-0.2,
        growth_score=0.5,
        yield_curve_score=-0.6,
        macro_score=0.15,
        risk_score=0.4,
        confidence=0.82,
        inputs={"series": ["CPI", "DGS10"]},
        outputs={"summary": "late-cycle macro regime"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _calendar_event() -> EconomicCalendarEventRecord:
    return EconomicCalendarEventRecord(
        event_id="event-1",
        event_name="CPI Release",
        event_timestamp=_timestamp(),
        source="econoday",
        region="US",
        event_type="inflation",
        importance_score=0.9,
        actual_value=0.2,
        forecast_value=0.3,
        previous_value=0.4,
        surprise_score=-0.2,
        unit="percent",
        currency="USD",
        release_status="released",
        lineage=_lineage(),
        metadata={"calendar_id": "cpi-2026-05"},
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="macro_analysis",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 13, 0, tzinfo=UTC)
