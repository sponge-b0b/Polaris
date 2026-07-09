from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence.macro import EconomicCalendarEventPersistenceFilters
from application.persistence.macro import MacroObservationPersistenceFilters
from application.persistence.macro import MacroPersistenceService
from application.persistence.macro import MacroRegimeSnapshotPersistenceFilters
from core.storage.persistence.macro import EconomicCalendarEventRecord
from core.storage.persistence.macro import MacroObservationRecord
from core.storage.persistence.macro import MacroPersistenceBundle
from core.storage.persistence.macro import MacroPersistenceResult
from core.storage.persistence.macro import MacroRegimeSnapshotRecord


class FakeMacroRepository:
    def __init__(
        self,
        *,
        observations: Sequence[MacroObservationRecord] = (),
        regime_snapshots: Sequence[MacroRegimeSnapshotRecord] = (),
        calendar_events: Sequence[EconomicCalendarEventRecord] = (),
    ) -> None:
        self.bundle: MacroPersistenceBundle | None = None
        self.observations = tuple(observations)
        self.regime_snapshots = tuple(regime_snapshots)
        self.calendar_events = tuple(calendar_events)
        self.observation_filters: dict[str, str | datetime | None] | None = None
        self.regime_filters: dict[str, str | datetime | None] | None = None
        self.calendar_filters: dict[str, str | datetime | None] | None = None

    async def persist_macro_bundle(
        self,
        bundle: MacroPersistenceBundle,
    ) -> MacroPersistenceResult:
        self.bundle = bundle
        return MacroPersistenceResult.succeeded(
            primary_record_id=_primary_record_id(bundle),
            records_persisted=(
                len(bundle.observations)
                + len(bundle.regime_snapshots)
                + len(bundle.calendar_events)
            ),
        )

    async def list_observations(
        self,
        *,
        indicator_name: str | None = None,
        indicator_category: str | None = None,
        source: str | None = None,
        region: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MacroObservationRecord]:
        self.observation_filters = {
            "indicator_name": indicator_name,
            "indicator_category": indicator_category,
            "source": source,
            "region": region,
            "start": start,
            "end": end,
        }
        return self.observations

    async def list_regime_snapshots(
        self,
        *,
        region: str | None = None,
        source: str | None = None,
        macro_regime: str | None = None,
        economic_regime: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[MacroRegimeSnapshotRecord]:
        self.regime_filters = {
            "region": region,
            "source": source,
            "macro_regime": macro_regime,
            "economic_regime": economic_regime,
            "start": start,
            "end": end,
        }
        return self.regime_snapshots

    async def list_calendar_events(
        self,
        *,
        event_name: str | None = None,
        event_type: str | None = None,
        source: str | None = None,
        region: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[EconomicCalendarEventRecord]:
        self.calendar_filters = {
            "event_name": event_name,
            "event_type": event_type,
            "source": source,
            "region": region,
            "start": start,
            "end": end,
        }
        return self.calendar_events


@pytest.mark.asyncio
async def test_macro_persistence_service_persists_existing_bundle() -> None:
    repository = FakeMacroRepository()
    service = MacroPersistenceService(repository)
    bundle = _bundle()

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 3
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_macro_persistence_service_builds_typed_bundle() -> None:
    repository = FakeMacroRepository()
    service = MacroPersistenceService(repository)

    result = await service.persist_records(
        observations=(_observation(),),
        regime_snapshots=(_regime_snapshot(),),
        calendar_events=(_calendar_event(),),
    )

    assert result.success is True
    assert repository.bundle is not None
    assert repository.bundle.observations[0].indicator_name == "cpi_yoy"
    assert repository.bundle.regime_snapshots[0].macro_regime == "constructive"
    assert repository.bundle.calendar_events[0].event_name == "CPI Release"


@pytest.mark.asyncio
async def test_macro_persistence_service_uses_typed_filters() -> None:
    repository = FakeMacroRepository(
        observations=(_observation(),),
        regime_snapshots=(_regime_snapshot(),),
        calendar_events=(_calendar_event(),),
    )
    service = MacroPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)

    observations = await service.list_observations(
        MacroObservationPersistenceFilters(
            indicator_name=" cpi_yoy ",
            indicator_category=" inflation ",
            source=" fred ",
            region=" us ",
            start=start,
            end=end,
        )
    )
    regimes = await service.list_regime_snapshots(
        MacroRegimeSnapshotPersistenceFilters(
            region=" us ",
            source=" macro-service ",
            macro_regime=" constructive ",
            economic_regime=" expansion ",
            start=start,
            end=end,
        )
    )
    events = await service.list_calendar_events(
        EconomicCalendarEventPersistenceFilters(
            event_name=" CPI Release ",
            event_type=" inflation ",
            source=" econ-calendar ",
            region=" us ",
            start=start,
            end=end,
        )
    )

    assert len(observations) == 1
    assert len(regimes) == 1
    assert len(events) == 1
    assert repository.observation_filters == {
        "indicator_name": "cpi_yoy",
        "indicator_category": "inflation",
        "source": "fred",
        "region": "us",
        "start": start,
        "end": end,
    }
    assert repository.regime_filters == {
        "region": "us",
        "source": "macro-service",
        "macro_regime": "constructive",
        "economic_regime": "expansion",
        "start": start,
        "end": end,
    }
    assert repository.calendar_filters == {
        "event_name": "CPI Release",
        "event_type": "inflation",
        "source": "econ-calendar",
        "region": "us",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_macro_persistence_service_uses_default_filters() -> None:
    repository = FakeMacroRepository(
        observations=(_observation(),),
        regime_snapshots=(_regime_snapshot(),),
        calendar_events=(_calendar_event(),),
    )
    service = MacroPersistenceService(repository)

    observations = await service.list_observations()
    regimes = await service.list_regime_snapshots()
    events = await service.list_calendar_events()

    assert len(observations) == 1
    assert len(regimes) == 1
    assert len(events) == 1
    assert repository.observation_filters == {
        "indicator_name": None,
        "indicator_category": None,
        "source": None,
        "region": None,
        "start": None,
        "end": None,
    }
    assert repository.regime_filters == {
        "region": None,
        "source": None,
        "macro_regime": None,
        "economic_regime": None,
        "start": None,
        "end": None,
    }
    assert repository.calendar_filters == {
        "event_name": None,
        "event_type": None,
        "source": None,
        "region": None,
        "start": None,
        "end": None,
    }


@pytest.mark.parametrize(
    "filters",
    [
        MacroObservationPersistenceFilters,
        MacroRegimeSnapshotPersistenceFilters,
        EconomicCalendarEventPersistenceFilters,
    ],
)
def test_macro_time_window_filters_require_ordered_bounds(
    filters: type[
        MacroObservationPersistenceFilters
        | MacroRegimeSnapshotPersistenceFilters
        | EconomicCalendarEventPersistenceFilters
    ],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            start=start,
            end=end,
        )


def _bundle() -> MacroPersistenceBundle:
    return MacroPersistenceBundle(
        observations=(_observation(),),
        regime_snapshots=(_regime_snapshot(),),
        calendar_events=(_calendar_event(),),
    )


def _observation() -> MacroObservationRecord:
    return MacroObservationRecord(
        observation_id="macro-observation-1",
        indicator_name="cpi_yoy",
        observation_timestamp=_timestamp(),
        source="fred",
        value=3.2,
        indicator_category="inflation",
        region="us",
        unit="percent",
        frequency="monthly",
        metadata={"series_id": "CPIAUCSL"},
    )


def _regime_snapshot() -> MacroRegimeSnapshotRecord:
    return MacroRegimeSnapshotRecord(
        regime_snapshot_id="macro-regime-1",
        timestamp=_timestamp(),
        source="macro-service",
        region="us",
        inflation_regime="moderating",
        liquidity_regime="neutral",
        growth_regime="expansion",
        fed_stance="higher-for-longer",
        yield_curve_regime="inverted",
        macro_regime="constructive",
        economic_regime="expansion",
        inflation_score=0.2,
        liquidity_score=0.1,
        growth_score=0.4,
        yield_curve_score=-0.2,
        macro_score=0.25,
        risk_score=0.35,
        confidence=0.81,
        inputs={"series": ["cpi_yoy", "fed_funds"]},
        outputs={"summary": "growth remains resilient"},
    )


def _calendar_event() -> EconomicCalendarEventRecord:
    return EconomicCalendarEventRecord(
        event_id="calendar-event-1",
        event_name="CPI Release",
        event_timestamp=_timestamp(),
        source="econ-calendar",
        region="us",
        event_type="inflation",
        importance_score=0.9,
        actual_value=3.2,
        forecast_value=3.3,
        previous_value=3.4,
        surprise_score=0.1,
        unit="percent",
        currency="USD",
        release_status="released",
        metadata={"period": "2026-05"},
    )


def _primary_record_id(
    bundle: MacroPersistenceBundle,
) -> str:
    if bundle.observations:
        return bundle.observations[0].observation_id
    if bundle.regime_snapshots:
        return bundle.regime_snapshots[0].regime_snapshot_id
    if bundle.calendar_events:
        return bundle.calendar_events[0].event_id
    return "empty-macro-persistence-bundle"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
