from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Literal

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_quality_models import (
    RagContextEvaluation,
    RagCorrectiveAction,
    RagSelfReflection,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.routing.query_routing_models import (
    RagQueryModelExecution,
    RagRetrievalRoute,
)
from application.rag.security.rag_security import safe_grounding_failure_answer
from core.storage.persistence.rag import JsonObject


class RagSelectionRoute(StrEnum):
    DIRECT = "direct"
    RETRIEVAL = "retrieval"
    DEEP_RESEARCH = "deep_research"


class RagCorrectiveRoute(StrEnum):
    GENERATE = "generate"
    REWRITE = "rewrite"
    WEB_FALLBACK = "web_fallback"
    FAIL_CLOSED = "fail_closed"


@dataclass(frozen=True, slots=True)
class RagPostProcessingDecision:
    result: RagResult
    status: Literal["completed", "failed"]


class RagGraphPolicy:
    """Pure routing and final-result policy for the RAG orchestration graph."""

    def route_after_selection(self, route: RagRetrievalRoute) -> RagSelectionRoute:
        if route is RagRetrievalRoute.DIRECT_ANSWER:
            return RagSelectionRoute.DIRECT
        if route is RagRetrievalRoute.DEEP_RESEARCH:
            return RagSelectionRoute.DEEP_RESEARCH
        return RagSelectionRoute.RETRIEVAL

    def route_after_crag(
        self,
        *,
        evaluation: RagContextEvaluation,
        has_context: bool,
        loop_count: int,
        max_loops: int,
        rewrite_available: bool,
        allow_web: bool,
        web_fallback_available: bool,
    ) -> RagCorrectiveRoute:
        if evaluation.action is RagCorrectiveAction.PROCEED:
            return RagCorrectiveRoute.GENERATE
        if evaluation.action is RagCorrectiveAction.DISCARD_WEAK_CONTEXT:
            return (
                RagCorrectiveRoute.GENERATE
                if has_context
                else RagCorrectiveRoute.FAIL_CLOSED
            )
        if evaluation.action is RagCorrectiveAction.REWRITE:
            if rewrite_available and loop_count < max_loops:
                return RagCorrectiveRoute.REWRITE
            return RagCorrectiveRoute.FAIL_CLOSED
        if evaluation.action is RagCorrectiveAction.WEB_FALLBACK:
            if allow_web and web_fallback_available:
                return RagCorrectiveRoute.WEB_FALLBACK
        return RagCorrectiveRoute.FAIL_CLOSED

    def route_after_web_fallback(self, *, has_context: bool) -> RagCorrectiveRoute:
        if has_context:
            return RagCorrectiveRoute.GENERATE
        return RagCorrectiveRoute.FAIL_CLOSED

    def finalize_result(
        self,
        *,
        result: RagResult,
        request: RagRequest,
        route: str,
        reflection: RagSelfReflection | None,
        contexts: tuple[RagRetrievedContext, ...],
        corrective_actions: tuple[RagCorrectiveAction, ...],
        model_executions: tuple[RagQueryModelExecution, ...],
        loop_count: int,
        stage_history: tuple[str, ...],
    ) -> RagPostProcessingDecision:
        final_result = self._apply_reflection_safety(result, reflection)
        metadata: JsonObject = {
            **dict(final_result.metadata),
            "adaptive_route": route,
            "loop_count": loop_count,
            "model_executions": [execution.to_dict() for execution in model_executions],
            "graph_stages": [*stage_history, "post_processing_safety"],
            "web_fallback_used": "web_fallback" in stage_history,
            "web_context_count": sum(
                context.retrieval_route == "web_fallback" for context in contexts
            ),
        }
        context_injection_detected = any(
            context.metadata.get("security_injection_detected") is True
            for context in contexts
        )
        final_result = replace(
            final_result,
            query_id=request.request_id,
            request=request,
            route=route,
            grounding_score=(
                None if reflection is None else reflection.scores.answer_support
            ),
            utility_score=(
                None if reflection is None else reflection.scores.usefulness
            ),
            injection_detected=(
                final_result.injection_detected
                or context_injection_detected
                or (reflection is not None and reflection.injection_detected)
            ),
            reflection_scores=None if reflection is None else reflection.scores,
            corrective_actions=corrective_actions,
            metadata=metadata,
        )
        return RagPostProcessingDecision(
            result=final_result,
            status="failed" if final_result.status == "failed" else "completed",
        )

    @staticmethod
    def _apply_reflection_safety(
        result: RagResult,
        reflection: RagSelfReflection | None,
    ) -> RagResult:
        if reflection is None or (
            reflection.answer_supported and not reflection.injection_detected
        ):
            return result
        return replace(
            result,
            answer_text=safe_grounding_failure_answer(),
            status="no_results",
            error=None,
        )
