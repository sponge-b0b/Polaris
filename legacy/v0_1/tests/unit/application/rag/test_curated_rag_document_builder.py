from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from application.rag.ingestion.curated_rag_document_builder import (
    CuratedRagDocumentBuilder,
    CuratedRagIngestionService,
)
from application.rag.ingestion.curated_rag_models import (
    CuratedRagBuildOptions,
    CuratedRagSourceNotEligibleError,
)
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.agent_signals import JsonObject as AgentSignalJsonObject
from core.storage.persistence.rag import (
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    RagPersistenceRepository,
    RagPersistenceResult,
    RagRecordPersistenceResult,
    RagSourceEligibilityRecord,
    RagSourceEligibilityResult,
    new_rag_source_eligibility_id,
)
from core.storage.persistence.reports import ReportRecord
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink


def test_builder_creates_rag_document_from_curated_report() -> None:
    report = _report()
    builder = CuratedRagDocumentBuilder()

    bundle = builder.build_from_report(
        report,
        options=CuratedRagBuildOptions(
            max_chunk_characters=80,
            queue_embedding_jobs=True,
            target_store="qdrant",
            embedding_model="bge-large",
        ),
    )

    assert bundle.document.source_table == "reports"
    assert bundle.document.source_id == report.report_id
    assert bundle.document.source_type == "morning_report"
    assert bundle.document.content_text == report.markdown_body
    assert bundle.document.workflow_name == "morning_report"
    assert bundle.document.execution_id == "exec-1"
    assert bundle.document.metadata["curated_source"] is True
    assert len(bundle.chunks) > 1
    assert len(bundle.embedding_jobs) == len(bundle.chunks)
    assert all(job.status == "queued" for job in bundle.embedding_jobs)


def test_report_chunking_preserves_section_boundaries_and_lineage_metadata() -> None:
    report = _report(
        markdown_body=(
            "# Morning Report\n\n"
            "## Executive Summary\n\n"
            "SPY strength improved during the session.\n\n"
            "## Risk Assessment\n\n"
            "Drawdown risk remains moderate."
        ),
    )
    builder = CuratedRagDocumentBuilder()

    bundle = builder.build_from_report(
        report,
        options=CuratedRagBuildOptions(
            max_chunk_characters=10_000,
            queue_embedding_jobs=True,
        ),
    )

    assert [chunk.metadata["section_name"] for chunk in bundle.chunks] == [
        "executive_summary",
        "risk_assessment",
    ]
    assert bundle.chunks[0].chunk_text.startswith("## Executive Summary")
    assert bundle.chunks[1].chunk_text.startswith("## Risk Assessment")
    for chunk in bundle.chunks:
        assert chunk.metadata["chunking_strategy"] == "record_aware_markdown_sections"
        assert chunk.metadata["source_table"] == "reports"
        assert chunk.metadata["source_record_id"] == report.report_id
        assert chunk.metadata["source_type"] == report.report_type
        assert chunk.metadata["parent_document_id"] == bundle.document.document_id
        assert chunk.metadata["workflow_name"] == report.workflow_name
        assert chunk.metadata["execution_id"] == report.execution_id
        assert chunk.metadata["runtime_id"] == report.runtime_id
        assert chunk.metadata["symbol"] == "SPY"
        assert chunk.metadata["embedding_status"] == "queued"
        assert chunk.metadata["graph_status"] == "not_queued"


def test_agent_signal_chunking_creates_semantic_sections_with_signal_metadata() -> None:
    signal = _agent_signal(
        llm_response="Full detailed LLM response for attribution.",
    )
    builder = CuratedRagDocumentBuilder()

    bundle = builder.build_from_agent_signal(
        signal,
        options=CuratedRagBuildOptions(
            max_chunk_characters=10_000,
            queue_embedding_jobs=False,
        ),
    )

    section_names = [chunk.metadata["section_name"] for chunk in bundle.chunks]
    assert section_names == [
        "technicalagent_signal_spy",
        "signals",
        "risks",
        "recommendations",
        "features",
        "reasoning",
        "llm_response",
    ]
    assert bundle.chunks[-1].chunk_text.endswith(signal.llm_response or "")
    for chunk in bundle.chunks:
        assert chunk.metadata["source_table"] == "agent_signals"
        assert chunk.metadata["source_record_id"] == signal.signal_id
        assert chunk.metadata["agent_name"] == "TechnicalAgent"
        assert chunk.metadata["agent_type"] == "technical"
        assert chunk.metadata["symbol"] == "SPY"
        assert chunk.metadata["confidence"] == signal.confidence
        assert chunk.metadata["directional_score"] == signal.directional_score
        assert chunk.metadata["embedding_status"] == "not_queued"


def test_long_report_section_splits_deterministically_with_section_metadata() -> None:
    report = _report(
        markdown_body=(
            "## Technical Setup\n\n"
            "First deterministic paragraph for technical context.\n\n"
            + ("Second deterministic paragraph with breadth evidence. " * 10)
            + "\n\nFinal deterministic paragraph."
        ),
    )
    builder = CuratedRagDocumentBuilder()

    first_bundle = builder.build_from_report(
        report,
        options=CuratedRagBuildOptions(
            max_chunk_characters=160,
        ),
    )
    second_bundle = builder.build_from_report(
        report,
        options=CuratedRagBuildOptions(
            max_chunk_characters=160,
        ),
    )

    assert len(first_bundle.chunks) > 1
    assert [chunk.chunk_text for chunk in first_bundle.chunks] == [
        chunk.chunk_text for chunk in second_bundle.chunks
    ]
    assert [chunk.chunk_id for chunk in first_bundle.chunks] == [
        chunk.chunk_id for chunk in second_bundle.chunks
    ]
    for index, chunk in enumerate(first_bundle.chunks):
        assert chunk.chunk_text.startswith("## Technical Setup")
        assert chunk.metadata["section_name"] == "technical_setup"
        assert chunk.metadata["section_chunk_index"] == index
        assert len(chunk.chunk_text) <= 160


def test_builder_does_not_queue_embedding_jobs_by_default() -> None:
    report = _report()
    builder = CuratedRagDocumentBuilder()

    bundle = builder.build_from_report(
        report,
        options=CuratedRagBuildOptions(
            max_chunk_characters=80,
        ),
    )

    assert bundle.document.source_table == "reports"
    assert len(bundle.chunks) > 1
    assert bundle.embedding_jobs == ()


def test_builder_creates_rag_document_from_agent_signal_without_truncation() -> None:
    full_llm_response = "Full detailed LLM response. " * 120
    signal = _agent_signal(
        llm_response=full_llm_response,
    )
    builder = CuratedRagDocumentBuilder()

    bundle = builder.build_from_agent_signal(
        signal,
        options=CuratedRagBuildOptions(
            max_chunk_characters=500,
            queue_embedding_jobs=False,
        ),
    )

    assert bundle.document.source_table == "agent_signals"
    assert bundle.document.source_id == signal.signal_id
    assert bundle.document.source_type == "technical"
    assert bundle.document.title == "TechnicalAgent Signal - SPY"
    assert "## Signals" in bundle.document.content_text
    assert "## LLM Response" in bundle.document.content_text
    assert full_llm_response in bundle.document.content_text
    assert bundle.document.metadata["agent_name"] == "TechnicalAgent"
    assert bundle.embedding_jobs == ()


def test_builder_excludes_reasoning_traces_from_curated_agent_signal_document() -> None:
    signal = _agent_signal(
        llm_response="```reasoning\nprivate model trace\n```\nVisible model response.",
        reasoning_text="<think>private reasoning</think>\nVisible technical rationale.",
        metadata={
            "chain_of_thought": "private metadata trace",
            "source": "unit-test",
        },
    )
    builder = CuratedRagDocumentBuilder()

    bundle = builder.build_from_agent_signal(
        signal,
        options=CuratedRagBuildOptions(
            max_chunk_characters=10_000,
            queue_embedding_jobs=False,
        ),
    )

    assert "Visible model response." in bundle.document.content_text
    assert "Visible technical rationale." in bundle.document.content_text
    assert "private" not in bundle.document.content_text
    assert "chain_of_thought" not in str(bundle.document.metadata)


def test_builder_applies_eligibility_gate_only_when_explicitly_enabled() -> None:
    signal = _agent_signal(
        llm_response="",
        empty_payloads=True,
    )
    builder = CuratedRagDocumentBuilder()

    legacy_bundle = builder.build_from_agent_signal(
        signal,
        options=CuratedRagBuildOptions(
            queue_embedding_jobs=False,
        ),
    )

    assert legacy_bundle.document.source_table == "agent_signals"
    assert legacy_bundle.document.metadata["rag_eligibility_required"] is False
    assert legacy_bundle.document.metadata["rag_eligibility_rule_name"] == (
        "missing_meaningful_content_ineligible"
    )

    with pytest.raises(CuratedRagSourceNotEligibleError, match="not eligible"):
        builder.build_from_agent_signal(
            signal,
            options=CuratedRagBuildOptions(
                queue_embedding_jobs=False,
                require_source_eligibility=True,
            ),
        )


@pytest.mark.asyncio
async def test_ingestion_service_uses_default_eligibility_gate_when_enabled() -> None:
    repository = FakeRagPersistenceRepository()
    service = CuratedRagIngestionService(
        cast(
            RagPersistenceRepository,
            repository,
        )
    )

    result = await service.persist_source(
        _report(),
        options=CuratedRagBuildOptions(
            max_chunk_characters=1000,
            queue_embedding_jobs=False,
            require_source_eligibility=True,
        ),
    )

    assert result.success is True
    assert repository.source_eligibility_get_calls == 1
    assert repository.persisted_document is not None
    assert repository.persisted_document.metadata["rag_eligibility_required"] is True
    assert repository.persisted_document.metadata["rag_eligibility_rule_name"] == (
        "curated_report_eligible"
    )


@pytest.mark.asyncio
async def test_ingestion_blocks_persisted_ineligible_source_before_building() -> None:
    report = _report()
    repository = FakeRagPersistenceRepository(
        eligibility=_source_eligibility_record(
            source_table="reports",
            source_id=report.report_id,
            source_type=report.report_type,
            eligible=False,
            reason="Manual review rejected this report.",
        )
    )
    service = CuratedRagIngestionService(
        cast(
            RagPersistenceRepository,
            repository,
        )
    )

    result = await service.persist_source(
        report,
        options=CuratedRagBuildOptions(
            require_source_eligibility=True,
        ),
    )

    assert result.success is False
    assert result.error is not None
    assert "Manual review rejected this report" in result.error
    assert repository.source_eligibility_get_calls == 1
    assert repository.persisted_document is None
    assert repository.persisted_chunks == ()
    assert repository.persisted_embedding_jobs == ()


@pytest.mark.asyncio
async def test_ingestion_service_respects_persisted_eligible_override() -> None:
    signal = _agent_signal(
        llm_response="",
        empty_payloads=True,
    )
    eligibility = _source_eligibility_record(
        source_table="agent_signals",
        source_id=signal.signal_id,
        source_type=signal.agent_type,
        eligible=True,
        reason="Manual review approved this signal.",
    )
    repository = FakeRagPersistenceRepository(
        eligibility=eligibility,
    )
    service = CuratedRagIngestionService(
        cast(
            RagPersistenceRepository,
            repository,
        )
    )

    result = await service.persist_source(
        signal,
        options=CuratedRagBuildOptions(
            queue_embedding_jobs=False,
            require_source_eligibility=True,
        ),
    )

    assert result.success is True
    assert repository.source_eligibility_get_calls == 1
    assert repository.persisted_document is not None
    assert repository.persisted_document.source_id == signal.signal_id
    assert repository.persisted_document.metadata["rag_eligibility_required"] is True
    assert repository.persisted_document.metadata["rag_eligibility_id"] == (
        eligibility.eligibility_id
    )
    assert repository.persisted_document.metadata["rag_eligibility_rule_name"] is None
    assert repository.persisted_embedding_jobs == ()


@pytest.mark.asyncio
async def test_ingestion_service_preserves_legacy_persistence_when_gate_disabled() -> (
    None
):
    report = _report()
    repository = FakeRagPersistenceRepository(
        eligibility=_source_eligibility_record(
            source_table="reports",
            source_id=report.report_id,
            source_type=report.report_type,
            eligible=False,
            reason="Manual review rejected this report.",
        )
    )
    service = CuratedRagIngestionService(
        cast(
            RagPersistenceRepository,
            repository,
        )
    )

    result = await service.persist_source(
        report,
        options=CuratedRagBuildOptions(
            queue_embedding_jobs=False,
        ),
    )

    assert result.success is True
    assert repository.source_eligibility_get_calls == 0
    assert repository.persisted_document is not None
    assert repository.persisted_document.source_id == report.report_id


def test_builder_rejects_raw_runtime_dump_payloads() -> None:
    builder = CuratedRagDocumentBuilder()

    raw_runtime_dump = cast(
        Any,
        {
            "workflow_runs": {
                "execution_id": "exec-1",
                "outputs": {"raw": "runtime dump"},
            }
        },
    )

    with pytest.raises(TypeError, match="raw runtime dumps"):
        builder.build_from_source(raw_runtime_dump)


@pytest.mark.asyncio
async def test_ingestion_service_persists_builder_bundle_through_repository() -> None:
    repository = FakeRagPersistenceRepository()
    service = CuratedRagIngestionService(
        cast(
            RagPersistenceRepository,
            repository,
        )
    )

    result = await service.persist_source(
        _report(),
        options=CuratedRagBuildOptions(
            max_chunk_characters=1000,
            queue_embedding_jobs=True,
        ),
    )

    assert result.success is True
    assert repository.persisted_document is not None
    assert repository.persisted_document.source_table == "reports"
    assert repository.persisted_chunks
    assert repository.persisted_embedding_jobs


@pytest.mark.asyncio
async def test_ingestion_retry_preserves_canonical_records_without_duplicates() -> None:
    repository = FakeRagPersistenceRepository()
    service = CuratedRagIngestionService(
        cast(
            RagPersistenceRepository,
            repository,
        )
    )
    options = CuratedRagBuildOptions(
        max_chunk_characters=120,
        queue_embedding_jobs=True,
    )

    first_result = await service.persist_source(
        _report(),
        options=options,
    )
    first_bundle_ids = repository.last_bundle_ids
    second_result = await service.persist_source(
        _report(),
        options=options,
    )

    assert first_result.success is True
    assert second_result.success is True
    assert repository.persist_document_calls == 2
    assert repository.last_bundle_ids == first_bundle_ids
    assert len(repository.documents_by_id) == 1
    assert len(repository.chunks_by_id) == len(repository.persisted_chunks)
    assert len(repository.embedding_jobs_by_id) == len(
        repository.persisted_embedding_jobs
    )


@pytest.mark.asyncio
async def test_ingestion_service_emits_observability_for_build_and_persistence() -> (
    None
):
    telemetry, sink, observability = _telemetry()
    repository = FakeRagPersistenceRepository()
    service = CuratedRagIngestionService(
        cast(
            RagPersistenceRepository,
            repository,
        ),
        telemetry=telemetry,
    )

    result = await service.persist_source(
        _report(),
        options=CuratedRagBuildOptions(
            max_chunk_characters=1000,
            queue_embedding_jobs=True,
            require_source_eligibility=True,
        ),
    )

    operations = _operations(
        sink,
    )
    assert result.success is True
    assert "rag.ingestion.persist_source" in operations
    assert "rag.ingestion.eligibility" in operations
    assert "rag.ingestion.build_bundle" in operations
    assert "rag.ingestion.persist_bundle" in operations
    assert any(
        point.name == "application.rag.operations.total"
        for point in observability.metrics_store.points()
    )


def test_build_options_default_to_canonical_rag_hybrid_embedding_model() -> None:
    assert CuratedRagBuildOptions().embedding_model == "BAAI/bge-m3"


def test_build_options_validate_embedding_queue_settings() -> None:
    with pytest.raises(ValueError, match="max_chunk_characters"):
        CuratedRagBuildOptions(
            max_chunk_characters=0,
        )

    with pytest.raises(ValueError, match="target_store"):
        CuratedRagBuildOptions(
            target_store=" ",
        )


class FakeRagPersistenceRepository:
    def __init__(
        self,
        eligibility: RagSourceEligibilityRecord | None = None,
    ) -> None:
        self.persisted_document: RagDocumentRecord | None = None
        self.persisted_chunks: tuple[RagChunkRecord, ...] = ()
        self.persisted_embedding_jobs: tuple[RagEmbeddingJobRecord, ...] = ()
        self.documents_by_id: dict[str, RagDocumentRecord] = {}
        self.chunks_by_id: dict[str, RagChunkRecord] = {}
        self.embedding_jobs_by_id: dict[str, RagEmbeddingJobRecord] = {}
        self.persist_document_calls = 0
        self.source_eligibility = eligibility
        self.source_eligibility_get_calls = 0

    @property
    def last_bundle_ids(
        self,
    ) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
        return (
            (
                self.persisted_document.document_id
                if self.persisted_document is not None
                else None
            ),
            tuple(chunk.chunk_id for chunk in self.persisted_chunks),
            tuple(job.job_id for job in self.persisted_embedding_jobs),
        )

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult:
        self.persist_document_calls += 1
        self.persisted_document = document
        self.persisted_chunks = tuple(chunks)
        self.persisted_embedding_jobs = tuple(embedding_jobs)
        self.documents_by_id[document.document_id] = document
        self.chunks_by_id.update((chunk.chunk_id, chunk) for chunk in chunks)
        self.embedding_jobs_by_id.update((job.job_id, job) for job in embedding_jobs)

        return RagPersistenceResult.succeeded(
            document_id=document.document_id,
            records_persisted=1 + len(chunks) + len(embedding_jobs),
        )

    async def get_document(
        self,
        document_id: str,
    ) -> RagDocumentRecord | None:
        return self.persisted_document if self.persisted_document is not None else None

    async def list_chunks(
        self,
        document_id: str,
    ) -> Sequence[RagChunkRecord]:
        return self.persisted_chunks

    async def get_chunk(
        self,
        chunk_id: str,
    ) -> RagChunkRecord | None:
        for chunk in self.persisted_chunks:
            if chunk.chunk_id == chunk_id:
                return chunk
        return None

    async def list_embedding_jobs(
        self,
        *,
        status: str | None = None,
    ) -> Sequence[RagEmbeddingJobRecord]:
        if status is None:
            return self.persisted_embedding_jobs

        return tuple(
            job for job in self.persisted_embedding_jobs if job.status == status
        )

    async def persist_embedding_job(
        self,
        job: RagEmbeddingJobRecord,
    ) -> RagRecordPersistenceResult:
        self.persisted_embedding_jobs = tuple(
            existing
            for existing in self.persisted_embedding_jobs
            if existing.job_id != job.job_id
        ) + (job,)
        return RagRecordPersistenceResult.succeeded(
            record_id=job.job_id,
        )

    async def mark_source_eligibility(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> RagSourceEligibilityResult:
        self.source_eligibility = eligibility
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
        self.source_eligibility = None
        return RagSourceEligibilityResult.succeeded(
            eligibility_id=new_rag_source_eligibility_id(
                source_table=source_table,
                source_id=source_id,
                source_type=source_type,
            ),
            records_persisted=0,
        )

    async def get_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityRecord | None:
        self.source_eligibility_get_calls += 1
        eligibility = self.source_eligibility
        if eligibility is None:
            return None
        if eligibility.source_key == (
            source_table,
            source_type,
            source_id,
        ):
            return eligibility
        return None

    async def list_source_eligibility(
        self,
        *,
        source_table: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        eligible: bool | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]:
        eligibility_record = self.source_eligibility
        if eligibility_record is None:
            return ()
        if source_table is not None and eligibility_record.source_table != source_table:
            return ()
        if source_id is not None and eligibility_record.source_id != source_id:
            return ()
        if source_type is not None and eligibility_record.source_type != source_type:
            return ()
        if eligible is not None and eligibility_record.eligible is not eligible:
            return ()
        return (eligibility_record,)


def _report(
    *,
    markdown_body: str | None = None,
) -> ReportRecord:
    return ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        markdown_body=markdown_body
        or "# Morning Report\n\n" + ("Full curated report section. " * 20),
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        structured_payload={"symbol": "SPY"},
    )


def _agent_signal(
    *,
    llm_response: str,
    reasoning_text: str | None = None,
    metadata: AgentSignalJsonObject | None = None,
    empty_payloads: bool = False,
) -> AgentSignalRecord:
    return AgentSignalRecord(
        signal_id="agent_signal:exec-1:TechnicalAgent:technical:SPY",
        agent_name="TechnicalAgent",
        agent_type="technical",
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical",
        symbol="SPY",
        universe=("SPY", "QQQ"),
        timestamp=datetime(2026, 5, 30, tzinfo=UTC),
        directional_score=0.6,
        confidence=0.82,
        regime="bullish",
        signals={} if empty_payloads else {"trend": "bullish"},
        risks={} if empty_payloads else {"drawdown": "moderate"},
        recommendations={} if empty_payloads else {"posture": "risk-on"},
        features={} if empty_payloads else {"rsi": 61.0},
        reasoning_text=reasoning_text
        if reasoning_text is not None
        else ("" if empty_payloads else "Full technical reasoning."),
        llm_response=llm_response,
        metadata={"source": "unit-test"} if metadata is None else metadata,
    )


def _source_eligibility_record(
    *,
    source_table: str,
    source_id: str,
    source_type: str,
    eligible: bool,
    reason: str,
) -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id=new_rag_source_eligibility_id(
            source_table=source_table,
            source_id=source_id,
            source_type=source_type,
        ),
        source_table=source_table,
        source_id=source_id,
        source_type=source_type,
        eligible=eligible,
        reason=reason,
        quality_score=0.0 if not eligible else 0.9,
        reviewed_timestamp=datetime(2026, 5, 30, tzinfo=UTC),
        metadata={"reviewer": "unit-test"},
    )


def _telemetry() -> tuple[
    ApplicationRagTelemetry,
    InMemoryTelemetrySink,
    ObservabilityManager,
]:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(
        sink,
    )
    return (
        ApplicationRagTelemetry(
            observability_manager=observability,
        ),
        sink,
        observability,
    )


def _operations(
    sink: InMemoryTelemetrySink,
) -> list[object]:
    return [event.attributes.get("operation") for event in sink.events]
