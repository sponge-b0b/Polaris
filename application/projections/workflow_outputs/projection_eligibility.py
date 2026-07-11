from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final
from typing import cast

from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionResolution,
)
from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionResolutionStatus,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import (
    coerce_completed_run_execution_mode,
)
from core.storage.persistence.completed_run_archive import CompletedRunRecord


WorkflowProjectionExecutionMode = CompletedRunExecutionMode


class WorkflowOutputQualityStatus(str, Enum):
    """First-class quality classification for a workflow node output."""

    NORMAL = "normal"
    DEGRADED = "degraded"
    FALLBACK = "fallback"


class WorkflowOutputProjectionEligibilityStatus(str, Enum):
    """Eligibility decision for one archived workflow node output."""

    ELIGIBLE = "eligible"
    SKIPPED = "skipped"


class WorkflowOutputProjectionSkipReason(str, Enum):
    """Stable skip reason values for workflow-output projection decisions."""

    NON_PRODUCTION_EXECUTION = "non_production_execution"
    NODE_NOT_SUCCESSFUL = "node_not_successful"
    NODE_SKIPPED = "node_skipped"
    UNSUPPORTED_CONTRACT = "unsupported_contract"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    UNSUPPORTED_NODE_NAME = "unsupported_node_name"
    QUALITY_STATUS_NOT_PERSISTABLE = "quality_status_not_persistable"
    REPORT_PERSISTENCE_BOUNDARY = "report_persistence_boundary"
    BACKTEST_PERSISTENCE_BOUNDARY = "backtest_persistence_boundary"


_REPORT_OUTPUT_CONTRACT_PREFIXES: Final[tuple[str, ...]] = ("polaris.report.",)
_BACKTEST_OUTPUT_CONTRACT_PREFIXES: Final[tuple[str, ...]] = ("polaris.backtest.",)


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionEligibilityContext:
    """First-class inputs used to evaluate projection eligibility."""

    run: CompletedRunRecord
    node_output: CompletedNodeOutputRecord
    execution_mode: CompletedRunExecutionMode | str = CompletedRunExecutionMode.NORMAL
    quality_status: WorkflowOutputQualityStatus | str = (
        WorkflowOutputQualityStatus.NORMAL
    )
    force_reproject: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "execution_mode",
            _coerce_execution_mode(self.execution_mode),
        )
        object.__setattr__(
            self,
            "quality_status",
            _coerce_quality_status(self.quality_status),
        )


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionEligibilityDecision:
    """Deterministic projection eligibility result for one node output."""

    status: WorkflowOutputProjectionEligibilityStatus
    node_name: str
    output_contract: str | None
    output_schema_version: int | None
    resolution: WorkflowOutputProjectionResolution | None = None
    skip_reason: WorkflowOutputProjectionSkipReason | None = None
    message: str | None = None

    @property
    def eligible(self) -> bool:
        return self.status is WorkflowOutputProjectionEligibilityStatus.ELIGIBLE

    @property
    def skipped(self) -> bool:
        return self.status is WorkflowOutputProjectionEligibilityStatus.SKIPPED

    @property
    def projector_name(self) -> str | None:
        if self.resolution is None:
            return None
        return self.resolution.projector_name


class WorkflowOutputProjectionEligibilityPolicy:
    """Deterministic policy for deciding if archived node output is projectable."""

    def evaluate(
        self,
        context: WorkflowOutputProjectionEligibilityContext,
        registry: WorkflowOutputProjectionRegistry,
    ) -> WorkflowOutputProjectionEligibilityDecision:
        node_output = context.node_output
        execution_mode = cast(CompletedRunExecutionMode, context.execution_mode)
        quality_status = cast(WorkflowOutputQualityStatus, context.quality_status)

        if execution_mode in {
            WorkflowProjectionExecutionMode.BACKTEST,
            WorkflowProjectionExecutionMode.SIMULATED,
        }:
            return _skipped(
                node_output,
                WorkflowOutputProjectionSkipReason.NON_PRODUCTION_EXECUTION,
                f"Projection is skipped for {execution_mode.value} runs.",
            )

        boundary_decision = _persistence_boundary_decision(node_output)
        if boundary_decision is not None:
            return boundary_decision

        if node_output.status.strip().lower() == "skipped":
            return _skipped(
                node_output,
                WorkflowOutputProjectionSkipReason.NODE_SKIPPED,
                "Projection is skipped for skipped node outputs.",
            )

        if node_output.success is not True:
            return _skipped(
                node_output,
                WorkflowOutputProjectionSkipReason.NODE_NOT_SUCCESSFUL,
                "Projection requires an archived node output with success=True.",
            )

        resolution = registry.resolve(
            output_contract=node_output.output_contract,
            output_schema_version=node_output.output_schema_version,
            node_name=node_output.node_name,
        )
        if not resolution.supported:
            return _skipped_for_resolution(node_output, resolution)

        if (
            quality_status is not WorkflowOutputQualityStatus.NORMAL
            and resolution.registration is not None
            and not resolution.registration.persists_quality_status
        ):
            return _skipped(
                node_output,
                WorkflowOutputProjectionSkipReason.QUALITY_STATUS_NOT_PERSISTABLE,
                (
                    "Projection is skipped because the output quality status is "
                    f"{quality_status.value!r} and the target projector does "
                    "not persist first-class quality/status fields."
                ),
                resolution=resolution,
            )

        return WorkflowOutputProjectionEligibilityDecision(
            status=WorkflowOutputProjectionEligibilityStatus.ELIGIBLE,
            node_name=node_output.node_name,
            output_contract=node_output.output_contract,
            output_schema_version=node_output.output_schema_version,
            resolution=resolution,
            message="Workflow node output is eligible for projection.",
        )


def _persistence_boundary_decision(
    node_output: CompletedNodeOutputRecord,
) -> WorkflowOutputProjectionEligibilityDecision | None:
    output_contract = node_output.output_contract
    if output_contract is None:
        return None
    cleaned_contract = output_contract.strip()
    if cleaned_contract.startswith(_REPORT_OUTPUT_CONTRACT_PREFIXES):
        return _skipped(
            node_output,
            WorkflowOutputProjectionSkipReason.REPORT_PERSISTENCE_BOUNDARY,
            (
                "Projection is skipped for report documents because "
                "MorningReportPersistenceService owns report persistence."
            ),
        )
    if cleaned_contract.startswith(_BACKTEST_OUTPUT_CONTRACT_PREFIXES):
        return _skipped(
            node_output,
            WorkflowOutputProjectionSkipReason.BACKTEST_PERSISTENCE_BOUNDARY,
            (
                "Projection is skipped for backtest result bundles because "
                "BacktestPersistenceService owns backtest persistence."
            ),
        )
    return None


def _skipped_for_resolution(
    node_output: CompletedNodeOutputRecord,
    resolution: WorkflowOutputProjectionResolution,
) -> WorkflowOutputProjectionEligibilityDecision:
    reason = _skip_reason_for_resolution(resolution.status)
    return _skipped(
        node_output,
        reason,
        resolution.message or f"Projection skipped: {reason.value}.",
        resolution=resolution,
    )


def _skip_reason_for_resolution(
    status: WorkflowOutputProjectionResolutionStatus,
) -> WorkflowOutputProjectionSkipReason:
    if status is WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_SCHEMA_VERSION:
        return WorkflowOutputProjectionSkipReason.UNSUPPORTED_SCHEMA_VERSION
    if status is WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_NODE_NAME:
        return WorkflowOutputProjectionSkipReason.UNSUPPORTED_NODE_NAME
    return WorkflowOutputProjectionSkipReason.UNSUPPORTED_CONTRACT


def _skipped(
    node_output: CompletedNodeOutputRecord,
    reason: WorkflowOutputProjectionSkipReason,
    message: str,
    *,
    resolution: WorkflowOutputProjectionResolution | None = None,
) -> WorkflowOutputProjectionEligibilityDecision:
    return WorkflowOutputProjectionEligibilityDecision(
        status=WorkflowOutputProjectionEligibilityStatus.SKIPPED,
        node_name=node_output.node_name,
        output_contract=node_output.output_contract,
        output_schema_version=node_output.output_schema_version,
        resolution=resolution,
        skip_reason=reason,
        message=message,
    )


def _coerce_execution_mode(
    value: CompletedRunExecutionMode | str,
) -> CompletedRunExecutionMode:
    return coerce_completed_run_execution_mode(value)


def _coerce_quality_status(
    value: WorkflowOutputQualityStatus | str,
) -> WorkflowOutputQualityStatus:
    if isinstance(value, WorkflowOutputQualityStatus):
        return value
    try:
        return WorkflowOutputQualityStatus(value.strip().lower())
    except ValueError as exc:
        raise ValueError(
            f"Unsupported workflow output quality status: {value!r}."
        ) from exc
