from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from datetime import timezone
from typing import cast

import pytest

from application.rag.generation import RagAnswerGenerator
from application.rag.routing.query_routing_models import RagQueryModelExecution
from application.rag.graphs import RagCorrectiveAction
from application.rag.contracts.rag_quality_models import RagReflectionScores
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_context import RagRetrievalFilters
from application.rag.retrieval.rag_retriever import RagRetrievalResult
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_result import RagResult
from application.rag.rag_service import RagService
from application.rag.contracts.rag_context import RagSource
from core.storage.persistence.rag import JsonObject
from core.storage.persistence.rag import RagAnswerLogRecord
from core.storage.persistence.rag import RagChunkRecord
from core.storage.persistence.rag import RagDocumentRecord
from core.storage.persistence.rag import RagEmbeddingJobRecord
from core.storage.persistence.rag import RagGraphJobRecord
from core.storage.persistence.rag import RagPersistenceRepository
from core.storage.persistence.rag import RagPersistenceResult
from core.storage.persistence.rag import RagQueryLogRecord
from core.storage.persistence.rag import RagQueryModelExecutionRecord
from core.storage.persistence.rag import RagQueryReflectionScores
from core.storage.persistence.rag import RagRecordPersistenceResult
from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import RagSourceEligibilityResult
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationRequest,
)
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationResult,
)


@pytest.mark.asyncio
async def test_rag_service_run_persists_success_query_and_answer_logs() -> None:
    request = RagRequest(
        query="  Summarize SPY breadth.  ",
        filters=RagRetrievalFilters(symbols=("SPY",)),
        top_k=2,
        requester="unit-test",
        workflow_name="morning_report",
        execution_id="exec-1",
        request_id="rag_query:service-success",
    )
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    repository = FakeRagRepository()
    retriever = FakeRetriever(
        contexts=(context,),
    )
    answer_provider = FakeAnswerProvider(
        result=RagAnswerGenerationResult(
            answer_text="SPY breadth improved with broad participation [C1].",
            model="unit-test-model",
            provider_name="unit-test-provider",
            confidence_score=0.88,
        )
    )
    service = RagService(
        pipeline=FakePipeline(
            retriever=retriever,
            answer_generator=RagAnswerGenerator(
                answer_provider=answer_provider,
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
    )

    result = await service.run(
        request,
    )

    assert result.status == "answered"
    assert result.citations == (context.source,)
    assert [log.status for log in repository.query_logs] == ["started", "answered"]
    final_query_log = repository.query_logs[-1]
    assert final_query_log.query_id == request.request_id
    assert final_query_log.normalized_query == "Summarize SPY breadth."
    assert final_query_log.completed_at is not None
    assert final_query_log.duration_ms is not None
    assert final_query_log.duration_ms >= 0.0
    assert final_query_log.filters["symbols"] == ["SPY"]
    assert final_query_log.context_count == 1
    assert final_query_log.citation_count == 1
    assert repository.answer_logs[0].query_id == request.request_id
    assert repository.answer_logs[0].status == "answered"
    assert repository.answer_logs[0].generation_model == "unit-test-model"
    assert repository.answer_logs[0].confidence_score == 0.88
    assert repository.answer_logs[0].source_count == 1
    assert repository.answer_logs[0].answer_hash is not None
    assert answer_provider.requests[0].query == "Summarize SPY breadth."


@pytest.mark.asyncio
async def test_rag_service_does_not_persist_raw_transient_web_context_payload() -> None:
    raw_web_payload = "RAW_FIRECRAWL_PAGE_BODY_DO_NOT_PERSIST"
    request = RagRequest(
        query="What changed today?",
        allow_web=True,
        request_id="rag_query:transient-web-persistence",
    )
    base_context = _context(context_id="web-result-1", text=raw_web_payload)
    web_context = replace(
        base_context,
        retrieval_route="web",
        metadata={"transient": True},
        source=replace(
            base_context.source,
            source_table="web_fallback",
            source_id="https://example.test/market-update",
            source_type="firecrawl_web",
            document_id="transient-web-document-1",
            chunk_id="transient-web-result-1",
            metadata={"transient": True},
        ),
    )
    result = RagResult(
        query_id=request.request_id,
        request=request,
        answer_text="Markets changed after the policy update [C1].",
        status="answered",
        route="web_fallback",
        contexts=(web_context,),
        citations=(web_context.source,),
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=StaticResultPipeline(result),
        repository=cast(RagPersistenceRepository, repository),
    )

    await service.run(request)

    persisted_logs = repr((repository.query_logs, repository.answer_logs))
    assert raw_web_payload not in persisted_logs
    assert repository.answer_logs[0].sources["items"]
    assert repository.answer_logs[0].metadata["route"] == "web_fallback"


@pytest.mark.asyncio
async def test_rag_service_persists_query_model_execution_metadata() -> None:
    execution = RagQueryModelExecution(
        operation="adaptive_triage",
        configured_model="qwen2.5:7b",
        provider_name="ollama",
        duration_ms=14.25,
        success=True,
    )
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:model-execution-metadata",
        metadata={"model_executions": [execution.to_dict()]},
    )
    repository = FakeRagRepository()
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(contexts=(context,)),
            answer_generator=RagAnswerGenerator(
                answer_provider=FakeAnswerProvider(
                    result=RagAnswerGenerationResult(
                        answer_text="SPY breadth improved [C1].",
                        model="unit-test-model",
                        provider_name="unit-test-provider",
                    )
                )
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
    )

    await service.run(request)

    assert repository.query_logs[-1].model_executions == (
        RagQueryModelExecutionRecord(
            operation="adaptive_triage",
            configured_model="qwen2.5:7b",
            provider_name="ollama",
            duration_ms=14.25,
            success=True,
        ),
    )
    assert repository.query_logs[-1].metadata == {}


@pytest.mark.asyncio
async def test_rag_service_emits_observability_for_generation_and_log_persistence() -> (
    None
):
    telemetry, sink, observability = _telemetry()
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:service-observability",
    )
    repository = FakeRagRepository()
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    answer_provider = FakeAnswerProvider(
        result=RagAnswerGenerationResult(
            answer_text="SPY breadth improved with broad participation [C1].",
            model="unit-test-model",
            provider_name="unit-test-provider",
            confidence_score=0.88,
        )
    )
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(
                contexts=(context,),
            ),
            answer_generator=RagAnswerGenerator(
                answer_provider=answer_provider,
                telemetry=telemetry,
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
        telemetry=telemetry,
    )

    result = await service.run(
        request,
    )

    operations = _operations(
        sink,
    )
    assert result.status == "answered"
    assert "rag.service.run" in operations
    assert operations.count("rag.persistence.query_log") == 2
    assert "rag.persistence.answer_log" in operations
    assert "rag.generation.answer" in operations
    assert "rag.generation.context_packaging" in operations
    assert "rag.generation.provider_call" in operations
    assert any(
        point.name == "application.rag.operations.total"
        for point in observability.metrics_store.points()
    )
    assert any(
        point.name == "application.rag.operation.duration_seconds"
        for point in observability.metrics_store.points()
    )


@pytest.mark.asyncio
async def test_rag_service_run_persists_no_results_when_retrieval_is_empty() -> None:
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:service-no-results",
    )
    repository = FakeRagRepository()
    answer_provider = FakeAnswerProvider(
        result=RagAnswerGenerationResult(
            answer_text="This provider should not be called.",
        )
    )
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(contexts=()),
            answer_generator=RagAnswerGenerator(answer_provider=answer_provider),
        ),
        repository=cast(RagPersistenceRepository, repository),
    )

    result = await service.run(
        request,
    )

    assert result.status == "no_results"
    assert result.answer_text == "No relevant curated RAG context was found."
    assert answer_provider.requests == ()
    assert [log.status for log in repository.query_logs] == ["started", "no_results"]
    assert repository.answer_logs[0].status == "no_results"
    assert repository.answer_logs[0].source_count == 0


@pytest.mark.asyncio
async def test_rag_service_run_persists_failed_generation_result() -> None:
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:service-generation-failure",
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(
                contexts=(
                    _context(
                        context_id="chunk-1",
                        text="SPY breadth deteriorated.",
                    ),
                )
            ),
            answer_generator=RagAnswerGenerator(
                answer_provider=FakeAnswerProvider(
                    error=RuntimeError("model unavailable"),
                )
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
    )

    result = await service.run(
        request,
    )

    assert result.status == "failed"
    assert result.error == "model unavailable"
    assert [log.status for log in repository.query_logs] == ["started", "failed"]
    assert repository.query_logs[-1].error == "model unavailable"
    assert repository.answer_logs[0].status == "failed"
    assert (
        repository.answer_logs[0].answer_text == "RAG request failed: model unavailable"
    )


@pytest.mark.asyncio
async def test_rag_service_run_persists_failed_retrieval_result() -> None:
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:service-retrieval-failure",
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(
                error=RuntimeError("retriever unavailable"),
            ),
            answer_generator=RagAnswerGenerator(
                answer_provider=FakeAnswerProvider(
                    result=RagAnswerGenerationResult(
                        answer_text="This provider should not be called.",
                    )
                )
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
    )

    result = await service.run(
        request,
    )

    assert result.status == "failed"
    assert result.error == "retriever unavailable"
    assert [log.status for log in repository.query_logs] == ["started", "failed"]
    assert repository.answer_logs[0].status == "failed"
    assert repository.answer_logs[0].source_count == 0


class FakePipeline:
    def __init__(
        self,
        *,
        retriever: "FakeRetriever",
        answer_generator: RagAnswerGenerator,
    ) -> None:
        self._retriever = retriever
        self._answer_generator = answer_generator

    async def run(
        self,
        request: RagRequest,
    ) -> RagResult:
        retrieval = await self._retriever.retrieve(request)
        return await self._answer_generator.generate(
            request=request,
            contexts=retrieval.contexts,
        )


class FakeRetriever:
    def __init__(
        self,
        *,
        contexts: tuple[RagRetrievedContext, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.contexts = contexts
        self.error = error
        self.requests: tuple[RagRequest, ...] = ()

    async def retrieve(
        self,
        request: RagRequest,
    ) -> RagRetrievalResult:
        self.requests = self.requests + (request,)
        if self.error is not None:
            raise self.error
        return RagRetrievalResult(
            request_id=request.request_id,
            route=request.route,
            contexts=self.contexts,
        )


class FakeAnswerProvider:
    def __init__(
        self,
        *,
        result: RagAnswerGenerationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.requests: tuple[RagAnswerGenerationRequest, ...] = ()

    async def generate_answer(
        self,
        request: RagAnswerGenerationRequest,
    ) -> RagAnswerGenerationResult:
        self.requests = self.requests + (request,)
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise RuntimeError("missing fake answer result")
        return self.result


class FakeRagRepository:
    def __init__(
        self,
    ) -> None:
        self.query_logs: list[RagQueryLogRecord] = []
        self.answer_logs: list[RagAnswerLogRecord] = []

    async def persist_document(
        self,
        document: RagDocumentRecord,
        *,
        chunks: Sequence[RagChunkRecord] = (),
        embedding_jobs: Sequence[RagEmbeddingJobRecord] = (),
    ) -> RagPersistenceResult:
        return RagPersistenceResult.succeeded(
            document_id=document.document_id,
        )

    async def get_document(
        self,
        document_id: str,
    ) -> RagDocumentRecord | None:
        return None

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
        self.query_logs.append(query)
        return RagRecordPersistenceResult.succeeded(
            record_id=query.query_id,
        )

    async def get_query_log(
        self,
        query_id: str,
    ) -> RagQueryLogRecord | None:
        for query_log in self.query_logs:
            if query_log.query_id == query_id:
                return query_log
        return None

    async def persist_answer_log(
        self,
        answer: RagAnswerLogRecord,
    ) -> RagRecordPersistenceResult:
        self.answer_logs.append(answer)
        return RagRecordPersistenceResult.succeeded(
            record_id=answer.answer_id,
        )

    async def list_answer_logs(
        self,
        *,
        query_id: str | None = None,
    ) -> Sequence[RagAnswerLogRecord]:
        if query_id is None:
            return tuple(self.answer_logs)
        return tuple(
            answer for answer in self.answer_logs if answer.query_id == query_id
        )

    async def mark_source_eligibility(
        self,
        eligibility: RagSourceEligibilityRecord,
    ) -> RagSourceEligibilityResult:
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
        return RagSourceEligibilityResult.succeeded(
            eligibility_id="eligibility-1",
        )

    async def get_source_eligibility(
        self,
        *,
        source_table: str,
        source_id: str,
        source_type: str,
    ) -> RagSourceEligibilityRecord | None:
        return None

    async def list_source_eligibility(
        self,
        *,
        source_table: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        eligible: bool | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]:
        return ()


def _context(
    *,
    context_id: str,
    text: str,
) -> RagRetrievedContext:
    return RagRetrievedContext(
        context_id=context_id,
        text=text,
        source=RagSource(
            source_table="reports",
            source_id="report-1",
            source_type="morning_report",
            document_id="document-1",
            title="Morning Report",
            chunk_id=context_id,
            section_name="market_breadth",
            generated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            workflow_name="morning_report",
            execution_id="exec-1",
            metadata={"symbol": "SPY"},
        ),
        score=0.91,
        rank=1,
        retrieval_route="hybrid",
        metadata={"fused_score": 0.91},
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


@pytest.mark.asyncio
async def test_rag_service_persists_quality_metadata() -> None:
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:quality-metadata",
    )
    scores = RagReflectionScores(
        retrieval_necessity=0.9,
        source_relevance=0.8,
        answer_support=0.7,
        usefulness=0.6,
    )
    result = RagResult(
        query_id=request.request_id,
        request=request,
        answer_text="Grounded answer.",
        status="answered",
        route="hybrid",
        grounding_score=0.7,
        utility_score=0.6,
        reflection_scores=scores,
        corrective_actions=(RagCorrectiveAction.REWRITE, RagCorrectiveAction.PROCEED),
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=StaticResultPipeline(result),
        repository=cast(RagPersistenceRepository, repository),
    )

    await service.run(request)

    query_log = repository.query_logs[-1]
    answer_metadata = repository.answer_logs[-1].metadata
    assert query_log.grounding_score == 0.7
    assert query_log.utility_score == 0.6
    assert query_log.reflection_scores == RagQueryReflectionScores(
        retrieval_necessity=0.9,
        source_relevance=0.8,
        answer_support=0.7,
        usefulness=0.6,
    )
    assert query_log.corrective_actions == ("rewrite", "proceed")
    assert query_log.metadata == {}
    assert "grounding_score" not in answer_metadata
    assert "reflection_scores" not in answer_metadata


class StaticResultPipeline:
    def __init__(self, result: RagResult) -> None:
        self._result = result

    async def run(self, request: RagRequest) -> RagResult:
        del request
        return self._result


class ExplodingPipeline:
    async def run(self, request: RagRequest) -> RagResult:
        del request
        raise RuntimeError("pipeline unavailable")


@pytest.mark.asyncio
async def test_rag_service_pipeline_exception_is_owned_by_canonical_telemetry() -> None:
    telemetry, sink, _ = _telemetry()
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:pipeline-exception",
    )
    service = RagService(
        pipeline=ExplodingPipeline(),
        repository=cast(RagPersistenceRepository, FakeRagRepository()),
        telemetry=telemetry,
    )

    result = await service.run(request)

    assert result.status == "failed"
    terminal_event = next(
        event
        for event in sink.events
        if event.attributes.get("operation") == "rag.service.run"
        and event.event_type == "application.rag.operation.failed"
    )
    assert terminal_event.exception_details is not None
    assert terminal_event.exception_details.exception_type == "RuntimeError"
    assert terminal_event.exception_details.message == "pipeline unavailable"
