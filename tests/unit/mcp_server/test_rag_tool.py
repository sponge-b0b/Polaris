"""Tests for the thin ``polaris_rag_ask`` MCP boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from dishka import AsyncContainer
from mcp.server.fastmcp.exceptions import ToolError

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
from application.rag.authority import (
    RAG_AUTHORITY_REQUEST_METADATA_KEY,
    classify_rag_result_authority,
)
from application.rag.contracts.rag_context import (
    RagRetrievedContext as DomainRagContext,
)
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_quality_models import RagReflectionScores
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from domain.authority import GateProfile, RiskTier
from mcp_server.contracts.models import RagAskRequest
from mcp_server.lifespan import McpApplicationContext
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.rag import execute_rag_ask

_GENERATED_AT = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)


class _FakeRagService:
    def __init__(self, result_factory: object) -> None:
        self._result_factory = cast("_ResultFactory", result_factory)
        self.requests: list[RagRequest] = []

    async def run(
        self,
        request: RagRequest,
    ) -> GovernedPresentationResult[RagResult]:
        self.requests.append(request)
        return self._result_factory(request)


class _ResultFactory:
    def __call__(
        self,
        request: RagRequest,
    ) -> GovernedPresentationResult[RagResult]: ...


class _RequestContainer:
    def __init__(self, service: _FakeRagService) -> None:
        self._service = service

    async def get(self, dependency_type: type[object]) -> object:
        assert dependency_type.__name__ == "RagService"
        return self._service


class _RequestScope:
    def __init__(self, service: _FakeRagService) -> None:
        self._container = _RequestContainer(service)
        self.closed = False

    async def __aenter__(self) -> _RequestContainer:
        return self._container

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        self.closed = True


class _ApplicationContainer:
    def __init__(self, service: _FakeRagService) -> None:
        self._service = service
        self.scopes: list[_RequestScope] = []

    def __call__(self) -> _RequestScope:
        scope = _RequestScope(self._service)
        self.scopes.append(scope)
        return scope


def _context(
    service: _FakeRagService,
    *,
    settings: McpServerSettings | None = None,
) -> tuple[McpApplicationContext, InMemoryTelemetrySink, _ApplicationContainer]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager(
        collector=TelemetryCollector(sinks=(sink,)),
        enable_domain_metrics=False,
    )
    container = _ApplicationContainer(service)
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


def _source() -> RagSource:
    return RagSource(
        source_table="curated_rag_documents",
        source_id="report-1",
        source_type="morning_report",
        document_id="document-1",
        title="Morning Report",
        chunk_id="chunk-1",
        section_name="Risk",
        generated_at=_GENERATED_AT,
        workflow_name="morning_report",
        execution_id="execution-1",
        metadata={"symbol": "SPY"},
    )


def _context_item() -> DomainRagContext:
    return DomainRagContext(
        context_id="context-1",
        text="Complete retrieved evidence.",
        source=_source(),
        score=0.91,
        rank=0,
        retrieval_route="hybrid",
        metadata={"engine": "vector_graph"},
    )


def _gate_decision(
    *,
    result: RagResult,
    disposition: PresentationSinkDisposition,
) -> PresentationSinkDecision:
    authority = result.authority
    if authority is None:
        raise AssertionError("test result must carry application authority")
    passed = disposition in {
        PresentationSinkDisposition.ELIGIBLE,
        PresentationSinkDisposition.DEGRADED,
    }
    failure_mode = (
        RiskAuthorityGateFailureMode.NONE
        if passed
        else (
            RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
            if disposition is PresentationSinkDisposition.WITHHELD
            else RiskAuthorityGateFailureMode.PROHIBITED_BOUNDARY
        )
    )
    risk_tier = (
        RiskTier.PROHIBITED_OUTSIDE_AUTHORITY
        if disposition is PresentationSinkDisposition.BLOCKED
        else authority.risk_tier
    )
    gate_profile = (
        GateProfile.PROHIBITED_BOUNDARY
        if disposition is PresentationSinkDisposition.BLOCKED
        else authority.gate_profile
    )
    return PresentationSinkDecision(
        disposition=disposition,
        gate_decision=RiskAuthorityGateDecision(
            status=(
                RiskAuthorityGateDecisionStatus.PASSED
                if passed
                else RiskAuthorityGateDecisionStatus.FAILED
            ),
            failure_mode=failure_mode,
            message="test presentation decision",
            risk_tier=risk_tier,
            gate_profile=gate_profile,
            authority_metadata=authority.to_metadata(),
            evidence=RiskAuthorityGateEvidence(
                provenance_record_ids=("provenance-1",),
            ),
        ),
        reasons=("test presentation decision",),
        limitations=(
            ("Evidence coverage is limited.",)
            if disposition is PresentationSinkDisposition.DEGRADED
            else ()
        ),
    )


def _governed_answer(
    request: RagRequest,
    *,
    disposition: PresentationSinkDisposition = PresentationSinkDisposition.ELIGIBLE,
    include_claims: bool = True,
) -> GovernedPresentationResult[RagResult]:
    context = _context_item()
    result = RagResult(
        query_id=request.request_id,
        request=request,
        answer_text=(
            "Complete grounded answer [C1]."
            if include_claims
            else "Grounded response is unavailable."
        ),
        status="answered" if include_claims else "no_results",
        route=request.route,
        contexts=(context,) if include_claims else (),
        citations=(context.source,) if include_claims else (),
        confidence_score=0.92 if include_claims else None,
        grounding_score=0.93 if include_claims else None,
        utility_score=0.94 if include_claims else None,
        reflection_scores=(
            RagReflectionScores(
                retrieval_necessity=0.8,
                source_relevance=0.9,
                answer_support=0.95,
                usefulness=0.85,
            )
            if include_claims
            else None
        ),
        generated_at=_GENERATED_AT,
    )
    result = classify_rag_result_authority(request=request, result=result)
    decision = _gate_decision(result=result, disposition=disposition)
    return GovernedPresentationResult(payload=result, decision=decision)


@pytest.mark.asyncio
async def test_rag_ask_maps_filters_and_requests_mcp_authority() -> None:
    service = _FakeRagService(_governed_answer)
    context, sink, container = _context(service)
    request = RagAskRequest(
        query="Explain market risk",
        symbols=("SPY",),
        source_types=("report",),
        source_tables=("morning_reports",),
        agent_names=("risk_agent",),
        agent_types=("risk",),
        report_types=("morning_report",),
        regimes=("volatile",),
        workflow_name="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
        top_k=12,
    )

    response = await execute_rag_ask(request, context, request_id="mcp-request-1")

    rag_request = service.requests[0]
    authority_request = cast(
        dict[str, object],
        rag_request.metadata[RAG_AUTHORITY_REQUEST_METADATA_KEY],
    )
    assert authority_request["intended_sink"] == "mcp_tool_response"
    assert authority_request["tool_response_external"] is True
    assert rag_request.filters.symbols == ("SPY",)
    assert rag_request.filters.agent_types == ("risk",)
    assert rag_request.filters.runtime_id == "runtime-1"
    assert response.answer_text == "Complete grounded answer [C1]."
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]


@pytest.mark.asyncio
async def test_rag_ask_preserves_mcp_authority_and_governed_projection() -> None:
    context, _, _ = _context(_FakeRagService(_governed_answer))

    response = await execute_rag_ask(
        RagAskRequest(query="risk"),
        context,
        request_id="mcp-authority-1",
    )

    assert response.authority_metadata["intended_sink"] == "mcp_tool_response"
    assert response.authority_metadata["externally_visible"] is True
    assert response.authority_metadata["risk_tier"] == "enhanced"
    assert response.presentation_disposition == "eligible"
    assert response.presentation_may_present is True
    assert response.presentation_gate_failure_mode == "none"
    assert response.presentation_risk_tier == "enhanced"
    assert response.presentation_gate_profile == "enhanced_provenance"
    assert response.provenance_record_ids == ("provenance-1",)
    serialized = json.loads(response.model_dump_json())
    assert serialized["authority_metadata"]["intended_sink"] == "mcp_tool_response"


@pytest.mark.asyncio
async def test_rag_ask_preserves_degraded_application_limitations() -> None:
    def factory(request: RagRequest) -> GovernedPresentationResult[RagResult]:
        return _governed_answer(
            request,
            disposition=PresentationSinkDisposition.DEGRADED,
        )

    context, _, _ = _context(_FakeRagService(factory))
    response = await execute_rag_ask(RagAskRequest(query="risk"), context)

    assert response.status == "answered"
    assert response.presentation_disposition == "degraded"
    assert response.presentation_may_present is True
    assert response.presentation_limitations == ("Evidence coverage is limited.",)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "disposition",
    (PresentationSinkDisposition.WITHHELD, PresentationSinkDisposition.BLOCKED),
)
async def test_rag_ask_cannot_recover_claims_from_ineligible_governed_payload(
    disposition: PresentationSinkDisposition,
) -> None:
    def factory(request: RagRequest) -> GovernedPresentationResult[RagResult]:
        return _governed_answer(
            request,
            disposition=disposition,
            include_claims=False,
        )

    context, _, _ = _context(_FakeRagService(factory))
    response = await execute_rag_ask(
        RagAskRequest(query="risk", include_contexts=True),
        context,
    )

    assert response.status == "no_results"
    assert "Complete grounded answer" not in response.answer_text
    assert response.citations == ()
    assert response.contexts == ()
    assert response.confidence_score is None
    assert response.grounding_score is None
    assert response.utility_score is None
    assert response.presentation_disposition == disposition.value
    assert response.presentation_may_present is False


@pytest.mark.asyncio
async def test_rag_ask_rejects_ineligible_claim_bearing_payload() -> None:
    def factory(request: RagRequest) -> GovernedPresentationResult[RagResult]:
        return _governed_answer(
            request,
            disposition=PresentationSinkDisposition.BLOCKED,
            include_claims=True,
        )

    context, sink, _ = _context(_FakeRagService(factory))

    with pytest.raises(ToolError, match="Polaris RAG request failed"):
        await execute_rag_ask(
            RagAskRequest(query="risk", include_contexts=True),
            context,
        )

    assert sink.events[-1].attributes["failure_category"] == "application"


@pytest.mark.asyncio
async def test_rag_ask_rejects_malformed_presentable_projection() -> None:
    class MalformedProjectionResult:
        def __init__(self, result: RagResult) -> None:
            self.projection = SimpleNamespace(
                authority_metadata={},
                disposition="eligible",
                may_present=True,
                limitations=(),
                gate_failure_mode="none",
                risk_tier=None,
                gate_profile=None,
                provenance_record_ids=(),
                decision_evidence_packet_ids=(),
                governance_approval_states=(),
            )
            self._result = result

        def require_payload(self) -> RagResult:
            return self._result

    def factory(request: RagRequest) -> GovernedPresentationResult[RagResult]:
        return cast(
            GovernedPresentationResult[RagResult],
            MalformedProjectionResult(_governed_answer(request).require_payload()),
        )

    context, sink, _ = _context(_FakeRagService(factory))

    with pytest.raises(ToolError, match="Polaris RAG request failed"):
        await execute_rag_ask(RagAskRequest(query="risk"), context)

    assert sink.events[-1].attributes["failure_category"] == "application"


@pytest.mark.asyncio
async def test_rag_ask_rejects_raw_ungoverned_service_result() -> None:
    class RawService(_FakeRagService):
        async def run(self, request: RagRequest) -> RagResult:  # type: ignore[override]
            self.requests.append(request)
            return RagResult.failed(request=request, error="raw result")

    context, sink, _ = _context(cast(_FakeRagService, RawService(_governed_answer)))

    with pytest.raises(ToolError, match="Polaris RAG request failed"):
        await execute_rag_ask(RagAskRequest(query="risk"), context)

    assert sink.events[-1].attributes["failure_category"] == "application"


@pytest.mark.asyncio
async def test_rag_ask_sanitizes_failed_governed_result() -> None:
    secret = "postgresql://user:password@localhost/polaris"

    def factory(request: RagRequest) -> GovernedPresentationResult[RagResult]:
        result = RagResult.failed(request=request, error=secret)
        result = classify_rag_result_authority(request=request, result=result)
        return GovernedPresentationResult(
            payload=result,
            decision=_gate_decision(
                result=result,
                disposition=PresentationSinkDisposition.WITHHELD,
            ),
        )

    context, sink, _ = _context(_FakeRagService(factory))
    response = await execute_rag_ask(RagAskRequest(query="risk"), context)

    assert response.status == "failed"
    assert response.answer_text == "Polaris RAG request failed."
    assert response.error == "Polaris RAG request failed."
    assert secret not in response.model_dump_json()
    assert sink.events[-1].attributes["result_status"] == "failed"


@pytest.mark.asyncio
async def test_rag_ask_denies_web_before_resolving_service() -> None:
    service = _FakeRagService(_governed_answer)
    context, sink, container = _context(service)

    with pytest.raises(ToolError, match="Web retrieval is disabled"):
        await execute_rag_ask(
            RagAskRequest(query="Search the web", allow_web=True),
            context,
        )

    assert service.requests == []
    assert container.scopes == []
    assert sink.events[-1].attributes["failure_category"] == "validation"


@pytest.mark.asyncio
async def test_rag_ask_enforces_query_and_top_k_limits() -> None:
    service = _FakeRagService(_governed_answer)
    context, _, _ = _context(
        service,
        settings=McpServerSettings(max_query_characters=4, max_top_k=2),
    )

    with pytest.raises(ToolError, match="query cannot exceed 4 characters"):
        await execute_rag_ask(RagAskRequest(query="12345"), context)
    with pytest.raises(ToolError, match="top_k cannot exceed 2"):
        await execute_rag_ask(RagAskRequest(query="risk", top_k=3), context)
    assert service.requests == []
