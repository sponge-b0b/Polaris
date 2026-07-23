from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from numbers import Real

from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    PersistenceRecordIdentity,
    clean_optional_identifier,
    require_non_empty_identifier,
)
from core.storage.persistence.validation.validation_persistence_models import (
    PersistenceValidationIssue,
    PersistenceValidationResult,
    PersistenceValidationSeverity,
)

DEFAULT_TIMESTAMP_FIELDS = (
    "generated_at",
    "published_at",
    "published_timestamp",
    "observed_at",
)

DEFAULT_TIMESTAMP_ORDER_RULES = (
    ("requested_at", "published_at"),
    ("created_at", "updated_at"),
    ("generated_at", "published_at"),
)

DEFAULT_SCORE_VALIDATION_SPECS = (
    # Confidence and setup/risk scores are normalized ratios.
    ("confidence", 0.0, 1.0, "confidence"),
    ("setup_quality", 0.0, 1.0, "setup_quality"),
    ("risk_score", 0.0, 1.0, "risk"),
    # Sentiment/directional/attribution scores are signed signals.
    ("sentiment_score", -1.0, 1.0, "sentiment"),
    ("news_sentiment_score", -1.0, 1.0, "sentiment"),
    ("market_sentiment_score", -1.0, 1.0, "sentiment"),
    ("social_sentiment_score", -1.0, 1.0, "sentiment"),
    ("composite_sentiment", -1.0, 1.0, "sentiment"),
    ("directional_score", -1.0, 1.0, "directional"),
    ("contribution_score", -1.0, 1.0, "attribution"),
)


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceScoreValidationSpec:
    """
    Non-destructive score field range contract for persistence validation.
    """

    field_name: str
    minimum: float
    maximum: float
    score_type: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "field_name",
            require_non_empty_identifier(
                self.field_name,
                "field_name",
            ),
        )
        object.__setattr__(
            self,
            "score_type",
            require_non_empty_identifier(
                self.score_type,
                "score_type",
            ),
        )
        if self.minimum > self.maximum:
            raise ValueError("minimum cannot be greater than maximum.")


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceTimestampOrderRule:
    """
    Non-destructive timestamp ordering rule for persistence validation.
    """

    earlier_field_name: str
    later_field_name: str

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "earlier_field_name",
            require_non_empty_identifier(
                self.earlier_field_name,
                "earlier_field_name",
            ),
        )
        object.__setattr__(
            self,
            "later_field_name",
            require_non_empty_identifier(
                self.later_field_name,
                "later_field_name",
            ),
        )
        if self.earlier_field_name == self.later_field_name:
            raise ValueError("timestamp order rule fields must be different.")


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRecordValidationTarget:
    """
    Typed target wrapper for validating a persistence-boundary record.
    """

    identity: PersistenceRecordIdentity
    record: object


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceExpectedLineage:
    """
    Optional expected workflow/runtime lineage for a persisted record.
    """

    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "workflow_name",
            "execution_id",
            "runtime_id",
            "node_name",
        ):
            object.__setattr__(
                self,
                field_name,
                clean_optional_identifier(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )

    @property
    def has_expectations(
        self,
    ) -> bool:
        return any(
            (
                self.workflow_name,
                self.execution_id,
                self.runtime_id,
                self.node_name,
            )
        )

    def as_dict(
        self,
    ) -> dict[str, str]:
        return {
            field_name: value
            for field_name, value in (
                (
                    "workflow_name",
                    self.workflow_name,
                ),
                (
                    "execution_id",
                    self.execution_id,
                ),
                (
                    "runtime_id",
                    self.runtime_id,
                ),
                (
                    "node_name",
                    self.node_name,
                ),
            )
            if value is not None
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceExternalSourceValidationSpec:
    """
    Source and dedupe requirements for externally sourced persisted records.
    """

    source_field_names: tuple[str, ...] = (
        "source",
        "source_type",
        "source_id",
    )
    dedupe_key_field_names: tuple[str, ...] = (
        "external_id",
        "url",
        "source_reference",
        "source_id",
    )
    require_source_key: bool = True
    require_dedupe_key: bool = True

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "source_field_names",
            tuple(
                require_non_empty_identifier(
                    field_name,
                    "source_field_names",
                )
                for field_name in self.source_field_names
            ),
        )
        object.__setattr__(
            self,
            "dedupe_key_field_names",
            tuple(
                require_non_empty_identifier(
                    field_name,
                    "dedupe_key_field_names",
                )
                for field_name in self.dedupe_key_field_names
            ),
        )


DEFAULT_SCORE_SPECS = tuple(
    PersistenceScoreValidationSpec(
        field_name=field_name,
        minimum=minimum,
        maximum=maximum,
        score_type=score_type,
    )
    for field_name, minimum, maximum, score_type in DEFAULT_SCORE_VALIDATION_SPECS
)

DEFAULT_EXTERNAL_SOURCE_SPEC = PersistenceExternalSourceValidationSpec()


DEFAULT_ORDER_RULES = tuple(
    PersistenceTimestampOrderRule(
        earlier_field_name=earlier_field_name,
        later_field_name=later_field_name,
    )
    for earlier_field_name, later_field_name in DEFAULT_TIMESTAMP_ORDER_RULES
)


def validate_timestamp_fields(
    target: PersistenceRecordValidationTarget,
    *,
    timestamp_field_names: Iterable[str] = DEFAULT_TIMESTAMP_FIELDS,
    required_timestamp_field_names: Iterable[str] = (),
    timestamp_order_rules: Iterable[
        PersistenceTimestampOrderRule
    ] = DEFAULT_ORDER_RULES,
    now: datetime | None = None,
    future_tolerance: timedelta = timedelta(),
) -> PersistenceValidationResult:
    """
    Validate timestamp shape and ordering without mutating the target record.
    """

    validation_now = now if now is not None else datetime.now(UTC)
    issues: list[PersistenceValidationIssue] = []
    timestamp_fields = _normalized_field_names(
        timestamp_field_names,
        "timestamp_field_names",
    )
    required_timestamp_fields = _normalized_field_names(
        required_timestamp_field_names,
        "required_timestamp_field_names",
    )

    for field_name in timestamp_fields:
        if not hasattr(
            target.record,
            field_name,
        ):
            if field_name in required_timestamp_fields:
                issues.append(
                    _issue(
                        target=target,
                        severity=PersistenceValidationSeverity.ERROR,
                        field_name=field_name,
                        message=f"required timestamp field {field_name} is missing.",
                        remediation_hint=(
                            "populate the required timestamp before persisting "
                            "or exporting the curated record."
                        ),
                    )
                )
            continue

        value = getattr(
            target.record,
            field_name,
        )
        issues.extend(
            _validate_timestamp_value(
                target=target,
                field_name=field_name,
                value=value,
                required=field_name in required_timestamp_fields,
                now=validation_now,
                future_tolerance=future_tolerance,
            )
        )

    for rule in timestamp_order_rules:
        issues.extend(
            _validate_timestamp_order_rule(
                target=target,
                rule=rule,
            )
        )

    return PersistenceValidationResult(
        record_type=target.identity.record_type,
        record_id=target.identity.record_id,
        issues=tuple(
            issues,
        ),
        metadata={"validator": "timestamp_fields"},
    )


def validate_score_fields(
    target: PersistenceRecordValidationTarget,
    *,
    score_specs: Iterable[PersistenceScoreValidationSpec] = DEFAULT_SCORE_SPECS,
) -> PersistenceValidationResult:
    """
    Validate canonical score ranges without mutating the target record.
    """

    issues: list[PersistenceValidationIssue] = []
    for spec in score_specs:
        if not hasattr(
            target.record,
            spec.field_name,
        ):
            continue
        value = getattr(
            target.record,
            spec.field_name,
        )
        if value is None:
            continue
        if isinstance(
            value,
            bool,
        ) or not isinstance(
            value,
            Real,
        ):
            issues.append(
                _issue(
                    target=target,
                    severity=PersistenceValidationSeverity.ERROR,
                    field_name=spec.field_name,
                    message=(
                        f"{spec.score_type} score field {spec.field_name} "
                        "must be numeric."
                    ),
                    remediation_hint=(
                        "normalize the score to a numeric value before "
                        "persisting or exporting the curated record."
                    ),
                    metadata={"observed_type": type(value).__name__},
                )
            )
            continue
        numeric_value = float(
            value,
        )
        if numeric_value < spec.minimum or numeric_value > spec.maximum:
            issues.append(
                _issue(
                    target=target,
                    severity=PersistenceValidationSeverity.ERROR,
                    field_name=spec.field_name,
                    message=(
                        f"{spec.score_type} score field {spec.field_name} "
                        f"must be between {spec.minimum} and {spec.maximum}."
                    ),
                    remediation_hint=(
                        "recompute or normalize the score using the canonical "
                        "persistence score range."
                    ),
                    metadata={
                        "observed_value": numeric_value,
                        "minimum": spec.minimum,
                        "maximum": spec.maximum,
                        "score_type": spec.score_type,
                    },
                )
            )

    return PersistenceValidationResult(
        record_type=target.identity.record_type,
        record_id=target.identity.record_id,
        issues=tuple(
            issues,
        ),
        metadata={"validator": "score_fields"},
    )


def validate_timestamp_and_score_fields(
    target: PersistenceRecordValidationTarget,
    *,
    timestamp_field_names: Iterable[str] = DEFAULT_TIMESTAMP_FIELDS,
    required_timestamp_field_names: Iterable[str] = (),
    timestamp_order_rules: Iterable[
        PersistenceTimestampOrderRule
    ] = DEFAULT_ORDER_RULES,
    score_specs: Iterable[PersistenceScoreValidationSpec] = DEFAULT_SCORE_SPECS,
    now: datetime | None = None,
    future_tolerance: timedelta = timedelta(),
) -> PersistenceValidationResult:
    """
    Validate representative timestamps and score ranges as one record result.
    """

    timestamp_result = validate_timestamp_fields(
        target,
        timestamp_field_names=timestamp_field_names,
        required_timestamp_field_names=required_timestamp_field_names,
        timestamp_order_rules=timestamp_order_rules,
        now=now,
        future_tolerance=future_tolerance,
    )
    score_result = validate_score_fields(
        target,
        score_specs=score_specs,
    )
    return PersistenceValidationResult(
        record_type=target.identity.record_type,
        record_id=target.identity.record_id,
        issues=timestamp_result.issues + score_result.issues,
        metadata={"validator": "timestamp_and_score_fields"},
    )


def validate_lineage_fields(
    target: PersistenceRecordValidationTarget,
    *,
    expected_lineage: PersistenceExpectedLineage | None = None,
    require_lineage: bool = False,
    warn_when_missing: bool = True,
) -> PersistenceValidationResult:
    """
    Validate record workflow/runtime lineage without mutating the record.

    Missing lineage is a warning by default because some curated records may be
    created outside workflow execution. Callers can opt into hard failure when a
    workflow-produced record is expected.
    """

    issues: list[PersistenceValidationIssue] = []
    lineage = getattr(
        target.record,
        "lineage",
        None,
    )
    if lineage is None:
        if require_lineage:
            issues.append(
                _issue(
                    target=target,
                    severity=PersistenceValidationSeverity.ERROR,
                    field_name="lineage",
                    message="record is missing required workflow lineage.",
                    remediation_hint=(
                        "attach PersistenceLineage before treating this "
                        "record as workflow-produced curated data."
                    ),
                )
            )
        elif warn_when_missing:
            issues.append(
                _issue(
                    target=target,
                    severity=PersistenceValidationSeverity.WARNING,
                    field_name="lineage",
                    message=(
                        "record has no workflow lineage and may have been "
                        "created outside the workflow runtime."
                    ),
                    remediation_hint=(
                        "confirm this record is an intentional external or "
                        "manual curated record, otherwise attach lineage."
                    ),
                )
            )
        return PersistenceValidationResult(
            record_type=target.identity.record_type,
            record_id=target.identity.record_id,
            issues=tuple(
                issues,
            ),
            metadata={"validator": "lineage_fields"},
        )

    if not isinstance(
        lineage,
        PersistenceLineage,
    ):
        issues.append(
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.ERROR,
                field_name="lineage",
                message="record lineage must be a PersistenceLineage instance.",
                remediation_hint=(
                    "normalize record lineage to the canonical persistence "
                    "lineage contract."
                ),
                metadata={"observed_type": type(lineage).__name__},
            )
        )
        return PersistenceValidationResult(
            record_type=target.identity.record_type,
            record_id=target.identity.record_id,
            issues=tuple(
                issues,
            ),
            metadata={"validator": "lineage_fields"},
        )

    if not lineage.as_dict():
        if require_lineage:
            severity = PersistenceValidationSeverity.ERROR
            message = "record workflow lineage is empty."
        else:
            severity = PersistenceValidationSeverity.WARNING
            message = (
                "record workflow lineage is empty and may have been created "
                "outside the workflow runtime."
            )
        if require_lineage or warn_when_missing:
            issues.append(
                _issue(
                    target=target,
                    severity=severity,
                    field_name="lineage",
                    message=message,
                    remediation_hint=(
                        "attach workflow_name and execution_id when this "
                        "record is produced by runtime workflow execution."
                    ),
                )
            )

    if expected_lineage is not None and expected_lineage.has_expectations:
        issues.extend(
            _validate_expected_lineage(
                target=target,
                lineage=lineage,
                expected_lineage=expected_lineage,
            )
        )

    return PersistenceValidationResult(
        record_type=target.identity.record_type,
        record_id=target.identity.record_id,
        issues=tuple(
            issues,
        ),
        metadata={"validator": "lineage_fields"},
    )


def validate_source_and_dedupe_fields(
    target: PersistenceRecordValidationTarget,
    *,
    source_spec: PersistenceExternalSourceValidationSpec = DEFAULT_EXTERNAL_SOURCE_SPEC,
) -> PersistenceValidationResult:
    """
    Validate source identity and dedupe keys for external-source records.
    """

    issues: list[PersistenceValidationIssue] = []
    source_field_names = source_spec.source_field_names
    dedupe_key_field_names = source_spec.dedupe_key_field_names
    tracked_field_names = source_field_names + tuple(
        field_name
        for field_name in dedupe_key_field_names
        if field_name not in source_field_names
    )
    has_external_source_shape = any(
        hasattr(
            target.record,
            field_name,
        )
        for field_name in tracked_field_names
    )
    if not has_external_source_shape:
        return PersistenceValidationResult(
            record_type=target.identity.record_type,
            record_id=target.identity.record_id,
            issues=(),
            metadata={"validator": "source_and_dedupe_fields"},
        )

    for field_name in tracked_field_names:
        if not hasattr(
            target.record,
            field_name,
        ):
            continue
        value = getattr(
            target.record,
            field_name,
        )
        if (
            isinstance(
                value,
                str,
            )
            and value.strip() == ""
        ):
            issues.append(
                _issue(
                    target=target,
                    severity=PersistenceValidationSeverity.ERROR,
                    field_name=field_name,
                    message=f"external source field {field_name} is blank.",
                    remediation_hint=(
                        "normalize blank source fields to None or populate "
                        "them with stable source identity values."
                    ),
                )
            )

    if source_spec.require_source_key and not _has_any_non_empty_field(
        target.record,
        source_field_names,
    ):
        issues.append(
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.ERROR,
                field_name="source",
                message="external-source record is missing a source identity.",
                remediation_hint=(
                    "populate a stable source, source_type, or source_id "
                    "before treating this record as curated external data."
                ),
                metadata={"source_field_names": source_field_names},
            )
        )

    if source_spec.require_dedupe_key and not _has_any_non_empty_field(
        target.record,
        dedupe_key_field_names,
    ):
        issues.append(
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.ERROR,
                field_name="dedupe_key",
                message="external-source record is missing a dedupe key.",
                remediation_hint=(
                    "populate at least one stable dedupe key such as "
                    "external_id, url, source_reference, or source_id."
                ),
                metadata={"dedupe_key_field_names": dedupe_key_field_names},
            )
        )

    return PersistenceValidationResult(
        record_type=target.identity.record_type,
        record_id=target.identity.record_id,
        issues=tuple(
            issues,
        ),
        metadata={"validator": "source_and_dedupe_fields"},
    )


def validate_lineage_source_and_dedupe_fields(
    target: PersistenceRecordValidationTarget,
    *,
    expected_lineage: PersistenceExpectedLineage | None = None,
    require_lineage: bool = False,
    warn_when_missing_lineage: bool = True,
    source_spec: PersistenceExternalSourceValidationSpec = DEFAULT_EXTERNAL_SOURCE_SPEC,
) -> PersistenceValidationResult:
    """
    Validate lineage plus external-source/dedupe requirements as one result.
    """

    lineage_result = validate_lineage_fields(
        target,
        expected_lineage=expected_lineage,
        require_lineage=require_lineage,
        warn_when_missing=warn_when_missing_lineage,
    )
    source_result = validate_source_and_dedupe_fields(
        target,
        source_spec=source_spec,
    )
    return PersistenceValidationResult(
        record_type=target.identity.record_type,
        record_id=target.identity.record_id,
        issues=lineage_result.issues + source_result.issues,
        metadata={"validator": "lineage_source_and_dedupe_fields"},
    )


def _validate_timestamp_value(
    *,
    target: PersistenceRecordValidationTarget,
    field_name: str,
    value: object,
    required: bool,
    now: datetime,
    future_tolerance: timedelta,
) -> tuple[PersistenceValidationIssue, ...]:
    if value is None:
        if not required:
            return ()
        return (
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.ERROR,
                field_name=field_name,
                message=f"required timestamp field {field_name} is null.",
                remediation_hint=(
                    "populate the required timestamp before persisting or "
                    "exporting the curated record."
                ),
            ),
        )
    if not isinstance(
        value,
        datetime,
    ):
        return (
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.ERROR,
                field_name=field_name,
                message=f"timestamp field {field_name} must be a datetime.",
                remediation_hint=(
                    "normalize external timestamps into timezone-aware "
                    "datetime values before persistence validation."
                ),
                metadata={"observed_type": type(value).__name__},
            ),
        )

    issues: list[PersistenceValidationIssue] = []
    if value.tzinfo is None or value.utcoffset() is None:
        issues.append(
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.WARNING,
                field_name=field_name,
                message=f"timestamp field {field_name} is timezone-naive.",
                remediation_hint=(
                    "store curated persistence timestamps with explicit "
                    "timezone information, preferably UTC."
                ),
            )
        )
        comparable_value = value.replace(
            tzinfo=UTC,
        )
    else:
        comparable_value = value.astimezone(
            UTC,
        )

    comparable_now = _aware_utc(
        now,
    )
    if comparable_value > comparable_now + future_tolerance:
        issues.append(
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.WARNING,
                field_name=field_name,
                message=f"timestamp field {field_name} is in the future.",
                remediation_hint=(
                    "verify provider clock skew, publication timing, or "
                    "workflow-generated timestamp source."
                ),
                metadata={
                    "observed_value": comparable_value.isoformat(),
                    "validation_time": comparable_now.isoformat(),
                },
            )
        )
    return tuple(
        issues,
    )


def _validate_timestamp_order_rule(
    *,
    target: PersistenceRecordValidationTarget,
    rule: PersistenceTimestampOrderRule,
) -> tuple[PersistenceValidationIssue, ...]:
    if not hasattr(
        target.record,
        rule.earlier_field_name,
    ) or not hasattr(
        target.record,
        rule.later_field_name,
    ):
        return ()
    earlier_value = getattr(
        target.record,
        rule.earlier_field_name,
    )
    later_value = getattr(
        target.record,
        rule.later_field_name,
    )
    if not isinstance(
        earlier_value,
        datetime,
    ) or not isinstance(
        later_value,
        datetime,
    ):
        return ()
    if _aware_utc(later_value) < _aware_utc(earlier_value):
        return (
            _issue(
                target=target,
                severity=PersistenceValidationSeverity.ERROR,
                field_name=rule.later_field_name,
                message=(
                    f"timestamp field {rule.later_field_name} cannot be "
                    f"earlier than {rule.earlier_field_name}."
                ),
                remediation_hint=(
                    "correct timestamp ordering before treating the persisted "
                    "record as curated."
                ),
                metadata={
                    "earlier_field_name": rule.earlier_field_name,
                    "later_field_name": rule.later_field_name,
                    "earlier_value": _aware_utc(earlier_value).isoformat(),
                    "later_value": _aware_utc(later_value).isoformat(),
                },
            ),
        )
    return ()


def _aware_utc(
    value: datetime,
) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(
            tzinfo=UTC,
        )
    return value.astimezone(
        UTC,
    )


def _normalized_field_names(
    field_names: Iterable[str],
    collection_name: str,
) -> tuple[str, ...]:
    normalized: list[str] = []
    for field_name in field_names:
        cleaned = require_non_empty_identifier(
            field_name,
            collection_name,
        )
        if cleaned not in normalized:
            normalized.append(
                cleaned,
            )
    return tuple(
        normalized,
    )


def _validate_expected_lineage(
    *,
    target: PersistenceRecordValidationTarget,
    lineage: PersistenceLineage,
    expected_lineage: PersistenceExpectedLineage,
) -> tuple[PersistenceValidationIssue, ...]:
    issues: list[PersistenceValidationIssue] = []
    for field_name, expected_value in expected_lineage.as_dict().items():
        actual_value = getattr(
            lineage,
            field_name,
        )
        if actual_value != expected_value:
            issues.append(
                _issue(
                    target=target,
                    severity=PersistenceValidationSeverity.ERROR,
                    field_name=f"lineage.{field_name}",
                    message=(
                        f"record lineage field {field_name} does not match "
                        "the expected workflow lineage."
                    ),
                    remediation_hint=(
                        "verify this record belongs to the requested "
                        "workflow execution before using it as curated input."
                    ),
                    metadata={
                        "expected_value": expected_value,
                        "observed_value": actual_value,
                    },
                )
            )
    return tuple(
        issues,
    )


def _has_any_non_empty_field(
    record: object,
    field_names: Iterable[str],
) -> bool:
    return any(
        hasattr(
            record,
            field_name,
        )
        and _is_non_empty_value(
            getattr(
                record,
                field_name,
            )
        )
        for field_name in field_names
    )


def _is_non_empty_value(
    value: object,
) -> bool:
    if value is None:
        return False
    if isinstance(
        value,
        str,
    ):
        return value.strip() != ""
    if isinstance(
        value,
        tuple,
    ):
        return (
            len(
                value,
            )
            > 0
        )
    return True


def _issue(
    *,
    target: PersistenceRecordValidationTarget,
    severity: PersistenceValidationSeverity,
    field_name: str,
    message: str,
    remediation_hint: str,
    metadata: JsonObject | None = None,
) -> PersistenceValidationIssue:
    return PersistenceValidationIssue(
        severity=severity,
        record_type=target.identity.record_type,
        record_id=target.identity.record_id,
        field_name=field_name,
        message=message,
        remediation_hint=remediation_hint,
        metadata={} if metadata is None else metadata,
    )
