from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Final, cast

from application.persistence.sentiment import SentimentPersistenceService
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
from core.storage.persistence.sentiment import (
    SentimentSnapshotRecord,
    SentimentSourceRecord,
)
from domain.workflow_outputs import (
    SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)

SENTIMENT_SNAPSHOT_PROJECTOR_NAME: Final = "sentiment_snapshot_projector"
SENTIMENT_SNAPSHOT_PROJECTOR_NODE_NAMES: Final = ("sentiment_agent",)
SENTIMENT_SNAPSHOT_OBSERVED_AT_FIELD: Final = "observed_at"
SENTIMENT_SNAPSHOT_SOURCE_FIELD: Final = "sentiment_source"
SENTIMENT_SNAPSHOT_UNIVERSE_FIELD: Final = "sentiment_universe"
SENTIMENT_SNAPSHOT_FIELD: Final = "sentiment_snapshot"
SENTIMENT_SOURCE_DATA_FIELD: Final = "sentiment_source_data"


class SentimentSnapshotWorkflowOutputProjector:
    """Project sentiment-agent workflow evidence into curated sentiment records."""

    def __init__(
        self,
        sentiment_persistence_service: SentimentPersistenceService,
    ) -> None:
        self._sentiment_persistence_service = sentiment_persistence_service

    @property
    def projector_name(self) -> str:
        return SENTIMENT_SNAPSHOT_PROJECTOR_NAME

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        outputs = _mapping(request.node_output.outputs)
        observed_at = _parse_timestamp(
            outputs.get(SENTIMENT_SNAPSHOT_OBSERVED_AT_FIELD)
        )
        if observed_at is None:
            return _skipped(
                request,
                "Sentiment output is missing first-class observed_at timestamp.",
            )

        sentiment_snapshot = _mapping(outputs.get(SENTIMENT_SNAPSHOT_FIELD))
        source_data = _mapping(outputs.get(SENTIMENT_SOURCE_DATA_FIELD))
        if not sentiment_snapshot and not source_data:
            return _skipped(
                request,
                "Sentiment output is missing first-class sentiment payload.",
            )

        source = _optional_identifier(outputs.get(SENTIMENT_SNAPSHOT_SOURCE_FIELD))
        symbol = _coalesce_identifier(
            outputs.get("symbol"),
            source_data.get("symbol"),
            _execution_metadata(request).get("symbol"),
        )
        universe = _optional_identifier(outputs.get(SENTIMENT_SNAPSHOT_UNIVERSE_FIELD))
        features = _mapping(outputs.get("features"))
        providers = _mapping(source_data.get("providers"))
        metadata = _projection_metadata(request)

        snapshot_record = _build_snapshot_record(
            request=request,
            observed_at=observed_at,
            source=source,
            symbol=symbol,
            universe=universe,
            metadata=metadata,
            outputs=outputs,
            sentiment_snapshot=sentiment_snapshot,
            source_data=source_data,
            features=features,
            providers=providers,
        )
        source_records = _build_source_records(
            request=request,
            sentiment_snapshot_id=snapshot_record.sentiment_snapshot_id,
            symbol=symbol,
            universe=universe,
            providers=providers,
            metadata=metadata,
        )

        result = await self._sentiment_persistence_service.persist_records(
            snapshots=(snapshot_record,),
            sources=source_records,
        )
        if not result.success:
            return _failed(request, result.error or "Sentiment persistence failed.")

        return _outcome(
            request=request,
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            records_written=result.records_persisted,
            message="Sentiment output projected into curated sentiment records.",
        )


def build_sentiment_snapshot_projector_registration(
    sentiment_persistence_service: SentimentPersistenceService,
) -> WorkflowOutputProjectorRegistration:
    """Build the canonical sentiment-snapshot projector registration."""
    projector = SentimentSnapshotWorkflowOutputProjector(sentiment_persistence_service)
    return WorkflowOutputProjectorRegistration(
        projector_name=SENTIMENT_SNAPSHOT_PROJECTOR_NAME,
        output_contract=SENTIMENT_SNAPSHOT_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        projector=projector,
        supported_node_names=SENTIMENT_SNAPSHOT_PROJECTOR_NODE_NAMES,
    )


def _build_snapshot_record(
    *,
    request: WorkflowOutputProjectorRequest,
    observed_at: datetime,
    source: str | None,
    symbol: str | None,
    universe: str | None,
    metadata: JsonObject,
    outputs: Mapping[str, object],
    sentiment_snapshot: Mapping[str, object],
    source_data: Mapping[str, object],
    features: Mapping[str, object],
    providers: Mapping[str, object],
) -> SentimentSnapshotRecord:
    components = _mapping(features.get("components"))
    natural_key = ":".join(
        part for part in (source, symbol, universe or "market_sentiment") if part
    )
    return SentimentSnapshotRecord(
        sentiment_snapshot_id=build_projected_record_id(
            record_type="sentiment_snapshot",
            execution_id=request.lineage.execution_id or request.run.execution_id,
            node_name=request.lineage.node_name or request.node_output.node_name,
            domain_natural_key=natural_key,
            source_timestamp=observed_at,
        ),
        timestamp=observed_at,
        lineage=request.lineage,
        source=source,
        symbol=symbol,
        universe=universe,
        market_regime=_coalesce_identifier(
            outputs.get("regime"),
            source_data.get("market_regime"),
            sentiment_snapshot.get("regime"),
        ),
        market_bias=_coalesce_identifier(
            source_data.get("market_bias"),
            sentiment_snapshot.get("market_bias"),
            features.get("sentiment_bias"),
        ),
        fear_greed_score=_fear_greed_score(providers, components),
        news_sentiment_score=_optional_stability_score(components.get("news")),
        market_sentiment_score=_optional_stability_score(
            _coalesce_object(
                components.get("market"),
                sentiment_snapshot.get("composite_sentiment"),
                source_data.get("composite_sentiment"),
            )
        ),
        social_sentiment_score=_optional_stability_score(components.get("social")),
        composite_sentiment=_optional_stability_score(
            _coalesce_object(
                source_data.get("composite_sentiment"),
                sentiment_snapshot.get("composite_sentiment"),
                features.get("composite_sentiment"),
            )
        ),
        confidence=_optional_ratio(
            _coalesce_object(
                outputs.get("confidence"),
                source_data.get("confidence"),
                sentiment_snapshot.get("confidence"),
            )
        ),
        directional_signal=_optional_stability_score(outputs.get("directional_score")),
        momentum=_optional_stability_score(features.get("momentum")),
        stability=_optional_ratio(features.get("stability")),
        divergence=_optional_non_negative_float(features.get("divergence")),
        fusion_components=_json_mapping(
            _coalesce_object(sentiment_snapshot.get("fusion_components"), components)
        ),
        providers_payload=_json_mapping(providers),
        features_payload=_json_mapping(features),
        sentiment_payload=_json_mapping(sentiment_snapshot),
        raw_payload=_json_mapping(source_data),
        metadata=metadata,
    )


def _build_source_records(
    *,
    request: WorkflowOutputProjectorRequest,
    sentiment_snapshot_id: str,
    symbol: str | None,
    universe: str | None,
    providers: Mapping[str, object],
    metadata: JsonObject,
) -> tuple[SentimentSourceRecord, ...]:
    records: list[SentimentSourceRecord] = []
    for provider_name, raw_provider in providers.items():
        provider = _mapping(raw_provider)
        if not provider:
            continue
        source = _optional_identifier(provider.get("source")) or _optional_identifier(
            provider_name
        )
        source_type = _optional_identifier(provider.get("source_type")) or source
        timestamp = _parse_timestamp(
            _coalesce_object(
                provider.get("timestamp"),
                provider.get("observed_at"),
                provider.get("published_at"),
                provider.get("as_of"),
            )
        )
        if source is None or source_type is None or timestamp is None:
            continue

        records.append(
            SentimentSourceRecord(
                sentiment_source_id=build_projected_record_id(
                    record_type="sentiment_source",
                    execution_id=request.lineage.execution_id
                    or request.run.execution_id,
                    node_name=request.lineage.node_name
                    or request.node_output.node_name,
                    domain_natural_key=f"{source}:{source_type}",
                    source_timestamp=timestamp,
                ),
                timestamp=timestamp,
                source=source,
                source_type=source_type,
                lineage=request.lineage,
                sentiment_snapshot_id=sentiment_snapshot_id,
                symbol=symbol,
                universe=universe,
                sentiment_score=_optional_stability_score(
                    _coalesce_object(
                        provider.get("normalized_sentiment"),
                        provider.get("sentiment_score"),
                    )
                ),
                confidence=_optional_ratio(provider.get("confidence")),
                weight=_optional_ratio(provider.get("weight")),
                sample_size=_optional_int(provider.get("sample_size")),
                source_reference=_optional_identifier(
                    _coalesce_object(
                        provider.get("source_reference"),
                        provider.get("url"),
                        provider.get("id"),
                    )
                ),
                summary=_optional_text(provider.get("summary")),
                metadata=metadata,
            )
        )
    return tuple(records)


def _projection_metadata(
    request: WorkflowOutputProjectorRequest,
) -> JsonObject:
    return _compact_json_object(
        {
            "source_fingerprint": request.source_fingerprint,
            "projector_name": SENTIMENT_SNAPSHOT_PROJECTOR_NAME,
            "node_output_id": request.node_output.node_output_id,
            "quality_status": _quality_status(request),
            "requested_at": request.requested_at.isoformat(),
        }
    )


def _execution_metadata(
    request: WorkflowOutputProjectorRequest,
) -> Mapping[str, object]:
    return _mapping(request.node_output.metadata.get("execution_metadata"))


def _quality_status(request: WorkflowOutputProjectorRequest) -> str | None:
    direct = _optional_identifier(request.node_output.metadata.get("quality_status"))
    if direct is not None:
        return direct
    return _optional_identifier(_execution_metadata(request).get("quality_status"))


def _fear_greed_score(
    providers: Mapping[str, object],
    components: Mapping[str, object],
) -> float | None:
    fear_greed = _mapping(providers.get("fear_greed"))
    ratio = _optional_ratio(fear_greed.get("score"))
    if ratio is not None:
        return ratio
    percent = _optional_float(fear_greed.get("fear_greed_index"))
    if percent is not None and 0.0 <= percent <= 100.0:
        return percent / 100.0
    return _optional_ratio(components.get("fear_greed"))


def _mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _coalesce_object(*values: object) -> object:
    for value in values:
        if value is not None:
            return value
    return None


def _coalesce_identifier(*values: object) -> str | None:
    for value in values:
        identifier = _optional_identifier(value)
        if identifier is not None:
            return identifier
    return None


def _optional_identifier(value: object) -> str | None:
    if value is None:
        return None
    identifier = str(value).strip()
    return identifier or None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, str | int | float):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _optional_ratio(value: object) -> float | None:
    candidate = _optional_float(value)
    if candidate is None or candidate < 0.0 or candidate > 1.0:
        return None
    return candidate


def _optional_stability_score(value: object) -> float | None:
    candidate = _optional_float(value)
    if candidate is None or candidate < -1.0 or candidate > 1.0:
        return None
    return candidate


def _optional_non_negative_float(value: object) -> float | None:
    candidate = _optional_float(value)
    if candidate is None or candidate < 0.0:
        return None
    return candidate


def _parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _json_mapping(value: object) -> JsonObject:
    if not isinstance(value, Mapping):
        return {}
    return cast(
        JsonObject, {str(key): _to_json_value(raw) for key, raw in value.items()}
    )


def _compact_json_object(value: Mapping[str, object]) -> JsonObject:
    return cast(
        JsonObject,
        {
            str(key): _to_json_value(raw)
            for key, raw in value.items()
            if raw is not None and raw != () and raw != {} and raw != []
        },
    )


def _to_json_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(raw) for key, raw in value.items()}
    if isinstance(value, tuple | list):
        return [_to_json_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _outcome(
    *,
    request: WorkflowOutputProjectorRequest,
    status: WorkflowOutputProjectionStatus,
    records_written: int,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=status,
        projector_name=SENTIMENT_SNAPSHOT_PROJECTOR_NAME,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 0,
        source_fingerprint=request.source_fingerprint,
        records_written=records_written,
        message=message,
        completed_at=datetime.now(UTC),
    )


def _skipped(
    request: WorkflowOutputProjectorRequest,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return _outcome(
        request=request,
        status=WorkflowOutputProjectionStatus.SKIPPED,
        records_written=0,
        message=message,
    )


def _failed(
    request: WorkflowOutputProjectorRequest,
    error: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.FAILED,
        projector_name=SENTIMENT_SNAPSHOT_PROJECTOR_NAME,
        node_name=request.node_output.node_name,
        output_contract=request.node_output.output_contract or "unknown",
        output_schema_version=request.node_output.output_schema_version or 0,
        source_fingerprint=request.source_fingerprint,
        records_written=0,
        error_type="persistence_error",
        error_message=error,
        completed_at=datetime.now(UTC),
    )
