from __future__ import annotations

from typing import Literal, TypedDict

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_quality_models import (
    RagContextEvaluation,
    RagCorrectiveAction,
    RagSelfReflection,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.retrieval.rag_retriever import RagRetrievalResult
from application.rag.routing.query_routing_models import (
    RagAdaptiveTriage,
    RagHydeExpansion,
    RagQueryContext,
    RagQueryModelExecution,
    RagRouteSelection,
    RagStandaloneQueryRewrite,
)

RagGraphStatus = Literal["initialized", "running", "completed", "failed"]


class RagGraphState(TypedDict, total=False):
    """Typed domain state carried across the internal LangGraph boundary."""

    request: RagRequest
    active_request: RagRequest
    result: RagResult
    status: RagGraphStatus
    query_context: RagQueryContext
    rewrite: RagStandaloneQueryRewrite
    triage: RagAdaptiveTriage
    route_selection: RagRouteSelection
    hyde: RagHydeExpansion | None
    model_executions: tuple[RagQueryModelExecution, ...]
    retrieval_result: RagRetrievalResult
    fused_context: tuple[RagRetrievedContext, ...]
    reranked_context: tuple[RagRetrievedContext, ...]
    context_evaluation: RagContextEvaluation
    self_reflection: RagSelfReflection
    corrective_actions: tuple[RagCorrectiveAction, ...]
    draft_answer: str | None
    final_answer: str | None
    loop_count: int
    max_loops: int
    stage_history: tuple[str, ...]
    errors: tuple[str, ...]


def initial_rag_graph_state(
    request: RagRequest,
    *,
    max_loops: int = 1,
) -> RagGraphState:
    if max_loops <= 0:
        raise ValueError("max_loops must be positive.")

    return RagGraphState(
        request=request,
        active_request=request,
        status="initialized",
        hyde=None,
        model_executions=(),
        fused_context=(),
        reranked_context=(),
        draft_answer=None,
        final_answer=None,
        loop_count=0,
        max_loops=max_loops,
        stage_history=(),
        corrective_actions=(),
        errors=(),
    )
