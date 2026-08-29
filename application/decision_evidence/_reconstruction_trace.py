from __future__ import annotations

from application.decision_evidence._reconstruction_contracts import (
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSourceError,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
    TelemetryTraceSourceRepository,
    UnsupportedDecisionEvidenceReferenceError,
)
from application.decision_evidence._reconstruction_digest import (
    datetime_value,
    stable_content_digest,
)
from core.storage.persistence.telemetry import TelemetryTraceRecord
from domain.authority import SourceOfTruthCategory
from domain.decision_evidence import ReconstructionReference


async def validate_trace_context(
    *,
    repository: TelemetryTraceSourceRepository | None,
    reference: ReconstructionReference,
) -> None:
    _validate_trace_context_reference(reference)
    if repository is None:
        raise UnsupportedDecisionEvidenceReferenceError(
            "trace context reconstruction requires a telemetry trace repository "
            f"or a retained snapshot for '{reference.record_id}'."
        )

    trace = await repository.get_trace(reference.record_id)
    if trace is None:
        raise MissingDecisionEvidenceSourceError(
            f"trace context source record '{reference.record_id}' was not found."
        )
    if trace.trace_record_id != reference.record_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "trace context evidence does not match reconstruction identifier "
            f"'{reference.record_id}'."
        )
    if trace.trace_id != reference.snapshot_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "trace context evidence does not belong to trace "
            f"'{reference.snapshot_id}'."
        )

    content_digest = calculate_trace_context_evidence_digest(trace=trace)
    if content_digest != reference.content_digest:
        raise StaleDecisionEvidenceSourceError(
            "trace context evidence content digest is stale for "
            f"'{reference.record_id}'."
        )


def calculate_trace_context_evidence_digest(
    *,
    trace: TelemetryTraceRecord,
) -> str:
    """Calculate a stable digest for durable trace/correlation evidence fields."""

    return stable_content_digest(
        {
            "trace_record_id": trace.trace_record_id,
            "trace_id": trace.trace_id,
            "span_id": trace.span_id,
            "operation_name": trace.operation_name,
            "source": trace.source,
            "parent_span_id": trace.parent_span_id,
            "started_at": datetime_value(trace.started_at),
            "ended_at": datetime_value(trace.ended_at),
            "duration_seconds": trace.duration_seconds,
            "status": trace.status,
            "correlation_id": trace.correlation_id,
            "terminal_event_id": trace.terminal_event_id,
            "exception_type": trace.exception_type,
            "exception_message": trace.exception_message,
        }
    )


def _validate_trace_context_reference(reference: ReconstructionReference) -> None:
    label = "trace context reconstruction reference"
    if reference.source_of_truth is not SourceOfTruthCategory.TELEMETRY:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must identify telemetry as its source of truth."
        )
    if reference.snapshot_id is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must include a snapshot_id."
        )
    if reference.content_digest is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must include a content digest."
        )
