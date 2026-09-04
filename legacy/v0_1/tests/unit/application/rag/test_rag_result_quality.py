from __future__ import annotations

from application.rag.contracts.rag_quality_models import RagReflectionScores
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.graphs import RagCorrectiveAction


def test_rag_result_quality_fields_round_trip() -> None:
    request = RagRequest(
        query="What changed?",
        request_id="rag_query:quality-result",
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
        injection_detected=False,
        reflection_scores=scores,
        corrective_actions=(RagCorrectiveAction.REWRITE, RagCorrectiveAction.PROCEED),
    )

    restored = RagResult.from_dict(result.to_dict())

    assert restored == result
    assert restored.reflection_scores == scores
