"""Isolated MCP transport/catalog integration contract tests."""

from __future__ import annotations

import ast
import asyncio
import sys
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from dishka import AsyncContainer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import SecretStr
from starlette.applications import Starlette

import mcp_server.server as server_module
from application.evaluations.risk_authority_gate import (
    RiskAuthorityGateDecision,
    RiskAuthorityGateDecisionStatus,
    RiskAuthorityGateEvidence,
    RiskAuthorityGateFailureMode,
)
from application.presentation.governed_result import GovernedPresentationResult
from application.presentation.sink_decision import (
    PresentationSinkDecision,
    PresentationSinkDisposition,
)
from application.rag.authority import classify_rag_result_authority
from application.rag.contracts.rag_operation_models import (
    RagCanonicalProjectionReadiness,
    RagGraphProjectionReadiness,
    RagModelReadiness,
    RagProjectionReadinessResult,
    RagStatusOperationRequest,
    RagVectorProjectionReadiness,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from core.workflow.execution.workflow_service import WorkflowSummary
from mcp_server.auth import McpHttpAuthenticationBoundary
from mcp_server.contracts.models import (
    CompletedRunGetRequest,
    CompletedRunsListRequest,
    GovernanceReviewStatesListRequest,
    RagAskRequest,
    RagStatusRequest,
    WorkflowDescribeRequest,
    WorkflowsListRequest,
)
from mcp_server.lifespan import McpApplicationContext
from mcp_server.server import create_streamable_http_app
from mcp_server.settings import McpServerSettings, McpTransport
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.allowlist import (
    APPROVED_MCP_TOOL_NAMES,
    validate_registered_tool_allowlist,
)
from mcp_server.tools.completed_run_get import execute_completed_run_get
from mcp_server.tools.completed_runs import execute_completed_runs_list
from mcp_server.tools.governance_review_state import (
    execute_governance_review_states_list,
)
from mcp_server.tools.rag import execute_rag_ask
from mcp_server.tools.rag_status import execute_rag_status
from mcp_server.tools.workflow_describe import execute_workflow_describe
from mcp_server.tools.workflows import execute_workflows_list


def _credential_url(password: str) -> str:
    return "postgresql://user:" + password + "@localhost/polaris"


_GENERATED_AT = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)


class _FakeRagService:
    async def run(self, request: RagRequest) -> GovernedPresentationResult[RagResult]:
        result = RagResult(
            query_id=request.request_id,
            request=request,
            answer_text="Complete fake answer.",
            status="answered",
            route=request.route,
            generated_at=_GENERATED_AT,
        )
        result = classify_rag_result_authority(request=request, result=result)
        authority = result.authority
        if authority is None:
            raise ValueError("fake RAG service result lacks authority.")
        decision = PresentationSinkDecision(
            disposition=PresentationSinkDisposition.ELIGIBLE,
            gate_decision=RiskAuthorityGateDecision(
                status=RiskAuthorityGateDecisionStatus.PASSED,
                failure_mode=RiskAuthorityGateFailureMode.NONE,
                message="test governed MCP RAG result",
                risk_tier=authority.risk_tier,
                gate_profile=authority.gate_profile,
                authority_metadata=authority.to_metadata(),
                evidence=RiskAuthorityGateEvidence(
                    provenance_record_ids=("mcp-integration",)
                ),
            ),
            reasons=("test governed MCP RAG result",),
        )
        return GovernedPresentationResult(payload=result, decision=decision)


class _FakeRagStatusService:
    async def status(
        self,
        request: RagStatusOperationRequest,
    ) -> RagProjectionReadinessResult:
        return RagProjectionReadinessResult(
            operation="rag_status",
            status="ready",
            message="RAG projections are ready.",
            canonical=RagCanonicalProjectionReadiness(
                available=True,
                document_count=2,
                chunk_count=4,
                embedding_job_count=0,
                graph_job_count=0,
                pending_embedding_jobs=0,
                retryable_embedding_jobs=0,
                failed_embedding_jobs=0,
            ),
            vector=RagVectorProjectionReadiness(
                collection_name="rag_chunks",
                exists=True,
                healthy=True,
                dense_vector_present=True,
                sparse_vector_present=True,
                configured_vector_size=1024,
                actual_vector_size=1024,
                vector_size_compatible=True,
                points_count=4,
                status="green",
            ),
            graph=RagGraphProjectionReadiness(
                connected=True,
                healthy=True,
                entity_count=3,
            ),
            embedding=RagModelReadiness(
                component="embedding",
                model="bge-m3:567m",
                ready=True,
                dimensions=1024,
            ),
            reranker=RagModelReadiness(
                component="reranker",
                model="bge-reranker-large",
                ready=True,
            ),
        )


class _FakeWorkflowFacade:
    def __init__(self, *, cancel: bool = False, fail: bool = False) -> None:
        self.cancel = cancel
        self.fail = fail

    def _maybe_fail(self) -> None:
        if self.cancel:
            raise asyncio.CancelledError()
        if self.fail:
            raise RuntimeError(_credential_url("secret"))

    def list_workflow_summaries(
        self,
        tag: str | None = None,
    ) -> tuple[WorkflowSummary, ...]:
        self._maybe_fail()
        return (
            WorkflowSummary(
                workflow_name="morning_report",
                description="Morning report",
                tags=("builtin",),
                metadata={"source": "isolated-test", "tag": tag},
            ),
        )

    def describe_workflow(self, workflow_name: str) -> dict[str, Any]:
        self._maybe_fail()
        return {
            "workflow_name": workflow_name,
            "description": "Morning report",
            "tags": ("builtin",),
            "metadata": {"source": "isolated-test"},
            "definition": {
                "workflow_name": workflow_name,
                "workflow_description": "Morning report graph",
                "nodes": [
                    {
                        "name": "technical_analysis",
                        "node_type": "analysis",
                        "dependencies": [],
                        "enabled": True,
                        "max_retries": 0,
                        "retry_backoff_seconds": 0.0,
                        "fail_fast": False,
                    }
                ],
            },
        }

    async def list_completed_runs(self, workflow_name: str) -> tuple[str, ...]:
        self._maybe_fail()
        assert workflow_name == "morning_report"
        return ("execution-1", "execution-2")

    async def load_completed_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> RuntimeContext | None:
        self._maybe_fail()
        assert workflow_name == "morning_report"
        if execution_id == "missing":
            return None
        return RuntimeContext(
            runtime_id="runtime-1",
            workflow_id=workflow_name,
            execution_id=execution_id,
            workflow_inputs={"symbol": "SPY"},
            node_outputs={
                "technical_analysis": {
                    "success": True,
                    "outputs": {"technical_score": 0.75},
                }
            },
        )


class _FakeAutomatedDecisionAuditService:
    async def list_governance_review_states(
        self,
        query: object | None = None,
    ) -> tuple[object, ...]:
        return ()


class _RequestContainer:
    def __init__(
        self,
        *,
        rag_service: _FakeRagService | None = None,
        rag_status_service: _FakeRagStatusService | None = None,
        workflow_facade: _FakeWorkflowFacade | None = None,
        audit_service: _FakeAutomatedDecisionAuditService | None = None,
    ) -> None:
        self._rag_service = rag_service or _FakeRagService()
        self._rag_status_service = rag_status_service or _FakeRagStatusService()
        self._workflow_facade = workflow_facade or _FakeWorkflowFacade()
        self._audit_service = audit_service or _FakeAutomatedDecisionAuditService()

    async def get(self, dependency_type: type[object]) -> object:
        dependency_name = dependency_type.__name__
        if dependency_name == "RagService":
            return self._rag_service
        if dependency_name == "RagStatusOperationsService":
            return self._rag_status_service
        if dependency_name == "WorkflowFacade":
            return self._workflow_facade
        if dependency_name == "AutomatedDecisionAuditService":
            return self._audit_service
        raise AssertionError(f"Unexpected dependency requested: {dependency_name}")


class _RequestScope:
    def __init__(self, container: _RequestContainer) -> None:
        self._container = container
        self.entered = False
        self.closed = False

    async def __aenter__(self) -> _RequestContainer:
        self.entered = True
        return self._container

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        self.closed = True


class _ApplicationContainer:
    def __init__(self, request_container: _RequestContainer | None = None) -> None:
        self._request_container = request_container or _RequestContainer()
        self.scopes: list[_RequestScope] = []

    def __call__(self) -> _RequestScope:
        scope = _RequestScope(self._request_container)
        self.scopes.append(scope)
        return scope


def _application_context(
    application_container: _ApplicationContainer | None = None,
    *,
    settings: McpServerSettings | None = None,
) -> tuple[McpApplicationContext, InMemoryTelemetrySink, _ApplicationContainer]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager(
        collector=TelemetryCollector(sinks=(sink,)),
        enable_domain_metrics=False,
    )
    container = application_container or _ApplicationContainer()
    return (
        McpApplicationContext(
            container=cast(AsyncContainer, container),
            runtime=cast(WorkflowBootstrapResult, SimpleNamespace()),
            telemetry=McpTelemetry(manager),
            settings=settings or McpServerSettings(),
        ),
        sink,
        container,
    )


@asynccontextmanager
async def _fake_lifespan(_: object) -> AsyncIterator[McpApplicationContext]:
    context, _, _ = _application_context()
    yield context


def _normalize_tool_schemas(
    tools: Iterable[Any],
) -> dict[str, dict[str, object]]:
    normalized: dict[str, dict[str, object]] = {}
    for tool in tools:
        payload = tool.model_dump(mode="json")
        normalized[payload["name"]] = {
            "description": payload["description"],
            "inputSchema": payload["inputSchema"],
            "annotations": payload["annotations"],
            "outputSchema": payload.get("outputSchema"),
        }
    return normalized


@pytest.mark.asyncio
async def test_stdio_and_streamable_http_expose_identical_tool_schemas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server_module.server._mcp_server, "lifespan", _fake_lifespan)
    http_settings = McpServerSettings(
        transport=McpTransport.STREAMABLE_HTTP,
        path="/mcp-test",
        bearer_token=SecretStr("unit-test-token"),
    )
    http_app = create_streamable_http_app(http_settings)
    authenticated_app = cast(McpHttpAuthenticationBoundary, http_app)
    inner_app = cast(Starlette, authenticated_app._app)
    http_transport = httpx.ASGITransport(app=http_app)

    script = dedent(
        r"""
        from __future__ import annotations

        from contextlib import asynccontextmanager
        from types import SimpleNamespace
        from typing import cast

        from dishka import AsyncContainer
        from core.telemetry.collectors.telemetry_collector import TelemetryCollector
        from core.telemetry.observability.observability_manager import (
            ObservabilityManager,
        )
        from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
        from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
        from mcp_server.lifespan import McpApplicationContext
        from mcp_server.server import run_stdio_server
        from mcp_server.server import server
        from mcp_server.settings import McpServerSettings
        from mcp_server.telemetry import McpTelemetry


        class RequestContainer:
            async def get(self, dependency_type):
                raise AssertionError("tool schema discovery must not resolve services")


        class RequestScope:
            async def __aenter__(self):
                return RequestContainer()

            async def __aexit__(self, *args):
                return None


        class ApplicationContainer:
            def __call__(self):
                return RequestScope()


        @asynccontextmanager
        async def fake_lifespan(_):
            manager = ObservabilityManager(
                collector=TelemetryCollector(sinks=(InMemoryTelemetrySink(),)),
                enable_domain_metrics=False,
            )
            yield McpApplicationContext(
                container=cast(AsyncContainer, ApplicationContainer()),
                runtime=cast(WorkflowBootstrapResult, SimpleNamespace()),
                telemetry=McpTelemetry(manager),
                settings=McpServerSettings(),
            )


        server._mcp_server.lifespan = fake_lifespan
        run_stdio_server(McpServerSettings())
        """,
    )
    stdio_parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", script],
    )

    async with inner_app.router.lifespan_context(inner_app):
        async with httpx.AsyncClient(
            transport=http_transport,
            base_url="http://localhost:8000",
            headers={"Authorization": "Bearer unit-test-token"},
        ) as http_client:
            async with streamable_http_client(
                "http://localhost:8000/mcp-test",
                http_client=http_client,
            ) as (http_read, http_write, _):
                async with ClientSession(
                    http_read,
                    http_write,
                    read_timeout_seconds=timedelta(seconds=10),
                ) as http_session:
                    await http_session.initialize()
                    http_tools = await http_session.list_tools()

    async with stdio_client(stdio_parameters) as (stdio_read, stdio_write):
        async with ClientSession(
            stdio_read,
            stdio_write,
            read_timeout_seconds=timedelta(seconds=10),
        ) as stdio_session:
            await stdio_session.initialize()
            stdio_tools = await stdio_session.list_tools()

    assert _normalize_tool_schemas(http_tools.tools) == _normalize_tool_schemas(
        stdio_tools.tools
    )
    assert set(_normalize_tool_schemas(http_tools.tools)) == APPROVED_MCP_TOOL_NAMES


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "call"),
    (
        (
            "polaris_rag_ask",
            lambda context: execute_rag_ask(RagAskRequest(query="risk"), context),
        ),
        (
            "polaris_rag_status",
            lambda context: execute_rag_status(RagStatusRequest(), context),
        ),
        (
            "polaris_workflows_list",
            lambda context: execute_workflows_list(WorkflowsListRequest(), context),
        ),
        (
            "polaris_workflow_describe",
            lambda context: execute_workflow_describe(
                WorkflowDescribeRequest(workflow_name="morning_report"), context
            ),
        ),
        (
            "polaris_completed_runs_list",
            lambda context: execute_completed_runs_list(
                CompletedRunsListRequest(workflow_name="morning_report"), context
            ),
        ),
        (
            "polaris_completed_run_get",
            lambda context: execute_completed_run_get(
                CompletedRunGetRequest(
                    workflow_name="morning_report",
                    execution_id="execution-1",
                ),
                context,
            ),
        ),
        (
            "polaris_governance_review_states_list",
            lambda context: execute_governance_review_states_list(
                GovernanceReviewStatesListRequest(), context
            ),
        ),
    ),
)
async def test_tool_handlers_open_and_close_one_request_scope(
    tool_name: str,
    call: object,
) -> None:
    context, sink, application_container = _application_context()

    response = await cast(Any, call)(context)

    assert response.model_dump(mode="json")
    assert len(application_container.scopes) == 1, tool_name
    assert application_container.scopes[0].entered is True
    assert application_container.scopes[0].closed is True
    assert sink.events[0].event_type == "mcp.tool.started"
    assert sink.events[-1].event_type == "mcp.tool.completed"
    assert sink.events[-1].success is True


@pytest.mark.asyncio
async def test_cancellation_releases_request_scope_and_preserves_cancelled_error() -> (
    None
):
    application_container = _ApplicationContainer(
        _RequestContainer(workflow_facade=_FakeWorkflowFacade(cancel=True))
    )
    context, sink, _ = _application_context(application_container)

    with pytest.raises(asyncio.CancelledError):
        await execute_workflows_list(WorkflowsListRequest(), context)

    assert len(application_container.scopes) == 1
    assert application_container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "cancelled"


@pytest.mark.asyncio
async def test_application_errors_become_safe_mcp_errors_and_close_scope() -> None:
    application_container = _ApplicationContainer(
        _RequestContainer(workflow_facade=_FakeWorkflowFacade(fail=True))
    )
    context, sink, _ = _application_context(application_container)

    with pytest.raises(ToolError) as caught:
        await execute_workflows_list(WorkflowsListRequest(), context)

    serialized_error = str(caught.value)
    assert "Polaris workflow discovery request failed." in serialized_error
    assert "postgresql://" not in serialized_error
    assert "secret" not in serialized_error
    assert application_container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "application"
    assert sink.events[-1].attributes["error_type"] == "RuntimeError"


def test_exact_read_only_tool_allowlist_is_enforced() -> None:
    registered_tools = server_module.server._tool_manager.list_tools()

    validate_registered_tool_allowlist(registered_tools)
    assert {tool.name for tool in registered_tools} == APPROVED_MCP_TOOL_NAMES


def test_mcp_handlers_do_not_import_forbidden_infrastructure() -> None:
    forbidden_exact = {
        "core.runtime.execution.runtime_engine",
        "qdrant_client",
        "neo4j",
        "crawl4ai",
        "httpx",
        "psycopg",
        "asyncpg",
        "yfinance",
        "alpaca",
    }
    forbidden_prefixes = (
        "core.storage.persistence.rag.postgres_",
        "core.storage.persistence.completed_run.postgres_",
        "integration.clients.",
        "integration.providers.",
    )
    forbidden_review_mutators = {
        "GovernanceResidualRiskAcceptanceRequest",
        "GovernanceReviewDecisionOutcome",
        "GovernanceReviewResolution",
        "GovernanceReviewResolutionRequest",
    }
    handler_paths = (
        tuple(Path("mcp_server/tools").glob("*.py"))
        + tuple(Path("mcp_server").glob("*_tool.py"))
        + (Path("mcp_server/server.py"),)
    )
    violations: list[str] = [
        violation
        for path in handler_paths
        for violation in _mcp_handler_import_violations(
            path,
            forbidden_exact=forbidden_exact,
            forbidden_prefixes=forbidden_prefixes,
            forbidden_review_mutators=forbidden_review_mutators,
        )
    ]

    assert violations == []


def _mcp_handler_import_violations(
    path: Path,
    *,
    forbidden_exact: set[str],
    forbidden_prefixes: tuple[str, ...],
    forbidden_review_mutators: set[str],
) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(
                _forbidden_direct_imports(
                    path,
                    node,
                    forbidden_exact=forbidden_exact,
                    forbidden_prefixes=forbidden_prefixes,
                )
            )
        elif isinstance(node, ast.ImportFrom):
            violations.extend(
                _forbidden_from_imports(
                    path,
                    node,
                    forbidden_exact=forbidden_exact,
                    forbidden_prefixes=forbidden_prefixes,
                    forbidden_review_mutators=forbidden_review_mutators,
                )
            )
    return tuple(violations)


def _forbidden_direct_imports(
    path: Path,
    node: ast.Import,
    *,
    forbidden_exact: set[str],
    forbidden_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        f"{path}: import {alias.name}"
        for alias in node.names
        if alias.name in forbidden_exact or alias.name.startswith(forbidden_prefixes)
    )


def _forbidden_from_imports(
    path: Path,
    node: ast.ImportFrom,
    *,
    forbidden_exact: set[str],
    forbidden_prefixes: tuple[str, ...],
    forbidden_review_mutators: set[str],
) -> tuple[str, ...]:
    module = node.module
    if module is None:
        return ()
    infrastructure = (
        (f"{path}: from {module} import ...",)
        if module in forbidden_exact or module.startswith(forbidden_prefixes)
        else ()
    )
    review_mutators = (
        tuple(
            f"{path}: imports {alias.name}"
            for alias in node.names
            if alias.name in forbidden_review_mutators
        )
        if module == "application.governance"
        else ()
    )
    return infrastructure + review_mutators
