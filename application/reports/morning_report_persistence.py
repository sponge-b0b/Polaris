from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from application.reports.authority import (
    ensure_report_publication_authority,
    report_authority_metadata,
)
from application.reports.morning_report_models import (
    MorningReportDocument,
    ReportMetric,
    ReportSection,
    ReportTable,
)
from core.storage.persistence.reports import (
    JsonObject,
    ReportArtifactRecord,
    ReportPersistenceBundle,
    ReportPersistenceRepository,
    ReportPersistenceResult,
    ReportRecord,
    ReportSectionRecord,
    new_report_id,
)
from domain.llm import (
    is_model_internal_reasoning_key,
    sanitize_reasoning_trace_text_for_boundary,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ReportArtifactReference:
    """
    Typed application-layer reference to a rendered report artifact.
    """

    uri: str
    artifact_type: str
    mime_type: str | None = None
    description: str | None = None

    @classmethod
    def from_path(
        cls,
        path: Path,
    ) -> ReportArtifactReference:
        suffix = path.suffix.lower().lstrip(
            ".",
        )
        artifact_type = _artifact_type_from_suffix(
            suffix,
        )
        return cls(
            uri=str(
                path,
            ),
            artifact_type=artifact_type,
            mime_type=_mime_type_for_artifact_type(
                artifact_type,
            ),
            description="CLI-rendered report artifact",
        )


class MorningReportPersistenceMapper:
    """
    Maps typed morning reports to typed durable report records.
    """

    def build_bundle(
        self,
        document: MorningReportDocument,
        *,
        markdown_body: str,
        workflow_name: str = "morning_report",
        runtime_id: str | None = None,
        artifact_references: Iterable[ReportArtifactReference] = (),
    ) -> ReportPersistenceBundle:
        report_id = new_report_id(
            "morning_report",
            document.execution_id,
        )
        safe_markdown_body = _publication_text(
            markdown_body,
            boundary_name="morning_report.persistence.markdown_body",
            allow_empty=False,
            strip_safe_text=False,
        )
        safe_publication_text = _strip_known_authority_disclosure(
            safe_markdown_body,
        )
        ensure_report_publication_authority(
            contract=document.authority,
            content_texts=(
                *_document_text_values(
                    document,
                ),
                safe_publication_text,
            ),
            boundary_name="morning_report.persistence",
        )
        authority_metadata = report_authority_metadata(
            document.authority,
        )
        sections = tuple(
            _section_record(
                report_id,
                key,
                section,
                display_order=index,
                authority_metadata=authority_metadata,
            )
            for index, (key, section) in enumerate(
                _document_sections(
                    document,
                ),
                start=1,
            )
        )
        artifacts = tuple(
            _artifact_record(
                report_id,
                reference,
                index=index,
                authority_metadata=authority_metadata,
            )
            for index, reference in enumerate(
                artifact_references,
                start=1,
            )
        )

        return ReportPersistenceBundle(
            report=ReportRecord(
                report_id=report_id,
                report_type="morning_report",
                title=document.title,
                subtitle=document.subtitle,
                workflow_name=workflow_name,
                execution_id=document.execution_id,
                runtime_id=runtime_id,
                status=document.status,
                generated_at=_parse_generated_at(
                    document.generated_at,
                ),
                markdown_body=safe_markdown_body,
                structured_payload=_json_object(
                    _document_payload(
                        document,
                        authority_metadata=authority_metadata,
                    ),
                    boundary_name="morning_report.persistence.structured_payload",
                ),
                metadata={
                    "symbol": document.symbol,
                    "execution_id": document.execution_id,
                    "status": document.status,
                    "workflow_name": workflow_name,
                    **authority_metadata,
                },
            ),
            sections=sections,
            artifacts=artifacts,
        )


class MorningReportPersistenceService:
    """
    Application service for persisting curated morning report output.
    """

    def __init__(
        self,
        repository: ReportPersistenceRepository,
        *,
        mapper: MorningReportPersistenceMapper | None = None,
    ) -> None:
        self._repository = repository
        self._mapper = mapper or MorningReportPersistenceMapper()

    async def persist(
        self,
        document: MorningReportDocument,
        *,
        markdown_body: str,
        workflow_name: str = "morning_report",
        runtime_id: str | None = None,
        artifact_references: Iterable[ReportArtifactReference] = (),
    ) -> ReportPersistenceResult:
        bundle = self._mapper.build_bundle(
            document,
            markdown_body=markdown_body,
            workflow_name=workflow_name,
            runtime_id=runtime_id,
            artifact_references=artifact_references,
        )

        return await self._repository.persist_report(
            bundle.report,
            sections=bundle.sections,
            artifacts=bundle.artifacts,
        )


def _document_sections(
    document: MorningReportDocument,
) -> tuple[tuple[str, ReportSection], ...]:
    sections: list[tuple[str, ReportSection]] = [
        (
            "executive_summary",
            document.executive_summary,
        ),
        (
            "portfolio_snapshot",
            document.portfolio_snapshot,
        ),
        (
            "macro_backdrop",
            document.macro_backdrop,
        ),
        (
            "technical_setup",
            document.technical_setup,
        ),
        (
            "news_sentiment",
            document.news_sentiment,
        ),
        (
            "risk_assessment",
            document.risk_assessment,
        ),
        (
            "recommended_action_plan",
            document.recommended_action_plan,
        ),
    ]
    if document.appendix is not None:
        sections.append(
            (
                "appendix",
                document.appendix,
            )
        )

    return tuple(
        sections,
    )


def _section_record(
    report_id: str,
    section_key: str,
    section: ReportSection,
    *,
    display_order: int,
    authority_metadata: JsonObject,
) -> ReportSectionRecord:
    return ReportSectionRecord(
        section_id=f"{report_id}:section:{section_key}",
        report_id=report_id,
        section_key=section_key,
        title=section.title,
        display_order=display_order,
        summary=_publication_text(
            section.summary,
            boundary_name=f"morning_report.persistence.sections.{section_key}.summary",
        ),
        content_payload=_json_object(
            asdict(
                section,
            ),
            boundary_name=f"morning_report.persistence.sections.{section_key}.content",
        ),
        metadata={
            "section_key": section_key,
            **authority_metadata,
        },
    )


def _artifact_record(
    report_id: str,
    reference: ReportArtifactReference,
    *,
    index: int,
    authority_metadata: JsonObject,
) -> ReportArtifactRecord:
    return ReportArtifactRecord(
        artifact_id=f"{report_id}:artifact:{index}",
        report_id=report_id,
        artifact_type=reference.artifact_type,
        artifact_uri=reference.uri,
        mime_type=reference.mime_type,
        description=reference.description,
        metadata={
            "source": "cli",
            **authority_metadata,
        },
    )


def _document_payload(
    document: MorningReportDocument,
    *,
    authority_metadata: JsonObject,
) -> dict[str, Any]:
    payload = asdict(
        document,
    )
    payload.pop(
        "authority",
        None,
    )
    payload["authority_boundary"] = authority_metadata
    return payload


def _document_text_values(
    document: MorningReportDocument,
) -> tuple[str, ...]:
    values = [
        document.title,
        document.subtitle,
        document.symbol,
        document.execution_id,
        document.generated_at,
        document.status,
        *document.run_errors,
    ]
    for section in (
        document.executive_summary,
        document.portfolio_snapshot,
        document.macro_backdrop,
        document.technical_setup,
        document.news_sentiment,
        document.risk_assessment,
        document.recommended_action_plan,
    ):
        values.extend(
            _section_text_values(
                section,
            )
        )
    if document.appendix is not None:
        values.extend(
            _section_text_values(
                document.appendix,
            )
        )
    return tuple(value for value in values if value)


def _section_text_values(
    section: ReportSection,
) -> tuple[str, ...]:
    values = [
        section.title,
        section.summary,
    ]
    for metric in section.metrics:
        values.extend(
            _metric_text_values(
                metric,
            )
        )
    for bullet in (
        *section.bullets,
        *section.risks,
        *section.recommendations,
    ):
        values.extend((bullet.label or "", bullet.text))
    for table in section.tables:
        values.extend(
            _table_text_values(
                table,
            )
        )
    return tuple(value for value in values if value)


def _metric_text_values(
    metric: ReportMetric,
) -> tuple[str, ...]:
    return (
        metric.label,
        metric.value,
        metric.note or "",
    )


def _table_text_values(
    table: ReportTable,
) -> tuple[str, ...]:
    values = [
        table.title,
    ]
    for row in table.rows:
        values.extend((row.label, row.value, row.note or ""))
    return tuple(value for value in values if value)


def _strip_known_authority_disclosure(
    markdown_body: str,
) -> str:
    heading = "## Authority Boundary"
    start = markdown_body.find(
        heading,
    )
    if start == -1:
        return markdown_body

    next_section = markdown_body.find(
        "\n## ",
        start
        + len(
            heading,
        ),
    )
    if next_section == -1:
        return markdown_body[:start]
    return markdown_body[:start] + markdown_body[next_section:]


def _parse_generated_at(
    value: str,
) -> datetime:
    normalized = value.strip()
    if normalized.endswith(
        "Z",
    ):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(
            normalized,
        )
    except ValueError:
        return datetime.now(
            UTC,
        )

    if parsed.tzinfo is None:
        return parsed.replace(
            tzinfo=UTC,
        )

    return parsed


def _json_object(
    value: Any,
    *,
    boundary_name: str,
) -> JsonObject:
    sanitized = _json_value(
        value,
        boundary_name=boundary_name,
    )
    if isinstance(
        sanitized,
        dict,
    ):
        return cast(
            JsonObject,
            sanitized,
        )

    return cast(
        JsonObject,
        {
            "value": sanitized,
        },
    )


def _json_value(
    value: Any,
    *,
    boundary_name: str,
) -> object:
    if value is None or isinstance(
        value,
        int | float | bool,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        return _publication_text(
            value,
            boundary_name=boundary_name,
        )

    if isinstance(
        value,
        datetime,
    ):
        return value.isoformat()

    if isinstance(
        value,
        Path,
    ):
        return str(
            value,
        )

    if isinstance(
        value,
        dict,
    ):
        return {
            str(
                key,
            ): _json_value(
                item,
                boundary_name=f"{boundary_name}.{key}",
            )
            for key, item in value.items()
            if not is_model_internal_reasoning_key(
                str(
                    key,
                )
            )
        }

    if isinstance(
        value,
        tuple | list,
    ):
        return [
            _json_value(
                item,
                boundary_name=f"{boundary_name}[]",
            )
            for item in value
        ]

    return _publication_text(
        str(
            value,
        ),
        boundary_name=boundary_name,
    )


def _publication_text(
    value: str,
    *,
    boundary_name: str,
    allow_empty: bool = True,
    strip_safe_text: bool = True,
) -> str:
    return sanitize_reasoning_trace_text_for_boundary(
        value,
        boundary_name=boundary_name,
        allow_empty=allow_empty,
        strip_safe_text=strip_safe_text,
    )


def _artifact_type_from_suffix(
    suffix: str,
) -> str:
    if suffix == "md":
        return "markdown"

    return suffix or "file"


def _mime_type_for_artifact_type(
    artifact_type: str,
) -> str | None:
    return {
        "html": "text/html",
        "json": "application/json",
        "markdown": "text/markdown",
        "md": "text/markdown",
        "pdf": "application/pdf",
        "txt": "text/plain",
    }.get(
        artifact_type,
    )
