from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationCaseRecord,
    EvaluationDatasetCaseReplacement,
    EvaluationDatasetRecord,
    EvaluationMetricResultRecord,
    EvaluationPersistenceBundle,
    EvaluationPersistenceResult,
    EvaluationRunRecord,
    LangfuseProjectionStatus,
    new_evaluation_artifact_id,
    new_evaluation_metric_result_id,
)
from domain.evaluation import (
    EvaluationCase,
    EvaluationDatasetReference,
    EvaluationMetricResult,
    EvaluationRun,
    EvaluationScore,
    EvaluationStatus,
    EvaluationTargetType,
    EvaluationThreshold,
)


def test_evaluation_records_preserve_canonical_fields() -> None:
    dataset = EvaluationDatasetRecord(
        dataset_id="dataset-1",
        name="rag-answer-quality",
        version="2026-07-14",
        target_type=EvaluationTargetType.RAG_ANSWER,
        tags=("rag", "quality"),
        source_lineage=("postgres.rag_documents",),
        deterministic_fixture_uri="tests/evaluation/fixtures/rag.jsonl",
        threshold_profile={"faithfulness": 0.8},
    )
    case = EvaluationCaseRecord(
        case_id="case-1",
        dataset_id=dataset.dataset_id,
        target_type="rag_answer",
        input_text="What changed?",
        actual_output="Rates moved higher.",
        expected_output="Rates moved higher.",
        source_record_ids=("record-1",),
        workflow_execution_id="execution-1",
        langfuse_trace_id="trace-1",
        langfuse_observation_id="observation-1",
        retrieval_context=("chunk-1",),
        citation_context_ids=("citation-1",),
    )
    run = EvaluationRunRecord(
        run_id="run-1",
        dataset_id=dataset.dataset_id,
        target_type=EvaluationTargetType.RAG_ANSWER,
        status=EvaluationStatus.RUNNING,
        evaluator_provider="openai",
        evaluator_model="gpt-test",
        case_ids=(case.case_id,),
    )
    metric_result = EvaluationMetricResultRecord(
        metric_result_id="metric-1",
        run_id=run.run_id,
        case_id=case.case_id,
        metric_name="faithfulness",
        score=0.91,
        threshold=0.8,
        threshold_version="v1",
        passed=True,
        reason="grounded answer",
        status=EvaluationStatus.PASSED,
        evaluator_provider="openai",
        evaluator_model="gpt-test",
        duration_ms=12.5,
    )
    artifact = EvaluationArtifactRecord(
        artifact_id="artifact-1",
        run_id=run.run_id,
        case_id=case.case_id,
        artifact_type="deepeval_report",
        payload={"summary": "ok"},
    )

    assert dataset.target_type is EvaluationTargetType.RAG_ANSWER
    assert dataset.source_lineage == ("postgres.rag_documents",)
    assert dataset.deterministic_fixture_uri == "tests/evaluation/fixtures/rag.jsonl"
    assert case.target_type is EvaluationTargetType.RAG_ANSWER
    assert run.langfuse_projection_status is LangfuseProjectionStatus.PENDING
    assert metric_result.langfuse_projection_status is LangfuseProjectionStatus.PENDING
    assert artifact.payload == {"summary": "ok"}


def test_evaluation_records_can_be_created_from_domain_models() -> None:
    created_at = datetime(2026, 7, 14, tzinfo=UTC)
    dataset = EvaluationDatasetReference(
        dataset_id="dataset-1",
        name="strategy-quality",
        version="v1",
    )
    case = EvaluationCase(
        case_id="case-1",
        dataset=dataset,
        target_type=EvaluationTargetType.STRATEGY_SYNTHESIS,
        input_text="Assess strategy.",
        actual_output="Prefer defensive tilt.",
        rubric="Must cite risk.",
        created_at=created_at,
    )
    run = EvaluationRun(
        run_id="run-1",
        dataset=dataset,
        target_type=EvaluationTargetType.STRATEGY_SYNTHESIS,
        status=EvaluationStatus.PASSED,
        evaluator_provider="openai",
        evaluator_model="gpt-test",
        case_ids=(case.case_id,),
        started_at=created_at,
    )
    result = EvaluationMetricResult(
        run_id=run.run_id,
        case_id=case.case_id,
        score=EvaluationScore(
            metric_name="answer_relevancy",
            score=0.93,
            threshold=EvaluationThreshold(
                metric_name="answer_relevancy",
                minimum_score=0.7,
                version="v2",
            ),
            reason="relevant",
        ),
        status=EvaluationStatus.PASSED,
        evaluator_provider="openai",
        evaluator_model="gpt-test",
        duration_ms=7.5,
        created_at=created_at,
    )

    case_record = EvaluationCaseRecord.from_domain(case)
    run_record = EvaluationRunRecord.from_domain(run)
    metric_record = EvaluationMetricResultRecord.from_domain(
        result,
        metric_result_id="metric-1",
    )

    assert case_record.dataset_id == dataset.dataset_id
    assert case_record.rubric == "Must cite risk."
    assert run_record.dataset_id == dataset.dataset_id
    assert run_record.case_ids == (case.case_id,)
    assert metric_record.threshold == 0.7
    assert metric_record.threshold_version == "v2"
    assert metric_record.passed is True
    assert metric_record.reason == "relevant"
    assert metric_record.created_at == created_at


def test_evaluation_persistence_bundle_reports_total_records() -> None:
    bundle = EvaluationPersistenceBundle(
        datasets=(
            EvaluationDatasetRecord(
                dataset_id="dataset-1",
                name="rag-quality",
                version="v1",
            ),
        ),
        cases=(
            EvaluationCaseRecord(
                case_id="case-1",
                target_type=EvaluationTargetType.RAG_ANSWER,
                input_text="Question",
                actual_output="Answer",
                rubric="Judge grounding.",
            ),
        ),
        dataset_case_replacements=(
            EvaluationDatasetCaseReplacement(
                dataset_id="dataset-1",
                case_ids=("case-1",),
            ),
        ),
    )
    result = EvaluationPersistenceResult(
        datasets_written=len(bundle.datasets),
        cases_written=len(bundle.cases),
        runs_written=1,
        metric_results_written=2,
        artifacts_written=3,
    )

    assert bundle.dataset_case_replacements[0].case_ids == ("case-1",)
    assert result.records_written == 8


def test_evaluation_record_validation_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="score must be between"):
        EvaluationMetricResultRecord(
            metric_result_id="metric-1",
            run_id="run-1",
            case_id="case-1",
            metric_name="faithfulness",
            score=1.2,
            status=EvaluationStatus.FAILED,
            evaluator_provider="openai",
            evaluator_model="gpt-test",
        )

    with pytest.raises(ValueError, match="uri or payload"):
        EvaluationArtifactRecord(
            artifact_id="artifact-1",
            run_id="run-1",
            artifact_type="report",
        )


def test_evaluation_record_ids_use_stable_prefixes() -> None:
    assert new_evaluation_metric_result_id().startswith("evaluation_metric_result_")
    assert new_evaluation_artifact_id().startswith("evaluation_artifact_")
