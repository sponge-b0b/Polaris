from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest

from application.decision_evidence.persistence import (
    DecisionEvidencePacketPersistenceService,
)
from application.observability import AiObservationType
from application.rag.contracts.rag_context import (
    RagRetrievalFilters,
    RagRetrievedContext,
    RagSource,
)
from application.rag.contracts.rag_generated_claims import RagGeneratedClaim
from application.rag.contracts.rag_quality_models import RagReflectionScores
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.generation import RagAnswerGenerator
from application.rag.graphs import RagCorrectiveAction
from application.rag.rag_service import RagService
from application.rag.retrieval.rag_retriever import RagRetrievalResult
from application.rag.routing.query_routing_models import RagQueryModelExecution
from core.storage.persistence.completed_run_archive import (
    CompletedRunArchive,
    CompletedRunBundle,
)
from core.storage.persistence.decision_evidence import (
    DecisionEvidencePacketPersistenceRepository,
    DecisionEvidencePacketPersistenceResult,
    DecisionEvidencePacketRecord,
)
from core.storage.persistence.rag import (
    JsonObject,
    RagAnswerLogRecord,
    RagChunkRecord,
    RagDocumentRecord,
    RagEmbeddingJobRecord,
    RagGraphJobRecord,
    RagPersistenceRepository,
    RagPersistenceResult,
    RagQueryLogRecord,
    RagQueryModelExecutionRecord,
    RagQueryReflectionScores,
    RagRecordPersistenceResult,
    RagSourceEligibilityRecord,
    RagSourceEligibilityResult,
)
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.registry.workflow_registry import WorkflowRegistry
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskTier,
    SourceOfTruthCategory,
    classify_risk_authority,
)
from domain.decision_evidence import DecisionEvidencePacket
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationRequest,
    RagAnswerGenerationResult,
)
from tests.helpers.recording_ai_observability import RecordingAiObservabilityProjector


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
            generated_claims=(_generated_claim(),),
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
        decision_evidence_packet_persistence_service=_packet_persistence(),
        workflow_registry=cast(WorkflowRegistry, _workflow_registry()),
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
async def test_rag_service_persists_contexts_for_packet_reconstruction() -> None:
    request = RagRequest(
        query="Summarize SPY breadth for the client portfolio.",
        requester="unit-test",
        workflow_name="morning_report",
        execution_id="exec-1",
        request_id="rag_query:packet-reconstruction",
        metadata={
            "rag_authority": {
                "audience": "external",
                "capital_relevant": True,
            }
        },
    )
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    repository = FakeRagRepository(
        documents=(_document_from_context(context),),
        chunks=(_chunk_from_context(context),),
    )
    packet_repository = FakeDecisionEvidencePacketRepository()
    packet_persistence = DecisionEvidencePacketPersistenceService(
        repository=cast(
            DecisionEvidencePacketPersistenceRepository,
            packet_repository,
        ),
        completed_run_archive=cast(CompletedRunArchive, FakeCompletedRunArchive()),
        rag_repository=cast(RagPersistenceRepository, repository),
    )
    answer_provider = FakeAnswerProvider(
        result=RagAnswerGenerationResult(
            answer_text="SPY breadth improved with broad participation [C1].",
            model="unit-test-model",
            provider_name="unit-test-provider",
            confidence_score=0.88,
            generated_claims=(_generated_claim(),),
        )
    )
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(contexts=(context,)),
            answer_generator=RagAnswerGenerator(
                answer_provider=answer_provider,
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
        decision_evidence_packet_persistence_service=packet_persistence,
        workflow_registry=cast(WorkflowRegistry, _workflow_registry()),
    )

    result = await service.run(request)

    assert result.evidence_packet is not None
    assert result.authority is not None
    assert result.evidence_packet.authority == result.authority
    final_query_log = repository.query_logs[-1]
    retrieved_contexts = cast(
        Sequence[Mapping[str, object]],
        final_query_log.metadata["retrieved_contexts"],
    )
    assert retrieved_contexts == (context.to_dict(),)
    assert packet_repository.records[result.evidence_packet.packet_id]
    assert result.evidence_packet.workflow_name == "morning_report"
    assert result.evidence_packet.execution_id == "exec-1"


@pytest.mark.asyncio
async def test_rag_service_ignores_request_provenance_for_packet_binding() -> None:
    request = RagRequest(
        query="Summarize SPY breadth for the client portfolio.",
        workflow_name="attacker_selected_workflow",
        execution_id="attacker-selected-execution",
        request_id="rag_query:request-provenance-substitution",
    )
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
                        answer_text=(
                            "SPY breadth improved with broad participation [C1]."
                        ),
                        model="unit-test-model",
                        provider_name="unit-test-provider",
                        generated_claims=(_generated_claim(),),
                    )
                ),
            ),
        ),
        repository=cast(RagPersistenceRepository, FakeRagRepository()),
        decision_evidence_packet_persistence_service=_packet_persistence(),
        workflow_registry=cast(WorkflowRegistry, _workflow_registry()),
    )

    result = await service.run(request)

    assert result.status == "answered"
    assert result.evidence_packet is not None
    assert result.authority is not None
    assert result.evidence_packet.authority == result.authority
    assert result.evidence_packet.workflow_name == "morning_report"
    assert result.evidence_packet.execution_id == "exec-1"


@pytest.mark.asyncio
async def test_rag_service_fails_closed_when_claim_packet_cannot_be_persisted() -> None:
    request = RagRequest(
        query="Summarize SPY breadth for the client portfolio.",
        request_id="rag_query:packet-persistence-failure",
        metadata={
            "rag_authority": {
                "audience": "external",
                "capital_relevant": True,
            }
        },
    )
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(contexts=(context,)),
            answer_generator=RagAnswerGenerator(
                answer_provider=FakeAnswerProvider(
                    result=RagAnswerGenerationResult(
                        answer_text="SPY breadth improved [C1].",
                        generated_claims=(_generated_claim(),),
                    )
                )
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
        decision_evidence_packet_persistence_service=cast(
            DecisionEvidencePacketPersistenceService,
            _PacketPersistenceDouble(fail_persistence=True),
        ),
    )

    result = await service.run(request)

    assert result.status == "no_results"
    assert result.evidence_packet is None
    assert result.metadata["rag_authority_failure_mode"] == "unsupported_evidence"
    assert repository.answer_logs[-1].status == "no_results"


@pytest.mark.asyncio
async def test_rag_service_ignores_result_metadata_for_packet_authority() -> None:
    request = RagRequest(
        query="Summarize SPY breadth for the client portfolio.",
        request_id="rag_query:metadata-authority-substitution",
    )
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=StaticResultPipeline(
            RagResult.answered(
                request=request,
                answer_text="SPY breadth improved with broad participation [C1].",
                contexts=(context,),
                generated_claims=(_generated_claim(),),
                metadata={
                    "risk_authority": {
                        "risk_tier": "baseline",
                        "intended_sink": "internal_runtime_evidence",
                    }
                },
            )
        ),
        repository=cast(RagPersistenceRepository, repository),
        decision_evidence_packet_persistence_service=_packet_persistence(),
        workflow_registry=cast(WorkflowRegistry, _workflow_registry()),
    )

    result = await service.run(request)

    assert result.status == "answered"
    assert result.authority is not None
    assert result.authority.risk_tier is RiskTier.ENHANCED
    assert result.evidence_packet is not None
    assert result.evidence_packet.authority == result.authority


@pytest.mark.asyncio
async def test_rag_service_does_not_persist_raw_transient_web_context_payload() -> None:
    raw_web_payload = "RAW_WEB_FALLBACK_PAGE_BODY_DO_NOT_PERSIST"
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
            source_type="web_fallback",
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
        decision_evidence_packet_persistence_service=_packet_persistence(),
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
        configured_model="polaris-local-fast",
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
                        generated_claims=(_generated_claim(),),
                    )
                )
            ),
        ),
        repository=cast(RagPersistenceRepository, repository),
        decision_evidence_packet_persistence_service=_packet_persistence(),
    )

    await service.run(request)

    assert repository.query_logs[-1].model_executions == (
        RagQueryModelExecutionRecord(
            operation="adaptive_triage",
            configured_model="polaris-local-fast",
            provider_name="ollama",
            duration_ms=14.25,
            success=True,
        ),
    )
    persisted_metadata = repository.query_logs[-1].metadata
    assert "request_metadata" not in persisted_metadata
    assert persisted_metadata["retrieved_contexts"] == (context.to_dict(),)


@pytest.mark.asyncio
async def test_rag_service_emits_observability_for_generation_and_log_persistence() -> (
    None
):
    telemetry, sink, observability = _telemetry()
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:service-observability",
        workflow_name="morning_report",
        execution_id="exec-observability",
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
            generated_claims=(_generated_claim(),),
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
        decision_evidence_packet_persistence_service=_packet_persistence(),
        telemetry=telemetry,
        workflow_registry=cast(WorkflowRegistry, _workflow_registry()),
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
async def test_rag_service_projects_sanitized_ai_query_observation() -> None:
    request = RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:service-ai-observability",
        workflow_name="morning_report",
        execution_id="exec-aiobs",
        metadata={"trace_id": "trace-aiobs"},
    )
    context = _context(
        context_id="chunk-aiobs",
        text="SPY breadth improved with broad participation.",
    )
    projector = RecordingAiObservabilityProjector()
    service = RagService(
        pipeline=FakePipeline(
            retriever=FakeRetriever(contexts=(context,)),
            answer_generator=RagAnswerGenerator(
                answer_provider=FakeAnswerProvider(
                    result=RagAnswerGenerationResult(
                        answer_text=(
                            "SPY breadth improved with broad participation [C1]."
                        ),
                        model="unit-test-model",
                        provider_name="unit-test-provider",
                        generated_claims=(_generated_claim(),),
                    )
                )
            ),
        ),
        repository=cast(RagPersistenceRepository, FakeRagRepository()),
        decision_evidence_packet_persistence_service=_packet_persistence(),
        ai_observability_projector=projector,
        workflow_registry=cast(WorkflowRegistry, _workflow_registry()),
    )

    result = await service.run(request)

    assert result.status == "answered"
    assert len(projector.observations) == 1
    observation = projector.observations[0]
    assert observation.observation_type is AiObservationType.RAG_QUERY
    assert observation.name == "rag_query"
    assert observation.correlation_ids.workflow_name == "morning_report"
    assert observation.correlation_ids.execution_id == "exec-aiobs"
    assert observation.correlation_ids.trace_id == "trace-aiobs"
    assert observation.prompt is None
    assert observation.response is None
    assert observation.metadata["context_count"] == 1
    assert "SPY breadth improved" not in repr(observation)


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
        decision_evidence_packet_persistence_service=_packet_persistence(),
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
        decision_evidence_packet_persistence_service=_packet_persistence(),
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
        decision_evidence_packet_persistence_service=_packet_persistence(),
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
        retriever: FakeRetriever,
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
        *,
        documents: Sequence[RagDocumentRecord] = (),
        chunks: Sequence[RagChunkRecord] = (),
    ) -> None:
        self.query_logs: list[RagQueryLogRecord] = []
        self.answer_logs: list[RagAnswerLogRecord] = []
        self.documents = {document.document_id: document for document in documents}
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}

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
        return self.documents.get(document_id)

    async def list_chunks(
        self,
        document_id: str,
    ) -> Sequence[RagChunkRecord]:
        return tuple(
            chunk for chunk in self.chunks.values() if chunk.document_id == document_id
        )

    async def get_chunk(
        self,
        chunk_id: str,
    ) -> RagChunkRecord | None:
        return self.chunks.get(chunk_id)

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


def _generated_claim(
    *,
    claim_id: str = "spy-breadth-improved",
    text: str = "SPY breadth improved with broad participation",
    citation_ids: tuple[str, ...] = ("C1",),
) -> RagGeneratedClaim:
    return RagGeneratedClaim(
        claim_id=claim_id,
        text=text,
        citation_ids=citation_ids,
        supporting_citation_ids=citation_ids,
    )


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
            generated_at=datetime(2026, 6, 1, tzinfo=UTC),
            workflow_name="morning_report",
            execution_id="exec-1",
            metadata={"symbol": "SPY"},
        ),
        score=0.91,
        rank=1,
        retrieval_route="hybrid",
        metadata={"fused_score": 0.91},
    )


class FakeCompletedRunArchive:
    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        return None


class FakeDecisionEvidencePacketRepository:
    def __init__(self) -> None:
        self.records: dict[str, DecisionEvidencePacketRecord] = {}

    async def persist_packet_record(
        self,
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacketPersistenceResult:
        self.records[record.packet_id] = record
        return DecisionEvidencePacketPersistenceResult.succeeded(
            packet_id=record.packet_id,
        )

    async def get_packet_record(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacketRecord | None:
        return self.records.get(packet_id)


def _packet_persistence() -> DecisionEvidencePacketPersistenceService:
    return cast(DecisionEvidencePacketPersistenceService, _PacketPersistenceDouble())


def _workflow_registry() -> object:
    authority = classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RUNTIME_EVIDENCE,
            authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
            canonical_owner=CanonicalOwner.RUNTIME,
            source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            intended_sink=IntendedSink.INTERNAL_RUNTIME_EVIDENCE,
        )
    )
    return SimpleNamespace(
        get_authority_facts=lambda workflow_name: SimpleNamespace(
            identity=SimpleNamespace(
                workflow_name=workflow_name,
                definition_fingerprint="test-workflow-fingerprint",
            ),
            authority=authority,
        )
    )


class _PacketPersistenceDouble:
    def __init__(self, *, fail_persistence: bool = False) -> None:
        self._packets: dict[str, DecisionEvidencePacket] = {}
        self._fail_persistence = fail_persistence

    async def persist_packet(
        self,
        packet: DecisionEvidencePacket,
    ) -> DecisionEvidencePacketPersistenceResult:
        if self._fail_persistence:
            return DecisionEvidencePacketPersistenceResult.failed(
                "packet repository unavailable",
                packet_id=packet.packet_id,
            )
        self._packets[packet.packet_id] = packet
        return DecisionEvidencePacketPersistenceResult.succeeded(packet.packet_id)

    async def reconstruct_packet(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacket:
        return self._packets[packet_id]


def _document_from_context(context: RagRetrievedContext) -> RagDocumentRecord:
    return RagDocumentRecord(
        document_id=context.source.document_id,
        source_table=context.source.source_table,
        source_id=context.source.source_id,
        source_type=context.source.source_type,
        title=context.source.title,
        content_text=context.text,
        generated_at=context.source.generated_at or datetime(2026, 6, 1, tzinfo=UTC),
        workflow_name=context.source.workflow_name,
        execution_id=context.source.execution_id,
        metadata={"section_name": context.source.section_name or ""},
    )


def _chunk_from_context(context: RagRetrievedContext) -> RagChunkRecord:
    return RagChunkRecord(
        chunk_id=context.source.chunk_id or context.context_id,
        document_id=context.source.document_id,
        chunk_index=0,
        chunk_text=context.text,
        metadata={"section_name": context.source.section_name or ""},
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
        decision_evidence_packet_persistence_service=_packet_persistence(),
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


@pytest.mark.asyncio
async def test_rag_service_classifies_external_capital_relevant_answers() -> None:
    request = RagRequest(
        query="Summarize SPY breadth for the client portfolio.",
        request_id="rag_query:external-capital-authority",
        metadata={
            "rag_authority": {
                "audience": "external",
                "capital_relevant": True,
                "intended_sink": "mcp_tool_response",
            }
        },
    )
    context = _context(
        context_id="chunk-1",
        text="SPY breadth improved with broad participation.",
    )
    service = RagService(
        pipeline=StaticResultPipeline(
            RagResult.answered(
                request=request,
                answer_text="SPY breadth improved with broad participation [C1].",
                contexts=(context,),
            )
        ),
        repository=cast(RagPersistenceRepository, FakeRagRepository()),
        decision_evidence_packet_persistence_service=_packet_persistence(),
    )

    result = await service.run(request)

    assert result.status == "no_results"
    assert result.metadata["rag_authority_failure_mode"] == "unsupported_evidence"
    risk_authority = _risk_authority_metadata(result)
    assert risk_authority["risk_tier"] == "enhanced"
    assert risk_authority["authority_effect"] == "non_authoritative_information"
    assert risk_authority["intended_sink"] == "rag_answer"
    assert risk_authority["capital_relevant"] is False
    assert risk_authority["externally_visible"] is False
    assert risk_authority["evidence_sufficient"] is False


@pytest.mark.asyncio
async def test_rag_service_fails_closed_on_stale_or_substituted_evidence() -> None:
    request = RagRequest(
        query="Summarize SPY breadth for the client portfolio.",
        request_id="rag_query:stale-evidence-authority",
        metadata={
            "rag_authority": {
                "audience": "external",
                "capital_relevant": True,
            }
        },
    )
    context = replace(
        _context(
            context_id="chunk-stale",
            text="SPY breadth improved with broad participation.",
        ),
        metadata={"stale_evidence": True},
    )
    repository = FakeRagRepository()
    service = RagService(
        pipeline=StaticResultPipeline(
            RagResult.answered(
                request=request,
                answer_text="SPY breadth improved with broad participation [C1].",
                contexts=(context,),
            )
        ),
        repository=cast(RagPersistenceRepository, repository),
        decision_evidence_packet_persistence_service=_packet_persistence(),
    )

    result = await service.run(request)

    assert result.status == "no_results"
    assert "sufficiently grounded" in result.answer_text
    assert result.metadata["rag_authority_failure_mode"] == (
        "stale_or_substituted_evidence"
    )
    assert result.metadata["rag_authority_fail_closed"] is True
    risk_authority = _risk_authority_metadata(result)
    assert risk_authority["risk_tier"] == "enhanced"
    assert risk_authority["evidence_sufficient"] is False
    assert repository.query_logs[-1].status == "no_results"
    persisted_result_metadata = cast(
        Mapping[str, object],
        repository.answer_logs[-1].metadata["result_metadata"],
    )
    persisted_risk_authority = cast(
        Mapping[str, object],
        persisted_result_metadata["risk_authority"],
    )
    assert persisted_risk_authority["evidence_sufficient"] is False


def _risk_authority_metadata(result: RagResult) -> Mapping[str, object]:
    return cast(Mapping[str, object], result.metadata["risk_authority"])


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
        decision_evidence_packet_persistence_service=_packet_persistence(),
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
