from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from time import perf_counter
from typing import Final, Protocol, cast

from application.governance import (
    GovernedOutputReleaseDecision,
    GovernedOutputReleaseRequest,
    requires_governed_output_release_review,
)
from application.observability.risk_authority import risk_authority_attributes
from application.projections.workflow_output_fingerprints import (
    calculate_workflow_output_source_fingerprint,
)
from application.projections.workflow_outputs.projection_eligibility import (
    WorkflowOutputProjectionEligibilityContext,
    WorkflowOutputProjectionEligibilityDecision,
    WorkflowOutputProjectionEligibilityPolicy,
    WorkflowOutputQualityStatus,
)
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionRequest,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectorRegistration,
)
from application.projections.workflow_outputs.projection_telemetry import (
    WorkflowOutputProjectionTelemetry,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
    CompletedRunRecord,
)
from core.storage.persistence.projections import (
    WorkflowOutputProjectionJobRecord,
    WorkflowOutputProjectionJobRepository,
    WorkflowOutputProjectionJobStatus,
)
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing import TraceContext
from domain.authority import RiskAuthorityContract

logger = logging.getLogger(__name__)

_UNRESOLVED_PROJECTOR_NAME = "unresolved"
_UNSUPPORTED_OUTPUT_CONTRACT = "unsupported"
_GOVERNED_RELEASE_SKIP_REASON = "governance_review_required"
_MATERIALIZER_OWNED_RELEASE_EVIDENCE_PROJECTORS: Final[frozenset[str]] = frozenset(
    {"strategy_synthesis_projector"}
)


class GovernedOutputReleaseService(Protocol):
    """Approval-state service used before capital-relevant output release."""

    async def evaluate_governed_output_release(
        self,
        request: GovernedOutputReleaseRequest,
    ) -> GovernedOutputReleaseDecision:
        """Return whether this scoped output may be promoted or published."""
        ...


class CompletedRunProjectionNotFoundError(LookupError):
    """Raised when a requested completed run archive cannot be found."""


@dataclass(frozen=True, slots=True)
class _ProjectionSkip:
    """Terminal projection exit before projector execution."""

    outcome: WorkflowOutputProjectionOutcome
    skip_reason: str | None
    job: WorkflowOutputProjectionJobRecord | None = None


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
        governed_output_release_service: GovernedOutputReleaseService | None = None,
    ) -> None:
        self._completed_run_archive = completed_run_archive
        self._projection_job_repository = projection_job_repository
        self._registry = registry
        self._eligibility_policy = (
            eligibility_policy or WorkflowOutputProjectionEligibilityPolicy()
        )
        self._observability_manager = observability_manager
        self._governed_output_release_service = governed_output_release_service
        self._telemetry = WorkflowOutputProjectionTelemetry(observability_manager)

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        """Project every eligible output in one archived completed workflow run."""
        started_at = perf_counter()
        missing_trace_context = self._telemetry.create_trace_context(
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
            error = CompletedRunProjectionNotFoundError(
                "Completed run archive not found for "
                f"workflow={request.workflow_name!r}, "
                f"execution={request.execution_id!r}."
            )
            await self._telemetry.emit_run_failed(
                request=request,
                error=error,
                duration_seconds=perf_counter() - started_at,
                trace_context=missing_trace_context,
                reason="completed_run_not_found",
            )
            raise error

        run = bundle.run
        trace_context = self._telemetry.create_trace_context(
            workflow_id=run.workflow_id,
            execution_id=run.execution_id,
            runtime_id=run.runtime_id,
            run_id=run.run_id,
            attributes={"workflow_name": run.workflow_name},
        )
        await self._telemetry.emit_run_started(
            run=run,
            node_output_count=len(bundle.node_outputs),
            trace_context=trace_context,
        )
        outcomes: list[WorkflowOutputProjectionOutcome] = []
        for node_output in bundle.node_outputs:
            outcomes.append(
                await self._project_node_output(
                    run=run,
                    bundle=bundle,
                    node_output=node_output,
                    request=request,
                    run_trace_context=trace_context,
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
        await self._telemetry.emit_run_completed(
            summary=summary,
            duration_seconds=duration_seconds,
            trace_context=trace_context,
        )
        return summary

    async def _project_node_output(
        self,
        *,
        run: CompletedRunRecord,
        bundle: CompletedRunBundle,
        node_output: CompletedNodeOutputRecord,
        request: WorkflowOutputProjectionRequest,
        run_trace_context: TraceContext | None,
    ) -> WorkflowOutputProjectionOutcome:
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

        pre_execution_skip = await self._pre_execution_skip(
            decision=decision,
            registration=registration,
            node_output=node_output,
            request=request,
            source_fingerprint=source_fingerprint,
        )
        if pre_execution_skip is not None:
            return await self._emit_projection_skip(
                run=run,
                node_output=node_output,
                skip=pre_execution_skip,
                run_trace_context=run_trace_context,
                authority_contract=decision.authority_contract,
            )

        registration = cast(WorkflowOutputProjectorRegistration, registration)
        job_or_skip = await self._acquire_projection_job(
            run=run,
            node_output=node_output,
            registration=registration,
            request=request,
            source_fingerprint=source_fingerprint,
        )
        if isinstance(job_or_skip, _ProjectionSkip):
            return await self._emit_projection_skip(
                run=run,
                node_output=node_output,
                skip=job_or_skip,
                run_trace_context=run_trace_context,
                authority_contract=decision.authority_contract,
            )

        return await self._execute_claimed_projector(
            run=run,
            bundle=bundle,
            node_output=node_output,
            request=request,
            registration=registration,
            claimed_job=job_or_skip,
            source_fingerprint=source_fingerprint,
            run_trace_context=run_trace_context,
            authority_contract=decision.authority_contract,
        )

    async def _pre_execution_skip(
        self,
        *,
        decision: WorkflowOutputProjectionEligibilityDecision,
        registration: WorkflowOutputProjectorRegistration | None,
        node_output: CompletedNodeOutputRecord,
        request: WorkflowOutputProjectionRequest,
        source_fingerprint: str,
    ) -> _ProjectionSkip | None:
        if not decision.eligible or registration is None:
            return _ProjectionSkip(
                outcome=_skipped_outcome(
                    decision=decision,
                    node_output=node_output,
                    source_fingerprint=source_fingerprint,
                ),
                skip_reason=(
                    decision.skip_reason.value if decision.skip_reason else None
                ),
            )

        if request.dry_run:
            return _ProjectionSkip(
                outcome=_dry_run_outcome(
                    registration=registration,
                    node_output=node_output,
                    source_fingerprint=source_fingerprint,
                ),
                skip_reason="dry_run",
            )

        release_outcome = await self._governed_release_skip_outcome(
            decision=decision,
            registration=registration,
            node_output=node_output,
            source_fingerprint=source_fingerprint,
        )
        if release_outcome is None:
            return None
        return _ProjectionSkip(
            outcome=release_outcome,
            skip_reason=_GOVERNED_RELEASE_SKIP_REASON,
        )

    async def _acquire_projection_job(
        self,
        *,
        run: CompletedRunRecord,
        node_output: CompletedNodeOutputRecord,
        registration: WorkflowOutputProjectorRegistration,
        request: WorkflowOutputProjectionRequest,
        source_fingerprint: str,
    ) -> WorkflowOutputProjectionJobRecord | _ProjectionSkip:
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
            return _ProjectionSkip(
                outcome=_already_succeeded_outcome(
                    job=job,
                    node_output=node_output,
                ),
                skip_reason="already_succeeded",
                job=job,
            )

        claimed_job = await self._projection_job_repository.claim_job(
            job.projection_job_id,
            statuses=_claimable_statuses(force_reproject=request.force_reproject),
        )
        if claimed_job is not None:
            return claimed_job
        return _ProjectionSkip(
            outcome=_not_claimed_outcome(
                job=job,
                node_output=node_output,
            ),
            skip_reason="not_claimed",
            job=job,
        )

    async def _emit_projection_skip(
        self,
        *,
        run: CompletedRunRecord,
        node_output: CompletedNodeOutputRecord,
        skip: _ProjectionSkip,
        run_trace_context: TraceContext | None,
        authority_contract: RiskAuthorityContract | None,
    ) -> WorkflowOutputProjectionOutcome:
        await self._telemetry.emit_projector_skipped(
            run=run,
            node_output=node_output,
            outcome=skip.outcome,
            job=skip.job,
            skip_reason=skip.skip_reason,
            trace_context=_projector_trace_context(
                run_trace_context=run_trace_context,
                node_name=node_output.node_name,
                projector_name=skip.outcome.projector_name,
            ),
            authority_contract=authority_contract,
        )
        return skip.outcome

    async def _execute_claimed_projector(
        self,
        *,
        run: CompletedRunRecord,
        bundle: CompletedRunBundle,
        node_output: CompletedNodeOutputRecord,
        request: WorkflowOutputProjectionRequest,
        registration: WorkflowOutputProjectorRegistration,
        claimed_job: WorkflowOutputProjectionJobRecord,
        source_fingerprint: str,
        run_trace_context: TraceContext | None,
        authority_contract: RiskAuthorityContract | None,
    ) -> WorkflowOutputProjectionOutcome:
        projector_trace_context = _projector_trace_context(
            run_trace_context=run_trace_context,
            node_name=node_output.node_name,
            projector_name=registration.projector_name,
        )
        projector_started_at = perf_counter()
        await self._telemetry.emit_projector_started(
            run=run,
            node_output=node_output,
            registration=registration,
            job=claimed_job,
            trace_context=projector_trace_context,
            authority_contract=authority_contract,
        )

        try:
            outcome = await registration.projector.project(
                WorkflowOutputProjectorRequest(
                    run=run,
                    node_output=node_output,
                    source_fingerprint=source_fingerprint,
                    bundle=bundle,
                    lineage=build_workflow_output_projection_lineage(
                        run=run,
                        node_output=node_output,
                    ),
                    authority_contract=authority_contract,
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
            outcome = WorkflowOutputProjectionOutcome(
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
            await self._telemetry.emit_projector_failed(
                run=run,
                node_output=node_output,
                outcome=outcome,
                registration=registration,
                job=claimed_job,
                error=exc,
                duration_seconds=perf_counter() - projector_started_at,
                trace_context=projector_trace_context,
                authority_contract=authority_contract,
            )
            return outcome

        persisted_outcome = await self._persist_projector_outcome(
            outcome=outcome,
            job=claimed_job,
            registration=registration,
            node_output=node_output,
            source_fingerprint=source_fingerprint,
        )
        await self._emit_projector_outcome_telemetry(
            run=run,
            node_output=node_output,
            outcome=persisted_outcome,
            registration=registration,
            job=claimed_job,
            duration_seconds=perf_counter() - projector_started_at,
            trace_context=projector_trace_context,
            authority_contract=authority_contract,
        )
        return persisted_outcome

    async def _governed_release_skip_outcome(
        self,
        *,
        decision: WorkflowOutputProjectionEligibilityDecision,
        registration: WorkflowOutputProjectorRegistration,
        node_output: CompletedNodeOutputRecord,
        source_fingerprint: str,
    ) -> WorkflowOutputProjectionOutcome | None:
        service = self._governed_output_release_service
        authority = decision.authority_contract
        if authority is None:
            return None
        if not requires_governed_output_release_review(authority):
            return None
        if (
            registration.projector_name
            in _MATERIALIZER_OWNED_RELEASE_EVIDENCE_PROJECTORS
        ):
            return None

        boundary_name = f"workflow_output_projection.{registration.projector_name}"
        if service is None:
            message = (
                f"{boundary_name} is blocked: capital-relevant "
                f"{authority.risk_tier.value} durable promotion requires the "
                "canonical governed output release service."
            )
            logger.warning(
                "workflow_output_projection.governance_review_blocked",
                extra={
                    "node_name": node_output.node_name,
                    "projector_name": registration.projector_name,
                    "output_contract": registration.output_contract,
                    "reason": message,
                },
            )
            return _governed_release_blocked_outcome(
                registration=registration,
                node_output=node_output,
                source_fingerprint=source_fingerprint,
                message=message,
            )

        release_request = _governed_output_release_request_from_materializer_state(
            authority=authority,
            node_output=node_output,
            boundary_name=boundary_name,
        )
        if isinstance(release_request, str):
            logger.warning(
                "workflow_output_projection.governance_review_blocked",
                extra={
                    "node_name": node_output.node_name,
                    "projector_name": registration.projector_name,
                    "output_contract": registration.output_contract,
                    "reason": release_request,
                },
            )
            return _governed_release_blocked_outcome(
                registration=registration,
                node_output=node_output,
                source_fingerprint=source_fingerprint,
                message=release_request,
            )

        release_decision = await service.evaluate_governed_output_release(
            release_request,
        )
        if release_decision.allowed:
            return None

        logger.warning(
            "workflow_output_projection.governance_review_blocked",
            extra={
                "node_name": node_output.node_name,
                "projector_name": registration.projector_name,
                "output_contract": registration.output_contract,
                "review_task_id": release_decision.review_task_id,
                "approval_state": (
                    release_decision.approval_state.value
                    if release_decision.approval_state is not None
                    else None
                ),
                "reason": release_decision.reason,
            },
        )
        return _governed_release_blocked_outcome(
            registration=registration,
            node_output=node_output,
            source_fingerprint=source_fingerprint,
            message=release_decision.reason,
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

    async def _emit_projector_outcome_telemetry(
        self,
        *,
        run: CompletedRunRecord,
        node_output: CompletedNodeOutputRecord,
        outcome: WorkflowOutputProjectionOutcome,
        registration: WorkflowOutputProjectorRegistration,
        job: WorkflowOutputProjectionJobRecord,
        duration_seconds: float,
        trace_context: TraceContext | None,
        authority_contract: RiskAuthorityContract | None,
    ) -> None:
        status = cast(WorkflowOutputProjectionStatus, outcome.status)
        if status is WorkflowOutputProjectionStatus.SUCCEEDED:
            await self._telemetry.emit_projector_completed(
                run=run,
                node_output=node_output,
                outcome=outcome,
                job=job,
                duration_seconds=duration_seconds,
                trace_context=trace_context,
                authority_contract=authority_contract,
            )
            return
        if status is WorkflowOutputProjectionStatus.SKIPPED:
            await self._telemetry.emit_projector_skipped(
                run=run,
                node_output=node_output,
                outcome=outcome,
                job=job,
                skip_reason=outcome.message,
                duration_seconds=duration_seconds,
                trace_context=trace_context,
                authority_contract=authority_contract,
            )
            return
        await self._telemetry.emit_projector_failed(
            run=run,
            node_output=node_output,
            outcome=outcome,
            registration=registration,
            job=job,
            duration_seconds=duration_seconds,
            trace_context=trace_context,
            authority_contract=authority_contract,
        )


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


def _governed_output_release_request_from_materializer_state(
    *,
    authority: RiskAuthorityContract,
    node_output: CompletedNodeOutputRecord,
    boundary_name: str,
) -> str:
    return (
        f"{boundary_name} is blocked: {authority.risk_tier.value} governed "
        f"workflow output {node_output.node_output_id!r} requires "
        "materializer-owned reconstructed decision evidence; completed-output "
        "metadata is not accepted as packet, subject, review-scope, action, "
        "or residual-risk authority."
    )


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
            **risk_authority_attributes(
                decision.authority_contract,
                observable_reason=(
                    decision.skip_reason.value if decision.skip_reason else None
                ),
            ),
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
        message=(
            "Projection dry run skipped durable job creation and projector execution."
        ),
        completed_at=datetime.now(UTC),
    )


def _governed_release_blocked_outcome(
    *,
    registration: WorkflowOutputProjectorRegistration,
    node_output: CompletedNodeOutputRecord,
    source_fingerprint: str,
    message: str,
) -> WorkflowOutputProjectionOutcome:
    return WorkflowOutputProjectionOutcome(
        status=WorkflowOutputProjectionStatus.SKIPPED,
        projector_name=registration.projector_name,
        node_name=node_output.node_name,
        output_contract=registration.output_contract,
        output_schema_version=registration.output_schema_version,
        source_fingerprint=source_fingerprint,
        message=message,
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


def _projector_trace_context(
    *,
    run_trace_context: TraceContext | None,
    node_name: str,
    projector_name: str,
) -> TraceContext | None:
    if run_trace_context is None:
        return None
    return run_trace_context.child(
        node_name=node_name,
        attributes={"projector_name": projector_name},
    )
