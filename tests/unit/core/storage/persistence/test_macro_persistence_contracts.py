from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.macro import EconomicCalendarEventRecord
from core.storage.persistence.macro import MacroObservationRecord
from core.storage.persistence.macro import MacroPersistenceBundle
from core.storage.persistence.macro import MacroPersistenceResult
from core.storage.persistence.macro import MacroRegimeSnapshotRecord
from core.storage.persistence.macro import new_economic_calendar_event_id
from core.storage.persistence.macro import new_macro_observation_id
from core.storage.persistence.macro import new_macro_regime_snapshot_id


def test_macro_observation_record_is_typed_normalized_and_immutable() -> None:
    record = MacroObservationRecord(
        observation_id="observation-1",
        indicator_name=" CPI YoY ",
        observation_timestamp=_timestamp(),
        source=" fred ",
        value=-0.2,
        indicator_category=" inflation ",
        region=" US ",
        unit=" percent ",
        frequency=" monthly ",
        release_timestamp=_timestamp(),
        vintage_timestamp=_timestamp(),
        lineage=_lineage(),
        metadata={"series_id": "CPIAUCSL"},
    )

    assert record.indicator_name == "CPI YoY"
    assert record.source == "fred"
    assert record.value == -0.2
    assert record.indicator_category == "inflation"
    assert record.region == "US"
    assert record.unit == "percent"
    assert record.frequency == "monthly"
    assert record.lineage.execution_id == "exec-1"

    with pytest.raises(FrozenInstanceError):
        record.value = 1.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"observation_id": " "}, "observation_id"),
        ({"indicator_name": ""}, "indicator_name"),
        ({"source": " "}, "source"),
    ],
)
def test_macro_observation_record_validates_required_identifiers(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "observation_id": "observation-1",
        "indicator_name": "CPI YoY",
        "observation_timestamp": _timestamp(),
        "source": "fred",
        "value": 3.1,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        MacroObservationRecord(**values)  # type: ignore[arg-type]


def test_macro_regime_snapshot_captures_regimes_scores_and_io() -> None:
    record = MacroRegimeSnapshotRecord(
        regime_snapshot_id="macro-regime-1",
        timestamp=_timestamp(),
        source=" morning_report ",
        region=" US ",
        inflation_regime=" disinflation ",
        liquidity_regime=" tightening ",
        growth_regime=" resilient ",
        fed_stance=" restrictive ",
        yield_curve_regime=" inverted ",
        macro_regime=" late_cycle ",
        economic_regime=" expansion ",
        inflation_score=0.35,
        liquidity_score=-0.25,
        growth_score=0.5,
        yield_curve_score=-0.6,
        macro_score=0.15,
        risk_score=0.4,
        confidence=0.82,
        inputs={"series": ["CPI", "UNRATE", "DGS10"]},
        outputs={"summary": "Growth remains resilient as policy stays tight."},
        lineage=_lineage(),
    )

    assert record.source == "morning_report"
    assert record.region == "US"
    assert record.inflation_regime == "disinflation"
    assert record.liquidity_regime == "tightening"
    assert record.growth_regime == "resilient"
    assert record.fed_stance == "restrictive"
    assert record.yield_curve_regime == "inverted"
    assert record.macro_regime == "late_cycle"
    assert record.economic_regime == "expansion"
    assert record.inputs == {"series": ["CPI", "UNRATE", "DGS10"]}
    assert record.outputs == {
        "summary": "Growth remains resilient as policy stays tight."
    }


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"regime_snapshot_id": " "}, "regime_snapshot_id"),
        ({"inflation_score": 1.1}, "inflation_score"),
        ({"liquidity_score": -1.1}, "liquidity_score"),
        ({"growth_score": 1.1}, "growth_score"),
        ({"yield_curve_score": -1.1}, "yield_curve_score"),
        ({"macro_score": 1.1}, "macro_score"),
        ({"risk_score": 1.1}, "risk_score"),
        ({"confidence": -0.1}, "confidence"),
    ],
)
def test_macro_regime_snapshot_validates_identifiers_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "regime_snapshot_id": "macro-regime-1",
        "timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        MacroRegimeSnapshotRecord(**values)  # type: ignore[arg-type]


def test_economic_calendar_event_record_captures_event_values() -> None:
    record = EconomicCalendarEventRecord(
        event_id="calendar-event-1",
        event_name=" CPI Release ",
        event_timestamp=_timestamp(),
        source=" econoday ",
        region=" US ",
        event_type=" inflation ",
        importance_score=0.9,
        actual_value=-0.1,
        forecast_value=0.2,
        previous_value=0.3,
        surprise_score=-0.4,
        unit=" percent ",
        currency=" USD ",
        release_status=" released ",
        metadata={"calendar_id": "cpi-2026-05"},
        lineage=_lineage(),
    )

    assert record.event_name == "CPI Release"
    assert record.source == "econoday"
    assert record.region == "US"
    assert record.event_type == "inflation"
    assert record.importance_score == 0.9
    assert record.actual_value == -0.1
    assert record.forecast_value == 0.2
    assert record.previous_value == 0.3
    assert record.surprise_score == -0.4
    assert record.release_status == "released"


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"event_id": " "}, "event_id"),
        ({"event_name": ""}, "event_name"),
        ({"source": " "}, "source"),
        ({"importance_score": 1.1}, "importance_score"),
        ({"surprise_score": -1.1}, "surprise_score"),
    ],
)
def test_economic_calendar_event_record_validates_identifiers_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "event_id": "calendar-event-1",
        "event_name": "CPI Release",
        "event_timestamp": _timestamp(),
        "source": "econoday",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        EconomicCalendarEventRecord(**values)  # type: ignore[arg-type]


def test_macro_bundle_groups_atomic_persistence_payload() -> None:
    bundle = MacroPersistenceBundle(
        observations=(_observation(),),
        regime_snapshots=(_regime_snapshot(),),
        calendar_events=(_calendar_event(),),
    )

    assert len(bundle.observations) == 1
    assert len(bundle.regime_snapshots) == 1
    assert len(bundle.calendar_events) == 1


def test_macro_persistence_result_validates_state() -> None:
    success = MacroPersistenceResult.succeeded(
        primary_record_id="macro-record-1",
        records_persisted=3,
    )
    failure = MacroPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 3
    assert success.primary_record_id == "macro-record-1"
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="records_persisted"):
        MacroPersistenceResult(
            success=True,
            primary_record_id="macro-record-1",
            records_persisted=-1,
        )

    with pytest.raises(ValueError, match="successful"):
        MacroPersistenceResult(
            success=True,
            primary_record_id="macro-record-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="primary_record_id"):
        MacroPersistenceResult(
            success=True,
        )

    with pytest.raises(ValueError, match="error"):
        MacroPersistenceResult.failed(
            " ",
        )


def test_macro_id_helpers_are_stable_with_lineage_and_source_keys() -> None:
    assert (
        new_macro_observation_id(
            indicator_name=" CPI YoY ",
            observation_timestamp=_timestamp(),
            source=" fred ",
            region=" US ",
        )
        == "macro_observation:2026-05-31T14:00:00+00:00:CPI YoY:fred:US"
    )
    assert (
        new_macro_regime_snapshot_id(
            timestamp=_timestamp(),
            execution_id=" exec-1 ",
            snapshot_key=" primary ",
            region=" US ",
        )
        == "macro_regime_snapshot:exec-1:2026-05-31T14:00:00+00:00:US:primary"
    )
    assert (
        new_economic_calendar_event_id(
            event_name=" CPI Release ",
            event_timestamp=_timestamp(),
            source=" econoday ",
            region=" US ",
        )
        == "economic_calendar_event:2026-05-31T14:00:00+00:00:CPI Release:econoday:US"
    )


def test_macro_fact_id_helpers_are_deterministic_by_source_keys() -> None:
    observation_id = new_macro_observation_id(
        indicator_name=" CPI YoY ",
        observation_timestamp=_timestamp(),
        source=" fred ",
        region=" US ",
    )
    repeat_observation_id = new_macro_observation_id(
        indicator_name="CPI YoY",
        observation_timestamp=_timestamp(),
        source="fred",
        region="US",
    )
    alternate_source_observation_id = new_macro_observation_id(
        indicator_name="CPI YoY",
        observation_timestamp=_timestamp(),
        source="bea",
        region="US",
    )
    calendar_event_id = new_economic_calendar_event_id(
        event_name=" CPI Release ",
        event_timestamp=_timestamp(),
        source=" econoday ",
        region=" US ",
    )
    repeat_calendar_event_id = new_economic_calendar_event_id(
        event_name="CPI Release",
        event_timestamp=_timestamp(),
        source="econoday",
        region="US",
    )

    assert observation_id == repeat_observation_id
    assert observation_id != alternate_source_observation_id
    assert calendar_event_id == repeat_calendar_event_id
    assert ":fred:US" in observation_id
    assert ":econoday:US" in calendar_event_id


def _observation() -> MacroObservationRecord:
    return MacroObservationRecord(
        observation_id="observation-1",
        indicator_name="CPI YoY",
        observation_timestamp=_timestamp(),
        source="fred",
        value=3.1,
    )


def _regime_snapshot() -> MacroRegimeSnapshotRecord:
    return MacroRegimeSnapshotRecord(
        regime_snapshot_id="macro-regime-1",
        timestamp=_timestamp(),
        macro_regime="late_cycle",
        macro_score=0.15,
    )


def _calendar_event() -> EconomicCalendarEventRecord:
    return EconomicCalendarEventRecord(
        event_id="calendar-event-1",
        event_name="CPI Release",
        event_timestamp=_timestamp(),
        source="econoday",
        importance_score=0.9,
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="macro_analysis",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
