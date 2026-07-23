from __future__ import annotations

import pytest

from application.evaluations.evaluation_telemetry import EvaluationTelemetry
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.evaluation import (
    EvaluationMetricResult,
    EvaluationScore,
    EvaluationStatus,
    EvaluationTargetType,
    EvaluationThreshold,
)


@pytest.mark.asyncio
async def test_evaluation_telemetry_records_run_lifecycle_and_metrics() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    telemetry = EvaluationTelemetry(observability)

    await telemetry.emit_run_started(
        run_id="run-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
        case_count=1,
        metric_count=1,
        dataset_id="dataset-1",
    )
    telemetry.record_cases_evaluated(
        target_type=EvaluationTargetType.RAG_ANSWER,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
        case_count=1,
    )
    telemetry.record_metric_result(
        EvaluationMetricResult(
            run_id="run-1",
            case_id="case-1",
            score=EvaluationScore(
                metric_name="faithfulness",
                score=0.7,
                threshold=EvaluationThreshold("faithfulness", 0.8),
            ),
            status=EvaluationStatus.FAILED,
            evaluator_provider="deepeval",
            evaluator_model="qwen3.5:4b",
            duration_ms=25.0,
        ),
        target_type=EvaluationTargetType.RAG_ANSWER,
    )
    await telemetry.emit_run_completed(
        run_id="run-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        status=EvaluationStatus.FAILED,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
        case_count=1,
        metric_result_count=1,
        dataset_id="dataset-1",
        duration_seconds=0.25,
    )

    event_types = [event.event_type for event in sink.events]
    metric_names = [point.name for point in observability.metrics_store.points()]

    assert event_types == ["evaluation.run.started", "evaluation.run.completed"]
    assert "evaluation_runs_total" in metric_names
    assert "evaluation_metric_duration_seconds" in metric_names
    assert "evaluation_cases_evaluated_total" in metric_names
    assert "evaluation_threshold_failures_total" in metric_names


@pytest.mark.asyncio
async def test_evaluation_telemetry_records_failure_projection_and_job_signals() -> (
    None
):
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    telemetry = EvaluationTelemetry(observability)

    await telemetry.emit_run_failed(
        run_id="run-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        evaluator_provider="deepeval",
        evaluator_model="qwen3.5:4b",
        case_count=1,
        dataset_id="dataset-1",
        duration_seconds=0.1,
        error=RuntimeError("judge unavailable"),
    )
    await telemetry.emit_dataset_load_failed(
        job_id="job-1",
        job_type="evaluate_rag_result",
        case_id="case-1",
        dataset_id="missing-dataset",
    )
    telemetry.record_langfuse_projection_failures(
        run_id="run-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        failed_count=2,
    )
    telemetry.record_retry_count(
        job_id="job-2",
        job_type="retry_failed_eval_projection",
    )
    telemetry.record_skipped_cases(
        job_id="job-3",
        job_type="project_eval_scores_to_langfuse",
        skipped_count=1,
        reason="no_metric_results",
    )

    event_types = [event.event_type for event in sink.events]
    metric_names = [point.name for point in observability.metrics_store.points()]

    assert "evaluation.run.failed" in event_types
    assert "evaluation.dataset.load_failed" in event_types
    assert "evaluation_judge_model_failures_total" in metric_names
    assert "evaluation_dataset_load_failures_total" in metric_names
    assert "evaluation_langfuse_projection_failures_total" in metric_names
    assert "evaluation_retry_jobs_total" in metric_names
    assert "evaluation_skipped_cases_total" in metric_names
