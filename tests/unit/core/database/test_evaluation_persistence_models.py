from __future__ import annotations

from sqlalchemy import Table

from core.database.models.evaluation import EvaluationArtifactModel
from core.database.models.evaluation import EvaluationCaseModel
from core.database.models.evaluation import EvaluationDatasetModel
from core.database.models.evaluation import EvaluationMetricResultModel
from core.database.models.evaluation import EvaluationRunModel


def test_evaluation_dataset_model_defines_first_class_fields() -> None:
    table = EvaluationDatasetModel.__table__
    assert isinstance(table, Table)

    assert table.name == "evaluation_datasets"
    assert table.c.dataset_id.primary_key
    assert table.c.name.nullable is False
    assert table.c.version.nullable is False
    assert "target_type" in table.c
    assert "source_lineage" in table.c
    assert "deterministic_fixture_uri" in table.c
    assert "threshold_profile" in table.c
    assert "active" in table.c
    assert "created_at" in table.c
    assert "updated_at" in table.c


def test_evaluation_case_model_defines_source_and_langfuse_fields() -> None:
    table = EvaluationCaseModel.__table__
    assert isinstance(table, Table)

    assert table.name == "evaluation_cases"
    assert table.c.case_id.primary_key
    assert table.c.target_type.nullable is False
    assert table.c.input_text.nullable is False
    assert table.c.actual_output.nullable is False
    assert "source_record_ids" in table.c
    assert "workflow_execution_id" in table.c
    assert "langfuse_trace_id" in table.c
    assert "langfuse_observation_id" in table.c
    assert "retrieval_context" in table.c
    assert "citation_context_ids" in table.c


def test_evaluation_run_model_defines_projection_status_fields() -> None:
    table = EvaluationRunModel.__table__
    assert isinstance(table, Table)

    assert table.name == "evaluation_runs"
    assert table.c.run_id.primary_key
    assert table.c.status.nullable is False
    assert table.c.evaluator_provider.nullable is False
    assert table.c.evaluator_model.nullable is False
    assert table.c.case_ids.nullable is False
    assert table.c.langfuse_projection_status.nullable is False
    assert "langfuse_export_job_id" in table.c
    assert "error_details" in table.c


def test_evaluation_metric_result_model_defines_metric_fields_and_constraints() -> None:
    table = EvaluationMetricResultModel.__table__
    assert isinstance(table, Table)
    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert table.name == "evaluation_metric_results"
    assert table.c.metric_result_id.primary_key
    assert table.c.metric_name.nullable is False
    assert table.c.score.nullable is False
    assert "threshold" in table.c
    assert "threshold_version" in table.c
    assert "passed" in table.c
    assert "reason" in table.c
    assert "duration_ms" in table.c
    assert "error_details" in table.c
    assert "langfuse_projection_status" in table.c
    assert "uq_evaluation_metric_results_run_case_metric" in constraint_names
    assert "ck_evaluation_metric_results_score_range" in constraint_names
    assert "ck_evaluation_metric_results_threshold_range" in constraint_names
    assert "idx_evaluation_metric_results_metric_passed" in index_names


def test_evaluation_artifact_model_defines_artifact_boundary_fields() -> None:
    table = EvaluationArtifactModel.__table__
    assert isinstance(table, Table)
    index_names = {index.name for index in table.indexes}

    assert table.name == "evaluation_artifacts"
    assert table.c.artifact_id.primary_key
    assert table.c.run_id.nullable is False
    assert table.c.artifact_type.nullable is False
    assert "case_id" in table.c
    assert "uri" in table.c
    assert "payload" in table.c
    assert "idx_evaluation_artifacts_run_type" in index_names
