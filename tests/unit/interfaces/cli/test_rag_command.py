from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from datetime import timezone

import pytest
from typer.testing import CliRunner

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_operation_models import (
    RagCanonicalProjectionReadiness,
)
from application.rag.contracts.rag_operation_models import RagGraphProjectionReadiness
from application.rag.contracts.rag_operation_models import RagIngestOperationRequest
from application.rag.contracts.rag_operation_models import RagOperationDetail
from application.rag.contracts.rag_operation_models import RagOperationResult
from application.rag.contracts.rag_operation_models import RagModelReadiness
from application.rag.contracts.rag_operation_models import RagProjectionReadinessResult
from application.rag.contracts.rag_operation_models import RagVectorProjectionReadiness
from application.rag.contracts.rag_operation_models import (
    RagProcessEmbeddingsOperationRequest,
)
from application.rag.contracts.rag_operation_models import (
    RagProcessGraphOperationRequest,
)
from application.rag.contracts.rag_operation_models import (
    RagRebuildProjectionOperationRequest,
)
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from interfaces.cli.app import create_app
from interfaces.cli.commands import rag_command
import interfaces.cli.services.rag_command_service as rag_command_service_module
from interfaces.cli.services.rag_command_service import RagAskCommandRequest
from interfaces.cli.services.rag_command_service import RagAskCommandResult
from interfaces.cli.services.rag_command_service import RagCommandService
from interfaces.cli.services.rag_command_service import default_rag_embedding_context
from interfaces.cli.services.rag_command_service import default_rag_ingestion_context
from interfaces.cli.services.rag_command_service import default_rag_projection_context
from interfaces.cli.services.rag_command_service import default_rag_status_context
from interfaces.cli.services.rag_command_service import default_rag_service_context
from interfaces.cli.services.rag_command_service import render_rag_ask_result
from interfaces.cli.services.rag_command_service import render_rag_operation_result
from interfaces.cli.services.rag_command_service import render_rag_projection_readiness


class FakeRagService:
    def __init__(
        self,
        result: RagResult,
    ) -> None:
        self.requests: list[RagRequest] = []
        self._result = result

    async def run(
        self,
        request: RagRequest,
    ) -> RagResult:
        self.requests.append(
            request,
        )
        return self._result


class _FakeRequestContainer:
    def __init__(self, dependency: object) -> None:
        self.dependency = dependency
        self.requested_types: list[type[object]] = []
        self.exit_calls = 0

    async def __aenter__(self) -> _FakeRequestContainer:
        return self

    async def __aexit__(self, *args: object) -> None:
        self.exit_calls += 1

    async def get(self, dependency_type: type[object]) -> object:
        self.requested_types.append(dependency_type)
        return self.dependency


@pytest.mark.asyncio
async def test_default_rag_contexts_use_canonical_application_request_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies = [object() for _ in range(5)]
    request_containers = [
        _FakeRequestContainer(dependency) for dependency in dependencies
    ]
    pending_containers = request_containers.copy()

    @asynccontextmanager
    async def fake_application_request_scope() -> AsyncIterator[_FakeRequestContainer]:
        request_container = pending_containers.pop(0)
        async with request_container:
            yield request_container

    monkeypatch.setattr(
        rag_command_service_module,
        "application_request_scope",
        fake_application_request_scope,
    )

    contexts = (
        default_rag_service_context,
        default_rag_ingestion_context,
        default_rag_embedding_context,
        default_rag_projection_context,
        default_rag_status_context,
    )
    for context, expected in zip(contexts, dependencies, strict=True):
        async with context() as resolved:
            assert resolved is expected

    assert [container.requested_types for container in request_containers] == [
        [rag_command_service_module.RagService],
        [rag_command_service_module.RagIngestionOperationsService],
        [rag_command_service_module.RagEmbeddingJobOperationsService],
        [rag_command_service_module.RagProjectionOperationsService],
        [rag_command_service_module.RagStatusOperationsService],
    ]
    assert [container.exit_calls for container in request_containers] == [1] * 5


def test_rag_command_service_builds_filtered_request() -> None:
    result = _answered_result()
    fake_service = FakeRagService(
        result,
    )
    service = RagCommandService(
        service=fake_service,
    )

    command_result = _run(
        service.ask(
            RagAskCommandRequest(
                query="  explain SPY breadth  ",
                symbols=("SPY",),
                source_types=("morning_report",),
                source_tables=("rag_documents",),
                agent_names=("technical_agent",),
                report_types=("morning_report",),
                workflow_name="morning_report",
                execution_id="execution-1",
                runtime_id="runtime-1",
                as_of_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                as_of_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
                top_k=3,
                allow_web=True,
            )
        )
    )

    assert command_result.success is True
    assert len(fake_service.requests) == 1
    request = fake_service.requests[0]
    assert request.normalized_query == "explain SPY breadth"
    assert request.top_k == 3
    assert request.allow_web is True
    assert request.filters.symbols == ("SPY",)
    assert request.filters.source_types == ("morning_report",)
    assert request.filters.source_tables == ("rag_documents",)
    assert request.filters.agent_names == ("technical_agent",)
    assert request.filters.report_types == ("morning_report",)
    assert request.filters.workflow_name == "morning_report"
    assert request.filters.execution_id == "execution-1"
    assert request.filters.runtime_id == "runtime-1"


def test_rag_ask_cli_renders_answer_with_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RagAskCommandRequest] = []

    class FakeRagCommandService:
        async def ask(
            self,
            request: RagAskCommandRequest,
        ) -> RagAskCommandResult:
            captured.append(
                request,
            )
            return RagAskCommandResult(
                success=True,
                result=_answered_result(),
            )

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "rag",
            "ask",
            "What changed in SPY breadth?",
            "--symbol",
            "SPY",
            "--source-type",
            "morning_report",
            "--source-table",
            "rag_documents",
            "--agent-name",
            "technical_agent",
            "--report-type",
            "morning_report",
            "--workflow-name",
            "morning_report",
            "--execution-id",
            "execution-1",
            "--runtime-id",
            "runtime-1",
            "--top-k",
            "3",
            "--web",
        ],
    )

    assert result.exit_code == 0
    assert "RAG Answer" in result.output
    assert "The breadth signal improved across SPY constituents." in result.output
    assert "Citations:" in result.output
    assert "Morning Report" in result.output
    assert captured[0].symbols == ("SPY",)
    assert captured[0].top_k == 3
    assert captured[0].workflow_name == "morning_report"
    assert captured[0].allow_web is True


def test_rag_ask_cli_renders_failure_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRagCommandService:
        async def ask(
            self,
            request: RagAskCommandRequest,
        ) -> RagAskCommandResult:
            rag_request = RagRequest(
                query=request.query,
            )
            return RagAskCommandResult(
                success=False,
                result=RagResult.failed(
                    request=rag_request,
                    error="generation provider unavailable",
                ),
                error="generation provider unavailable",
            )

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "rag",
            "ask",
            "What changed?",
        ],
    )

    assert result.exit_code == 1
    assert "RAG Answer" in result.output
    assert "Status: failed" in result.output
    assert "generation provider unavailable" in result.output


def test_render_rag_ask_result_does_not_truncate_answer() -> None:
    result = _answered_result(
        answer_text="Line one.\n" + "Full detail. " * 50,
    )

    rendered = render_rag_ask_result(
        RagAskCommandResult(
            success=True,
            result=result,
        )
    )

    assert rendered.count("Full detail.") == 50


def test_rag_ingest_cli_delegates_and_renders_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RagIngestOperationRequest] = []

    class FakeRagCommandService:
        async def ingest(
            self,
            request: RagIngestOperationRequest,
        ) -> RagOperationResult:
            captured.append(
                request,
            )
            return RagOperationResult.succeeded(
                operation="rag.ingest",
                message="dry run complete",
                records_processed=2,
                dry_run=True,
                details=(
                    RagOperationDetail(
                        "source",
                        request.source,
                    ),
                ),
            )

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "rag",
            "ingest",
            "--source",
            "reports",
            "--limit",
            "2",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "RAG Operation" in result.output
    assert "Operation: rag.ingest" in result.output
    assert "Dry run: True" in result.output
    assert "Records processed: 2" in result.output
    assert captured[0].source == "reports"
    assert captured[0].limit == 2
    assert captured[0].dry_run is True


def test_rag_process_embeddings_cli_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RagProcessEmbeddingsOperationRequest] = []

    class FakeRagCommandService:
        async def process_embeddings(
            self,
            request: RagProcessEmbeddingsOperationRequest,
        ) -> RagOperationResult:
            captured.append(
                request,
            )
            return RagOperationResult.succeeded(
                operation="rag.process_embeddings",
                message="processed",
                records_processed=3,
            )

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "rag",
            "process-embeddings",
            "--batch-size",
            "3",
        ],
    )

    assert result.exit_code == 0
    assert "Operation: rag.process_embeddings" in result.output
    assert captured[0].batch_size == 3
    assert captured[0].dry_run is False


def test_rag_process_graph_cli_is_dry_run_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RagProcessGraphOperationRequest] = []

    class FakeRagCommandService:
        async def process_graph(
            self,
            request: RagProcessGraphOperationRequest,
        ) -> RagOperationResult:
            captured.append(
                request,
            )
            return RagOperationResult.succeeded(
                operation="rag.process_graph",
                message="dry run",
                dry_run=request.dry_run,
            )

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "rag",
            "process-graph",
        ],
    )

    assert result.exit_code == 0
    assert "Dry run: True" in result.output
    assert captured[0].dry_run is True


def test_rag_rebuild_cli_requires_confirmation_for_destructive_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RagRebuildProjectionOperationRequest] = []

    class FakeRagCommandService:
        async def rebuild(
            self,
            request: RagRebuildProjectionOperationRequest,
        ) -> RagOperationResult:
            captured.append(
                request,
            )
            return RagOperationResult.succeeded(
                operation="rag.rebuild_projection",
                message="dry run",
                dry_run=request.dry_run,
            )

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "rag",
            "rebuild",
            "--projection",
            "qdrant",
        ],
    )

    assert result.exit_code == 0
    assert "Operation: rag.rebuild_projection" in result.output
    assert "Dry run: True" in result.output
    assert captured[0].projection == "qdrant"
    assert captured[0].dry_run is True
    assert captured[0].confirm_delete is False


def test_rag_rebuild_cli_executes_only_with_explicit_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RagRebuildProjectionOperationRequest] = []

    class FakeRagCommandService:
        async def rebuild(
            self,
            request: RagRebuildProjectionOperationRequest,
        ) -> RagOperationResult:
            captured.append(request)
            return RagOperationResult.succeeded(
                operation="rag.rebuild_projection",
                message="verified rebuild",
                dry_run=request.dry_run,
            )

    monkeypatch.setattr(rag_command, "RagCommandService", FakeRagCommandService)

    result = CliRunner().invoke(
        create_app(),
        [
            "rag",
            "rebuild",
            "--projection",
            "qdrant",
            "--confirm-delete",
        ],
    )

    assert result.exit_code == 0
    assert captured == [
        RagRebuildProjectionOperationRequest(
            projection="qdrant",
            dry_run=False,
            confirm_delete=True,
        )
    ]


def test_rag_status_cli_renders_typed_projection_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRagCommandService:
        async def status(self) -> RagProjectionReadinessResult:
            return _readiness_result()

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(create_app(), ["rag", "status"])

    assert result.exit_code == 0
    assert "RAG Projection Readiness" in result.output
    assert "Documents: 3" in result.output
    assert "Named sparse vector: True" in result.output
    assert "Reranker (bge-reranker-large): True" in result.output


def test_projection_readiness_renderer_includes_dependency_errors() -> None:
    ready = _readiness_result()
    result = RagProjectionReadinessResult(
        operation=ready.operation,
        status="degraded",
        message="requires attention",
        canonical=ready.canonical,
        vector=RagVectorProjectionReadiness(
            collection_name="test_chunks",
            exists=False,
            healthy=False,
            dense_vector_present=False,
            sparse_vector_present=False,
            configured_vector_size=3,
            actual_vector_size=None,
            vector_size_compatible=False,
            points_count=0,
            error="qdrant unavailable",
        ),
        graph=ready.graph,
        embedding=ready.embedding,
        reranker=ready.reranker,
    )

    rendered = render_rag_projection_readiness(result)

    assert "Status: degraded" in rendered
    assert "Qdrant error: qdrant unavailable" in rendered
    assert "Actual dimensions: unavailable" in rendered


def test_rag_operation_cli_renders_failure_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRagCommandService:
        async def ingest(
            self,
            request: RagIngestOperationRequest,
        ) -> RagOperationResult:
            return RagOperationResult.failed(
                operation="rag.ingest",
                error="unsupported source",
            )

    monkeypatch.setattr(
        rag_command,
        "RagCommandService",
        FakeRagCommandService,
    )
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "rag",
            "ingest",
            "--source",
            "bad-source",
        ],
    )

    assert result.exit_code == 1
    assert "Status: failed" in result.output
    assert "unsupported source" in result.output


def test_render_rag_operation_result_includes_details() -> None:
    rendered = render_rag_operation_result(
        RagOperationResult.succeeded(
            operation="rag.status",
            message="loaded",
            details=(
                RagOperationDetail(
                    "queued_embedding_jobs",
                    "4",
                ),
            ),
        )
    )

    assert "RAG Operation" in rendered
    assert "queued_embedding_jobs: 4" in rendered


def _readiness_result() -> RagProjectionReadinessResult:
    return RagProjectionReadinessResult(
        operation="rag.status",
        status="ready",
        message="ready",
        canonical=RagCanonicalProjectionReadiness(
            available=True,
            document_count=3,
            chunk_count=8,
            embedding_job_count=5,
            graph_job_count=2,
            pending_embedding_jobs=1,
            retryable_embedding_jobs=0,
            failed_embedding_jobs=0,
        ),
        vector=RagVectorProjectionReadiness(
            collection_name="test_chunks",
            exists=True,
            healthy=True,
            dense_vector_present=True,
            sparse_vector_present=True,
            configured_vector_size=3,
            actual_vector_size=3,
            vector_size_compatible=True,
            points_count=8,
            status="green",
        ),
        graph=RagGraphProjectionReadiness(
            connected=True, healthy=True, entity_count=12
        ),
        embedding=RagModelReadiness(
            component="embedding", model="bge-m3", ready=True, dimensions=3
        ),
        reranker=RagModelReadiness(
            component="reranker", model="bge-reranker-large", ready=True
        ),
    )


def _answered_result(
    answer_text: str = "The breadth signal improved across SPY constituents.",
) -> RagResult:
    request = RagRequest(
        query="What changed in SPY breadth?",
        top_k=3,
    )
    source = RagSource(
        source_table="rag_documents",
        source_id="report-1",
        source_type="morning_report",
        document_id="document-1",
        title="Morning Report",
        chunk_id="chunk-1",
        section_name="Technical Breadth",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        workflow_name="morning_report",
        execution_id="execution-1",
    )
    context = RagRetrievedContext(
        context_id="context-1",
        text="SPY breadth improved.",
        source=source,
        score=0.91,
        rank=1,
        retrieval_route="hybrid",
    )
    return RagResult.answered(
        request=request,
        answer_text=answer_text,
        contexts=(context,),
        confidence_score=0.82,
    )


def _run(
    awaitable,
):
    import asyncio

    return asyncio.run(
        awaitable,
    )
