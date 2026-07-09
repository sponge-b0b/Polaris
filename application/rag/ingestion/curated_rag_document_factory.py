from __future__ import annotations

from typing import cast

from application.rag.ingestion.curated_rag_chunking import hash_text
from application.rag.ingestion.curated_rag_metadata import agent_signal_metadata
from application.rag.ingestion.curated_rag_metadata import report_metadata
from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from application.rag.ingestion.curated_rag_rendering import agent_signal_title
from application.rag.ingestion.curated_rag_rendering import render_agent_signal_text
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import new_rag_document_id
from core.storage.persistence.reports import ReportRecord


class CuratedRagDocumentFactory:
    """Constructs canonical RAG documents from typed curated source records."""

    def build_report_document(
        self,
        report: ReportRecord,
        *,
        eligibility: RagSourceEligibilityRecord,
        options: CuratedRagBuildOptions,
    ) -> RagDocumentRecord:
        return RagDocumentRecord(
            document_id=new_rag_document_id(
                source_table="reports",
                source_id=report.report_id,
                source_type=report.report_type,
            ),
            source_table="reports",
            source_id=report.report_id,
            source_type=report.report_type,
            title=report.title,
            content_text=report.markdown_body,
            content_hash=hash_text(
                report.markdown_body,
            ),
            workflow_name=report.workflow_name,
            execution_id=report.execution_id,
            generated_at=report.generated_at,
            metadata=cast(
                JsonObject,
                report_metadata(
                    report=report,
                    eligibility=eligibility,
                    options=options,
                ),
            ),
        )

    def build_agent_signal_document(
        self,
        signal: AgentSignalRecord,
        *,
        eligibility: RagSourceEligibilityRecord,
        options: CuratedRagBuildOptions,
    ) -> RagDocumentRecord:
        content_text = render_agent_signal_text(
            signal,
        )
        return RagDocumentRecord(
            document_id=new_rag_document_id(
                source_table="agent_signals",
                source_id=signal.signal_id,
                source_type=signal.agent_type,
            ),
            source_table="agent_signals",
            source_id=signal.signal_id,
            source_type=signal.agent_type,
            title=agent_signal_title(
                signal,
            ),
            content_text=content_text,
            content_hash=hash_text(
                content_text,
            ),
            workflow_name=signal.workflow_name,
            execution_id=signal.execution_id,
            generated_at=signal.timestamp,
            metadata=cast(
                JsonObject,
                agent_signal_metadata(
                    signal=signal,
                    eligibility=eligibility,
                    options=options,
                ),
            ),
        )
