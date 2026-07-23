from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from application.projections.workflow_outputs.projection_registry import (
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectionResolution,
    WorkflowOutputProjectionResolutionStatus,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    coerce_completed_run_execution_mode,
)
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskAuthorityContract,
    SourceOfTruthCategory,
    classify_risk_authority,
    validate_risk_authority_metadata,
)

WorkflowProjectionExecutionMode = CompletedRunExecutionMode


class WorkflowOutputQualityStatus(StrEnum):
    """First-class quality classification for a workflow node output."""

    NORMAL = "normal"
    DEGRADED = "degraded"
    FALLBACK = "fallback"


class WorkflowOutputProjectionEligibilityStatus(StrEnum):
    """Eligibility decision for one archived workflow node output."""

    ELIGIBLE = "eligible"
    SKIPPED = "skipped"


class WorkflowOutputProjectionSkipReason(StrEnum):
    """Stable skip reason values for workflow-output projection decisions."""

    NON_PRODUCTION_EXECUTION = "non_production_execution"
    BASELINE_RUNTIME_EVIDENCE_ONLY = "baseline_runtime_evidence_only"
    AUTHORITY_METADATA_REQUIRED = "authority_metadata_required"
    AUTHORITY_METADATA_MALFORMED = "authority_metadata_malformed"
    AUTHORITY_METADATA_INCONSISTENT = "authority_metadata_inconsistent"
    PROHIBITED_OUTSIDE_AUTHORITY = "prohibited_outside_authority"
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
WORKFLOW_OUTPUT_AUTHORITY_METADATA_KEY: Final[str] = "risk_authority"


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionEligibilityContext:
    """First-class inputs used to evaluate projection eligibility."""

    run: CompletedRunRecord
    node_output: CompletedNodeOutputRecord
    execution_mode: CompletedRunExecutionMode | str = CompletedRunExecutionMode.NORMAL
    quality_status: WorkflowOutputQualityStatus | str = (
        WorkflowOutputQualityStatus.NORMAL
    )
    intended_sink: IntendedSink | str = IntendedSink.DURABLE_DOMAIN_RECORD
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
        object.__setattr__(
            self,
            "intended_sink",
            _coerce_intended_sink(self.intended_sink),
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
    authority_contract: RiskAuthorityContract | None = None

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

    @property
    def authority_metadata(self) -> dict[str, object] | None:
        """Stable serialized authority metadata emitted at the curation seam."""

        if self.authority_contract is None:
            return None
        return self.authority_contract.to_metadata()


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

        authority_contract, authority_decision = _evaluate_authority_contract(
            context,
        )
        if authority_decision is not None:
            return authority_decision

        resolution = registry.resolve(
            output_contract=node_output.output_contract,
            output_schema_version=node_output.output_schema_version,
            node_name=node_output.node_name,
        )
        if not resolution.supported:
            return _skipped_for_resolution(
                node_output,
                resolution,
                authority_contract=authority_contract,
            )

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
                authority_contract=authority_contract,
            )

        return WorkflowOutputProjectionEligibilityDecision(
            status=WorkflowOutputProjectionEligibilityStatus.ELIGIBLE,
            node_name=node_output.node_name,
            output_contract=node_output.output_contract,
            output_schema_version=node_output.output_schema_version,
            resolution=resolution,
            message="Workflow node output is eligible for projection.",
            authority_contract=authority_contract,
        )


def _evaluate_authority_contract(
    context: WorkflowOutputProjectionEligibilityContext,
) -> tuple[
    RiskAuthorityContract | None, WorkflowOutputProjectionEligibilityDecision | None
]:
    node_output = context.node_output
    intended_sink = cast(IntendedSink, context.intended_sink)
    raw_authority_metadata = node_output.metadata.get(
        WORKFLOW_OUTPUT_AUTHORITY_METADATA_KEY,
    )

    if raw_authority_metadata is None:
        if intended_sink is IntendedSink.INTERNAL_RUNTIME_EVIDENCE:
            authority_contract = _classify_internal_baseline_runtime_evidence()
            return authority_contract, _skipped(
                node_output,
                WorkflowOutputProjectionSkipReason.BASELINE_RUNTIME_EVIDENCE_ONLY,
                (
                    "Projection is skipped because explicitly internal Baseline "
                    "runtime evidence remains runtime evidence and is not durably "
                    "curated."
                ),
                authority_contract=authority_contract,
            )
        return None, _skipped(
            node_output,
            WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_REQUIRED,
            (
                "Projection requires canonical risk authority metadata for "
                "durable workflow-output curation."
            ),
        )

    try:
        validation = validate_risk_authority_metadata(raw_authority_metadata)
    except ValueError as exc:
        return None, _skipped(
            node_output,
            WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_MALFORMED,
            f"Projection requires well-formed risk authority metadata: {exc}",
        )

    authority_contract = validation.contract
    if authority_contract.intended_sink is not intended_sink:
        return authority_contract, _skipped(
            node_output,
            WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_INCONSISTENT,
            (
                "Projection authority metadata intended sink "
                f"{authority_contract.intended_sink.value!r} does not match "
                f"the curation sink {intended_sink.value!r}."
            ),
            authority_contract=authority_contract,
        )

    if not validation.platform_consistent:
        return authority_contract, _skipped(
            node_output,
            WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_INCONSISTENT,
            (
                "Projection authority metadata does not match the canonical "
                "platform authority classifier."
            ),
            authority_contract=authority_contract,
        )

    if validation.selected_profile.prohibits_boundary:
        return authority_contract, _skipped(
            node_output,
            WorkflowOutputProjectionSkipReason.PROHIBITED_OUTSIDE_AUTHORITY,
            (
                "Projection rejected before durable curation because the "
                "canonical authority tier is 'prohibited_outside_authority'."
            ),
            authority_contract=authority_contract,
        )

    return authority_contract, None


def _classify_internal_baseline_runtime_evidence() -> RiskAuthorityContract:
    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.RUNTIME_EVIDENCE,
            authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
            canonical_owner=CanonicalOwner.WORKFLOW_OUTPUT_CURATION,
            source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
            intended_sink=IntendedSink.INTERNAL_RUNTIME_EVIDENCE,
        )
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
    *,
    authority_contract: RiskAuthorityContract | None = None,
) -> WorkflowOutputProjectionEligibilityDecision:
    reason = _skip_reason_for_resolution(resolution.status)
    return _skipped(
        node_output,
        reason,
        resolution.message or f"Projection skipped: {reason.value}.",
        resolution=resolution,
        authority_contract=authority_contract,
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
    authority_contract: RiskAuthorityContract | None = None,
) -> WorkflowOutputProjectionEligibilityDecision:
    return WorkflowOutputProjectionEligibilityDecision(
        status=WorkflowOutputProjectionEligibilityStatus.SKIPPED,
        node_name=node_output.node_name,
        output_contract=node_output.output_contract,
        output_schema_version=node_output.output_schema_version,
        resolution=resolution,
        skip_reason=reason,
        message=message,
        authority_contract=authority_contract,
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


def _coerce_intended_sink(value: IntendedSink | str) -> IntendedSink:
    if isinstance(value, IntendedSink):
        return value
    try:
        return IntendedSink(value.strip().lower())
    except ValueError as exc:
        raise ValueError(
            f"Unsupported workflow output intended sink: {value!r}."
        ) from exc
