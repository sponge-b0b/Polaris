from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.validation import (
    DEFAULT_EXTERNAL_SOURCE_SPEC,
    DEFAULT_ORDER_RULES,
    DEFAULT_SCORE_SPECS,
    DEFAULT_TIMESTAMP_FIELDS,
    PersistenceExpectedLineage,
    PersistenceExternalSourceValidationSpec,
    PersistenceRecordValidationTarget,
    PersistenceScoreValidationSpec,
    PersistenceTimestampOrderRule,
    PersistenceValidationBatchResult,
    PersistenceValidationResult,
    validate_lineage_source_and_dedupe_fields,
    validate_timestamp_and_score_fields,
)


class ValidationPersistenceService:
    """
    Application service for non-destructive persisted-record validation.

    This service coordinates core persistence validation checks and returns
    typed validation results. It does not mutate records, write audit events, or
    perform repository access; persistence validation remains an application
    boundary over typed PostgreSQL system-of-record contracts.
    """

    async def validate_record(
        self,
        target: PersistenceRecordValidationTarget,
        *,
        expected_lineage: PersistenceExpectedLineage | None = None,
        require_lineage: bool = False,
        warn_when_missing_lineage: bool = True,
        source_spec: PersistenceExternalSourceValidationSpec = (
            DEFAULT_EXTERNAL_SOURCE_SPEC
        ),
        timestamp_field_names: Sequence[str] = DEFAULT_TIMESTAMP_FIELDS,
        required_timestamp_field_names: Sequence[str] = (),
        timestamp_order_rules: Sequence[
            PersistenceTimestampOrderRule
        ] = DEFAULT_ORDER_RULES,
        score_specs: Sequence[PersistenceScoreValidationSpec] = DEFAULT_SCORE_SPECS,
        now: datetime | None = None,
        future_tolerance: timedelta = timedelta(),
    ) -> PersistenceValidationResult:
        timestamp_score_result = validate_timestamp_and_score_fields(
            target,
            timestamp_field_names=timestamp_field_names,
            required_timestamp_field_names=required_timestamp_field_names,
            timestamp_order_rules=timestamp_order_rules,
            score_specs=score_specs,
            now=now,
            future_tolerance=future_tolerance,
        )
        lineage_source_result = validate_lineage_source_and_dedupe_fields(
            target,
            expected_lineage=expected_lineage,
            require_lineage=require_lineage,
            warn_when_missing_lineage=warn_when_missing_lineage,
            source_spec=source_spec,
        )
        return PersistenceValidationResult(
            record_type=target.identity.record_type,
            record_id=target.identity.record_id,
            issues=timestamp_score_result.issues + lineage_source_result.issues,
            metadata={"validator": "persistence_validation_service"},
        )

    async def validate_record_object(
        self,
        *,
        record_type: str,
        record_id: str,
        record: object,
        expected_lineage: PersistenceExpectedLineage | None = None,
        require_lineage: bool = False,
        warn_when_missing_lineage: bool = True,
        source_spec: PersistenceExternalSourceValidationSpec = (
            DEFAULT_EXTERNAL_SOURCE_SPEC
        ),
        timestamp_field_names: Sequence[str] = DEFAULT_TIMESTAMP_FIELDS,
        required_timestamp_field_names: Sequence[str] = (),
        timestamp_order_rules: Sequence[
            PersistenceTimestampOrderRule
        ] = DEFAULT_ORDER_RULES,
        score_specs: Sequence[PersistenceScoreValidationSpec] = DEFAULT_SCORE_SPECS,
        now: datetime | None = None,
        future_tolerance: timedelta = timedelta(),
    ) -> PersistenceValidationResult:
        return await self.validate_record(
            PersistenceRecordValidationTarget(
                identity=PersistenceRecordIdentity(
                    record_type=record_type,
                    record_id=record_id,
                ),
                record=record,
            ),
            expected_lineage=expected_lineage,
            require_lineage=require_lineage,
            warn_when_missing_lineage=warn_when_missing_lineage,
            source_spec=source_spec,
            timestamp_field_names=timestamp_field_names,
            required_timestamp_field_names=required_timestamp_field_names,
            timestamp_order_rules=timestamp_order_rules,
            score_specs=score_specs,
            now=now,
            future_tolerance=future_tolerance,
        )

    async def validate_records(
        self,
        targets: Sequence[PersistenceRecordValidationTarget],
        *,
        expected_lineage: PersistenceExpectedLineage | None = None,
        require_lineage: bool = False,
        warn_when_missing_lineage: bool = True,
        source_spec: PersistenceExternalSourceValidationSpec = (
            DEFAULT_EXTERNAL_SOURCE_SPEC
        ),
        timestamp_field_names: Sequence[str] = DEFAULT_TIMESTAMP_FIELDS,
        required_timestamp_field_names: Sequence[str] = (),
        timestamp_order_rules: Sequence[
            PersistenceTimestampOrderRule
        ] = DEFAULT_ORDER_RULES,
        score_specs: Sequence[PersistenceScoreValidationSpec] = DEFAULT_SCORE_SPECS,
        now: datetime | None = None,
        future_tolerance: timedelta = timedelta(),
    ) -> PersistenceValidationBatchResult:
        results = []
        for target in targets:
            results.append(
                await self.validate_record(
                    target,
                    expected_lineage=expected_lineage,
                    require_lineage=require_lineage,
                    warn_when_missing_lineage=warn_when_missing_lineage,
                    source_spec=source_spec,
                    timestamp_field_names=timestamp_field_names,
                    required_timestamp_field_names=required_timestamp_field_names,
                    timestamp_order_rules=timestamp_order_rules,
                    score_specs=score_specs,
                    now=now,
                    future_tolerance=future_tolerance,
                )
            )
        return PersistenceValidationBatchResult(
            results=tuple(
                results,
            ),
            metadata={"validator": "persistence_validation_service"},
        )
