from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.validation import PersistenceRecordValidationTarget
from core.storage.persistence.validation import PersistenceScoreValidationSpec
from core.storage.persistence.validation import PersistenceTimestampOrderRule
from core.storage.persistence.validation import PersistenceValidationSeverity
from core.storage.persistence.validation import PersistenceValidationStatus
from core.storage.persistence.validation import validate_score_fields
from core.storage.persistence.validation import validate_timestamp_and_score_fields
from core.storage.persistence.validation import validate_timestamp_fields


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeReportRecord:
    generated_at: datetime | None
    published_at: datetime | None
    requested_at: datetime | None
    confidence: float | None
    setup_quality: float | None
    risk_score: float | None


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeSignalRecord:
    observed_at: datetime | str | None
    directional_score: float | None
    sentiment_score: float | None
    contribution_score: float | str | None


def test_timestamp_validation_accepts_aware_ordered_representative_record() -> None:
    record = RepresentativeReportRecord(
        generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
        published_at=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
        requested_at=datetime(2026, 5, 30, 12, 45, tzinfo=timezone.utc),
        confidence=0.82,
        setup_quality=0.76,
        risk_score=0.24,
    )

    result = validate_timestamp_fields(
        _target(
            "report",
            "report-1",
            record,
        ),
        required_timestamp_field_names=("generated_at",),
        now=datetime(2026, 5, 30, 15, 0, tzinfo=timezone.utc),
    )

    assert result.status == PersistenceValidationStatus.PASSED
    assert result.issue_count == 0


def test_timestamp_validation_reports_required_missing_naive_future_and_order_issues() -> (
    None
):
    record = RepresentativeReportRecord(
        generated_at=None,
        published_at=datetime(2026, 5, 30, 12, 0),
        requested_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
        confidence=0.82,
        setup_quality=0.76,
        risk_score=0.24,
    )

    result = validate_timestamp_fields(
        _target(
            "report",
            "report-1",
            record,
        ),
        required_timestamp_field_names=("generated_at",),
        now=datetime(2026, 5, 30, 11, 0, tzinfo=timezone.utc),
        future_tolerance=timedelta(),
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert result.is_valid is False
    assert [issue.field_name for issue in result.issues] == [
        "generated_at",
        "published_at",
        "published_at",
        "published_at",
    ]
    assert result.issues[0].severity == PersistenceValidationSeverity.ERROR
    assert result.issues[1].severity == PersistenceValidationSeverity.WARNING
    assert result.issues[2].severity == PersistenceValidationSeverity.WARNING
    assert result.issues[3].severity == PersistenceValidationSeverity.ERROR


def test_timestamp_validation_reports_type_and_required_missing_field() -> None:
    record = RepresentativeSignalRecord(
        observed_at="2026-05-30T14:00:00Z",
        directional_score=0.6,
        sentiment_score=-0.2,
        contribution_score=0.45,
    )

    result = validate_timestamp_fields(
        _target(
            "signal",
            "signal-1",
            record,
        ),
        timestamp_field_names=("observed_at", "generated_at"),
        required_timestamp_field_names=("observed_at", "generated_at"),
        timestamp_order_rules=(),
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert [issue.field_name for issue in result.issues] == [
        "observed_at",
        "generated_at",
    ]
    assert "datetime" in result.issues[0].message
    assert "missing" in result.issues[1].message


def test_score_validation_accepts_canonical_representative_ranges() -> None:
    record = RepresentativeSignalRecord(
        observed_at=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
        directional_score=-0.4,
        sentiment_score=0.25,
        contribution_score=0.8,
    )

    result = validate_score_fields(
        _target(
            "signal",
            "signal-1",
            record,
        )
    )

    assert result.status == PersistenceValidationStatus.PASSED
    assert result.issue_count == 0


def test_score_validation_reports_ratio_signed_and_non_numeric_issues() -> None:
    record = RepresentativeSignalRecord(
        observed_at=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
        directional_score=1.4,
        sentiment_score=-1.2,
        contribution_score="high",
    )

    result = validate_score_fields(
        _target(
            "signal",
            "signal-1",
            record,
        )
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert result.is_valid is False
    assert [issue.field_name for issue in result.issues] == [
        "sentiment_score",
        "directional_score",
        "contribution_score",
    ]
    assert result.issues[0].metadata["minimum"] == -1.0
    assert result.issues[1].metadata["score_type"] == "directional"
    assert result.issues[2].metadata["observed_type"] == "str"


def test_custom_score_spec_validates_setup_quality_style_fields() -> None:
    record = RepresentativeReportRecord(
        generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
        published_at=None,
        requested_at=None,
        confidence=0.95,
        setup_quality=1.1,
        risk_score=0.2,
    )

    result = validate_score_fields(
        _target(
            "trade_setup",
            "setup-1",
            record,
        ),
        score_specs=(
            PersistenceScoreValidationSpec(
                field_name="setup_quality",
                minimum=0.0,
                maximum=1.0,
                score_type="setup_quality",
            ),
        ),
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert result.issues[0].field_name == "setup_quality"
    assert result.issues[0].metadata["maximum"] == 1.0


def test_combined_timestamp_and_score_validation_merges_non_destructive_results() -> (
    None
):
    record = RepresentativeReportRecord(
        generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
        published_at=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
        requested_at=datetime(2026, 5, 30, 12, 45, tzinfo=timezone.utc),
        confidence=1.2,
        setup_quality=0.76,
        risk_score=0.24,
    )

    result = validate_timestamp_and_score_fields(
        _target(
            "report",
            "report-1",
            record,
        ),
        required_timestamp_field_names=("generated_at",),
        timestamp_order_rules=(
            PersistenceTimestampOrderRule(
                earlier_field_name="generated_at",
                later_field_name="published_at",
            ),
        ),
        now=datetime(2026, 5, 30, 15, 0, tzinfo=timezone.utc),
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert result.issue_count == 1
    assert result.issues[0].field_name == "confidence"
    assert result.metadata == {"validator": "timestamp_and_score_fields"}


def _target(
    record_type: str,
    record_id: str,
    record: object,
) -> PersistenceRecordValidationTarget:
    return PersistenceRecordValidationTarget(
        identity=PersistenceRecordIdentity(
            record_type=record_type,
            record_id=record_id,
        ),
        record=record,
    )
