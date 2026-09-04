from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4

from core.storage.persistence.lineage import (
    JsonObject,
    JsonValue,
    clean_optional_identifier,
    require_non_empty_identifier,
)
from core.storage.persistence.query import PersistenceTimeRange


class PersistenceExportFormat(StrEnum):
    """
    Supported persistence export payload formats.

    These contracts describe export intent only. Export services may support a
    subset of formats and should serialize typed records only at boundaries.
    """

    JSON = "json"
    JSONL = "jsonl"
    CSV = "csv"


class PersistenceExportDestinationType(StrEnum):
    """
    Supported destination categories for persistence exports.
    """

    MEMORY = "memory"
    LOCAL_FILE = "local_file"
    OBJECT_STORE = "object_store"


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceExportDestination:
    """
    Destination metadata for a persistence export request.

    The destination is descriptive only. Concrete export services decide how to
    persist or return the exported payload at their application boundary.
    """

    destination_type: PersistenceExportDestinationType | str = (
        PersistenceExportDestinationType.MEMORY
    )
    uri: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "destination_type",
            _coerce_destination_type(
                self.destination_type,
            ),
        )
        object.__setattr__(
            self,
            "uri",
            clean_optional_identifier(
                self.uri,
                "uri",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        destination_type = _coerce_destination_type(
            self.destination_type,
        )
        result: dict[str, JsonValue] = {
            "destination_type": destination_type.value,
            "metadata": self.metadata,
        }
        if self.uri is not None:
            result["uri"] = self.uri
        return result


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceExportRequest:
    """
    Typed request describing a curated PostgreSQL persistence export.

    Export requests are intentionally domain/query metadata contracts. They do
    not contain raw records and do not imply vector, graph, or RAG ingestion.
    """

    domains: tuple[str, ...]
    time_range: PersistenceTimeRange = field(default_factory=PersistenceTimeRange)
    export_format: PersistenceExportFormat | str = PersistenceExportFormat.JSON
    destination: PersistenceExportDestination = field(
        default_factory=PersistenceExportDestination,
    )
    export_id: str = field(default_factory=lambda: f"persistence_export:{uuid4().hex}")
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "export_id",
            require_non_empty_identifier(
                self.export_id,
                "export_id",
            ),
        )
        object.__setattr__(
            self,
            "domains",
            _normalize_domains(
                self.domains,
            ),
        )
        object.__setattr__(
            self,
            "export_format",
            _coerce_export_format(
                self.export_format,
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def domain(
        self,
    ) -> str | None:
        if (
            len(
                self.domains,
            )
            != 1
        ):
            return None
        return self.domains[0]

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        export_format = _coerce_export_format(
            self.export_format,
        )
        return {
            "export_id": self.export_id,
            "domains": self.domains,
            "time_range": _time_range_as_boundary_dict(
                self.time_range,
            ),
            "format": export_format.value,
            "destination": self.destination.as_dict(),
            "metadata": self.metadata,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceExportResult:
    """
    Typed result returned by persistence export application services.
    """

    request: PersistenceExportRequest
    success: bool
    records_exported: int = 0
    domain_record_counts: Mapping[str, int] = field(default_factory=dict)
    artifact_uri: str | None = None
    error: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        if self.records_exported < 0:
            raise ValueError("records_exported cannot be negative.")
        object.__setattr__(
            self,
            "domain_record_counts",
            _normalize_domain_counts(
                self.domain_record_counts,
            ),
        )
        object.__setattr__(
            self,
            "artifact_uri",
            clean_optional_identifier(
                self.artifact_uri,
                "artifact_uri",
            ),
        )
        object.__setattr__(
            self,
            "error",
            clean_optional_identifier(
                self.error,
                "error",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )
        if self.success and self.error is not None:
            raise ValueError("successful export results cannot include an error.")
        if not self.success and self.error is None:
            raise ValueError("error is required when success is false.")

    @classmethod
    def succeeded(
        cls,
        *,
        request: PersistenceExportRequest,
        records_exported: int,
        domain_record_counts: Mapping[str, int] | None = None,
        artifact_uri: str | None = None,
        metadata: JsonObject | None = None,
    ) -> PersistenceExportResult:
        return cls(
            request=request,
            success=True,
            records_exported=records_exported,
            domain_record_counts=domain_record_counts or {},
            artifact_uri=artifact_uri,
            metadata=metadata or {},
        )

    @classmethod
    def failed(
        cls,
        *,
        request: PersistenceExportRequest,
        error: str,
        metadata: JsonObject | None = None,
    ) -> PersistenceExportResult:
        return cls(
            request=request,
            success=False,
            records_exported=0,
            error=error,
            metadata=metadata or {},
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {
            "request": self.request.as_dict(),
            "success": self.success,
            "records_exported": self.records_exported,
            "domain_record_counts": dict(
                self.domain_record_counts,
            ),
            "metadata": self.metadata,
        }
        if self.artifact_uri is not None:
            result["artifact_uri"] = self.artifact_uri
        if self.error is not None:
            result["error"] = self.error
        return result


def _coerce_export_format(
    export_format: PersistenceExportFormat | str,
) -> PersistenceExportFormat:
    if isinstance(
        export_format,
        PersistenceExportFormat,
    ):
        return export_format

    normalized = export_format.strip().lower()
    try:
        return PersistenceExportFormat(
            normalized,
        )
    except ValueError as exc:
        raise ValueError("export_format must be one of: json, jsonl, csv.") from exc


def _coerce_destination_type(
    destination_type: PersistenceExportDestinationType | str,
) -> PersistenceExportDestinationType:
    if isinstance(
        destination_type,
        PersistenceExportDestinationType,
    ):
        return destination_type

    normalized = destination_type.strip().lower()
    try:
        return PersistenceExportDestinationType(
            normalized,
        )
    except ValueError as exc:
        raise ValueError(
            "destination_type must be one of: memory, local_file, object_store."
        ) from exc


def _normalize_domains(
    domains: tuple[str, ...],
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for index, domain in enumerate(
        domains,
    ):
        cleaned = require_non_empty_identifier(
            domain,
            f"domains[{index}]",
        ).lower()
        if cleaned in seen:
            continue
        seen.add(
            cleaned,
        )
        normalized.append(
            cleaned,
        )
    if not normalized:
        raise ValueError("domains cannot be empty.")
    return tuple(
        normalized,
    )


def _normalize_domain_counts(
    domain_record_counts: Mapping[str, int],
) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for domain, count in domain_record_counts.items():
        cleaned = require_non_empty_identifier(
            domain,
            "domain_record_counts key",
        ).lower()
        if count < 0:
            raise ValueError("domain record counts cannot be negative.")
        normalized[cleaned] = count
    return normalized


def _time_range_as_boundary_dict(
    time_range: PersistenceTimeRange,
) -> dict[str, str]:
    result: dict[str, str] = {}
    if time_range.start is not None:
        result["start"] = time_range.start.isoformat()
    if time_range.end is not None:
        result["end"] = time_range.end.isoformat()
    return result
