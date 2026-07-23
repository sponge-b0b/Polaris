from __future__ import annotations

import logging
from collections.abc import Mapping

from application.observability.risk_authority import (
    risk_authority_attributes,
    risk_authority_payload,
)
from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionSkipReason,
)
from application.projections.workflow_outputs.projection_models import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunRecord,
)
from core.storage.persistence.projections import WorkflowOutputProjectionJobRecord
from core.telemetry.events.telemetry_event import TelemetryEvent, TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import TelemetryExceptionDetails
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing import TraceContext
from domain.authority import RiskAuthorityContract

logger = logging.getLogger(__name__)

_PROJECTION_SOURCE = "application.workflow_output_projection"


class WorkflowOutputProjectionTelemetry:
    """Telemetry emitter for durable workflow-output projection operations."""

    def __init__(
        self,
        observability_manager: ObservabilityManager | None,
    ) -> None:
        self._observability_manager = observability_manager

    def create_trace_context(
        self,
        *,
        workflow_id: str | None,
        execution_id: str,
        runtime_id: str | None,
        run_id: str | None,
        node_name: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> TraceContext | None:
        if self._observability_manager is None:
            return None
        return self._observability_manager.create_trace_context(
            workflow_id=workflow_id,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
            attributes={
                "run_id": run_id,
                **dict(attributes or {}),
            },
        )

    async def emit_run_started(
        self,
        *,
        run: CompletedRunRecord,
        node_output_count: int,
        trace_context: TraceContext | None,
    ) -> None:
        self._increment(
            "workflow_output_projection.runs.started",
            attributes=_run_attributes(run),
        )
        await self._emit(
            event_type="workflow_output_projection.completed_run_started",
            level=TelemetryEventLevel.INFO,
            success=None,
            trace_context=trace_context,
            attributes={
                **_run_attributes(run),
                "node_output_count": node_output_count,
            },
            payload={
                **_run_attributes(run),
                "node_output_count": node_output_count,
            },
        )

    async def emit_run_completed(
        self,
        *,
        summary: CompletedRunProjectionSummary,
        duration_seconds: float,
        trace_context: TraceContext | None,
    ) -> None:
        attributes = _summary_attributes(summary)
        self._increment("workflow_output_projection.runs.total", attributes=attributes)
        if summary.success:
            self._increment(
                "workflow_output_projection.runs.completed",
                attributes=attributes,
            )
        else:
            self._increment(
                "workflow_output_projection.runs.failed",
                attributes=attributes,
            )
        self._increment(
            "workflow_output_projection.jobs.succeeded",
            value=float(summary.succeeded_jobs),
            attributes=attributes,
        )
        self._increment(
            "workflow_output_projection.jobs.failed",
            value=float(summary.failed_jobs),
            attributes=attributes,
        )
        self._increment(
            "workflow_output_projection.jobs.skipped",
            value=float(summary.skipped_jobs),
            attributes=attributes,
        )
        self._observe(
            "workflow_output_projection.run.duration_seconds",
            value=duration_seconds,
            attributes=attributes,
        )
        await self._emit(
            event_type=(
                "workflow_output_projection.completed_run_finished"
                if summary.success
                else "workflow_output_projection.completed_run_failed"
            ),
            level=(
                TelemetryEventLevel.INFO
                if summary.success
                else TelemetryEventLevel.ERROR
            ),
            success=summary.success,
            error_count=0 if summary.success else summary.failed_jobs,
            duration_seconds=duration_seconds,
            trace_context=trace_context,
            attributes=attributes,
            payload={
                **attributes,
                "total_jobs": summary.total_jobs,
                "succeeded_jobs": summary.succeeded_jobs,
                "failed_jobs": summary.failed_jobs,
                "skipped_jobs": summary.skipped_jobs,
                "records_written": summary.records_written,
            },
        )

    async def emit_run_failed(
        self,
        *,
        request: WorkflowOutputProjectionRequest,
        error: BaseException | str,
        duration_seconds: float,
        trace_context: TraceContext | None,
        reason: str,
    ) -> None:
        attributes = {
            "workflow_name": request.workflow_name,
            "execution_id": request.execution_id,
            "run_id": request.run_id,
            "reason": reason,
        }
        self._increment("workflow_output_projection.runs.failed", attributes=attributes)
        if reason == "completed_run_not_found":
            self._increment(
                "workflow_output_projection.archives.missing",
                attributes=attributes,
            )
        await self._emit(
            event_type="workflow_output_projection.completed_run_not_found",
            level=TelemetryEventLevel.ERROR,
            success=False,
            duration_seconds=duration_seconds,
            error_count=1,
            error=error,
            trace_context=trace_context,
            attributes=attributes,
            payload={
                **attributes,
                "error_type": (
                    type(error).__name__
                    if isinstance(error, BaseException)
                    else "WorkflowOutputProjectionError"
                ),
                "error_message": str(error),
            },
        )

    async def emit_projector_started(
        self,
        *,
        run: CompletedRunRecord,
        node_output: CompletedNodeOutputRecord,
        registration: WorkflowOutputProjectorRegistration,
        job: WorkflowOutputProjectionJobRecord,
        trace_context: TraceContext | None,
        authority_contract: RiskAuthorityContract | None = None,
    ) -> None:
        attributes = _projector_attributes(
            run=run,
            node_output=node_output,
            projector_name=registration.projector_name,
            output_contract=registration.output_contract,
            output_schema_version=registration.output_schema_version,
            job=job,
            authority_contract=authority_contract,
        )
        self._increment(
            "workflow_output_projection.projector.started",
            attributes=attributes,
        )
        self._observe(
            "workflow_output_projection.jobs.retry_count",
            value=float(max(job.attempt_count - 1, 0)),
            attributes=attributes,
        )
        await self._emit(
            event_type="workflow_output_projection.projector_started",
            level=TelemetryEventLevel.INFO,
            success=None,
            trace_context=trace_context,
            attributes=attributes,
            payload={**attributes, **risk_authority_payload(authority_contract)},
        )

    async def emit_projector_completed(
        self,
        *,
        run: CompletedRunRecord,
        node_output: CompletedNodeOutputRecord,
        outcome: WorkflowOutputProjectionOutcome,
        job: WorkflowOutputProjectionJobRecord | None,
        duration_seconds: float | None,
        trace_context: TraceContext | None,
        authority_contract: RiskAuthorityContract | None = None,
    ) -> None:
        attributes = _outcome_attributes(
            run=run,
            node_output=node_output,
            outcome=outcome,
            job=job,
            authority_contract=authority_contract,
        )
        self._increment(
            "workflow_output_projection.projector.completed",
            attributes=attributes,
        )
        self._record_records_persisted(outcome=outcome, attributes=attributes)
        if duration_seconds is not None:
            self._observe(
                "workflow_output_projection.projector.duration_seconds",
                value=duration_seconds,
                attributes=attributes,
            )
        await self._emit(
            event_type="workflow_output_projection.projector_completed",
            level=TelemetryEventLevel.INFO,
            success=True,
            duration_seconds=duration_seconds,
            trace_context=trace_context,
            attributes=attributes,
            payload={
                **attributes,
                "records_written": outcome.records_written,
                **risk_authority_payload(authority_contract),
            },
        )

    async def emit_projector_skipped(
        self,
        *,
        run: CompletedRunRecord,
        node_output: CompletedNodeOutputRecord,
        outcome: WorkflowOutputProjectionOutcome,
        job: WorkflowOutputProjectionJobRecord | None = None,
        skip_reason: str | None = None,
        duration_seconds: float | None = None,
        trace_context: TraceContext | None = None,
        authority_contract: RiskAuthorityContract | None = None,
    ) -> None:
        attributes = {
            **_outcome_attributes(
                run=run,
                node_output=node_output,
                outcome=outcome,
                job=job,
                authority_contract=authority_contract,
                observable_reason=skip_reason,
            ),
            "skip_reason": skip_reason,
        }
        self._increment(
            "workflow_output_projection.projector.skipped",
            attributes=attributes,
        )
        if skip_reason in {
            WorkflowOutputProjectionSkipReason.UNSUPPORTED_CONTRACT.value,
            WorkflowOutputProjectionSkipReason.UNSUPPORTED_SCHEMA_VERSION.value,
        }:
            self._increment(
                "workflow_output_projection.unsupported_contracts.total",
                attributes=attributes,
            )
        await self._emit(
            event_type="workflow_output_projection.projector_skipped",
            level=TelemetryEventLevel.INFO,
            success=True,
            duration_seconds=duration_seconds,
            trace_context=trace_context,
            attributes=attributes,
            payload={
                **attributes,
                "message": outcome.message,
                **risk_authority_payload(authority_contract),
            },
        )

    async def emit_projector_failed(
        self,
        *,
        run: CompletedRunRecord,
        node_output: CompletedNodeOutputRecord,
        outcome: WorkflowOutputProjectionOutcome | None,
        registration: WorkflowOutputProjectorRegistration | None = None,
        job: WorkflowOutputProjectionJobRecord | None = None,
        error: BaseException | str | None = None,
        duration_seconds: float | None = None,
        trace_context: TraceContext | None = None,
        authority_contract: RiskAuthorityContract | None = None,
    ) -> None:
        attributes = _failed_projector_attributes(
            run=run,
            node_output=node_output,
            outcome=outcome,
            registration=registration,
            job=job,
            authority_contract=authority_contract,
        )
        self._increment(
            "workflow_output_projection.projector.failed",
            attributes=attributes,
        )
        self._increment(
            "workflow_output_projection.projector.failures",
            attributes=attributes,
        )
        if duration_seconds is not None:
            self._observe(
                "workflow_output_projection.projector.duration_seconds",
                value=duration_seconds,
                attributes=attributes,
            )
        emit_error = error
        if emit_error is None and outcome is not None:
            emit_error = outcome.error_message or outcome.message
        await self._emit(
            event_type="workflow_output_projection.projector_failed",
            level=TelemetryEventLevel.ERROR,
            success=False,
            duration_seconds=duration_seconds,
            error_count=1,
            error=emit_error or "Projection failed.",
            trace_context=trace_context,
            attributes=attributes,
            payload={
                **attributes,
                "error_type": _error_type(error=error, outcome=outcome),
                "error_message": _error_message(error=error, outcome=outcome),
                "message": outcome.message if outcome is not None else None,
                **risk_authority_payload(authority_contract),
            },
        )

    def record_stale_jobs_recovered(
        self,
        *,
        recovered_count: int,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        self._increment(
            "workflow_output_projection.jobs.stale_recovered",
            value=float(recovered_count),
            attributes=dict(attributes or {}),
        )

    def _record_records_persisted(
        self,
        *,
        outcome: WorkflowOutputProjectionOutcome,
        attributes: Mapping[str, object],
    ) -> None:
        if outcome.records_written <= 0:
            return
        self._increment(
            "workflow_output_projection.records.persisted",
            value=float(outcome.records_written),
            attributes={
                **dict(attributes),
                "record_type": outcome.output_contract,
            },
        )

    def _increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            self._observability_manager.increment(
                name,
                value=value,
                attributes=dict(attributes or {}),
            )
        except Exception:  # noqa: BLE001 - telemetry must not break projection.
            logger.exception("workflow_output_projection.metrics_failed")

    def _observe(
        self,
        name: str,
        *,
        value: float,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            self._observability_manager.observe(
                name,
                value=value,
                attributes=dict(attributes or {}),
            )
        except Exception:  # noqa: BLE001 - telemetry must not break projection.
            logger.exception("workflow_output_projection.metrics_failed")

    async def _emit(
        self,
        *,
        event_type: str,
        level: TelemetryEventLevel,
        success: bool | None,
        trace_context: TraceContext | None,
        attributes: Mapping[str, object] | None = None,
        payload: Mapping[str, object] | None = None,
        duration_seconds: float | None = None,
        error_count: int = 0,
        error: BaseException | str | None = None,
    ) -> None:
        if self._observability_manager is None:
            return
        exception_details = (
            TelemetryExceptionDetails.from_exception(error)
            if isinstance(error, BaseException)
            else None
        )
        trace_attributes = _trace_attributes(trace_context)
        try:
            await self._observability_manager.emit(
                TelemetryEvent(
                    event_type=event_type,
                    source=_PROJECTION_SOURCE,
                    level=level,
                    workflow_id=(
                        trace_context.workflow_id if trace_context is not None else None
                    ),
                    execution_id=(
                        trace_context.execution_id
                        if trace_context is not None
                        else None
                    ),
                    runtime_id=(
                        trace_context.runtime_id if trace_context is not None else None
                    ),
                    node_name=(
                        trace_context.node_name if trace_context is not None else None
                    ),
                    correlation_id=(
                        trace_context.correlation_id
                        if trace_context is not None
                        else None
                    ),
                    trace_id=trace_context.trace_id if trace_context else None,
                    span_id=trace_context.span_id if trace_context else None,
                    parent_span_id=(
                        trace_context.parent_span_id if trace_context else None
                    ),
                    duration_seconds=duration_seconds,
                    success=success,
                    error_count=error_count,
                    exception_details=exception_details,
                    attributes={
                        **dict(attributes or {}),
                        **trace_attributes,
                    },
                    payload=dict(payload or {}),
                )
            )
        except Exception:  # noqa: BLE001 - telemetry must not break projection.
            logger.exception("workflow_output_projection.telemetry_emit_failed")


def _run_attributes(run: CompletedRunRecord) -> dict[str, object]:
    return {
        "workflow_name": run.workflow_name,
        "execution_id": run.execution_id,
        "run_id": run.run_id,
    }


def _summary_attributes(summary: CompletedRunProjectionSummary) -> dict[str, object]:
    return {
        "workflow_name": summary.workflow_name,
        "execution_id": summary.execution_id,
        "run_id": summary.run_id,
    }


def _projector_attributes(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
    projector_name: str,
    output_contract: str,
    output_schema_version: int,
    job: WorkflowOutputProjectionJobRecord | None,
    authority_contract: RiskAuthorityContract | None = None,
    observable_reason: str | None = None,
) -> dict[str, object]:
    return {
        **_run_attributes(run),
        "node_name": node_output.node_name,
        "projector_name": projector_name,
        "projection_job_id": job.projection_job_id if job is not None else None,
        "output_contract": output_contract,
        "output_schema_version": output_schema_version,
        "attempt_count": job.attempt_count if job is not None else 0,
        **risk_authority_attributes(
            authority_contract,
            observable_reason=observable_reason,
        ),
    }


def _outcome_attributes(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
    outcome: WorkflowOutputProjectionOutcome,
    job: WorkflowOutputProjectionJobRecord | None,
    authority_contract: RiskAuthorityContract | None = None,
    observable_reason: str | None = None,
) -> dict[str, object]:
    return _projector_attributes(
        run=run,
        node_output=node_output,
        projector_name=outcome.projector_name,
        output_contract=outcome.output_contract,
        output_schema_version=outcome.output_schema_version,
        job=job,
        authority_contract=authority_contract,
        observable_reason=observable_reason,
    )


def _failed_projector_attributes(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
    outcome: WorkflowOutputProjectionOutcome | None,
    registration: WorkflowOutputProjectorRegistration | None,
    job: WorkflowOutputProjectionJobRecord | None,
    authority_contract: RiskAuthorityContract | None = None,
) -> dict[str, object]:
    projector_name = (
        outcome.projector_name
        if outcome is not None
        else registration.projector_name
        if registration is not None
        else "unknown"
    )
    output_contract = (
        outcome.output_contract
        if outcome is not None
        else registration.output_contract
        if registration is not None
        else "unknown"
    )
    output_schema_version = (
        outcome.output_schema_version
        if outcome is not None
        else registration.output_schema_version
        if registration is not None
        else 1
    )
    return _projector_attributes(
        run=run,
        node_output=node_output,
        projector_name=projector_name,
        output_contract=output_contract,
        output_schema_version=output_schema_version,
        job=job,
        authority_contract=authority_contract,
    )


def _trace_attributes(trace_context: TraceContext | None) -> dict[str, object]:
    if trace_context is None:
        return {}
    return {
        **trace_context.attributes,
        **trace_context.telemetry_attributes(),
    }


def _error_type(
    *,
    error: BaseException | str | None,
    outcome: WorkflowOutputProjectionOutcome | None,
) -> str:
    if isinstance(error, BaseException):
        return type(error).__name__
    if outcome is not None and outcome.error_type:
        return outcome.error_type
    if isinstance(error, str) and error:
        return "WorkflowOutputProjectionError"
    return "WorkflowOutputProjectionError"


def _error_message(
    *,
    error: BaseException | str | None,
    outcome: WorkflowOutputProjectionOutcome | None,
) -> str:
    if error is not None:
        return str(error)
    if outcome is not None and outcome.error_message:
        return outcome.error_message
    if outcome is not None and outcome.message:
        return outcome.message
    return "Projection failed."
