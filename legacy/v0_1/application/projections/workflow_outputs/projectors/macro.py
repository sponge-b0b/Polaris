from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Final, cast

from application.persistence.macro import MacroPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_projected_record_id,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.macro import (
    EconomicCalendarEventRecord,
    MacroObservationRecord,
    MacroRegimeSnapshotRecord,
)
from domain.workflow_outputs import (
    MACRO_ANALYSIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)

MACRO_ANALYSIS_PROJECTOR_NAME: Final = "macro_analysis_projector"
MACRO_ANALYSIS_PROJECTOR_NODE_NAMES: Final = ("fundamental_agent",)
MACRO_ANALYSIS_OBSERVED_AT_FIELD: Final = "observed_at"
MACRO_ANALYSIS_FIELD: Final = "macro_analysis"
MACRO_ANALYSIS_SOURCE_FIELD: Final = "macro_source"
MACRO_ANALYSIS_REGION_FIELD: Final = "macro_region"
ECONOMIC_CALENDAR_EVENTS_FIELD: Final = "economic_calendar_events"


class MacroAnalysisWorkflowOutputProjector:
    """Project macro analysis workflow evidence into curated macro records."""

    def __init__(
        self,
        macro_persistence_service: MacroPersistenceService,
    ) -> None:
        self._macro_persistence_service = macro_persistence_service

    @property
    def projector_name(self) -> str:
        return MACRO_ANALYSIS_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        observed_at = _parse_timestamp(outputs.get(MACRO_ANALYSIS_OBSERVED_AT_FIELD))
        if observed_at is None:
            return _skipped(
                request,
                "Macro output is missing first-class observed_at timestamp.",
            )

        macro_analysis = _mapping(outputs.get(MACRO_ANALYSIS_FIELD))
        if not macro_analysis:
            return _skipped(
                request,
                "Macro output is missing first-class macro_analysis payload.",
            )

        source = _optional_identifier(outputs.get(MACRO_ANALYSIS_SOURCE_FIELD))
        region = _optional_identifier(outputs.get(MACRO_ANALYSIS_REGION_FIELD))
        metadata = _projection_metadata(request)
        macro_data = _mapping(macro_analysis.get("macro_data"))

        observations = _build_observation_records(
            request=request,
            macro_data=macro_data,
            region=region,
            metadata=metadata,
        )
        regime_snapshot = _build_regime_snapshot_record(
            request=request,
            observed_at=observed_at,
            source=source,
            region=region,
            metadata=metadata,
            outputs=outputs,
            macro_analysis=macro_analysis,
            macro_data=macro_data,
        )
        calendar_events = _build_calendar_event_records(
            request=request,
            outputs=outputs,
            source=source,
            region=region,
            metadata=metadata,
        )

        result = await self._macro_persistence_service.persist_records(
            observations=observations,
            regime_snapshots=(regime_snapshot,),
            calendar_events=calendar_events,
        )
        if not result.success:
            return _failed(request, result.error or "Macro persistence failed.")

        return _outcome(
            request=request,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message="Macro analysis output projected into curated macro records.",
        )


def build_macro_analysis_projector_registration(
    macro_persistence_service: MacroPersistenceService,
) -> WorkflowOutputProjectorRegistration:
    """Build the canonical macro-analysis projector registration."""
    projector = MacroAnalysisWorkflowOutputProjector(macro_persistence_service)
    return WorkflowOutputProjectorRegistration(
        projector_name=MACRO_ANALYSIS_PROJECTOR_NAME,
        output_contract=MACRO_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        projector=projector,
        supported_node_names=MACRO_ANALYSIS_PROJECTOR_NODE_NAMES,
    )


def _build_observation_records(
    *,
    request: WorkflowOutputProjectorRequest,
    macro_data: Mapping[str, object],
    region: str | None,
    metadata: JsonObject,
) -> tuple[MacroObservationRecord, ...]:
    raw_observations = macro_data.get("observations")
    if not isinstance(raw_observations, Sequence) or isinstance(raw_observations, str):
        return ()

    records: list[MacroObservationRecord] = []
    for raw_observation in raw_observations:
        observation = _mapping(raw_observation)
        if not observation:
            continue
        indicator_name = _optional_identifier(observation.get("indicator_name"))
        source = _optional_identifier(observation.get("source"))
        observation_timestamp = _parse_timestamp(
            observation.get("observation_timestamp"),
        )
        value = _optional_float(observation.get("value"))
        if (
            indicator_name is None
            or source is None
            or observation_timestamp is None
            or value is None
        ):
            continue

        record_region = _coalesce_identifier(observation.get("region"), region)
        records.append(
            MacroObservationRecord(
                observation_id=build_projected_record_id(
                    record_type="macro_observation",
                    execution_id=request.lineage.execution_id
                    or request.run.execution_id,
                    node_name=request.lineage.node_name
                    or request.node_output.node_name,
                    domain_natural_key=":".join(
                        part
                        for part in (indicator_name, source, record_region)
                        if part is not None
                    ),
                    source_timestamp=observation_timestamp,
                ),
                indicator_name=indicator_name,
                observation_timestamp=observation_timestamp,
                source=source,
                value=value,
                lineage=request.lineage,
                indicator_category=_optional_identifier(
                    observation.get("indicator_category")
                ),
                region=record_region,
                unit=_optional_identifier(observation.get("unit")),
                frequency=_optional_identifier(observation.get("frequency")),
                release_timestamp=_parse_timestamp(
                    observation.get("release_timestamp")
                ),
                vintage_timestamp=_parse_timestamp(
                    observation.get("vintage_timestamp")
                ),
                metadata=metadata,
            )
        )

    return tuple(records)


def _build_regime_snapshot_record(
    *,
    request: WorkflowOutputProjectorRequest,
    observed_at: datetime,
    source: str | None,
    region: str | None,
    metadata: JsonObject,
    outputs: Mapping[str, object],
    macro_analysis: Mapping[str, object],
    macro_data: Mapping[str, object],
) -> MacroRegimeSnapshotRecord:
    inflation_analysis = _mapping(macro_analysis.get("inflation_analysis"))
    fed_analysis = _mapping(macro_analysis.get("fed_analysis"))
    liquidity_analysis = _mapping(macro_analysis.get("liquidity_analysis"))
    yield_curve_analysis = _mapping(macro_analysis.get("yield_curve_analysis"))
    economic_regime = _mapping(macro_analysis.get("economic_regime"))

    return MacroRegimeSnapshotRecord(
        regime_snapshot_id=build_projected_record_id(
            record_type="macro_regime_snapshot",
            execution_id=request.lineage.execution_id or request.run.execution_id,
            node_name=request.lineage.node_name or request.node_output.node_name,
            domain_natural_key=region or "global",
            source_timestamp=observed_at,
        ),
        timestamp=observed_at,
        lineage=request.lineage,
        source=source,
        region=region,
        inflation_regime=_coalesce_identifier(
            macro_analysis.get("inflation_regime"),
            inflation_analysis.get("inflation_regime"),
        ),
        liquidity_regime=_coalesce_identifier(
            macro_analysis.get("liquidity_regime"),
            liquidity_analysis.get("liquidity_regime"),
        ),
        fed_stance=_coalesce_identifier(
            macro_analysis.get("fed_stance"),
            fed_analysis.get("fed_stance"),
        ),
        yield_curve_regime=_coalesce_identifier(
            macro_analysis.get("yield_curve_regime"),
            yield_curve_analysis.get("curve_regime"),
        ),
        macro_regime=_coalesce_identifier(
            outputs.get("regime"),
            economic_regime.get("economic_regime"),
        ),
        economic_regime=_optional_identifier(economic_regime.get("economic_regime")),
        inflation_score=_optional_stability_score(
            inflation_analysis.get("inflation_score")
        ),
        liquidity_score=_optional_stability_score(
            liquidity_analysis.get("liquidity_score")
        ),
        yield_curve_score=_optional_stability_score(
            yield_curve_analysis.get("yield_curve_score")
        ),
        macro_score=_optional_stability_score(economic_regime.get("macro_score")),
        risk_score=_optional_ratio(economic_regime.get("risk_score")),
        confidence=_optional_ratio(outputs.get("confidence")),
        inputs=_compact_json_object(
            {
                "macro_data": _json_mapping(macro_data),
            }
        ),
        outputs=_compact_json_object(
            {
                "inflation_analysis": _json_mapping(inflation_analysis),
                "fed_analysis": _json_mapping(fed_analysis),
                "liquidity_analysis": _json_mapping(liquidity_analysis),
                "yield_curve_analysis": _json_mapping(yield_curve_analysis),
                "economic_regime": _json_mapping(economic_regime),
            }
        ),
        metadata=metadata,
    )


def _build_calendar_event_records(
    *,
    request: WorkflowOutputProjectorRequest,
    outputs: Mapping[str, object],
    source: str | None,
    region: str | None,
    metadata: JsonObject,
) -> tuple[EconomicCalendarEventRecord, ...]:
    raw_events = outputs.get(ECONOMIC_CALENDAR_EVENTS_FIELD)
    if not isinstance(raw_events, Sequence) or isinstance(raw_events, str):
        return ()

    records: list[EconomicCalendarEventRecord] = []
    for raw_event in raw_events:
        event = _mapping(raw_event)
        if not event:
            continue
        event_name = _optional_identifier(event.get("event_name"))
        event_source = _coalesce_identifier(event.get("source"), source)
        event_timestamp = _parse_timestamp(event.get("event_timestamp"))
        if event_name is None or event_source is None or event_timestamp is None:
            continue

        event_region = _coalesce_identifier(event.get("region"), region)
        records.append(
            EconomicCalendarEventRecord(
                event_id=build_projected_record_id(
                    record_type="economic_calendar_event",
                    execution_id=request.lineage.execution_id
                    or request.run.execution_id,
                    node_name=request.lineage.node_name
                    or request.node_output.node_name,
                    domain_natural_key=":".join(
                        part
                        for part in (event_name, event_source, event_region)
                        if part is not None
                    ),
                    source_timestamp=event_timestamp,
                ),
                event_name=event_name,
                event_timestamp=event_timestamp,
                source=event_source,
                lineage=request.lineage,
                region=event_region,
                event_type=_optional_identifier(event.get("event_type")),
                importance_score=_optional_ratio(event.get("importance_score")),
                actual_value=_optional_float(event.get("actual_value")),
                forecast_value=_optional_float(event.get("forecast_value")),
                previous_value=_optional_float(event.get("previous_value")),
                surprise_score=_optional_stability_score(event.get("surprise_score")),
                unit=_optional_identifier(event.get("unit")),
                currency=_optional_identifier(event.get("currency")),
                release_status=_optional_identifier(event.get("release_status")),
                metadata=metadata,
            )
        )

    return tuple(records)


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    status: WorkflowOutputProjectionStatus,
    records_written: int = 0,
    message: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> WorkflowOutputProjectionOutcome:
    completed_at = datetime.now(UTC)
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=MACRO_ANALYSIS_PROJECTOR_NAME,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract
        or MACRO_ANALYSIS_OUTPUT_CONTRACT,
        output_schema_version=request.node_output.output_schema_version
        or WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
        error_type=error_type,
        error_message=error_message,
        completed_at=completed_at,
    )


def _skipped(
    request: WorkflowOutputProjectorRequest,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.SKIPPED,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    error: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.FAILED,
        error_type="macro_persistence_failed",
        error_message=error,
        message="Macro analysis projection failed during persistence.",
    )


def _projection_metadata(request: WorkflowOutputProjectorRequest) -> JsonObject:
    quality_status = _optional_identifier(
        request.node_output.metadata.get("quality_status")
    )
    return _compact_json_object(
        {
            "source_fingerprint": request.source_fingerprint,
            "quality_status": quality_status,
            "projector_name": MACRO_ANALYSIS_PROJECTOR_NAME,
            "node_output_id": request.node_output.node_output_id,
        }
    )


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        raw_value = value.strip()
        if not raw_value:
            return None
        if raw_value.endswith("Z"):
            raw_value = f"{raw_value[:-1]}+00:00"
        try:
            timestamp = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
    else:
        return None

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _json_mapping(value: object) -> JsonObject:
    if isinstance(value, Mapping):
        return cast(JsonObject, dict(value))
    return {}


def _compact_json_object(payload: Mapping[str, object | None]) -> JsonObject:
    return cast(
        JsonObject,
        {key: value for key, value in payload.items() if value is not None},
    )


def _optional_identifier(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _coalesce_identifier(*values: object) -> str | None:
    for value in values:
        cleaned = _optional_identifier(value)
        if cleaned is not None:
            return cleaned
    return None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_ratio(value: object) -> float | None:
    cleaned = _optional_float(value)
    if cleaned is None or not 0.0 <= cleaned <= 1.0:
        return None
    return cleaned


def _optional_stability_score(value: object) -> float | None:
    cleaned = _optional_float(value)
    if cleaned is None or not -1.0 <= cleaned <= 1.0:
        return None
    return cleaned
