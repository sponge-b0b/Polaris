from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence import RagEligibilityPersistenceFilters
from application.persistence import RagEligibilityPersistenceService
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagAnswerLogRecord
from core.storage.persistence.rag import RagCanonicalRecordCounts
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagEmbeddingJobRecord
from core.storage.persistence.rag import RagGraphJobRecord
from core.storage.persistence.rag import RagQueryLogRecord
from core.storage.persistence.rag import RagPersistenceResult
from core.storage.persistence.rag import RagRecordPersistenceResult
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import RagSourceEligibilityResult


class FakeRagPersistenceRepository:
    def __init__(
        self,
        records: Sequence[RagSourceEligibilityRecord] = (),
    ) -> None:
        self.records = tuple(records)
        self.marked: list[RagSourceEligibilityRecord] = []
        self.unmarked: list[tuple[str, str, str]] = []
        self.list_filters: dict[str, object | None] = {}

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult:
        return RagPersistenceResult.succeeded(
            document_id=document.document_id,
            records_persisted=1
            + len(
                chunks,
            )
            + len(
                embedding_jobs,
            ),
        )

    async def get_document(
        self,
        document_id: str,
    ) -> RagDocumentRecord | None:
        return None

    async def get_canonical_record_counts(self) -> RagCanonicalRecordCounts:
        return RagCanonicalRecordCounts(0, 0, 0, 0)

    async def list_chunks(
        self,
        document_id: str,
    ) -> Sequence[RagChunkRecord]:
        return ()

    async def get_chunk(
        self,
        chunk_id: str,
    ) -> RagChunkRecord | None:
        return None

    async def list_chunks_by_metadata(
        self,
        *,
        metadata_filters: JsonObject,
        limit: int | None = None,
    ) -> Sequence[RagChunkRecord]:
        return ()

    async def list_embedding_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagEmbeddingJobRecord]:
        return ()

    async def persist_embedding_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagRecordPersistenceResult:
        return RagRecordPersistenceResult.succeeded(
            record_id=job.job_id,
        )

    async def persist_graph_job(
        self,
        job: RagGraphJobRecord,
    ) -> RagRecordPersistenceResult:
        return RagRecordPersistenceResult.succeeded(
            record_id=job.job_id,
        )

    async def list_graph_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagGraphJobRecord]:
        return ()

    async def persist_query_log(
        self,
        query: RagQueryLogRecord,
    ) -> RagRecordPersistenceResult:
        return RagRecordPersistenceResult.succeeded(
            record_id=query.query_id,
        )

    async def get_query_log(
        self,
        query_id: str,
    ) -> RagQueryLogRecord | None:
        return None

    async def persist_answer_log(
        self,
        answer: RagAnswerLogRecord,
    ) -> RagRecordPersistenceResult:
        return RagRecordPersistenceResult.succeeded(
            record_id=answer.answer_id,
        )

    async def list_answer_logs(
        self,
        *,
        query_id: str | None = None,
    ) -> Sequence[RagAnswerLogRecord]:
        return ()

    async def mark_source_eligibility(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> RagSourceEligibilityResult:
        self.marked.append(
            eligibility,
        )
        return RagSourceEligibilityResult.succeeded(
            eligibility_id=eligibility.eligibility_id,
        )

    async def unmark_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityResult:
        self.unmarked.append(
            (
                source_table,
                source_id,
                source_type,
            )
        )
        return RagSourceEligibilityResult.succeeded(
            eligibility_id="rag_source_eligibility:reports:morning_report:report-1",
            records_persisted=1,
        )

    async def get_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityRecord | None:
        for record in self.records:
            if record.source_key == (
                source_table,
                source_type,
                source_id,
            ):
                return record
        return None

    async def list_source_eligibility(
        self,
        *,
        source_table: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        eligible: bool | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]:
        self.list_filters = {
            "source_table": source_table,
            "source_id": source_id,
            "source_type": source_type,
            "eligible": eligible,
        }
        return tuple(
            record
            for record in self.records
            if (source_table is None or record.source_table == source_table)
            and (source_id is None or record.source_id == source_id)
            and (source_type is None or record.source_type == source_type)
            and (eligible is None or record.eligible == eligible)
        )


@pytest.mark.asyncio
async def test_rag_eligibility_service_marks_and_unmarks_metadata_only_records() -> (
    None
):
    repository = FakeRagPersistenceRepository()
    service = RagEligibilityPersistenceService(repository)
    eligibility = _eligibility()

    mark_result = await service.mark_source_eligibility(
        eligibility,
    )
    unmark_result = await service.unmark_source_eligibility(
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
    )

    assert mark_result.success is True
    assert repository.marked == [eligibility]
    assert unmark_result.success is True
    assert repository.unmarked == [("reports", "report-1", "morning_report")]


@pytest.mark.asyncio
async def test_rag_eligibility_service_gets_and_lists_filtered_sources() -> None:
    repository = FakeRagPersistenceRepository(records=(_eligibility(),))
    service = RagEligibilityPersistenceService(repository)

    record = await service.get_source_eligibility(
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
    )
    records = await service.list_source_eligibility(
        RagEligibilityPersistenceFilters(
            source_table=" reports ",
            source_type=" morning_report ",
            eligible=True,
        )
    )

    assert record == _eligibility()
    assert records == (_eligibility(),)
    assert repository.list_filters == {
        "source_table": "reports",
        "source_id": None,
        "source_type": "morning_report",
        "eligible": True,
    }


@pytest.mark.asyncio
async def test_rag_eligibility_service_returns_typed_list_result_envelope() -> None:
    repository = FakeRagPersistenceRepository(records=(_eligibility(),))
    service = RagEligibilityPersistenceService(repository)

    result = await service.list_source_eligibility_result(
        RagEligibilityPersistenceFilters(
            source_table="reports",
            source_type="morning_report",
            eligible=True,
        )
    )

    assert result.records == (_eligibility(),)
    assert result.total_count == 1
    assert result.returned_count == 1
    assert result.query is not None
    assert result.query.metadata["record_type"] == "rag_source_eligibility"
    assert result.query.metadata["source_table"] == "reports"
    assert result.query.metadata["source_type"] == "morning_report"
    assert result.query.metadata["eligible"] is True


def _eligibility() -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id="rag_source_eligibility:reports:morning_report:report-1",
        source_table="reports",
        source_id="report-1",
        source_type="morning_report",
        eligible=True,
        reason="Curated report is suitable for future RAG source building.",
        quality_score=0.91,
        reviewed_timestamp=datetime(2026, 5, 30, tzinfo=timezone.utc),
        metadata={"reviewer": "default_rules"},
    )
