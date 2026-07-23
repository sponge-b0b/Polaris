from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class EvaluationDatasetModel(Base):
    """Versioned canonical dataset used by Polaris LLM evaluation workflows."""

    __tablename__ = "evaluation_datasets"
    __table_args__ = (
        UniqueConstraint(
            "name",
            "version",
            name="uq_evaluation_datasets_name_version",
        ),
        CheckConstraint(
            "jsonb_typeof(tags) = 'array'",
            name="ck_evaluation_datasets_tags_array",
        ),
        CheckConstraint(
            "jsonb_typeof(source_lineage) = 'array'",
            name="ck_evaluation_datasets_source_lineage_array",
        ),
        CheckConstraint(
            "threshold_profile IS NULL OR jsonb_typeof(threshold_profile) = 'object'",
            name="ck_evaluation_datasets_threshold_profile_object",
        ),
    )

    dataset_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    version: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_lineage: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    deterministic_fixture_uri: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    threshold_profile: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EvaluationCaseModel(Base):
    """Canonical input/output case prepared for deterministic LLM evaluation."""

    __tablename__ = "evaluation_cases"
    __table_args__ = (
        CheckConstraint(
            "expected_output IS NOT NULL OR rubric IS NOT NULL",
            name="ck_evaluation_cases_expected_output_or_rubric",
        ),
        CheckConstraint(
            "jsonb_typeof(source_record_ids) = 'array'",
            name="ck_evaluation_cases_source_record_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(retrieval_context) = 'array'",
            name="ck_evaluation_cases_retrieval_context_array",
        ),
        CheckConstraint(
            "jsonb_typeof(citation_context_ids) = 'array'",
            name="ck_evaluation_cases_citation_context_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(tags) = 'array'",
            name="ck_evaluation_cases_tags_array",
        ),
    )

    case_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("evaluation_datasets.dataset_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    actual_output: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_record_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    workflow_execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    langfuse_trace_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    langfuse_observation_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    retrieval_context: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    citation_context_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EvaluationRunModel(Base):
    """Durable execution record for one Polaris LLM evaluation run."""

    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'passed', 'failed', 'errored', "
            "'skipped')",
            name="ck_evaluation_runs_status",
        ),
        CheckConstraint(
            "langfuse_projection_status IN ('pending', 'projected', 'failed', "
            "'skipped')",
            name="ck_evaluation_runs_langfuse_projection_status",
        ),
        CheckConstraint(
            "jsonb_typeof(case_ids) = 'array'",
            name="ck_evaluation_runs_case_ids_array",
        ),
    )

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("evaluation_datasets.dataset_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evaluator_provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evaluator_model: Mapped[str] = mapped_column(String, nullable=False, index=True)
    case_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    langfuse_projection_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )
    langfuse_export_job_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EvaluationMetricResultModel(Base):
    """Queryable DeepEval metric result for one evaluation run and case."""

    __tablename__ = "evaluation_metric_results"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "case_id",
            "metric_name",
            name="uq_evaluation_metric_results_run_case_metric",
        ),
        CheckConstraint(
            "score >= 0.0 AND score <= 1.0",
            name="ck_evaluation_metric_results_score_range",
        ),
        CheckConstraint(
            "threshold IS NULL OR (threshold >= 0.0 AND threshold <= 1.0)",
            name="ck_evaluation_metric_results_threshold_range",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'passed', 'failed', 'errored', "
            "'skipped')",
            name="ck_evaluation_metric_results_status",
        ),
        CheckConstraint(
            "langfuse_projection_status IN ('pending', 'projected', 'failed', "
            "'skipped')",
            name="ck_evaluation_metric_results_langfuse_projection_status",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0.0",
            name="ck_evaluation_metric_results_duration_non_negative",
        ),
        CheckConstraint(
            "error_details IS NULL OR jsonb_typeof(error_details) = 'object'",
            name="ck_evaluation_metric_results_error_details_object",
        ),
    )

    metric_result_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("evaluation_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("evaluation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_version: Mapped[str | None] = mapped_column(String, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evaluator_provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    evaluator_model: Mapped[str] = mapped_column(String, nullable=False, index=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    langfuse_projection_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending",
        index=True,
    )
    langfuse_export_job_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EvaluationArtifactModel(Base):
    """Durable evaluation artifact linked to a run and optionally a case."""

    __tablename__ = "evaluation_artifacts"
    __table_args__ = (
        CheckConstraint(
            "payload IS NULL OR jsonb_typeof(payload) = 'object'",
            name="ck_evaluation_artifacts_payload_object",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("evaluation_runs.run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("evaluation_cases.case_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index(
    "idx_evaluation_cases_dataset_target",
    EvaluationCaseModel.dataset_id,
    EvaluationCaseModel.target_type,
)
Index(
    "idx_evaluation_cases_langfuse_trace_observation",
    EvaluationCaseModel.langfuse_trace_id,
    EvaluationCaseModel.langfuse_observation_id,
)
Index(
    "idx_evaluation_runs_dataset_status",
    EvaluationRunModel.dataset_id,
    EvaluationRunModel.status,
)
Index(
    "idx_evaluation_runs_target_started_at",
    EvaluationRunModel.target_type,
    EvaluationRunModel.started_at,
)
Index(
    "idx_evaluation_metric_results_run_status",
    EvaluationMetricResultModel.run_id,
    EvaluationMetricResultModel.status,
)
Index(
    "idx_evaluation_metric_results_metric_passed",
    EvaluationMetricResultModel.metric_name,
    EvaluationMetricResultModel.passed,
)
Index(
    "idx_evaluation_artifacts_run_type",
    EvaluationArtifactModel.run_id,
    EvaluationArtifactModel.artifact_type,
)
