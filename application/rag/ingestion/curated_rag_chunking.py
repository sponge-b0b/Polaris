from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.rag import (
    JsonObject,
    JsonValue,
    RagChunkRecord,
    RagDocumentRecord,
    new_rag_chunk_id,
)
from core.storage.persistence.reports import ReportRecord

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(
    frozen=True,
    slots=True,
)
class MarkdownSection:
    section_index: int
    section_name: str
    section_title: str
    heading_line: str | None
    body: str

    @property
    def text(self) -> str:
        if self.heading_line is None:
            return self.body
        if not self.body:
            return self.heading_line
        return f"{self.heading_line}\n\n{self.body}"


def build_report_chunks(
    *,
    document: RagDocumentRecord,
    report: ReportRecord,
    options: CuratedRagBuildOptions,
) -> tuple[RagChunkRecord, ...]:
    return build_record_aware_chunks(
        document=document,
        text=report.markdown_body,
        source_metadata={
            "source_kind": "report",
            "source_table": "reports",
            "source_id": report.report_id,
            "source_record_id": report.report_id,
            "source_type": report.report_type,
            "workflow_name": report.workflow_name,
            "workflow_id": _metadata_value(
                report.metadata,
                "workflow_id",
            ),
            "execution_id": report.execution_id,
            "runtime_id": report.runtime_id,
            "symbol": _metadata_value(
                report.structured_payload,
                "symbol",
            ),
            "asset_class": _metadata_value(
                report.structured_payload,
                "asset_class",
            ),
            "agent_name": None,
            "agent_type": None,
            "report_type": report.report_type,
            "regime": _metadata_value(
                report.structured_payload,
                "regime",
            ),
            "confidence": _metadata_value(
                report.structured_payload,
                "confidence",
            ),
            "directional_score": _metadata_value(
                report.structured_payload,
                "directional_score",
            ),
            "risk_score": _metadata_value(
                report.structured_payload,
                "risk_score",
            ),
            "created_at": report.generated_at.isoformat(),
            "as_of_date": _as_of_date(
                report.generated_at,
            ),
        },
        chunk_type="report_section",
        options=options,
    )


def build_agent_signal_chunks(
    *,
    document: RagDocumentRecord,
    signal: AgentSignalRecord,
    text: str,
    options: CuratedRagBuildOptions,
) -> tuple[RagChunkRecord, ...]:
    return build_record_aware_chunks(
        document=document,
        text=text,
        source_metadata={
            "source_kind": "agent_signal",
            "source_table": "agent_signals",
            "source_id": signal.signal_id,
            "source_record_id": signal.signal_id,
            "source_type": signal.agent_type,
            "workflow_name": signal.workflow_name,
            "workflow_id": _metadata_value(
                signal.metadata,
                "workflow_id",
            ),
            "execution_id": signal.execution_id,
            "runtime_id": signal.runtime_id,
            "symbol": signal.symbol,
            "asset_class": _metadata_value(
                signal.metadata,
                "asset_class",
            ),
            "agent_name": signal.agent_name,
            "agent_type": signal.agent_type,
            "report_type": None,
            "regime": signal.regime,
            "confidence": signal.confidence,
            "directional_score": signal.directional_score,
            "risk_score": _metadata_value(
                signal.risks,
                "risk_score",
            ),
            "created_at": signal.timestamp.isoformat(),
            "as_of_date": _as_of_date(
                signal.timestamp,
            ),
        },
        chunk_type="agent_signal_section",
        options=options,
    )


def build_record_aware_chunks(
    *,
    document: RagDocumentRecord,
    text: str,
    source_metadata: JsonObject,
    chunk_type: str,
    options: CuratedRagBuildOptions,
) -> tuple[RagChunkRecord, ...]:
    chunks: list[RagChunkRecord] = []
    sections = parse_markdown_sections(
        text,
    )
    for section in sections:
        section_parts = split_section_text(
            section,
            max_chunk_characters=options.max_chunk_characters,
        )
        for section_chunk_index, chunk_text in enumerate(section_parts):
            chunk_index = len(chunks)
            chunk_id = new_rag_chunk_id(
                document_id=document.document_id,
                chunk_index=chunk_index,
            )
            chunks.append(
                RagChunkRecord(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    chunk_index=chunk_index,
                    chunk_text=chunk_text,
                    token_count=estimate_token_count(
                        chunk_text,
                    ),
                    content_hash=hash_text(
                        chunk_text,
                    ),
                    metadata=cast(
                        JsonObject,
                        {
                            **source_metadata,
                            "parent_document_id": document.document_id,
                            "chunk_id": chunk_id,
                            "chunk_type": chunk_type,
                            "section_name": section.section_name,
                            "section_title": section.section_title,
                            "section_index": section.section_index,
                            "section_chunk_index": section_chunk_index,
                            "chunking_strategy": "record_aware_markdown_sections",
                            "rag_builder_version": "1",
                            "embedding_status": (
                                "queued"
                                if options.queue_embedding_jobs
                                else "not_queued"
                            ),
                            "graph_status": "not_queued",
                        },
                    ),
                )
            )

    return tuple(chunks)


def build_chunks(
    *,
    document_id: str,
    text: str,
    source_kind: str,
    max_chunk_characters: int,
) -> tuple[RagChunkRecord, ...]:
    """
    Backward-compatible generic chunking helper.

    New curated ingestion paths should call the record-aware builders above so
    chunks carry source lineage, section names, and retrieval metadata.
    """

    chunks: list[RagChunkRecord] = []
    for index, chunk_text in enumerate(
        split_text(
            text,
            max_chunk_characters=max_chunk_characters,
        )
    ):
        chunks.append(
            RagChunkRecord(
                chunk_id=new_rag_chunk_id(
                    document_id=document_id,
                    chunk_index=index,
                ),
                document_id=document_id,
                chunk_index=index,
                chunk_text=chunk_text,
                token_count=estimate_token_count(
                    chunk_text,
                ),
                content_hash=hash_text(
                    chunk_text,
                ),
                metadata={
                    "source_kind": source_kind,
                    "chunking_strategy": "paragraph_preserving_character_limit",
                    "rag_builder_version": "1",
                },
            )
        )

    return tuple(chunks)


def parse_markdown_sections(
    text: str,
) -> tuple[MarkdownSection, ...]:
    normalized_text = text.strip()
    if not normalized_text:
        return (
            MarkdownSection(
                section_index=0,
                section_name="body",
                section_title="Body",
                heading_line=None,
                body="",
            ),
        )

    sections: list[MarkdownSection] = []
    current_heading: str | None = None
    current_title = "Body"
    current_lines: list[str] = []

    for raw_line in normalized_text.splitlines():
        line = raw_line.rstrip()
        heading_match = _HEADING_PATTERN.match(
            line,
        )
        if heading_match is not None:
            _append_section(
                sections,
                heading_line=current_heading,
                section_title=current_title,
                lines=current_lines,
            )
            current_heading = line
            current_title = heading_match.group(2).strip()
            current_lines = []
            continue

        current_lines.append(line)

    _append_section(
        sections,
        heading_line=current_heading,
        section_title=current_title,
        lines=current_lines,
    )

    if not sections:
        return (
            MarkdownSection(
                section_index=0,
                section_name="body",
                section_title="Body",
                heading_line=None,
                body=normalized_text,
            ),
        )

    return tuple(sections)


def split_section_text(
    section: MarkdownSection,
    *,
    max_chunk_characters: int,
) -> tuple[str, ...]:
    full_text = section.text.strip()
    if len(full_text) <= max_chunk_characters:
        return (full_text,)

    heading_prefix = ""
    if section.heading_line is not None:
        heading_prefix = f"{section.heading_line}\n\n"

    body_limit = max(
        1,
        max_chunk_characters - len(heading_prefix),
    )
    body_chunks = split_text(
        section.body,
        max_chunk_characters=body_limit,
    )

    return tuple(f"{heading_prefix}{body_chunk}".strip() for body_chunk in body_chunks)


def split_text(
    text: str,
    *,
    max_chunk_characters: int,
) -> tuple[str, ...]:
    paragraphs = [
        paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()
    ]
    if not paragraphs:
        return (text,)

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_chunks = _split_long_paragraph(
            paragraph,
            max_chunk_characters=max_chunk_characters,
        )
        for paragraph_chunk in paragraph_chunks:
            separator_length = 2 if current_parts else 0
            proposed_length = current_length + separator_length + len(paragraph_chunk)
            if current_parts and proposed_length > max_chunk_characters:
                chunks.append(
                    "\n\n".join(
                        current_parts,
                    )
                )
                current_parts = []
                current_length = 0

            current_parts.append(
                paragraph_chunk,
            )
            current_length += (2 if current_length else 0) + len(paragraph_chunk)

    if current_parts:
        chunks.append(
            "\n\n".join(
                current_parts,
            )
        )

    return tuple(chunks)


def estimate_token_count(
    text: str,
) -> int:
    return len(
        text.split(),
    )


def hash_text(
    text: str,
) -> str:
    return sha256(
        text.encode(
            "utf-8",
        )
    ).hexdigest()


def _append_section(
    sections: list[MarkdownSection],
    *,
    heading_line: str | None,
    section_title: str,
    lines: list[str],
) -> None:
    body = "\n".join(lines).strip()
    if heading_line is None and not body:
        return
    if heading_line is not None and not body:
        return

    sections.append(
        MarkdownSection(
            section_index=len(sections),
            section_name=_section_name(
                section_title,
            ),
            section_title=section_title,
            heading_line=heading_line,
            body=body,
        )
    )


def _section_name(
    section_title: str,
) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "_",
        section_title.lower(),
    ).strip("_")
    return normalized or "body"


def _split_long_paragraph(
    paragraph: str,
    *,
    max_chunk_characters: int,
) -> tuple[str, ...]:
    if len(paragraph) <= max_chunk_characters:
        return (paragraph,)

    chunks: list[str] = []
    start = 0
    while start < len(paragraph):
        chunks.append(
            paragraph[start : start + max_chunk_characters],
        )
        start += max_chunk_characters

    return tuple(chunks)


def _metadata_value(
    metadata: JsonObject,
    key: str,
) -> JsonValue:
    return metadata.get(
        key,
    )


def _as_of_date(
    timestamp: object,
) -> str | None:
    if hasattr(
        timestamp,
        "date",
    ):
        return str(
            timestamp.date(),
        )

    return None
