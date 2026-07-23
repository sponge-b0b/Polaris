from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum, StrEnum

from core.storage.persistence.lineage import (
    JsonObject,
    JsonValue,
    PersistenceRecordIdentity,
    clean_optional_identifier,
    require_non_empty_identifier,
)


class PersistenceValidationSeverity(StrEnum):
    """
    Non-destructive validation issue severity for persisted platform records.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class PersistenceValidationStatus(StrEnum):
    """
    Aggregated validation status for one record or a batch of records.
    """

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceValidationIssue:
    """
    Typed, non-destructive validation issue for a persisted platform record.
    """

    severity: PersistenceValidationSeverity | str
    record_type: str
    record_id: str
    message: str
    field_name: str | None = None
    remediation_hint: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "severity",
            _coerce_validation_severity(
                self.severity,
            ),
        )
        object.__setattr__(
            self,
            "record_type",
            require_non_empty_identifier(
                self.record_type,
                "record_type",
            ),
        )
        object.__setattr__(
            self,
            "record_id",
            require_non_empty_identifier(
                self.record_id,
                "record_id",
            ),
        )
        object.__setattr__(
            self,
            "message",
            require_non_empty_identifier(
                self.message,
                "message",
            ),
        )
        object.__setattr__(
            self,
            "field_name",
            clean_optional_identifier(
                self.field_name,
                "field_name",
            ),
        )
        object.__setattr__(
            self,
            "remediation_hint",
            clean_optional_identifier(
                self.remediation_hint,
                "remediation_hint",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def identity(
        self,
    ) -> PersistenceRecordIdentity:
        return PersistenceRecordIdentity(
            record_type=self.record_type,
            record_id=self.record_id,
        )

    @property
    def is_info(
        self,
    ) -> bool:
        return self.severity == PersistenceValidationSeverity.INFO

    @property
    def is_warning(
        self,
    ) -> bool:
        return self.severity == PersistenceValidationSeverity.WARNING

    @property
    def is_error(
        self,
    ) -> bool:
        return self.severity == PersistenceValidationSeverity.ERROR

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        severity = self.severity
        severity_value = severity.value if isinstance(severity, Enum) else severity
        result: dict[str, JsonValue] = {
            "severity": severity_value,
            "record_type": self.record_type,
            "record_id": self.record_id,
            "message": self.message,
            "metadata": self.metadata,
        }
        if self.field_name is not None:
            result["field_name"] = self.field_name
        if self.remediation_hint is not None:
            result["remediation_hint"] = self.remediation_hint
        return result


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceValidationResult:
    """
    Non-destructive validation result scoped to one persisted record identity.
    """

    record_type: str
    record_id: str
    issues: tuple[PersistenceValidationIssue, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "record_type",
            require_non_empty_identifier(
                self.record_type,
                "record_type",
            ),
        )
        object.__setattr__(
            self,
            "record_id",
            require_non_empty_identifier(
                self.record_id,
                "record_id",
            ),
        )
        object.__setattr__(
            self,
            "issues",
            _normalize_issues(
                issues=self.issues,
                record_type=self.record_type,
                record_id=self.record_id,
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def identity(
        self,
    ) -> PersistenceRecordIdentity:
        return PersistenceRecordIdentity(
            record_type=self.record_type,
            record_id=self.record_id,
        )

    @property
    def issue_count(
        self,
    ) -> int:
        return len(
            self.issues,
        )

    @property
    def has_errors(
        self,
    ) -> bool:
        return any(issue.is_error for issue in self.issues)

    @property
    def has_warnings(
        self,
    ) -> bool:
        return any(issue.is_warning for issue in self.issues)

    @property
    def is_valid(
        self,
    ) -> bool:
        return not self.has_errors

    @property
    def status(
        self,
    ) -> PersistenceValidationStatus:
        if self.has_errors:
            return PersistenceValidationStatus.FAILED
        if self.has_warnings:
            return PersistenceValidationStatus.WARNING
        return PersistenceValidationStatus.PASSED

    def issues_by_severity(
        self,
        severity: PersistenceValidationSeverity | str,
    ) -> tuple[PersistenceValidationIssue, ...]:
        normalized_severity = _coerce_validation_severity(
            severity,
        )
        return tuple(
            issue for issue in self.issues if issue.severity == normalized_severity
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "issue_count": self.issue_count,
            "issues": tuple(issue.as_dict() for issue in self.issues),
            "metadata": self.metadata,
        }

    def summary_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "issue_count": self.issue_count,
            "error_count": len(
                self.issues_by_severity(
                    PersistenceValidationSeverity.ERROR,
                ),
            ),
            "warning_count": len(
                self.issues_by_severity(
                    PersistenceValidationSeverity.WARNING,
                ),
            ),
            "info_count": len(
                self.issues_by_severity(
                    PersistenceValidationSeverity.INFO,
                ),
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceValidationBatchResult:
    """
    Aggregated, non-destructive validation result for multiple records.
    """

    results: tuple[PersistenceValidationResult, ...] = ()
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "results",
            tuple(
                self.results,
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def record_count(
        self,
    ) -> int:
        return len(
            self.results,
        )

    @property
    def issues(
        self,
    ) -> tuple[PersistenceValidationIssue, ...]:
        return tuple(issue for result in self.results for issue in result.issues)

    @property
    def issue_count(
        self,
    ) -> int:
        return len(
            self.issues,
        )

    @property
    def has_errors(
        self,
    ) -> bool:
        return any(result.has_errors for result in self.results)

    @property
    def has_warnings(
        self,
    ) -> bool:
        return any(result.has_warnings for result in self.results)

    @property
    def is_valid(
        self,
    ) -> bool:
        return not self.has_errors

    @property
    def status(
        self,
    ) -> PersistenceValidationStatus:
        if self.has_errors:
            return PersistenceValidationStatus.FAILED
        if self.has_warnings:
            return PersistenceValidationStatus.WARNING
        return PersistenceValidationStatus.PASSED

    def results_by_status(
        self,
        status: PersistenceValidationStatus | str,
    ) -> tuple[PersistenceValidationResult, ...]:
        normalized_status = _coerce_validation_status(
            status,
        )
        return tuple(
            result for result in self.results if result.status == normalized_status
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "record_count": self.record_count,
            "issue_count": self.issue_count,
            "results": tuple(result.as_dict() for result in self.results),
            "metadata": self.metadata,
        }

    def summary_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "record_count": self.record_count,
            "issue_count": self.issue_count,
            "failed_record_count": len(
                self.results_by_status(
                    PersistenceValidationStatus.FAILED,
                ),
            ),
            "warning_record_count": len(
                self.results_by_status(
                    PersistenceValidationStatus.WARNING,
                ),
            ),
            "passed_record_count": len(
                self.results_by_status(
                    PersistenceValidationStatus.PASSED,
                ),
            ),
        }


def _coerce_validation_severity(
    severity: PersistenceValidationSeverity | str,
) -> PersistenceValidationSeverity:
    if isinstance(
        severity,
        PersistenceValidationSeverity,
    ):
        return severity
    normalized_severity = require_non_empty_identifier(
        severity,
        "severity",
    ).lower()
    try:
        return PersistenceValidationSeverity(
            normalized_severity,
        )
    except ValueError as exc:
        valid_values = ", ".join(item.value for item in PersistenceValidationSeverity)
        raise ValueError(f"severity must be one of: {valid_values}.") from exc


def _coerce_validation_status(
    status: PersistenceValidationStatus | str,
) -> PersistenceValidationStatus:
    if isinstance(
        status,
        PersistenceValidationStatus,
    ):
        return status
    normalized_status = require_non_empty_identifier(
        status,
        "status",
    ).lower()
    try:
        return PersistenceValidationStatus(
            normalized_status,
        )
    except ValueError as exc:
        valid_values = ", ".join(item.value for item in PersistenceValidationStatus)
        raise ValueError(f"status must be one of: {valid_values}.") from exc


def _normalize_issues(
    *,
    issues: Iterable[PersistenceValidationIssue],
    record_type: str,
    record_id: str,
) -> tuple[PersistenceValidationIssue, ...]:
    normalized_issues = tuple(
        issues,
    )
    for issue in normalized_issues:
        if issue.record_type != record_type or issue.record_id != record_id:
            raise ValueError(
                "validation result issues must match the result record identity."
            )
    return normalized_issues
