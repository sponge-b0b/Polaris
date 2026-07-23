from __future__ import annotations

from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from intelligence.research.rag import RagResearchNode, RagResearchNodeConfig


class FakeRagService:
    def __init__(
        self,
        result_status: str = "answered",
    ) -> None:
        self.result_status = result_status
        self.requests: list[RagRequest] = []

    async def run(
        self,
        request: RagRequest,
    ) -> RagResult:
        self.requests.append(
            request,
        )
        if self.result_status == "failed":
            return RagResult.failed(
                request=request,
                error="generation unavailable",
            )
        return RagResult.answered(
            request=request,
            answer_text="The curated records support a neutral risk posture.",
            contexts=(),
            confidence_score=0.74,
        )


def _context(
    workflow_inputs: dict[str, object],
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        workflow_inputs=workflow_inputs,
    )


async def test_rag_research_node_returns_serialized_result_output() -> None:
    service = FakeRagService()
    node = RagResearchNode(
        rag_service=service,
    )

    output = await node.run(
        _context(
            {
                "rag_query": "What did the latest market regime say?",
                "rag_filters": {
                    "symbols": ["SPY"],
                    "source_types": ["morning_report"],
                },
                "rag_top_k": 5,
            }
        )
    )

    assert isinstance(
        output,
        RuntimeNodeOutput,
    )
    assert output.success is True
    assert set(output.outputs) == {"rag_result"}

    serialized_result = output.outputs["rag_result"]
    assert serialized_result["status"] == "answered"
    assert serialized_result["route"] == "hybrid"
    assert serialized_result["request"]["top_k"] == 5
    assert serialized_result["request"]["workflow_name"] == "morning_report"
    assert serialized_result["request"]["execution_id"] == "execution-1"
    assert serialized_result["request"]["filters"]["symbols"] == ["SPY"]

    assert service.requests[0].filters.symbols == ("SPY",)
    assert service.requests[0].metadata["runtime_id"] == "runtime-1"


async def test_rag_research_node_serializes_request_payloads() -> None:
    request = RagRequest(
        query="Use persisted recommendation evidence.",
        route="keyword",
        top_k=3,
    )
    service = FakeRagService()
    node = RagResearchNode(
        rag_service=service,
    )

    output = await node.run(
        _context(
            {
                "rag_request": request.to_dict(),
            }
        )
    )

    assert output.success is True
    serialized_result = output.outputs["rag_result"]
    assert serialized_result["request"]["query"] == request.query
    assert serialized_result["request"]["route"] == "keyword"
    assert serialized_result["request"]["top_k"] == 3
    assert service.requests[0].query == request.query


async def test_rag_research_node_keeps_service_failed_result_renderable() -> None:
    service = FakeRagService(
        result_status="failed",
    )
    node = RagResearchNode(
        rag_service=service,
    )

    output = await node.run(
        _context(
            {
                "rag_query": "Summarize latest curated research.",
            }
        )
    )

    assert output.success is True
    serialized_result = output.outputs["rag_result"]
    assert serialized_result["status"] == "failed"
    assert serialized_result["error"] == "generation unavailable"
    assert "RAG request failed" in serialized_result["answer_text"]


async def test_rag_research_node_reports_invalid_runtime_input() -> None:
    service = FakeRagService()
    node = RagResearchNode(
        rag_service=service,
        config=RagResearchNodeConfig(
            query_key="question",
        ),
    )

    output = await node.run(
        _context(
            {},
        )
    )

    assert output.success is False
    assert output.outputs == {}
    assert output.errors[0]["error_type"] == "ValueError"
    assert "question is required" in output.errors[0]["message"]
    assert service.requests == []
