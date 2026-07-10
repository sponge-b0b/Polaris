from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.validation import PersistenceExpectedLineage
from core.storage.persistence.validation import PersistenceExternalSourceValidationSpec
from core.storage.persistence.validation import PersistenceRecordValidationTarget
from core.storage.persistence.validation import PersistenceValidationSeverity
from core.storage.persistence.validation import PersistenceValidationStatus
from core.storage.persistence.validation import validate_lineage_fields
from core.storage.persistence.validation import (
    validate_lineage_source_and_dedupe_fields,
)
from core.storage.persistence.validation import validate_source_and_dedupe_fields


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeWorkflowRecord:
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    external_id: str | None = None
    url: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeExternalRecord:
    source: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    external_id: str | None = None
    source_reference: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeManualRecord:
    title: str = "manual note"


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeBadLineageRecord:
    lineage: str = "workflow-1"


def test_lineage_validation_accepts_matching_expected_lineage() -> None:
    record = RepresentativeWorkflowRecord(
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="report_node",
        )
    )

    result = validate_lineage_fields(
        _target(
            "report",
            "report-1",
            record,
        ),
        expected_lineage=PersistenceExpectedLineage(
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
        ),
        require_lineage=True,
    )

    assert result.status == PersistenceValidationStatus.PASSED
    assert result.issue_count == 0


def test_lineage_validation_warns_for_records_created_outside_workflows() -> None:
    record = RepresentativeWorkflowRecord()

    result = validate_lineage_fields(
        _target(
            "manual_research_note",
            "note-1",
            record,
        )
    )

    assert result.status == PersistenceValidationStatus.WARNING
    assert result.is_valid is True
    assert result.issues[0].severity == PersistenceValidationSeverity.WARNING
    assert result.issues[0].field_name == "lineage"
    assert "outside the workflow runtime" in result.issues[0].message


def test_lineage_validation_fails_when_required_or_mismatched() -> None:
    missing_result = validate_lineage_fields(
        _target(
            "report",
            "report-1",
            RepresentativeManualRecord(),
        ),
        require_lineage=True,
    )
    mismatch_result = validate_lineage_fields(
        _target(
            "report",
            "report-2",
            RepresentativeWorkflowRecord(
                lineage=PersistenceLineage(
                    workflow_name="morning_report",
                    execution_id="exec-1",
                )
            ),
        ),
        expected_lineage=PersistenceExpectedLineage(
            workflow_name="morning_report",
            execution_id="exec-2",
        ),
    )
    invalid_type_result = validate_lineage_fields(
        _target(
            "report",
            "report-3",
            RepresentativeBadLineageRecord(),
        )
    )

    assert missing_result.status == PersistenceValidationStatus.FAILED
    assert missing_result.issues[0].field_name == "lineage"
    assert mismatch_result.status == PersistenceValidationStatus.FAILED
    assert mismatch_result.issues[0].field_name == "lineage.execution_id"
    assert mismatch_result.issues[0].metadata == {
        "expected_value": "exec-2",
        "observed_value": "exec-1",
    }
    assert invalid_type_result.status == PersistenceValidationStatus.FAILED
    assert invalid_type_result.issues[0].metadata["observed_type"] == "str"


def test_source_and_dedupe_validation_accepts_external_records_with_stable_keys() -> (
    None
):
    record = RepresentativeExternalRecord(
        source="fmp",
        source_type="news_api",
        external_id="article-123",
    )

    result = validate_source_and_dedupe_fields(
        _target(
            "news_article",
            "article-1",
            record,
        )
    )

    assert result.status == PersistenceValidationStatus.PASSED
    assert result.issue_count == 0


def test_source_and_dedupe_validation_reports_missing_source_and_dedupe_keys() -> None:
    record = RepresentativeExternalRecord()

    result = validate_source_and_dedupe_fields(
        _target(
            "news_article",
            "article-1",
            record,
        )
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert [issue.field_name for issue in result.issues] == [
        "source",
        "dedupe_key",
    ]
    assert result.issues[0].metadata["source_field_names"] == (
        "source",
        "source_type",
        "source_id",
    )
    assert result.issues[1].metadata["dedupe_key_field_names"] == (
        "external_id",
        "url",
        "source_reference",
        "source_id",
    )


def test_source_and_dedupe_validation_reports_blank_source_fields() -> None:
    record = RepresentativeExternalRecord(
        source=" ",
        external_id="article-123",
    )

    result = validate_source_and_dedupe_fields(
        _target(
            "news_article",
            "article-1",
            record,
        )
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert result.issues[0].field_name == "source"
    assert "blank" in result.issues[0].message


def test_source_and_dedupe_validation_supports_custom_external_source_specs() -> None:
    record = RepresentativeExternalRecord(
        source_reference="tweet-123",
    )

    result = validate_source_and_dedupe_fields(
        _target(
            "sentiment_source",
            "source-1",
            record,
        ),
        source_spec=PersistenceExternalSourceValidationSpec(
            source_field_names=("source_reference",),
            dedupe_key_field_names=("source_reference",),
        ),
    )

    assert result.status == PersistenceValidationStatus.PASSED
    assert result.issue_count == 0


def test_combined_lineage_source_and_dedupe_validation_merges_results() -> None:
    record = RepresentativeWorkflowRecord(
        lineage=PersistenceLineage(),
        source="news-api",
    )

    result = validate_lineage_source_and_dedupe_fields(
        _target(
            "news_article",
            "article-1",
            record,
        ),
        expected_lineage=PersistenceExpectedLineage(
            workflow_name="morning_report",
        ),
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert [issue.field_name for issue in result.issues] == [
        "lineage",
        "lineage.workflow_name",
        "dedupe_key",
    ]
    assert result.metadata == {"validator": "lineage_source_and_dedupe_fields"}


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
