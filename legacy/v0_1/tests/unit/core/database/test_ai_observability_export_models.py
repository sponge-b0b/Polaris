from __future__ import annotations

from sqlalchemy import Table

from core.database.models.ai_observability import AiObservabilityExportJobModel


def test_ai_observability_export_job_model_defines_canonical_table() -> None:
    table = AiObservabilityExportJobModel.__table__
    assert isinstance(table, Table)

    assert table.name == "ai_observability_export_jobs"
    assert table.c.export_job_id.primary_key
    assert table.c.idempotency_key.nullable is False
    assert table.c.payload.nullable is False
    assert table.c.status.nullable is False
    assert "external_trace_id" in table.c
    assert "external_observation_id" in table.c
    assert "dataset_id" in table.c
    assert "case_id" in table.c
    assert "run_id" in table.c


def test_ai_observability_export_job_model_defines_retry_constraints() -> None:
    table = AiObservabilityExportJobModel.__table__
    assert isinstance(table, Table)
    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert "uq_ai_observability_export_jobs_idempotency_key" in constraint_names
    assert "ck_ai_observability_export_jobs_status" in constraint_names
    assert (
        "ck_ai_observability_export_jobs_attempt_count_non_negative" in constraint_names
    )
    assert "ck_ai_observability_export_jobs_max_attempts_positive" in constraint_names
    assert (
        "ck_ai_observability_export_jobs_retry_after_non_negative" in constraint_names
    )
    assert "ck_ai_observability_export_jobs_payload_object" in constraint_names
    assert "idx_ai_observability_export_jobs_status_available_at" in index_names
    assert "idx_ai_observability_export_jobs_trace_span" in index_names
