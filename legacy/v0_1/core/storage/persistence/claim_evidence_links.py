from __future__ import annotations

import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from core.telemetry.context import get_active_telemetry_context
from core.telemetry.contracts import TelemetryContext
from core.telemetry.events import TelemetryEventLevel, TelemetryExceptionDetails
from core.telemetry.events.telemetry_event import TelemetryEvent
from core.telemetry.observability import ObservabilityManager
from domain.authority import RiskTier

logger = logging.getLogger(__name__)

ENFORCED_CLAIM_EVIDENCE_LINK_RISK_TIERS = frozenset(
    (RiskTier.ENHANCED, RiskTier.VIGILANT),
)

_COMMON_CLAIM_EVIDENCE_LINK_VALUE_COLUMNS = (
    "link_id",
    "claim_target_id",
    "packet_id",
    "packet_claim_id",
    "risk_tier",
    "material",
    "supporting_evidence_ids",
    "reconstruction_reference_ids",
    "uncertainty_ids",
    "limitation_ids",
)
_COMMON_CLAIM_EVIDENCE_LINK_UPSERT_COLUMNS = (
    "claim_target_id",
    "packet_id",
    "packet_claim_id",
    "risk_tier",
    "material",
    "supporting_evidence_ids",
    "reconstruction_reference_ids",
    "uncertainty_ids",
    "limitation_ids",
)

_DATASTORE_EVENT_TYPE = "storage.postgres.operation"
_SOURCE = "core.storage.persistence"
_OBSERVABILITY_FAILURE_EXCEPTIONS = (RuntimeError, OSError, ValueError, TypeError)


class ClaimEvidenceObservabilityError(RuntimeError):
    """Raised when claim-evidence PostgreSQL observability emission fails."""


@dataclass(frozen=True, slots=True)
class PostgresClaimEvidenceLinkObservability:
    """Records PostgreSQL telemetry for claim-evidence link operations."""

    observability_manager: ObservabilityManager | None
    component_name: str
    table_name: str
    metric_prefix: str
    owner_id_attribute: str

    async def record_operation(
        self,
        *,
        operation: str,
        started_at: float,
        success: bool,
        owner_id: str | None = None,
        filters: Mapping[str, str | None] | None = None,
        error: BaseException | None = None,
        records_persisted: int | None = None,
        records_returned: int | None = None,
    ) -> None:
        """Emit event, counter, failure counter, and latency histogram."""

        if self.observability_manager is None:
            return

        try:
            await _record_claim_evidence_observability(
                observability_manager=self.observability_manager,
                component_name=self.component_name,
                table_name=self.table_name,
                metric_prefix=self.metric_prefix,
                owner_id_attribute=self.owner_id_attribute,
                operation=operation,
                started_at=started_at,
                success=success,
                owner_id=owner_id,
                filters=filters,
                error=error,
                records_persisted=records_persisted,
                records_returned=records_returned,
            )
        except ClaimEvidenceObservabilityError:
            logger.debug(
                "Claim-evidence PostgreSQL observability recording failed.",
                extra={
                    "component_name": self.component_name,
                    "database_system": "postgresql",
                    "operation": operation,
                    "table": self.table_name,
                },
                exc_info=True,
            )


async def _record_claim_evidence_observability(
    *,
    observability_manager: ObservabilityManager,
    component_name: str,
    table_name: str,
    metric_prefix: str,
    owner_id_attribute: str,
    operation: str,
    started_at: float,
    success: bool,
    owner_id: str | None,
    filters: Mapping[str, str | None] | None,
    error: BaseException | None,
    records_persisted: int | None,
    records_returned: int | None,
) -> None:
    """Emit claim-evidence observability behind a typed failure boundary."""

    try:
        duration_seconds = perf_counter() - started_at
        normalized_filters = _non_empty_filter_values(filters or {})
        context = _claim_evidence_operation_context(
            component_name=component_name,
            table_name=table_name,
            operation=operation,
            success=success,
            owner_id_attribute=owner_id_attribute,
            owner_id=owner_id,
            filters=normalized_filters,
        )
        attributes = _claim_evidence_operation_attributes(
            component_name=component_name,
            table_name=table_name,
            operation=operation,
            success=success,
            owner_id_attribute=owner_id_attribute,
            owner_id=owner_id,
            filters=normalized_filters,
        )
        metric_attributes = _claim_evidence_operation_metric_attributes(
            component_name=component_name,
            table_name=table_name,
            operation=operation,
            success=success,
        )
        payload: dict[str, Any] = {
            "component_name": component_name,
            "database_system": "postgresql",
            "duration_seconds": duration_seconds,
            "operation": operation,
            "outcome": "succeeded" if success else "failed",
            "success": success,
            "table": table_name,
        }
        if owner_id is not None:
            payload[owner_id_attribute] = owner_id
        payload.update(normalized_filters)
        if records_persisted is not None:
            payload["records_persisted"] = records_persisted
        if records_returned is not None:
            payload["records_returned"] = records_returned
        if error is not None:
            payload["error_message"] = str(error)
            payload["error_type"] = type(error).__name__

        observability_manager.increment(
            f"{metric_prefix}.operations.total",
            tags=("postgresql", operation),
            attributes=metric_attributes,
        )
        if not success:
            observability_manager.increment(
                f"{metric_prefix}.operations.failed",
                tags=("postgresql", operation),
                attributes=metric_attributes,
            )
        observability_manager.observe(
            f"{metric_prefix}.duration_seconds",
            value=duration_seconds,
            tags=("postgresql", operation),
            attributes=metric_attributes,
        )
        await observability_manager.emit(
            TelemetryEvent(
                event_type=_DATASTORE_EVENT_TYPE,
                source=_SOURCE,
                level=(
                    TelemetryEventLevel.INFO if success else TelemetryEventLevel.ERROR
                ),
                workflow_id=context.workflow_id,
                execution_id=context.execution_id,
                runtime_id=context.runtime_id,
                node_name=context.node_name,
                correlation_id=context.correlation_id,
                trace_id=context.trace_id,
                span_id=context.span_id,
                parent_span_id=context.parent_span_id,
                duration_seconds=duration_seconds,
                success=success,
                error_count=0 if success else 1,
                exception_details=(
                    TelemetryExceptionDetails.from_exception(error)
                    if error is not None
                    else None
                ),
                tags=context.tags,
                attributes=context.merged_attributes(attributes),
                payload=payload,
            )
        )
    except _OBSERVABILITY_FAILURE_EXCEPTIONS as exc:
        raise ClaimEvidenceObservabilityError(
            "Claim-evidence PostgreSQL observability recording failed."
        ) from exc


class ClaimEvidenceLinkRecordProtocol(Protocol):
    """Common typed surface for persisted claim-evidence link records."""

    @property
    def link_id(self) -> str: ...

    @property
    def claim_target_id(self) -> str: ...

    @property
    def packet_id(self) -> str: ...

    @property
    def packet_claim_id(self) -> str: ...

    @property
    def risk_tier(self) -> RiskTier: ...

    @property
    def material(self) -> bool: ...

    @property
    def supporting_evidence_ids(self) -> tuple[str, ...]: ...

    @property
    def reconstruction_reference_ids(self) -> tuple[str, ...]: ...

    @property
    def uncertainty_ids(self) -> tuple[str, ...]: ...

    @property
    def limitation_ids(self) -> tuple[str, ...]: ...


def claim_evidence_link_started_at() -> float:
    """Return a monotonic start timestamp for claim-evidence link telemetry."""

    return perf_counter()


def _claim_evidence_operation_context(
    *,
    component_name: str,
    table_name: str,
    operation: str,
    success: bool,
    owner_id_attribute: str,
    owner_id: str | None,
    filters: Mapping[str, str],
) -> TelemetryContext:
    active_context = get_active_telemetry_context() or TelemetryContext()
    return active_context.child_operation(
        attributes=_claim_evidence_operation_attributes(
            component_name=component_name,
            table_name=table_name,
            operation=operation,
            success=success,
            owner_id_attribute=owner_id_attribute,
            owner_id=owner_id,
            filters=filters,
        ),
    )


def _claim_evidence_operation_attributes(
    *,
    component_name: str,
    table_name: str,
    operation: str,
    success: bool,
    owner_id_attribute: str,
    owner_id: str | None,
    filters: Mapping[str, str],
) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "component_name": component_name,
        "database_system": "postgresql",
        "operation": operation,
        "operation_kind": "datastore_operation",
        "outcome": "succeeded" if success else "failed",
        "table": table_name,
    }
    if owner_id is not None:
        attributes[owner_id_attribute] = owner_id
    attributes.update(filters)
    return attributes


def _claim_evidence_operation_metric_attributes(
    *,
    component_name: str,
    table_name: str,
    operation: str,
    success: bool,
) -> dict[str, Any]:
    return {
        "component_name": component_name,
        "database_system": "postgresql",
        "operation": operation,
        "operation_kind": "datastore_operation",
        "outcome": "succeeded" if success else "failed",
        "table": table_name,
    }


def _non_empty_filter_values(filters: Mapping[str, str | None]) -> dict[str, str]:
    return {key: value for key, value in filters.items() if value is not None}


def claim_evidence_link_common_model_kwargs(model: Any) -> dict[str, Any]:
    """Return constructor kwargs shared by report and recommendation links."""

    return {
        "link_id": model.link_id,
        "claim_target_id": model.claim_target_id,
        "packet_id": model.packet_id,
        "packet_claim_id": model.packet_claim_id,
        "risk_tier": model.risk_tier,
        "material": model.material,
        "supporting_evidence_ids": string_tuple(model.supporting_evidence_ids),
        "reconstruction_reference_ids": string_tuple(
            model.reconstruction_reference_ids,
        ),
        "uncertainty_ids": string_tuple(model.uncertainty_ids),
        "limitation_ids": string_tuple(model.limitation_ids),
    }


def claim_evidence_link_common_values(
    record: ClaimEvidenceLinkRecordProtocol,
) -> dict[str, Any]:
    """Return database values shared by report and recommendation links."""

    values = {
        column: getattr(record, column)
        for column in _COMMON_CLAIM_EVIDENCE_LINK_VALUE_COLUMNS
    }
    values["risk_tier"] = record.risk_tier.value
    values["supporting_evidence_ids"] = list(record.supporting_evidence_ids)
    values["reconstruction_reference_ids"] = list(record.reconstruction_reference_ids)
    values["uncertainty_ids"] = list(record.uncertainty_ids)
    values["limitation_ids"] = list(record.limitation_ids)
    return values


async def execute_claim_evidence_link_upserts[LinkRecordT](
    session: AsyncSession,
    links: Iterable[LinkRecordT],
    statement_factory: Callable[[LinkRecordT], Any],
) -> None:
    """Execute claim-evidence link upserts for an owning repository."""

    for link in links:
        await session.execute(statement_factory(link))


def claim_evidence_link_upsert_set_values(
    excluded: Any,
    *,
    owner_columns: tuple[str, ...],
) -> dict[str, Any]:
    """Return shared ``ON CONFLICT`` values for claim-evidence link tables."""

    return {
        **{
            column: getattr(excluded, column)
            for column in (*owner_columns, *_COMMON_CLAIM_EVIDENCE_LINK_UPSERT_COLUMNS)
        },
        "updated_at": func.now(),
    }


def normalize_claim_evidence_link_fields(
    record: object,
    *,
    risk_tier: object,
    material: object,
    supporting_evidence_ids: Sequence[str],
    reconstruction_reference_ids: Sequence[str],
    uncertainty_ids: Sequence[str],
    limitation_ids: Sequence[str],
) -> None:
    """Normalize and validate fields common to claim-evidence link records."""

    normalized_risk_tier = coerce_claim_evidence_link_risk_tier(risk_tier)
    if not isinstance(material, bool):
        raise ValueError("material must be a boolean.")
    normalized_supporting_evidence_ids = clean_identifier_tuple(
        supporting_evidence_ids,
        "supporting_evidence_id",
    )
    normalized_reconstruction_reference_ids = clean_identifier_tuple(
        reconstruction_reference_ids,
        "reconstruction_reference_id",
    )
    object.__setattr__(record, "risk_tier", normalized_risk_tier)
    object.__setattr__(
        record,
        "supporting_evidence_ids",
        normalized_supporting_evidence_ids,
    )
    object.__setattr__(
        record,
        "reconstruction_reference_ids",
        normalized_reconstruction_reference_ids,
    )
    object.__setattr__(
        record,
        "uncertainty_ids",
        clean_identifier_tuple(uncertainty_ids, "uncertainty_id"),
    )
    object.__setattr__(
        record,
        "limitation_ids",
        clean_identifier_tuple(limitation_ids, "limitation_id"),
    )
    validate_material_claim_evidence_link(
        material=material,
        risk_tier=normalized_risk_tier,
        supporting_evidence_ids=normalized_supporting_evidence_ids,
        reconstruction_reference_ids=normalized_reconstruction_reference_ids,
    )


def normalize_claim_evidence_link_record(
    record: ClaimEvidenceLinkRecordProtocol,
) -> None:
    """Normalize and validate common fields on a claim-evidence link record."""

    normalize_claim_evidence_link_fields(
        record,
        risk_tier=record.risk_tier,
        material=record.material,
        supporting_evidence_ids=record.supporting_evidence_ids,
        reconstruction_reference_ids=record.reconstruction_reference_ids,
        uncertainty_ids=record.uncertainty_ids,
        limitation_ids=record.limitation_ids,
    )


def clean_identifier_tuple(values: Sequence[str], label: str) -> tuple[str, ...]:
    """Validate and normalize a tuple/list of non-empty string identifiers."""

    return tuple(_clean_identifier(value, label) for value in values)


def coerce_claim_evidence_link_risk_tier(value: object) -> RiskTier:
    """Normalize and validate risk tiers allowed for material claim links."""

    if isinstance(value, RiskTier):
        risk_tier = value
    elif isinstance(value, str):
        risk_tier = RiskTier(value.strip().lower())
    else:
        raise ValueError("risk_tier must be a RiskTier.")
    if risk_tier not in ENFORCED_CLAIM_EVIDENCE_LINK_RISK_TIERS:
        raise ValueError(
            "claim evidence links require enhanced or vigilant risk tiers."
        )
    return risk_tier


def string_tuple(values: object) -> tuple[str, ...]:
    """Extract string identifiers from JSON values read from persistence."""

    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, str))


def validate_material_claim_evidence_link(
    *,
    material: bool,
    risk_tier: RiskTier,
    supporting_evidence_ids: tuple[str, ...],
    reconstruction_reference_ids: tuple[str, ...],
) -> None:
    """Ensure enforced material claim links are reconstructable."""

    if not material or risk_tier not in ENFORCED_CLAIM_EVIDENCE_LINK_RISK_TIERS:
        return
    if not supporting_evidence_ids:
        raise ValueError(
            "material enhanced and vigilant claim evidence links require "
            "supporting evidence identifiers."
        )
    if not reconstruction_reference_ids:
        raise ValueError(
            "material enhanced and vigilant claim evidence links require "
            "reconstruction reference identifiers."
        )


def _clean_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


__all__ = [
    "ClaimEvidenceLinkRecordProtocol",
    "execute_claim_evidence_link_upserts",
    "PostgresClaimEvidenceLinkObservability",
    "claim_evidence_link_common_model_kwargs",
    "claim_evidence_link_started_at",
    "claim_evidence_link_common_values",
    "claim_evidence_link_upsert_set_values",
    "normalize_claim_evidence_link_fields",
    "normalize_claim_evidence_link_record",
    "clean_identifier_tuple",
    "coerce_claim_evidence_link_risk_tier",
    "string_tuple",
    "validate_material_claim_evidence_link",
]
