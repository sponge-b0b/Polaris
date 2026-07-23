from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
type JsonObject = Mapping[str, JsonValue]


@dataclass(
    frozen=True,
    slots=True,
)
class ReportRecord:
    """
    Typed persistence-boundary record for a curated human report.

    Report content is intentionally stored in full. Persistence adapters may
    serialize this record to JSON/SQL, but application/report layers should use
    this typed contract internally.
    """

    report_id: str
    report_type: str
    title: str
    generated_at: datetime
    markdown_body: str
    subtitle: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    status: str | None = None
    structured_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.report_id,
            "report_id",
        )
        _require_non_empty(
            self.report_type,
            "report_type",
        )
        _require_non_empty(
            self.title,
            "title",
        )
        _require_non_empty(
            self.markdown_body,
            "markdown_body",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ReportSectionRecord:
    """
    Typed persistence-boundary record for a curated report section.
    """

    section_id: str
    report_id: str
    section_key: str
    title: str
    display_order: int = 0
    summary: str | None = None
    markdown_body: str | None = None
    content_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.section_id,
            "section_id",
        )
        _require_non_empty(
            self.report_id,
            "report_id",
        )
        _require_non_empty(
            self.section_key,
            "section_key",
        )
        _require_non_empty(
            self.title,
            "title",
        )
        _require_non_negative(
            self.display_order,
            "display_order",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ReportArtifactRecord:
    """
    Typed persistence-boundary record for a file/blob artifact reference.
    """

    artifact_id: str
    report_id: str
    artifact_type: str
    artifact_uri: str
    section_id: str | None = None
    mime_type: str | None = None
    description: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.artifact_id,
            "artifact_id",
        )
        _require_non_empty(
            self.report_id,
            "report_id",
        )
        _require_non_empty(
            self.artifact_type,
            "artifact_type",
        )
        _require_non_empty(
            self.artifact_uri,
            "artifact_uri",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ReportVersionRecord:
    """
    Typed persistence-boundary record for a curated report version.

    Versions are linked to an existing report and preserve full report content
    for audit/republication without requiring callers to inspect mutable report
    rows.
    """

    version_id: str
    report_id: str
    version_number: int
    created_at: datetime
    markdown_body: str
    title: str | None = None
    subtitle: str | None = None
    change_summary: str | None = None
    created_by: str | None = None
    structured_payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.version_id,
            "version_id",
        )
        _require_non_empty(
            self.report_id,
            "report_id",
        )
        _require_positive(
            self.version_number,
            "version_number",
        )
        _require_non_empty(
            self.markdown_body,
            "markdown_body",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ReportPublicationRecord:
    """
    Typed persistence-boundary record for a report publication attempt.
    """

    publication_id: str
    report_id: str
    publication_target: str
    publication_status: str
    requested_at: datetime
    version_id: str | None = None
    published_at: datetime | None = None
    artifact_uri: str | None = None
    error: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.publication_id,
            "publication_id",
        )
        _require_non_empty(
            self.report_id,
            "report_id",
        )
        _require_non_empty(
            self.publication_target,
            "publication_target",
        )
        _require_non_empty(
            self.publication_status,
            "publication_status",
        )
        if self.version_id is not None:
            _require_non_empty(
                self.version_id,
                "version_id",
            )
        if self.published_at is not None and self.published_at < self.requested_at:
            raise ValueError(
                "published_at must be greater than or equal to requested_at."
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ReportPersistenceBundle:
    """
    Atomic report persistence payload.
    """

    report: ReportRecord
    sections: tuple[ReportSectionRecord, ...] = ()
    artifacts: tuple[ReportArtifactRecord, ...] = ()
    versions: tuple[ReportVersionRecord, ...] = ()
    publications: tuple[ReportPublicationRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class ReportPersistenceResult:
    """
    Typed result returned by report persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    report_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative(
            self.records_persisted,
            "records_persisted",
        )

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            _require_non_empty(
                self.report_id,
                "report_id",
            )

        if not self.success:
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        report_id: str,
        records_persisted: int = 1,
    ) -> ReportPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            report_id=report_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> ReportPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_report_id(
    report_type: str,
    execution_id: str | None,
) -> str:
    """
    Build a stable report id for workflow-backed reports.
    """

    if execution_id is not None and execution_id.strip():
        return f"{report_type}:{execution_id.strip()}"

    return f"{report_type}:{uuid4().hex}"


def new_report_version_id(
    report_id: str,
    version_number: int,
) -> str:
    """
    Build a stable report version id for a report/version pair.
    """

    _require_non_empty(
        report_id,
        "report_id",
    )
    _require_positive(
        version_number,
        "version_number",
    )

    return f"{report_id}:version:{version_number}"


def new_report_publication_id(
    *,
    report_id: str,
    publication_target: str,
    requested_at: datetime,
    version_id: str | None = None,
) -> str:
    """
    Build a stable report publication id from report, target, and request time.
    """

    _require_non_empty(
        report_id,
        "report_id",
    )
    _require_non_empty(
        publication_target,
        "publication_target",
    )
    id_parts = [
        report_id,
        "publication",
        publication_target.strip(),
        requested_at.isoformat(),
    ]
    if version_id is not None and version_id.strip():
        id_parts.append(
            version_id.strip(),
        )

    return ":".join(
        id_parts,
    )


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _require_non_negative(
    value: int,
    field_name: str,
) -> None:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_positive(
    value: int,
    field_name: str,
) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive.")
