from __future__ import annotations

import hashlib
import json
import logging
import uuid
from time import perf_counter
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from enum import Enum
from typing import Mapping
from typing import Sequence
from typing import cast

from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionEligibilityContext,
)
from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionEligibilityDecision,
)
from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionEligibilityPolicy,
)
from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputQualityStatus,
)
from application.projections.workflow_outputs.projection_models import (
    CompletedRunProjectionSummary,
)
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionOutcome,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionRequest,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectorRegistration,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.projections import WorkflowOutputProjectionJobRecord
from core.storage.persistence.projections import WorkflowOutputProjectionJobRepository
from core.storage.persistence.projections import WorkflowOutputProjectionJobStatus
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing import TraceContext

logger = logging.getLogger(__name__)

_UNRESOLVED_PROJECTOR_NAME = "unresolved"
_UNSUPPORTED_OUTPUT_CONTRACT = "unsupported"


class CompletedRunProjectionNotFoundError(LookupError):
    """Raised when a requested completed run archive cannot be found."""


class WorkflowOutputProjectionService:
    """Coordinates completed-run node-output projection into curated records."""

    def __init__(
        self,
        *,
        completed_run_archive: CompletedRunArchive,
        projection_job_repository: WorkflowOutputProjectionJobRepository,
        registry: WorkflowOutputProjectionRegistry,
        eligibility_policy: WorkflowOutputProjectionEligibilityPolicy | None = None,
        observability_manager: ObservabilityManager | None = None,
    ) -> None:
        self._completed_run_archive = completed_run_archive
        self._projection_job_repository = projection_job_repository
        self._registry = registry
        self._eligibility_policy = (
            eligibility_policy or WorkflowOutputProjectionEligibilityPolicy()
        )
        self._observability_manager = observability_manager

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        """Project every eligible output in one archived completed workflow run."""
        started_at = perf_counter()
        missing_trace_context = self._create_trace_context(
            workflow_id=None,
            execution_id=request.execution_id,
            runtime_id=None,
            run_id=request.run_id,
            attributes={"workflow_name": request.workflow_name},
        )
        bundle = await self._completed_run_archive.load_archived_run(
            request.workflow_name,
            request.execution_id,
        )
        if bundle is None:
            logger.warning(
                "workflow_output_projection.completed_run_not_found",
                extra={
                    "workflow_name": request.workflow_name,
                    "execution_id": request.execution_id,
                },
            )
            await self._emit_projection_error(
                event_type="workflow_output_projection.completed_run_not_found",
                trace_context=missing_trace_context,
                payload={
                    "workflow_name": request.workflow_name,
                    "execution_id": request.execution_id,
                    "run_id": request.run_id,
                    "duration_seconds": perf_counter() - started_at,
                },
            )
            raise CompletedRunProjectionNotFoundError(
                "Completed run archive not found for "
                f"workflow={request.workflow_name!r}, "
                f"execution={request.execution_id!r}."
            )

        run = bundle.run
        trace_context = self._create_trace_context(
            workflow_id=run.workflow_id,
            execution_id=run.execution_id,
            runtime_id=run.runtime_id,
            run_id=run.run_id,
            attributes={"workflow_name": run.workflow_name},
        )
        await self._emit_projection_info(
            event_type="workflow_output_projection.completed_run_started",
            trace_context=trace_context,
            payload={
                "workflow_name": run.workflow_name,
                "execution_id": run.execution_id,
                "run_id": run.run_id,
                "node_output_count": len(bundle.node_outputs),
            },
        )
        outcomes: list[WorkflowOutputProjectionOutcome] = []
        for node_output in bundle.node_outputs:
            outcomes.append(
                await self._project_node_output(
                    run=run,
                    bundle=bundle,
                    node_output=node_output,
                    request=request,
                )
            )

        completed_at = datetime.now(UTC)
        summary = CompletedRunProjectionSummary(
            workflow_name=run.workflow_name,
            execution_id=run.execution_id,
            run_id=run.run_id,
            requested_at=request.requested_at,
            completed_at=completed_at,
            outcomes=tuple(outcomes),
        )
        duration_seconds = perf_counter() - started_at
        logger.info(
            "workflow_output_projection.completed_run_finished",
            extra={
                "workflow_name": summary.workflow_name,
                "execution_id": summary.execution_id,
                "run_id": summary.run_id,
                "total_jobs": summary.total_jobs,
                "succeeded_jobs": summary.succeeded_jobs,
                "failed_jobs": summary.failed_jobs,
                "skipped_jobs": summary.skipped_jobs,
                "records_written": summary.records_written,
                "duration_seconds": duration_seconds,
            },
        )
        self._record_summary_metrics(summary=summary, duration_seconds=duration_seconds)
        await self._emit_projection_info(
            event_type="workflow_output_projection.completed_run_finished",
            trace_context=trace_context,
            payload={
                "workflow_name": summary.workflow_name,
                "execution_id": summary.execution_id,
                "run_id": summary.run_id,
                "total_jobs": summary.total_jobs,
                "succeeded_jobs": summary.succeeded_jobs,
                "failed_jobs": summary.failed_jobs,
                "skipped_jobs": summary.skipped_jobs,
                "records_written": summary.records_written,
                "duration_seconds": duration_seconds,
            },
        )
        return summary

    async def _project_node_output(
        self,
        *,
        run: CompletedRunRecord,
        bundle: CompletedRunBundle,
        node_output: CompletedNodeOutputRecord,
        request: WorkflowOutputProjectionRequest,
    ) -> WorkflowOutputProjectionOutcome:
        del (
            bundle
        )  # Reserved for future projector context without changing service API.
        source_fingerprint = calculate_workflow_output_source_fingerprint(
            run=run,
            node_output=node_output,
        )
        decision = self._eligibility_policy.evaluate(
            WorkflowOutputProjectionEligibilityContext(
                run=run,
                node_output=node_output,
                execution_mode=run.execution_mode,
                quality_status=_quality_status_from_metadata(node_output.metadata),
                force_reproject=request.force_reproject,
            ),
            self._registry,
        )
        registration = _registration_from_decision(decision)
        if not decision.eligible or registration is None:
            return _skipped_outcome(
                decision=decision,
                node_output=node_output,
                source_fingerprint=source_fingerprint,
            )

        if request.dry_run:
            return _dry_run_outcome(
                registration=registration,
                node_output=node_output,
                source_fingerprint=source_fingerprint,
            )

        job = await self._projection_job_repository.create_job(
            _new_projection_job_record(
                run=run,
                node_output=node_output,
                registration=registration,
                source_fingerprint=source_fingerprint,
            )
        )
        if (
            cast(WorkflowOutputProjectionJobStatus, job.status)
            is WorkflowOutputProjectionJobStatus.SUCCEEDED
            and not request.force_reproject
        ):
            return _already_succeeded_outcome(
                job=job,
                node_output=node_output,
            )

        claim_statuses = _claimable_statuses(force_reproject=request.force_reproject)
        claimed_job = await self._projection_job_repository.claim_job(
            job.projection_job_id,
            statuses=claim_statuses,
        )
        if claimed_job is None:
            return _not_claimed_outcome(
                job=job,
                node_output=node_output,
            )

        try:
            outcome = await registration.projector.project(
                WorkflowOutputProjectorRequest(
                    run=run,
                    node_output=node_output,
                    source_fingerprint=source_fingerprint,
                    lineage=build_workflow_output_projection_lineage(
                        run=run,
                        node_output=node_output,
                    ),
                    requested_at=request.requested_at,
                    force_reproject=request.force_reproject,
                    dry_run=request.dry_run,
                )
            )
        except Exception as exc:  # noqa: BLE001 - projection failures must be recorded.
            logger.exception(
                "workflow_output_projection.projector_failed",
                extra={
                    "workflow_name": run.workflow_name,
                    "execution_id": run.execution_id,
                    "run_id": run.run_id,
                    "node_name": node_output.node_name,
                    "projector_name": registration.projector_name,
                    "projection_job_id": claimed_job.projection_job_id,
                    "output_contract": registration.output_contract,
                    "output_schema_version": registration.output_schema_version,
                },
            )
            error_message = f"{type(exc).__name__}: {exc}"
            await self._projection_job_repository.mark_failed(
                claimed_job.projection_job_id,
                error=error_message,
            )
            self._record_projector_failure_metric(
                projector_name=registration.projector_name,
                node_name=node_output.node_name,
            )
            await self._emit_projection_error(
                event_type="workflow_output_projection.projector_failed",
                trace_context=self._create_trace_context(
                    workflow_id=run.workflow_id,
                    execution_id=run.execution_id,
                    runtime_id=run.runtime_id,
                    run_id=run.run_id,
                    node_name=node_output.node_name,
                    attributes={"projector_name": registration.projector_name},
                ),
                payload={
                    "workflow_name": run.workflow_name,
                    "execution_id": run.execution_id,
                    "run_id": run.run_id,
                    "node_name": node_output.node_name,
                    "projector_name": registration.projector_name,
                    "projection_job_id": claimed_job.projection_job_id,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
            return WorkflowOutputProjectionOutcome(
                status=WorkflowOutputProjectionStatus.FAILED,
                projector_name=registration.projector_name,
                node_name=node_output.node_name,
                output_contract=registration.output_contract,
                output_schema_version=registration.output_schema_version,
                source_fingerprint=source_fingerprint,
                job_id=claimed_job.projection_job_id,
                error_type=type(exc).__name__,
                error_message=str(exc),
                message="Workflow output projector raised an exception.",
                started_at=claimed_job.started_at,
                completed_at=datetime.now(UTC),
            )

        return await self._persist_projector_outcome(
            outcome=outcome,
            job=claimed_job,
            registration=registration,
            node_output=node_output,
            source_fingerprint=source_fingerprint,
        )

    async def _persist_projector_outcome(
        self,
        *,
        outcome: WorkflowOutputProjectionOutcome,
        job: WorkflowOutputProjectionJobRecord,
        registration: WorkflowOutputProjectorRegistration,
        node_output: CompletedNodeOutputRecord,
        source_fingerprint: str,
    ) -> WorkflowOutputProjectionOutcome:
        normalized = _normalize_outcome(
            outcome=outcome,
            job=job,
            registration=registration,
            node_output=node_output,
            source_fingerprint=source_fingerprint,
        )
        status = cast(WorkflowOutputProjectionStatus, normalized.status)
        if status is WorkflowOutputProjectionStatus.SUCCEEDED:
            await self._projection_job_repository.mark_succeeded(job.projection_job_id)
            return normalized
        if status is WorkflowOutputProjectionStatus.SKIPPED:
            await self._projection_job_repository.mark_skipped(
                job.projection_job_id,
                reason=normalized.message,
            )
            return normalized

        error = normalized.error_message or normalized.message or "Projection failed."
        await self._projection_job_repository.mark_failed(
            job.projection_job_id,
            error=error,
        )
        return normalized

    def _record_summary_metrics(
        self,
        *,
        summary: CompletedRunProjectionSummary,
        duration_seconds: float,
    ) -> None:
        if self._observability_manager is None:
            return
        attributes = {
            "workflow_name": summary.workflow_name,
            "execution_id": summary.execution_id,
            "run_id": summary.run_id,
        }
        try:
            self._observability_manager.increment(
                "workflow_output_projection.runs.total",
                attributes=attributes,
            )
            self._observability_manager.increment(
                "workflow_output_projection.jobs.succeeded",
                value=float(summary.succeeded_jobs),
                attributes=attributes,
            )
            self._observability_manager.increment(
                "workflow_output_projection.jobs.failed",
                value=float(summary.failed_jobs),
                attributes=attributes,
            )
            self._observability_manager.increment(
                "workflow_output_projection.jobs.skipped",
                value=float(summary.skipped_jobs),
                attributes=attributes,
            )
            self._observability_manager.observe(
                "workflow_output_projection.run.duration_seconds",
                value=duration_seconds,
                attributes=attributes,
            )
        except Exception:  # noqa: BLE001 - telemetry must never break projection.
            logger.exception("workflow_output_projection.metrics_failed")

    def _record_projector_failure_metric(
        self,
        *,
        projector_name: str,
        node_name: str,
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            self._observability_manager.increment(
                "workflow_output_projection.projector.failures",
                attributes={
                    "projector_name": projector_name,
                    "node_name": node_name,
                },
            )
        except Exception:  # noqa: BLE001 - telemetry must never break projection.
            logger.exception("workflow_output_projection.metrics_failed")

    def _create_trace_context(
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

    async def _emit_projection_info(
        self,
        *,
        event_type: str,
        trace_context: TraceContext | None,
        payload: dict[str, object],
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            await self._observability_manager.info(
                event_type=event_type,
                source="application.workflow_output_projection",
                payload=payload,
                trace_context=trace_context,
            )
        except Exception:  # noqa: BLE001 - telemetry must never break projection.
            logger.exception("workflow_output_projection.telemetry_emit_failed")

    async def _emit_projection_error(
        self,
        *,
        event_type: str,
        trace_context: TraceContext | None,
        payload: dict[str, object],
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            await self._observability_manager.error(
                event_type=event_type,
                source="application.workflow_output_projection",
                payload=payload,
                trace_context=trace_context,
            )
        except Exception:  # noqa: BLE001 - telemetry must never break projection.
            logger.exception("workflow_output_projection.telemetry_emit_failed")


def calculate_workflow_output_source_fingerprint(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
) -> str:
    """Calculate a deterministic fingerprint for one archived node output."""
    payload = {
        "run_id": run.run_id,
        "workflow_name": run.workflow_name,
        "execution_id": run.execution_id,
        "node_output_id": node_output.node_output_id,
        "node_name": node_output.node_name,
        "output_contract": node_output.output_contract,
        "output_schema_version": node_output.output_schema_version,
        "status": node_output.status,
        "success": node_output.success,
        "outputs": node_output.outputs,
        "metadata": node_output.metadata,
        "errors_json": node_output.errors_json,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _registration_from_decision(
    decision: WorkflowOutputProjectionEligibilityDecision,
) -> WorkflowOutputProjectorRegistration | None:
    if decision.resolution is None:
        return None
    return decision.resolution.registration


def _quality_status_from_metadata(
    metadata: Mapping[str, object],
) -> WorkflowOutputQualityStatus:
    raw_value = metadata.get("quality_status")
    if isinstance(raw_value, str):
        try:
            return WorkflowOutputQualityStatus(raw_value)
        except ValueError:
            logger.warning(
                "workflow_output_projection.unknown_quality_status",
                extra={"quality_status": raw_value},
            )
    return WorkflowOutputQualityStatus.NORMAL


def _new_projection_job_record(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
    registration: WorkflowOutputProjectorRegistration,
    source_fingerprint: str,
) -> WorkflowOutputProjectionJobRecord:
    return WorkflowOutputProjectionJobRecord(
        projection_job_id=_projection_job_id(
            run_id=run.run_id,
            node_name=node_output.node_name,
            projector_name=registration.projector_name,
            source_fingerprint=source_fingerprint,
        ),
        run_id=run.run_id,
        workflow_name=run.workflow_name,
        execution_id=run.execution_id,
        node_name=node_output.node_name,
        projector_name=registration.projector_name,
        output_contract=registration.output_contract,
        output_schema_version=registration.output_schema_version,
        source_fingerprint=source_fingerprint,
        status=WorkflowOutputProjectionJobStatus.PENDING,
    )


def _projection_job_id(
    *,
    run_id: str,
    node_name: str,
    projector_name: str,
    source_fingerprint: str,
) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            ":".join(
                (
                    "polaris.workflow_output_projection_job",
                    run_id,
                    node_name,
                    projector_name,
                    source_fingerprint,
                )
            ),
        )
    )


def _claimable_statuses(
    *,
    force_reproject: bool,
) -> Sequence[WorkflowOutputProjectionJobStatus]:
    if force_reproject:
        return (
            WorkflowOutputProjectionJobStatus.PENDING,
            WorkflowOutputProjectionJobStatus.FAILED,
            WorkflowOutputProjectionJobStatus.SUCCEEDED,
            WorkflowOutputProjectionJobStatus.SKIPPED,
        )
    return (
        WorkflowOutputProjectionJobStatus.PENDING,
        WorkflowOutputProjectionJobStatus.FAILED,
    )


def _skipped_outcome(
    *,
    decision: WorkflowOutputProjectionEligibilityDecision,
    node_output: CompletedNodeOutputRecord,
    source_fingerprint: str,
) -> WorkflowOutputProjectionOutcome:
    logger.info(
        "workflow_output_projection.node_skipped",
        extra={
            "node_name": node_output.node_name,
            "output_contract": node_output.output_contract,
            "output_schema_version": node_output.output_schema_version,
            "skip_reason": decision.skip_reason.value if decision.skip_reason else None,
        },
    )
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.SKIPPED,
        projector_name=decision.projector_name or _UNRESOLVED_PROJECTOR_NAME,
        node_name=node_output.node_name,
        output_contract=node_output.output_contract or _UNSUPPORTED_OUTPUT_CONTRACT,
        output_schema_version=node_output.output_schema_version or 1,
        source_fingerprint=source_fingerprint,
        message=decision.message,
        completed_at=datetime.now(UTC),
    )


def _dry_run_outcome(
    *,
    registration: WorkflowOutputProjectorRegistration,
    node_output: CompletedNodeOutputRecord,
    source_fingerprint: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.SKIPPED,
        projector_name=registration.projector_name,
        node_name=node_output.node_name,
        output_contract=registration.output_contract,
        output_schema_version=registration.output_schema_version,
        source_fingerprint=source_fingerprint,
        message="Projection dry run skipped durable job creation and projector execution.",
        completed_at=datetime.now(UTC),
    )


def _already_succeeded_outcome(
    *,
    job: WorkflowOutputProjectionJobRecord,
    node_output: CompletedNodeOutputRecord,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.SKIPPED,
        projector_name=job.projector_name,
        node_name=node_output.node_name,
        output_contract=job.output_contract,
        output_schema_version=job.output_schema_version,
        source_fingerprint=job.source_fingerprint,
        job_id=job.projection_job_id,
        message="Projection job already succeeded for this source fingerprint.",
        started_at=job.started_at,
        completed_at=job.completed_at or datetime.now(UTC),
    )


def _not_claimed_outcome(
    *,
    job: WorkflowOutputProjectionJobRecord,
    node_output: CompletedNodeOutputRecord,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.SKIPPED,
        projector_name=job.projector_name,
        node_name=node_output.node_name,
        output_contract=job.output_contract,
        output_schema_version=job.output_schema_version,
        source_fingerprint=job.source_fingerprint,
        job_id=job.projection_job_id,
        message="Projection job was not claimable.",
        completed_at=datetime.now(UTC),
    )


def _normalize_outcome(
    *,
    outcome: WorkflowOutputProjectionOutcome,
    job: WorkflowOutputProjectionJobRecord,
    registration: WorkflowOutputProjectorRegistration,
    node_output: CompletedNodeOutputRecord,
    source_fingerprint: str,
) -> WorkflowOutputProjectionOutcome:
    if (
        outcome.projector_name == registration.projector_name
        and outcome.node_name == node_output.node_name
        and outcome.output_contract == registration.output_contract
        and outcome.output_schema_version == registration.output_schema_version
        and outcome.source_fingerprint == source_fingerprint
        and outcome.job_id == job.projection_job_id
    ):
        return outcome

    return replace(
        outcome,
        projector_name=registration.projector_name,
        node_name=node_output.node_name,
        output_contract=registration.output_contract,
        output_schema_version=registration.output_schema_version,
        source_fingerprint=source_fingerprint,
        job_id=job.projection_job_id,
        started_at=outcome.started_at or job.started_at,
        completed_at=outcome.completed_at or datetime.now(UTC),
    )
