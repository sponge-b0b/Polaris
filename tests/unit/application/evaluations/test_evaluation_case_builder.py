from __future__ import annotations

from application.evaluations import EvaluationCaseBuildRequest
from application.evaluations import EvaluationCaseBuilder
from domain.evaluation import EvaluationDatasetReference
from domain.evaluation import EvaluationTargetType


def test_case_builder_preserves_lineage_and_context() -> None:
    dataset = EvaluationDatasetReference(
        dataset_id="dataset-1",
        name="golden_rag_questions",
        version="v1",
    )
    case = EvaluationCaseBuilder().build(
        EvaluationCaseBuildRequest(
            case_id="case-1",
            target_type=EvaluationTargetType.RAG_ANSWER,
            input_text="What changed?",
            actual_output="The answer cites record A.",
            dataset=dataset,
            rubric="Answer must cite supported evidence.",
            source_record_ids=("rag-doc-1",),
            workflow_execution_id="execution-1",
            langfuse_trace_id="trace-1",
            langfuse_observation_id="observation-1",
            retrieval_context=("context text",),
            citation_context_ids=("chunk-1",),
            tags=("smoke",),
        )
    )

    assert case.case_id == "case-1"
    assert case.dataset == dataset
    assert case.source_record_ids == ("rag-doc-1",)
    assert case.retrieval_context == ("context text",)
    assert case.citation_context_ids == ("chunk-1",)
