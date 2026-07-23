from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, cast, runtime_checkable
from uuid import UUID

from core.storage.persistence.export import (
    PersistenceExportDestinationType,
    PersistenceExportFormat,
    PersistenceExportRequest,
    PersistenceExportResult,
)
from core.storage.persistence.lineage import (
    DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
    DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
    JsonObject,
    JsonScalar,
    JsonValue,
    PersistenceLineageTraversalResult,
    PersistenceRecordIdentity,
    require_non_empty_identifier,
)


@runtime_checkable
class _SupportsAsDict(Protocol):
    def as_dict(
        self,
    ) -> Mapping[str, object]: ...


@runtime_checkable
class _ReportHistoryBundle(Protocol):
    report: object
    sections: Sequence[object]
    artifacts: Sequence[object]
    versions: Sequence[object]
    publications: Sequence[object]


@runtime_checkable
class _RecommendationHistoryBundle(Protocol):
    recommendation: object
    rationales: Sequence[object]
    outcomes: Sequence[object]
    trade_setups: Sequence[object]
    watchlist_items: Sequence[object]


class _ReportHistoryReportService(Protocol):
    async def get_bundle(
        self,
        report_id: str,
    ) -> object | None: ...


class _ReportHistoryLineageService(Protocol):
    async def trace_downstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH,
        max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult: ...


class _RecommendationHistoryService(Protocol):
    async def get_bundle(
        self,
        recommendation_id: str,
    ) -> object | None: ...


class _AgentSignalHistoryService(Protocol):
    async def get_signal(
        self,
        signal_id: str,
    ) -> object | None: ...


class _AgentIntelligenceHistoryService(Protocol):
    async def get_reasoning(
        self,
        reasoning_id: str,
    ) -> object | None: ...

    async def get_recommendation(
        self,
        agent_recommendation_id: str,
    ) -> object | None: ...

    async def get_risk_assessment(
        self,
        risk_assessment_id: str,
    ) -> object | None: ...


class _AttributionHistoryService(Protocol):
    async def get_attribution(
        self,
        attribution_id: str,
    ) -> object | None: ...

    async def get_signal_attribution(
        self,
        signal_attribution_id: str,
    ) -> object | None: ...

    async def get_recommendation_attribution(
        self,
        recommendation_attribution_id: str,
    ) -> object | None: ...


@dataclass(
    frozen=True,
    slots=True,
)
class ReportHistoryExportRequest:
    """
    Typed request for exporting one curated report history.

    The wrapped persistence export request controls the external JSON boundary.
    Linked records are discovered only through persisted lineage when a lineage
    service is provided.
    """

    report_id: str
    export_request: PersistenceExportRequest
    max_depth: int = DEFAULT_LINEAGE_TRAVERSAL_DEPTH
    max_edges: int = DEFAULT_LINEAGE_TRAVERSAL_EDGE_LIMIT
    relationship_types: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "report_id",
            require_non_empty_identifier(
                self.report_id,
                "report_id",
            ),
        )
        if self.max_depth < 0:
            raise ValueError("max_depth cannot be negative.")
        if self.max_edges <= 0:
            raise ValueError("max_edges must be positive.")
        object.__setattr__(
            self,
            "relationship_types",
            tuple(
                require_non_empty_identifier(
                    relationship_type,
                    "relationship_type",
                )
                for relationship_type in self.relationship_types
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class JsonPersistenceExportPayload:
    """
    JSON-compatible boundary payload for selected persisted records.

    The records are already serialized for an external/API/file boundary. Inside
    the platform, callers should continue to work with typed persistence records.
    """

    request: PersistenceExportRequest
    records_by_domain: Mapping[str, tuple[JsonObject, ...]]
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        normalized = _normalize_json_records_by_domain(
            self.records_by_domain,
        )
        object.__setattr__(
            self,
            "records_by_domain",
            normalized,
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def records_exported(
        self,
    ) -> int:
        return sum(
            len(
                records,
            )
            for records in self.records_by_domain.values()
        )

    @property
    def domain_record_counts(
        self,
    ) -> dict[str, int]:
        return {
            domain: len(
                records,
            )
            for domain, records in self.records_by_domain.items()
        }

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "request": self.request.as_dict(),
            "records": cast(
                JsonValue,
                dict(
                    self.records_by_domain,
                ),
            ),
            "metadata": self.metadata,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class JsonPersistenceExportResult:
    """
    Application result for JSON persistence exports.
    """

    export_result: PersistenceExportResult
    payload: JsonPersistenceExportPayload | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.export_result.success and self.payload is None:
            raise ValueError("payload is required when export_result succeeds.")
        if not self.export_result.success and self.payload is not None:
            raise ValueError("payload must be omitted when export_result fails.")

    @property
    def success(
        self,
    ) -> bool:
        return self.export_result.success

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {
            "export_result": self.export_result.as_dict(),
        }
        if self.payload is not None:
            result["payload"] = self.payload.as_dict()
        return result


class JsonPersistenceExportService:
    """
    Application service for exporting selected typed records to JSON payloads.

    The service accepts typed persistence records selected by upstream
    application services and serializes them only at this explicit export
    boundary. It does not query repositories, write files, or run RAG/vector
    ingestion.
    """

    async def export_records(
        self,
        request: PersistenceExportRequest,
        records_by_domain: Mapping[str, Sequence[object]],
    ) -> JsonPersistenceExportResult:
        if request.export_format is not PersistenceExportFormat.JSON:
            return JsonPersistenceExportResult(
                export_result=PersistenceExportResult.failed(
                    request=request,
                    error="JsonPersistenceExportService only supports json exports.",
                    metadata={
                        "supported_format": PersistenceExportFormat.JSON.value,
                    },
                )
            )

        try:
            selected_records = _select_requested_records(
                request=request,
                records_by_domain=records_by_domain,
            )
            payload = JsonPersistenceExportPayload(
                request=request,
                records_by_domain=selected_records,
                metadata={
                    "serializer": "json",
                    "boundary": "application.persistence.export",
                },
            )
        except (TypeError, ValueError) as exc:
            return JsonPersistenceExportResult(
                export_result=PersistenceExportResult.failed(
                    request=request,
                    error=str(
                        exc,
                    ),
                    metadata={
                        "serializer": "json",
                        "boundary": "application.persistence.export",
                    },
                )
            )

        destination_type = PersistenceExportDestinationType(
            request.destination.destination_type,
        )
        export_result = PersistenceExportResult.succeeded(
            request=request,
            records_exported=payload.records_exported,
            domain_record_counts=payload.domain_record_counts,
            artifact_uri=request.destination.uri,
            metadata={
                "serializer": "json",
                "destination_type": destination_type.value,
            },
        )
        return JsonPersistenceExportResult(
            export_result=export_result,
            payload=payload,
        )

    async def export_report_history(
        self,
        request: ReportHistoryExportRequest,
        *,
        report_service: _ReportHistoryReportService,
        lineage_service: _ReportHistoryLineageService | None = None,
        recommendation_service: _RecommendationHistoryService | None = None,
        agent_signal_service: _AgentSignalHistoryService | None = None,
        agent_intelligence_service: _AgentIntelligenceHistoryService | None = None,
        attribution_service: _AttributionHistoryService | None = None,
    ) -> JsonPersistenceExportResult:
        """
        Export report history plus linked curated records when lineage exists.

        This method coordinates existing typed application services and delegates
        final JSON serialization to ``export_records``. It does not access
        repositories directly and does not create RAG/vector/graph artifacts.
        """

        report_bundle = await report_service.get_bundle(
            request.report_id,
        )
        if report_bundle is None:
            return JsonPersistenceExportResult(
                export_result=PersistenceExportResult.failed(
                    request=request.export_request,
                    error=(
                        f"Report history export source not found: {request.report_id}."
                    ),
                    metadata={
                        "report_id": request.report_id,
                    },
                )
            )
        if not isinstance(
            report_bundle,
            _ReportHistoryBundle,
        ):
            return JsonPersistenceExportResult(
                export_result=PersistenceExportResult.failed(
                    request=request.export_request,
                    error=(
                        "Report history export source does not expose a report bundle."
                    ),
                    metadata={
                        "report_id": request.report_id,
                    },
                )
            )

        records_by_domain = _report_bundle_records(
            report_bundle,
        )
        if lineage_service is not None:
            lineage_result = await lineage_service.trace_downstream_lineage(
                PersistenceRecordIdentity(
                    record_type="report",
                    record_id=request.report_id,
                ),
                max_depth=request.max_depth,
                max_edges=request.max_edges,
                relationship_types=request.relationship_types,
            )
            _append_records(
                records_by_domain,
                "lineage_paths",
                lineage_result.paths,
            )
            await _append_linked_report_history_records(
                records_by_domain=records_by_domain,
                lineage_result=lineage_result,
                recommendation_service=recommendation_service,
                agent_signal_service=agent_signal_service,
                agent_intelligence_service=agent_intelligence_service,
                attribution_service=attribution_service,
            )

        return await self.export_records(
            request.export_request,
            records_by_domain=records_by_domain,
        )


def _select_requested_records(
    *,
    request: PersistenceExportRequest,
    records_by_domain: Mapping[str, Sequence[object]],
) -> dict[str, tuple[JsonObject, ...]]:
    normalized_input = {
        _normalize_domain(
            domain,
        ): tuple(
            records,
        )
        for domain, records in records_by_domain.items()
    }
    return {
        domain: tuple(
            _record_to_json_object(
                record,
            )
            for record in normalized_input.get(
                domain,
                (),
            )
        )
        for domain in request.domains
    }


def _record_to_json_object(
    record: object,
) -> JsonObject:
    if isinstance(
        record,
        _SupportsAsDict,
    ):
        return _mapping_to_json_object(
            record.as_dict(),
        )

    if is_dataclass(
        record,
    ) and not isinstance(
        record,
        type,
    ):
        return {
            field.name: _to_json_value(
                getattr(
                    record,
                    field.name,
                )
            )
            for field in fields(
                record,
            )
        }

    raise TypeError(
        "Persistence export records must be dataclass instances or expose as_dict()."
    )


def _mapping_to_json_object(
    value: Mapping[str, object],
) -> JsonObject:
    return {
        _normalize_json_key(
            key,
        ): _to_json_value(
            item,
        )
        for key, item in value.items()
    }


def _to_json_value(
    value: object,
) -> JsonValue:
    if value is None or isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return cast(
            JsonScalar,
            value,
        )

    if isinstance(
        value,
        datetime | date,
    ):
        return value.isoformat()

    if isinstance(
        value,
        Enum,
    ):
        return _to_json_value(
            value.value,
        )

    if isinstance(
        value,
        Decimal | UUID,
    ):
        return str(
            value,
        )

    if isinstance(
        value,
        Mapping,
    ):
        return {
            _normalize_json_key(
                key,
            ): _to_json_value(
                item,
            )
            for key, item in value.items()
        }

    if isinstance(
        value,
        Sequence,
    ) and not isinstance(
        value,
        (
            str,
            bytes,
            bytearray,
        ),
    ):
        return tuple(
            _to_json_value(
                item,
            )
            for item in value
        )

    if is_dataclass(
        value,
    ) and not isinstance(
        value,
        type,
    ):
        return _record_to_json_object(
            value,
        )

    raise TypeError(f"Value of type {type(value).__name__} is not JSON-compatible.")


def _normalize_json_records_by_domain(
    records_by_domain: Mapping[str, tuple[JsonObject, ...]],
) -> dict[str, tuple[JsonObject, ...]]:
    return {
        _normalize_domain(
            domain,
        ): tuple(
            dict(
                record,
            )
            for record in records
        )
        for domain, records in records_by_domain.items()
    }


def _normalize_domain(
    domain: str,
) -> str:
    return require_non_empty_identifier(
        domain,
        "domain",
    ).lower()


def _normalize_json_key(
    key: object,
) -> str:
    return require_non_empty_identifier(
        str(
            key,
        ),
        "json key",
    )


def _report_bundle_records(
    bundle: _ReportHistoryBundle,
) -> dict[str, list[object]]:
    return {
        "reports": [bundle.report],
        "report_sections": list(
            bundle.sections,
        ),
        "report_artifacts": list(
            bundle.artifacts,
        ),
        "report_versions": list(
            bundle.versions,
        ),
        "report_publications": list(
            bundle.publications,
        ),
    }


async def _append_linked_report_history_records(
    *,
    records_by_domain: dict[str, list[object]],
    lineage_result: PersistenceLineageTraversalResult,
    recommendation_service: _RecommendationHistoryService | None,
    agent_signal_service: _AgentSignalHistoryService | None,
    agent_intelligence_service: _AgentIntelligenceHistoryService | None,
    attribution_service: _AttributionHistoryService | None,
) -> None:
    for identity in lineage_result.visited_records[1:]:
        await _append_linked_record_for_identity(
            records_by_domain=records_by_domain,
            identity=identity,
            recommendation_service=recommendation_service,
            agent_signal_service=agent_signal_service,
            agent_intelligence_service=agent_intelligence_service,
            attribution_service=attribution_service,
        )


async def _append_linked_record_for_identity(
    *,
    records_by_domain: dict[str, list[object]],
    identity: PersistenceRecordIdentity,
    recommendation_service: _RecommendationHistoryService | None,
    agent_signal_service: _AgentSignalHistoryService | None,
    agent_intelligence_service: _AgentIntelligenceHistoryService | None,
    attribution_service: _AttributionHistoryService | None,
) -> None:
    record_type = identity.record_type.lower()
    if record_type == "recommendation" and recommendation_service is not None:
        bundle = await recommendation_service.get_bundle(
            identity.record_id,
        )
        if isinstance(
            bundle,
            _RecommendationHistoryBundle,
        ):
            _append_recommendation_bundle_records(
                records_by_domain,
                bundle,
            )
        return

    if record_type == "agent_signal" and agent_signal_service is not None:
        record = await agent_signal_service.get_signal(
            identity.record_id,
        )
        _append_optional_record(
            records_by_domain,
            "agent_signals",
            record,
        )
        return

    if agent_intelligence_service is not None:
        await _append_agent_intelligence_record(
            records_by_domain=records_by_domain,
            identity=identity,
            agent_intelligence_service=agent_intelligence_service,
        )

    if attribution_service is not None:
        await _append_attribution_record(
            records_by_domain=records_by_domain,
            identity=identity,
            attribution_service=attribution_service,
        )


def _append_recommendation_bundle_records(
    records_by_domain: dict[str, list[object]],
    bundle: _RecommendationHistoryBundle,
) -> None:
    _append_optional_record(
        records_by_domain,
        "recommendations",
        bundle.recommendation,
    )
    _append_records(
        records_by_domain,
        "recommendation_rationales",
        bundle.rationales,
    )
    _append_records(
        records_by_domain,
        "recommendation_outcomes",
        bundle.outcomes,
    )
    _append_records(
        records_by_domain,
        "trade_setups",
        bundle.trade_setups,
    )
    _append_records(
        records_by_domain,
        "watchlist_items",
        bundle.watchlist_items,
    )


async def _append_agent_intelligence_record(
    *,
    records_by_domain: dict[str, list[object]],
    identity: PersistenceRecordIdentity,
    agent_intelligence_service: _AgentIntelligenceHistoryService,
) -> None:
    record_type = identity.record_type.lower()
    if record_type == "agent_reasoning":
        record = await agent_intelligence_service.get_reasoning(
            identity.record_id,
        )
        _append_optional_record(
            records_by_domain,
            "agent_reasoning",
            record,
        )
        return
    if record_type == "agent_recommendation":
        record = await agent_intelligence_service.get_recommendation(
            identity.record_id,
        )
        _append_optional_record(
            records_by_domain,
            "agent_recommendations",
            record,
        )
        return
    if record_type == "agent_risk_assessment":
        record = await agent_intelligence_service.get_risk_assessment(
            identity.record_id,
        )
        _append_optional_record(
            records_by_domain,
            "agent_risk_assessments",
            record,
        )


async def _append_attribution_record(
    *,
    records_by_domain: dict[str, list[object]],
    identity: PersistenceRecordIdentity,
    attribution_service: _AttributionHistoryService,
) -> None:
    record_type = identity.record_type.lower()
    if record_type == "attribution":
        record = await attribution_service.get_attribution(
            identity.record_id,
        )
        _append_optional_record(
            records_by_domain,
            "attributions",
            record,
        )
        return
    if record_type == "signal_attribution":
        record = await attribution_service.get_signal_attribution(
            identity.record_id,
        )
        _append_optional_record(
            records_by_domain,
            "signal_attributions",
            record,
        )
        return
    if record_type == "recommendation_attribution":
        record = await attribution_service.get_recommendation_attribution(
            identity.record_id,
        )
        _append_optional_record(
            records_by_domain,
            "recommendation_attributions",
            record,
        )


def _append_optional_record(
    records_by_domain: dict[str, list[object]],
    domain: str,
    record: object | None,
) -> None:
    if record is not None:
        records_by_domain.setdefault(
            domain,
            [],
        ).append(
            record,
        )


def _append_records(
    records_by_domain: dict[str, list[object]],
    domain: str,
    records: Sequence[object],
) -> None:
    records_by_domain.setdefault(
        domain,
        [],
    ).extend(
        records,
    )
