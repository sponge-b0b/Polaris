from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from core.storage.persistence.validation import (
    PersistenceValidationBatchResult,
    PersistenceValidationIssue,
    PersistenceValidationResult,
    PersistenceValidationSeverity,
    PersistenceValidationStatus,
)


def test_validation_issue_normalizes_fields_and_serializes_boundary_shape() -> None:
    issue = PersistenceValidationIssue(
        severity=" WARNING ",
        record_type=" report ",
        record_id=" morning-report-1 ",
        field_name=" confidence_score ",
        message=" confidence score is outside expected range ",
        remediation_hint=" clamp generated confidence to 0.0..1.0 ",
        metadata={"observed_value": 1.25},
    )

    assert issue.severity == PersistenceValidationSeverity.WARNING
    assert issue.record_type == "report"
    assert issue.record_id == "morning-report-1"
    assert issue.field_name == "confidence_score"
    assert issue.message == "confidence score is outside expected range"
    assert issue.remediation_hint == "clamp generated confidence to 0.0..1.0"
    assert issue.is_warning is True
    assert issue.is_error is False
    assert issue.identity.record_type == "report"
    assert issue.as_dict() == {
        "severity": "warning",
        "record_type": "report",
        "record_id": "morning-report-1",
        "message": "confidence score is outside expected range",
        "metadata": {"observed_value": 1.25},
        "field_name": "confidence_score",
        "remediation_hint": "clamp generated confidence to 0.0..1.0",
    }

    with pytest.raises(FrozenInstanceError):
        issue.message = "mutated"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"severity": "critical"}, "severity"),
        ({"record_type": " "}, "record_type"),
        ({"record_id": " "}, "record_id"),
        ({"message": " "}, "message"),
    ],
)
def test_validation_issue_rejects_invalid_required_fields(
    kwargs: dict[str, Any],
    field_name: str,
) -> None:
    values: dict[str, Any] = {
        "severity": "info",
        "record_type": "report",
        "record_id": "report-1",
        "message": "valid message",
    }
    values.update(
        kwargs,
    )

    with pytest.raises(ValueError, match=field_name):
        PersistenceValidationIssue(
            **values,
        )


def test_validation_result_aggregates_issues_without_mutating_records() -> None:
    warning = _issue(
        "warning",
        "published_at",
    )
    info = _issue(
        "info",
        None,
    )
    result = PersistenceValidationResult(
        record_type="news_article",
        record_id="article-1",
        issues=[warning, info],  # type: ignore[arg-type]
        metadata={"validator": "timestamp-check"},
    )

    assert result.identity.record_id == "article-1"
    assert result.issues == (
        warning,
        info,
    )
    assert result.issue_count == 2
    assert result.has_errors is False
    assert result.has_warnings is True
    assert result.is_valid is True
    assert result.status == PersistenceValidationStatus.WARNING
    assert result.issues_by_severity("warning") == (warning,)
    assert result.summary_dict() == {
        "record_type": "news_article",
        "record_id": "article-1",
        "status": "warning",
        "is_valid": True,
        "issue_count": 2,
        "error_count": 0,
        "warning_count": 1,
        "info_count": 1,
    }
    assert result.as_dict()["issues"] == (
        warning.as_dict(),
        info.as_dict(),
    )

    with pytest.raises(FrozenInstanceError):
        result.record_id = "mutated"  # type: ignore[misc]


def test_validation_result_rejects_cross_record_issues() -> None:
    with pytest.raises(ValueError, match="record identity"):
        PersistenceValidationResult(
            record_type="report",
            record_id="report-1",
            issues=(
                PersistenceValidationIssue(
                    severity="error",
                    record_type="recommendation",
                    record_id="rec-1",
                    message="wrong record",
                ),
            ),
        )


def test_validation_result_status_failed_when_error_issue_exists() -> None:
    error = _issue(
        "error",
        "score",
    )
    result = PersistenceValidationResult(
        record_type="news_article",
        record_id="article-1",
        issues=(error,),
    )

    assert result.has_errors is True
    assert result.is_valid is False
    assert result.status == PersistenceValidationStatus.FAILED


def test_validation_batch_result_aggregates_record_results() -> None:
    passed = PersistenceValidationResult(
        record_type="report",
        record_id="report-1",
    )
    warning = PersistenceValidationResult(
        record_type="news_article",
        record_id="article-1",
        issues=(
            _issue(
                "warning",
                "published_at",
            ),
        ),
    )
    failed = PersistenceValidationResult(
        record_type="signal",
        record_id="signal-1",
        issues=(
            PersistenceValidationIssue(
                severity="error",
                record_type="signal",
                record_id="signal-1",
                field_name="confidence",
                message="confidence score is outside expected range",
            ),
        ),
    )

    batch = PersistenceValidationBatchResult(
        results=[passed, warning, failed],  # type: ignore[arg-type]
        metadata={"scope": "curated-records"},
    )

    assert batch.record_count == 3
    assert batch.issue_count == 2
    assert batch.has_errors is True
    assert batch.has_warnings is True
    assert batch.is_valid is False
    assert batch.status == PersistenceValidationStatus.FAILED
    assert batch.results_by_status("passed") == (passed,)
    assert batch.results_by_status(PersistenceValidationStatus.WARNING) == (warning,)
    assert batch.summary_dict() == {
        "status": "failed",
        "is_valid": False,
        "record_count": 3,
        "issue_count": 2,
        "failed_record_count": 1,
        "warning_record_count": 1,
        "passed_record_count": 1,
    }
    assert batch.as_dict()["metadata"] == {"scope": "curated-records"}


def _issue(
    severity: PersistenceValidationSeverity | str,
    field_name: str | None,
) -> PersistenceValidationIssue:
    return PersistenceValidationIssue(
        severity=severity,
        record_type="news_article",
        record_id="article-1",
        field_name=field_name,
        message="representative validation issue",
        remediation_hint="review curated source record",
    )
