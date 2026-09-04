from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from application.governance.automated_decision_audit import (
    GovernanceReviewApprovalState,
    GovernedOutputReleaseDecision,
    GovernedOutputReleaseRequest,
)
from core.storage.persistence.governance_audit import GovernanceReviewDecisionOutcome
from domain.authority import (
    GateProfile,
    IntendedSink,
    RiskAuthorityContract,
    RiskTier,
    risk_authority_decision_profile_for_tier,
    validate_risk_authority_metadata,
)
from domain.decision_evidence import (
    DecisionEvidencePacket,
    DecisionEvidencePacketReadiness,
    EvidenceClaimReference,
    assess_decision_evidence_packet_readiness,
)


class RiskAuthorityGateDecisionStatus(StrEnum):
    """Outcome status for authority-driven readiness gate selection."""

    PASSED = "passed"
    FAILED = "failed"


class RiskAuthorityGateFailureMode(StrEnum):
    """Fail-closed reasons for authority-driven readiness gate selection."""

    NONE = "none"
    METADATA_MISSING = "metadata_missing"
    METADATA_MALFORMED = "metadata_malformed"
    METADATA_INCONSISTENT = "metadata_inconsistent"
    PROVENANCE_EVIDENCE_REQUIRED = "provenance_evidence_required"
    DECISION_EVIDENCE_REQUIRED = "decision_evidence_required"
    OUTPUT_GOVERNANCE_EVIDENCE_REQUIRED = "output_governance_evidence_required"
    PROHIBITED_BOUNDARY = "prohibited_boundary"


@dataclass(frozen=True, slots=True)
class OutputGovernanceGateReadiness:
    """Readiness of governance accountability evidence for one output boundary."""

    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class OutputGovernanceGateEvidence:
    """Governance review/release accountability evidence for readiness gates."""

    release_decision: GovernedOutputReleaseDecision
    review_scope: str
    requested_action: str
    boundary_name: str
    evidence_packet_id: str
    evidence_packet_version: int
    residual_risk_acceptance_required: bool = False
    residual_risk_scope: str | None = None
    review_decision_outcome: GovernanceReviewDecisionOutcome | None = None

    @classmethod
    def from_release_decision(
        cls,
        *,
        request: GovernedOutputReleaseRequest,
        decision: GovernedOutputReleaseDecision,
    ) -> OutputGovernanceGateEvidence:
        return cls(
            release_decision=decision,
            review_scope=request.review_scope,
            requested_action=request.requested_action,
            boundary_name=request.boundary_name,
            evidence_packet_id=request.evidence.packet_id,
            evidence_packet_version=request.evidence.packet_version,
            residual_risk_acceptance_required=(
                request.residual_risk_acceptance_required
            ),
            residual_risk_scope=request.residual_risk_scope,
            review_decision_outcome=decision.review_decision_outcome,
        )

    def __post_init__(self) -> None:
        if not isinstance(self.release_decision, GovernedOutputReleaseDecision):
            raise ValueError(
                "release_decision must be a GovernedOutputReleaseDecision instance."
            )
        object.__setattr__(
            self,
            "review_scope",
            _clean_string(self.review_scope, "review_scope"),
        )
        object.__setattr__(
            self,
            "requested_action",
            _clean_string(self.requested_action, "requested_action"),
        )
        object.__setattr__(
            self,
            "boundary_name",
            _clean_string(self.boundary_name, "boundary_name"),
        )
        object.__setattr__(
            self,
            "evidence_packet_id",
            _clean_string(self.evidence_packet_id, "evidence_packet_id"),
        )
        if self.evidence_packet_version < 1:
            raise ValueError("evidence_packet_version must be positive.")
        if self.residual_risk_acceptance_required and self.residual_risk_scope is None:
            raise ValueError(
                "residual_risk_scope is required when residual-risk acceptance "
                "is required."
            )
        object.__setattr__(
            self,
            "residual_risk_scope",
            _clean_optional_string(self.residual_risk_scope, "residual_risk_scope"),
        )
        if self.review_decision_outcome is not None and not isinstance(
            self.review_decision_outcome,
            GovernanceReviewDecisionOutcome,
        ):
            raise ValueError(
                "review_decision_outcome must be a GovernanceReviewDecisionOutcome "
                "instance."
            )

    @property
    def allowed(self) -> bool:
        return self.release_decision.allowed

    @property
    def approval_state(self) -> GovernanceReviewApprovalState | None:
        return self.release_decision.approval_state

    @property
    def review_task_id(self) -> str | None:
        return self.release_decision.review_task_id

    @property
    def residual_risk_acceptance_id(self) -> str | None:
        return self.release_decision.residual_risk_acceptance_id


@dataclass(frozen=True, slots=True)
class RiskAuthorityGateEvidence:
    """Trace evidence supplied to satisfy the selected gate profile."""

    provenance_record_ids: tuple[str, ...] = ()
    evaluation_run_ids: tuple[str, ...] = ()
    decision_evidence_ids: tuple[str, ...] = ()
    model_replacement_gate_ids: tuple[str, ...] = ()
    decision_evidence_packets: tuple[DecisionEvidencePacket, ...] = ()
    decision_evidence_claim_references: tuple[EvidenceClaimReference, ...] = ()
    output_governance_evidence: tuple[OutputGovernanceGateEvidence, ...] = ()
    rejected_evidence_ids: tuple[str, ...] = ()
    metric_result_count: int = 0

    def __post_init__(self) -> None:
        if self.metric_result_count < 0:
            raise ValueError("metric_result_count cannot be negative.")
        object.__setattr__(
            self,
            "provenance_record_ids",
            _clean_string_tuple(self.provenance_record_ids, "provenance_record_ids"),
        )
        object.__setattr__(
            self,
            "evaluation_run_ids",
            _clean_string_tuple(self.evaluation_run_ids, "evaluation_run_ids"),
        )
        object.__setattr__(
            self,
            "decision_evidence_ids",
            _clean_string_tuple(self.decision_evidence_ids, "decision_evidence_ids"),
        )
        object.__setattr__(
            self,
            "model_replacement_gate_ids",
            _clean_string_tuple(
                self.model_replacement_gate_ids,
                "model_replacement_gate_ids",
            ),
        )
        object.__setattr__(
            self,
            "rejected_evidence_ids",
            _clean_string_tuple(self.rejected_evidence_ids, "rejected_evidence_ids"),
        )
        object.__setattr__(
            self,
            "decision_evidence_packets",
            _typed_tuple(
                self.decision_evidence_packets,
                DecisionEvidencePacket,
                "decision_evidence_packets",
            ),
        )
        object.__setattr__(
            self,
            "decision_evidence_claim_references",
            _typed_tuple(
                self.decision_evidence_claim_references,
                EvidenceClaimReference,
                "decision_evidence_claim_references",
            ),
        )
        object.__setattr__(
            self,
            "output_governance_evidence",
            _typed_tuple(
                self.output_governance_evidence,
                OutputGovernanceGateEvidence,
                "output_governance_evidence",
            ),
        )

    @property
    def has_provenance_evidence(self) -> bool:
        return bool(
            self.provenance_record_ids
            or self.evaluation_run_ids
            or self.metric_result_count > 0
        )

    @property
    def has_decision_evidence(self) -> bool:
        return self.packet_readiness().passed

    def packet_readiness(
        self,
        *,
        required_risk_tier: RiskTier | None = None,
    ) -> DecisionEvidencePacketReadiness:
        return assess_decision_evidence_packet_readiness(
            packets=self.decision_evidence_packets,
            claim_references=self.decision_evidence_claim_references,
            rejected_evidence_ids=self.rejected_evidence_ids,
            required_risk_tier=required_risk_tier,
        )

    def output_governance_readiness(self) -> OutputGovernanceGateReadiness:
        if not self.output_governance_evidence:
            return OutputGovernanceGateReadiness(
                passed=False,
                message=(
                    "Selected Vigilant authority gate profile requires output "
                    "governance accountability evidence."
                ),
            )
        packet_versions = {
            packet.packet_id: packet.schema_version
            for packet in self.decision_evidence_packets
            if packet.authority.risk_tier is RiskTier.VIGILANT
        }
        if not packet_versions:
            return OutputGovernanceGateReadiness(
                passed=False,
                message=(
                    "Selected Vigilant authority gate profile requires selected "
                    "Vigilant decision evidence packets before output governance "
                    "accountability evidence."
                ),
            )
        matched_packet_ids = set()
        for evidence in self.output_governance_evidence:
            evidence_packet_version = packet_versions.get(evidence.evidence_packet_id)
            if evidence_packet_version is None:
                return OutputGovernanceGateReadiness(
                    passed=False,
                    message=(
                        "Output governance evidence does not match a selected "
                        "Vigilant decision evidence packet."
                    ),
                )
            if evidence_packet_version != evidence.evidence_packet_version:
                return OutputGovernanceGateReadiness(
                    passed=False,
                    message=(
                        "Output governance evidence references a mismatched "
                        "decision evidence packet version."
                    ),
                )
            failure = _output_governance_failure(evidence)
            if failure is not None:
                return OutputGovernanceGateReadiness(passed=False, message=failure)
            matched_packet_ids.add(evidence.evidence_packet_id)
        if set(packet_versions) != matched_packet_ids:
            return OutputGovernanceGateReadiness(
                passed=False,
                message=(
                    "Output governance evidence is missing for a selected Vigilant "
                    "decision evidence packet."
                ),
            )
        return OutputGovernanceGateReadiness(
            passed=True,
            message="Output governance accountability evidence is complete.",
        )


@dataclass(frozen=True, slots=True)
class RiskAuthorityGateDecision:
    """Selected profile and fail-closed readiness result for one output boundary."""

    status: RiskAuthorityGateDecisionStatus
    failure_mode: RiskAuthorityGateFailureMode
    message: str
    risk_tier: RiskTier | None
    gate_profile: GateProfile | None
    authority_metadata: Mapping[str, object] | None
    evidence: RiskAuthorityGateEvidence
    expected_risk_tier: RiskTier | None = None
    expected_gate_profile: GateProfile | None = None

    @property
    def selected_profile(self) -> str | None:
        if self.gate_profile is None:
            return None
        return self.gate_profile.value

    @property
    def passed(self) -> bool:
        return self.status is RiskAuthorityGateDecisionStatus.PASSED


def select_risk_authority_gate(
    authority_metadata: Mapping[str, object] | RiskAuthorityContract | None,
    *,
    evidence: RiskAuthorityGateEvidence | None = None,
    expected_authority_metadata: Mapping[str, object] | RiskAuthorityContract | None = (
        None
    ),
) -> RiskAuthorityGateDecision:
    """Select and enforce the readiness gate profile from canonical metadata."""

    gate_evidence = evidence or RiskAuthorityGateEvidence()
    expected_contract = _expected_contract(expected_authority_metadata)
    if authority_metadata is None:
        return _missing_metadata_decision(
            gate_evidence,
            expected_contract=expected_contract,
        )

    try:
        validation = validate_risk_authority_metadata(authority_metadata)
    except ValueError as exc:
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.METADATA_MALFORMED,
            message=f"Risk authority metadata is malformed: {exc}",
            risk_tier=(
                None if expected_contract is None else expected_contract.risk_tier
            ),
            gate_profile=None
            if expected_contract is None
            else expected_contract.gate_profile,
            authority_metadata=_metadata_copy(authority_metadata),
            evidence=gate_evidence,
            expected_risk_tier=None
            if expected_contract is None
            else expected_contract.risk_tier,
            expected_gate_profile=None
            if expected_contract is None
            else expected_contract.gate_profile,
        )

    supplied_contract = validation.contract
    supplied_metadata = supplied_contract.to_metadata()
    platform_expected_contract = validation.expected_contract
    authoritative_contract = expected_contract or platform_expected_contract
    if not validation.platform_consistent or not _same_authority_contract(
        supplied_contract,
        authoritative_contract,
    ):
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.METADATA_INCONSISTENT,
            message=(
                "Risk authority metadata attempted to select a lower or "
                "inconsistent gate profile than the platform target allows."
            ),
            risk_tier=authoritative_contract.risk_tier,
            gate_profile=authoritative_contract.gate_profile,
            authority_metadata=supplied_metadata,
            evidence=gate_evidence,
            expected_risk_tier=authoritative_contract.risk_tier,
            expected_gate_profile=authoritative_contract.gate_profile,
        )

    decision_profile = risk_authority_decision_profile_for_tier(
        authoritative_contract.risk_tier,
    )
    if decision_profile.prohibits_boundary:
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.PROHIBITED_BOUNDARY,
            message="The output boundary is outside platform authority.",
            risk_tier=authoritative_contract.risk_tier,
            gate_profile=authoritative_contract.gate_profile,
            authority_metadata=authoritative_contract.to_metadata(),
            evidence=gate_evidence,
            expected_risk_tier=authoritative_contract.risk_tier,
            expected_gate_profile=authoritative_contract.gate_profile,
        )

    if authoritative_contract.risk_tier in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
        packet_readiness = gate_evidence.packet_readiness(
            required_risk_tier=authoritative_contract.risk_tier,
        )
        if not packet_readiness.passed:
            return RiskAuthorityGateDecision(
                status=RiskAuthorityGateDecisionStatus.FAILED,
                failure_mode=RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED,
                message=(
                    "Selected authority gate profile requires complete decision "
                    f"evidence packet support: {packet_readiness.message}"
                ),
                risk_tier=authoritative_contract.risk_tier,
                gate_profile=authoritative_contract.gate_profile,
                authority_metadata=authoritative_contract.to_metadata(),
                evidence=gate_evidence,
                expected_risk_tier=authoritative_contract.risk_tier,
                expected_gate_profile=authoritative_contract.gate_profile,
            )

    output_governance_failure = _output_governance_required_decision(
        authoritative_contract,
        gate_evidence,
    )
    if output_governance_failure is not None:
        return output_governance_failure

    if decision_profile.requires_decision_evidence and not (
        gate_evidence.has_decision_evidence
    ):
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED,
            message="Selected authority gate profile requires decision evidence.",
            risk_tier=authoritative_contract.risk_tier,
            gate_profile=authoritative_contract.gate_profile,
            authority_metadata=authoritative_contract.to_metadata(),
            evidence=gate_evidence,
            expected_risk_tier=authoritative_contract.risk_tier,
            expected_gate_profile=authoritative_contract.gate_profile,
        )

    if decision_profile.requires_provenance_evidence and not (
        gate_evidence.has_provenance_evidence
    ):
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.PROVENANCE_EVIDENCE_REQUIRED,
            message="Selected authority gate profile requires provenance evidence.",
            risk_tier=authoritative_contract.risk_tier,
            gate_profile=authoritative_contract.gate_profile,
            authority_metadata=authoritative_contract.to_metadata(),
            evidence=gate_evidence,
            expected_risk_tier=authoritative_contract.risk_tier,
            expected_gate_profile=authoritative_contract.gate_profile,
        )

    return RiskAuthorityGateDecision(
        status=RiskAuthorityGateDecisionStatus.PASSED,
        failure_mode=RiskAuthorityGateFailureMode.NONE,
        message="Risk authority gate profile selected from canonical metadata.",
        risk_tier=authoritative_contract.risk_tier,
        gate_profile=authoritative_contract.gate_profile,
        authority_metadata=authoritative_contract.to_metadata(),
        evidence=gate_evidence,
        expected_risk_tier=authoritative_contract.risk_tier,
        expected_gate_profile=authoritative_contract.gate_profile,
    )


def _expected_contract(
    expected_authority_metadata: Mapping[str, object] | RiskAuthorityContract | None,
) -> RiskAuthorityContract | None:
    if expected_authority_metadata is None:
        return None
    return validate_risk_authority_metadata(
        expected_authority_metadata,
    ).expected_contract


def _missing_metadata_decision(
    gate_evidence: RiskAuthorityGateEvidence,
    *,
    expected_contract: RiskAuthorityContract | None,
) -> RiskAuthorityGateDecision:
    if (
        expected_contract is not None
        and expected_contract.risk_tier is RiskTier.BASELINE
        and expected_contract.intended_sink is IntendedSink.INTERNAL_RUNTIME_EVIDENCE
    ):
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.PASSED,
            failure_mode=RiskAuthorityGateFailureMode.NONE,
            message=(
                "Missing risk authority metadata is accepted only for explicit "
                "Baseline internal runtime evidence."
            ),
            risk_tier=expected_contract.risk_tier,
            gate_profile=expected_contract.gate_profile,
            authority_metadata=None,
            evidence=gate_evidence,
            expected_risk_tier=expected_contract.risk_tier,
            expected_gate_profile=expected_contract.gate_profile,
        )

    return RiskAuthorityGateDecision(
        status=RiskAuthorityGateDecisionStatus.FAILED,
        failure_mode=RiskAuthorityGateFailureMode.METADATA_MISSING,
        message="Risk authority metadata is required before selecting a gate profile.",
        risk_tier=None if expected_contract is None else expected_contract.risk_tier,
        gate_profile=(
            None if expected_contract is None else expected_contract.gate_profile
        ),
        authority_metadata=None,
        evidence=gate_evidence,
        expected_risk_tier=(
            None if expected_contract is None else expected_contract.risk_tier
        ),
        expected_gate_profile=None
        if expected_contract is None
        else expected_contract.gate_profile,
    )


def _output_governance_required_decision(
    authoritative_contract: RiskAuthorityContract,
    gate_evidence: RiskAuthorityGateEvidence,
) -> RiskAuthorityGateDecision | None:
    if authoritative_contract.risk_tier is not RiskTier.VIGILANT:
        return None
    output_governance_readiness = gate_evidence.output_governance_readiness()
    if output_governance_readiness.passed:
        return None
    return RiskAuthorityGateDecision(
        status=RiskAuthorityGateDecisionStatus.FAILED,
        failure_mode=RiskAuthorityGateFailureMode.OUTPUT_GOVERNANCE_EVIDENCE_REQUIRED,
        message=output_governance_readiness.message,
        risk_tier=authoritative_contract.risk_tier,
        gate_profile=authoritative_contract.gate_profile,
        authority_metadata=authoritative_contract.to_metadata(),
        evidence=gate_evidence,
        expected_risk_tier=authoritative_contract.risk_tier,
        expected_gate_profile=authoritative_contract.gate_profile,
    )


def _metadata_copy(
    authority_metadata: Mapping[str, object] | RiskAuthorityContract,
) -> Mapping[str, object]:
    if isinstance(authority_metadata, RiskAuthorityContract):
        return authority_metadata.to_metadata()
    return dict(authority_metadata)


def _same_authority_contract(
    supplied_contract: RiskAuthorityContract,
    expected_contract: RiskAuthorityContract,
) -> bool:
    return (
        supplied_contract.risk_tier is expected_contract.risk_tier
        and supplied_contract.gate_profile is expected_contract.gate_profile
        and supplied_contract.authority_effect is expected_contract.authority_effect
        and supplied_contract.content_type is expected_contract.content_type
        and supplied_contract.canonical_owner is expected_contract.canonical_owner
        and supplied_contract.source_of_truth is expected_contract.source_of_truth
        and supplied_contract.intended_sink is expected_contract.intended_sink
        and supplied_contract.capital_relevant == expected_contract.capital_relevant
        and supplied_contract.durable_authority == expected_contract.durable_authority
        and supplied_contract.externally_visible == expected_contract.externally_visible
        and supplied_contract.governance_impact == expected_contract.governance_impact
        and supplied_contract.evidence_sufficient
        == expected_contract.evidence_sufficient
    )


def _clean_string_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    cleaned_values: list[str] = []
    for value in values:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError(f"{field_name} cannot contain empty strings.")
        cleaned_values.append(cleaned_value)
    return tuple(cleaned_values)


def _clean_string(value: str, field_name: str) -> str:
    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned_value


def _clean_optional_string(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _clean_string(value, field_name)


def _output_governance_failure(
    evidence: OutputGovernanceGateEvidence,
) -> str | None:
    decision = evidence.release_decision
    if decision.approval_state is None:
        return "Output governance evidence must carry approval state."
    if decision.review_task_id is None:
        return "Output governance evidence must carry a review task id."
    if not decision.review_task_id.strip():
        return "Output governance evidence review task id cannot be empty."
    expected_outcome = _REVIEW_OUTCOME_BY_APPROVAL_STATE.get(decision.approval_state)
    if expected_outcome is not None and evidence.review_decision_outcome is None:
        return "Output governance evidence must carry the reviewer outcome."
    if (
        expected_outcome is not None
        and evidence.review_decision_outcome is not expected_outcome
    ):
        return (
            "Output governance evidence reviewer outcome does not match approval state."
        )
    if not decision.allowed:
        return (
            "Output governance release is not allowed: "
            f"{decision.approval_state.value}."
        )
    if decision.approval_state not in _RELEASE_ALLOWED_APPROVAL_STATES:
        return "Output governance approval state does not permit release."
    if (
        evidence.residual_risk_acceptance_required
        and decision.residual_risk_acceptance_id is None
    ):
        return "Output governance evidence must carry residual-risk acceptance."
    return None


_RELEASE_ALLOWED_APPROVAL_STATES = frozenset(
    (
        GovernanceReviewApprovalState.REVIEW_APPROVED,
        GovernanceReviewApprovalState.REVIEW_OVERRIDDEN,
    )
)
_REVIEW_OUTCOME_BY_APPROVAL_STATE = {
    GovernanceReviewApprovalState.REVIEW_APPROVED: (
        GovernanceReviewDecisionOutcome.APPROVED
    ),
    GovernanceReviewApprovalState.REVIEW_DENIED: GovernanceReviewDecisionOutcome.DENIED,
    GovernanceReviewApprovalState.REVIEW_CONTESTED: (
        GovernanceReviewDecisionOutcome.CONTESTED
    ),
    GovernanceReviewApprovalState.CHANGES_REQUESTED: (
        GovernanceReviewDecisionOutcome.CHANGES_REQUESTED
    ),
    GovernanceReviewApprovalState.REVIEW_OVERRIDDEN: (
        GovernanceReviewDecisionOutcome.OVERRIDDEN
    ),
}


def _typed_tuple[T](
    values: tuple[object, ...],
    expected_type: type[T],
    field_name: str,
) -> tuple[T, ...]:
    typed_values: list[T] = []
    for value in values:
        if not isinstance(value, expected_type):
            raise ValueError(
                f"{field_name} entries must be {expected_type.__name__} instances."
            )
        typed_values.append(value)
    return tuple(typed_values)
