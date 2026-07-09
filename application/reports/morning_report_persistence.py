from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import cast

from application.reports.morning_report_models import MorningReportDocument
from application.reports.morning_report_models import ReportSection
from core.storage.persistence.reports import JsonObject
from core.storage.persistence.reports import ReportArtifactRecord
from core.storage.persistence.reports import ReportPersistenceBundle
from core.storage.persistence.reports import ReportPersistenceRepository
from core.storage.persistence.reports import ReportPersistenceResult
from core.storage.persistence.reports import ReportRecord
from core.storage.persistence.reports import ReportSectionRecord
from core.storage.persistence.reports import new_report_id


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
        sections = tuple(
            _section_record(
                report_id,
                key,
                section,
                display_order=index,
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
                markdown_body=markdown_body,
                structured_payload=_json_object(
                    asdict(
                        document,
                    )
                ),
                metadata={
                    "symbol": document.symbol,
                    "execution_id": document.execution_id,
                    "status": document.status,
                    "workflow_name": workflow_name,
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
) -> ReportSectionRecord:
    return ReportSectionRecord(
        section_id=f"{report_id}:section:{section_key}",
        report_id=report_id,
        section_key=section_key,
        title=section.title,
        display_order=display_order,
        summary=section.summary,
        content_payload=_json_object(
            asdict(
                section,
            )
        ),
        metadata={
            "section_key": section_key,
        },
    )


def _artifact_record(
    report_id: str,
    reference: ReportArtifactReference,
    *,
    index: int,
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
        },
    )


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
) -> JsonObject:
    sanitized = _json_value(
        value,
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
) -> object:
    if value is None or isinstance(
        value,
        str | int | float | bool,
    ):
        return value

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
            )
            for key, item in value.items()
        }

    if isinstance(
        value,
        tuple | list,
    ):
        return [
            _json_value(
                item,
            )
            for item in value
        ]

    return str(
        value,
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
