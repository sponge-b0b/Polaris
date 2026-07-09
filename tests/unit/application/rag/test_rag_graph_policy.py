from __future__ import annotations

import pytest

from application.rag.graphs.rag_graph_policy import RagCorrectiveRoute
from application.rag.graphs.rag_graph_policy import RagGraphPolicy
from application.rag.graphs.rag_graph_policy import RagSelectionRoute
from application.rag.routing.query_routing_models import RagQueryModelExecution
from application.rag.routing.query_routing_models import RagRetrievalRoute
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_quality_models import RagContextEvaluation
from application.rag.contracts.rag_quality_models import RagContextQuality
from application.rag.contracts.rag_quality_models import RagCorrectiveAction
from application.rag.contracts.rag_quality_models import RagReflectionScores
from application.rag.contracts.rag_quality_models import RagSelfReflection
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.security.rag_security import safe_grounding_failure_answer


@pytest.fixture
def policy() -> RagGraphPolicy:
    return RagGraphPolicy()


def test_routes_corrective_loop_when_rewrite_is_available(
    policy: RagGraphPolicy,
) -> None:
    route = policy.route_after_crag(
        evaluation=_evaluation(RagCorrectiveAction.REWRITE),
        has_context=False,
        loop_count=1,
        max_loops=2,
        rewrite_available=True,
        allow_web=False,
        web_fallback_available=False,
    )

    assert route is RagCorrectiveRoute.REWRITE


def test_fails_closed_when_corrective_loop_reaches_maximum(
    policy: RagGraphPolicy,
) -> None:
    route = policy.route_after_crag(
        evaluation=_evaluation(RagCorrectiveAction.REWRITE),
        has_context=False,
        loop_count=2,
        max_loops=2,
        rewrite_available=True,
        allow_web=False,
        web_fallback_available=False,
    )

    assert route is RagCorrectiveRoute.FAIL_CLOSED


def test_fails_closed_when_low_quality_filter_removes_all_context(
    policy: RagGraphPolicy,
) -> None:
    route = policy.route_after_crag(
        evaluation=_evaluation(RagCorrectiveAction.DISCARD_WEAK_CONTEXT),
        has_context=False,
        loop_count=0,
        max_loops=1,
        rewrite_available=False,
        allow_web=False,
        web_fallback_available=False,
    )

    assert route is RagCorrectiveRoute.FAIL_CLOSED


def test_routes_to_permitted_web_fallback(policy: RagGraphPolicy) -> None:
    route = policy.route_after_crag(
        evaluation=_evaluation(RagCorrectiveAction.WEB_FALLBACK),
        has_context=False,
        loop_count=0,
        max_loops=1,
        rewrite_available=False,
        allow_web=True,
        web_fallback_available=True,
    )

    assert route is RagCorrectiveRoute.WEB_FALLBACK
    assert (
        policy.route_after_web_fallback(has_context=True) is RagCorrectiveRoute.GENERATE
    )


def test_security_rejection_replaces_unsupported_synthesis(
    policy: RagGraphPolicy,
) -> None:
    request = _request()
    reflection = RagSelfReflection(
        scores=_scores(answer_support=0.1, usefulness=0.2),
        answer_supported=False,
        injection_detected=True,
    )

    decision = policy.finalize_result(
        result=RagResult.answered(
            request=request,
            answer_text="Unsupported answer.",
            contexts=(_context(),),
        ),
        request=request,
        route=RagRetrievalRoute.RETRIEVAL.value,
        reflection=reflection,
        contexts=(_context(),),
        corrective_actions=(RagCorrectiveAction.FAIL_CLOSED,),
        model_executions=(),
        loop_count=0,
        stage_history=("self_rag_reflection",),
    )

    assert decision.status == "completed"
    assert decision.result.status == "no_results"
    assert decision.result.answer_text == safe_grounding_failure_answer()
    assert decision.result.injection_detected is True
    assert decision.result.grounding_score == 0.1


def test_successful_synthesis_preserves_answer_and_audit_data(
    policy: RagGraphPolicy,
) -> None:
    request = _request()
    context = _context()
    result = RagResult.answered(
        request=request,
        answer_text="Breadth improved [C1].",
        contexts=(context,),
    )
    reflection = RagSelfReflection(
        scores=_scores(answer_support=0.95, usefulness=0.85),
        answer_supported=True,
    )
    execution = RagQueryModelExecution(
        operation="route_selection",
        configured_model="unit-test-model",
        provider_name="unit-test-provider",
        duration_ms=1.0,
        success=True,
    )

    decision = policy.finalize_result(
        result=result,
        request=request,
        route=RagRetrievalRoute.RETRIEVAL.value,
        reflection=reflection,
        contexts=(context,),
        corrective_actions=(RagCorrectiveAction.PROCEED,),
        model_executions=(execution,),
        loop_count=1,
        stage_history=("secure_generation", "self_rag_reflection"),
    )

    assert decision.status == "completed"
    assert decision.result.answer_text == result.answer_text
    assert decision.result.status == "answered"
    assert decision.result.grounding_score == 0.95
    assert decision.result.utility_score == 0.85
    assert decision.result.corrective_actions == (RagCorrectiveAction.PROCEED,)
    assert decision.result.metadata["loop_count"] == 1
    assert decision.result.metadata["graph_stages"] == [
        "secure_generation",
        "self_rag_reflection",
        "post_processing_safety",
    ]


@pytest.mark.parametrize(
    ("route", "expected"),
    [
        (RagRetrievalRoute.DIRECT_ANSWER, RagSelectionRoute.DIRECT),
        (RagRetrievalRoute.RETRIEVAL, RagSelectionRoute.RETRIEVAL),
        (RagRetrievalRoute.DEEP_RESEARCH, RagSelectionRoute.DEEP_RESEARCH),
    ],
)
def test_selects_typed_graph_route(
    policy: RagGraphPolicy,
    route: RagRetrievalRoute,
    expected: RagSelectionRoute,
) -> None:
    assert policy.route_after_selection(route) is expected


def _evaluation(action: RagCorrectiveAction) -> RagContextEvaluation:
    return RagContextEvaluation(
        quality=RagContextQuality.MISSING,
        action=action,
    )


def _request() -> RagRequest:
    return RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:graph-policy",
    )


def _scores(*, answer_support: float, usefulness: float) -> RagReflectionScores:
    return RagReflectionScores(
        retrieval_necessity=0.8,
        source_relevance=0.9,
        answer_support=answer_support,
        usefulness=usefulness,
    )


def _context() -> RagRetrievedContext:
    return RagRetrievedContext(
        context_id="context-1",
        text="SPY breadth improved as participation widened.",
        source=RagSource(
            "policy_sources",
            "policy-source-1",
            "policy_test",
            "policy-document-1",
            "Policy Evidence",
        ),
        score=0.91,
        rank=0,
        retrieval_route="hybrid",
    )
