from __future__ import annotations

from datetime import datetime
from datetime import timezone

from core.database.models.macro import EconomicCalendarEventModel
from core.database.models.macro import MacroObservationModel
from core.database.models.macro import MacroRegimeSnapshotModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.macro import EconomicCalendarEventRecord
from core.storage.persistence.macro import MacroObservationRecord
from core.storage.persistence.macro import MacroRegimeSnapshotRecord
from core.storage.persistence.serializers.macro_persistence_serializer import (
    MacroPersistenceSerializer,
)


def test_macro_serializer_flattens_observation_record() -> None:
    record = _observation()

    values = MacroPersistenceSerializer.observation_values(record)

    assert values["observation_id"] == "observation-1"
    assert values["indicator_name"] == "CPI YoY"
    assert values["source"] == "fred"
    assert values["value"] == 3.2
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"series_id": "CPIAUCSL"}


def test_macro_serializer_round_trips_observation_record() -> None:
    model = MacroObservationModel(
        **MacroPersistenceSerializer.observation_values(_observation())
    )

    record = MacroPersistenceSerializer.observation_from_model(
        model,
    )

    assert record.observation_id == "observation-1"
    assert record.indicator_name == "CPI YoY"
    assert record.value == 3.2
    assert record.region == "US"
    assert record.lineage.node_name == "macro_analysis"
    assert record.metadata == {"series_id": "CPIAUCSL"}


def test_macro_serializer_round_trips_regime_and_calendar_records() -> None:
    regime_model = MacroRegimeSnapshotModel(
        **MacroPersistenceSerializer.regime_snapshot_values(_regime())
    )
    calendar_model = EconomicCalendarEventModel(
        **MacroPersistenceSerializer.calendar_event_values(_calendar_event())
    )

    regime = MacroPersistenceSerializer.regime_snapshot_from_model(
        regime_model,
    )
    calendar_event = MacroPersistenceSerializer.calendar_event_from_model(
        calendar_model,
    )

    assert regime.regime_snapshot_id == "regime-1"
    assert regime.inflation_regime == "disinflation"
    assert regime.liquidity_regime == "tightening"
    assert regime.growth_regime == "resilient"
    assert regime.fed_stance == "restrictive"
    assert regime.yield_curve_regime == "inverted"
    assert regime.inputs == {"series": ["CPI", "DGS10"]}
    assert regime.outputs == {"summary": "late-cycle macro regime"}
    assert calendar_event.event_id == "event-1"
    assert calendar_event.event_name == "CPI Release"
    assert calendar_event.actual_value == 0.2
    assert calendar_event.metadata == {"calendar_id": "cpi-2026-05"}


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
    return datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc)
