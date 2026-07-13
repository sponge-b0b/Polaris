from __future__ import annotations

import pytest

from core.storage.persistence.ai_observability import AiObservabilityExportJobClaim
from core.storage.persistence.ai_observability import AiObservabilityExportJobRecord
from core.storage.persistence.ai_observability import AiObservabilityExportJobStatus


def test_ai_observability_export_job_record_coerces_status() -> None:
    record = AiObservabilityExportJobRecord(
        export_job_id="job-1",
        idempotency_key="key-1",
        observation_type="rag.query",
        observation_name="rag query",
        observation_family="rag",
        observation_status="success",
        payload={"name": "rag query"},
        status="failed",
        trace_id="trace-1",
    )

    assert record.status is AiObservabilityExportJobStatus.FAILED
    assert record.payload == {"name": "rag query"}
    assert record.trace_id == "trace-1"


def test_ai_observability_export_job_record_rejects_negative_attempt_count() -> None:
    with pytest.raises(ValueError):
        _record(attempt_count=-1)


def test_ai_observability_export_job_record_rejects_non_positive_max_attempts() -> None:
    with pytest.raises(ValueError):
        _record(max_attempts=0)


def test_ai_observability_export_job_record_rejects_negative_retry_delay() -> None:
    with pytest.raises(ValueError):
        _record(retry_after_seconds=-0.1)


def test_ai_observability_export_job_claim_defaults_to_retryable_statuses() -> None:
    claim = AiObservabilityExportJobClaim()

    assert claim.statuses == (
        AiObservabilityExportJobStatus.PENDING,
        AiObservabilityExportJobStatus.FAILED,
    )


def _record(
    *,
    attempt_count: int = 0,
    max_attempts: int = 3,
    retry_after_seconds: float | None = None,
) -> AiObservabilityExportJobRecord:
    return AiObservabilityExportJobRecord(
        export_job_id="job-1",
        idempotency_key="key-1",
        observation_type="rag.query",
        observation_name="rag query",
        observation_family="rag",
        observation_status="success",
        payload={"name": "rag query"},
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        retry_after_seconds=retry_after_seconds,
    )


def test_ai_observability_export_queue_status_reports_backlog_and_totals() -> None:
    from core.storage.persistence.ai_observability import (
        AiObservabilityExportQueueStatus,
    )

    status = AiObservabilityExportQueueStatus(
        pending_count=2,
        running_count=1,
        exported_count=5,
        failed_count=2,
        skipped_count=1,
        retryable_failed_count=1,
        exhausted_failed_count=1,
    )

    assert status.backlog_count == 4
    assert status.total_count == 11
    assert status.has_retry_pressure is True
    assert status.status_counts()[AiObservabilityExportJobStatus.PENDING.value] == 2


def test_ai_observability_export_queue_status_rejects_invalid_counts() -> None:
    from core.storage.persistence.ai_observability import (
        AiObservabilityExportQueueStatus,
    )

    with pytest.raises(ValueError):
        AiObservabilityExportQueueStatus(pending_count=-1)
    with pytest.raises(ValueError):
        AiObservabilityExportQueueStatus(
            failed_count=1,
            retryable_failed_count=2,
        )
