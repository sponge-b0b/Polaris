from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

import pytest

from application.rag.ingestion.curated_rag_bundle_persistence import (
    CuratedRagBundlePersister,
)
from application.rag.ingestion.curated_rag_document_builder import (
    CuratedRagDocumentBuilder,
)
from application.rag.ingestion.curated_rag_document_factory import (
    CuratedRagDocumentFactory,
)
from application.rag.ingestion.curated_rag_metadata import evaluate_source_eligibility
from application.rag.ingestion.curated_rag_models import CuratedRagBuildOptions
from core.storage.persistence.rag import (
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    RagPersistenceRepository,
    RagPersistenceResult,
)
from core.storage.persistence.reports import ReportRecord


def test_document_factory_constructs_typed_report_document() -> None:
    report = _report()
    options = CuratedRagBuildOptions(queue_embedding_jobs=True)

    document = CuratedRagDocumentFactory().build_report_document(
        report,
        eligibility=evaluate_source_eligibility(report),
        options=options,
    )

    assert document.source_table == "reports"
    assert document.source_id == report.report_id
    assert document.content_text == report.markdown_body
    assert document.generated_at == report.generated_at


@pytest.mark.asyncio
async def test_bundle_persister_delegates_complete_bundle_to_one_repository_call() -> (
    None
):
    repository = RecordingBundleRepository()
    bundle = CuratedRagDocumentBuilder().build_from_report(
        _report(),
        options=CuratedRagBuildOptions(
            max_chunk_characters=80,
            queue_embedding_jobs=True,
        ),
    )
    persister = CuratedRagBundlePersister(cast(RagPersistenceRepository, repository))

    result = await persister.persist(bundle)

    assert result.success is True
    assert repository.calls == 1
    assert repository.document == bundle.document
    assert repository.chunks == bundle.chunks
    assert repository.embedding_jobs == bundle.embedding_jobs


class RecordingBundleRepository:
    def __init__(self) -> None:
        self.calls = 0
        self.document: RagDocumentRecord | None = None
        self.chunks: tuple[RagChunkRecord, ...] = ()
        self.embedding_jobs: tuple[RagEmbeddingJobRecord, ...] = ()

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult:
        self.calls += 1
        self.document = document
        self.chunks = tuple(chunks)
        self.embedding_jobs = tuple(embedding_jobs)
        return RagPersistenceResult.succeeded(
            document_id=document.document_id,
            records_persisted=1 + len(chunks) + len(embedding_jobs),
        )


def _report() -> ReportRecord:
    return ReportRecord(
        report_id="morning_report:exec-step-10",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 6, 25, tzinfo=UTC),
        markdown_body="# Morning Report\n\nDeterministic curated content.",
        workflow_name="morning_report",
        execution_id="exec-step-10",
        runtime_id="runtime-step-10",
        status="succeeded",
        structured_payload={"symbol": "SPY"},
    )
