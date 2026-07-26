from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from domain.authority import (
    GateProfile,
    IntendedSink,
    RiskAuthorityContract,
    RiskTier,
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
    PROHIBITED_BOUNDARY = "prohibited_boundary"


@dataclass(frozen=True, slots=True)
class RiskAuthorityGateEvidence:
    """Trace evidence supplied to satisfy the selected gate profile."""

    provenance_record_ids: tuple[str, ...] = ()
    evaluation_run_ids: tuple[str, ...] = ()
    decision_evidence_ids: tuple[str, ...] = ()
    model_replacement_gate_ids: tuple[str, ...] = ()
    decision_evidence_packets: tuple[DecisionEvidencePacket, ...] = ()
    decision_evidence_claim_references: tuple[EvidenceClaimReference, ...] = ()
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

    contract = validation.contract
    selected_metadata = contract.to_metadata()
    expected_contract = validation.expected_contract
    if not validation.platform_consistent:
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.METADATA_INCONSISTENT,
            message=(
                "Risk authority metadata attempted to select a lower or inconsistent "
                "gate profile than the platform classification allows."
            ),
            risk_tier=contract.risk_tier,
            gate_profile=contract.gate_profile,
            authority_metadata=selected_metadata,
            evidence=gate_evidence,
            expected_risk_tier=expected_contract.risk_tier,
            expected_gate_profile=expected_contract.gate_profile,
        )

    decision_profile = validation.selected_profile
    if decision_profile.prohibits_boundary:
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.PROHIBITED_BOUNDARY,
            message="The output boundary is outside platform authority.",
            risk_tier=contract.risk_tier,
            gate_profile=contract.gate_profile,
            authority_metadata=selected_metadata,
            evidence=gate_evidence,
            expected_risk_tier=expected_contract.risk_tier,
            expected_gate_profile=expected_contract.gate_profile,
        )

    if contract.risk_tier in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
        packet_readiness = gate_evidence.packet_readiness(
            required_risk_tier=contract.risk_tier,
        )
        if not packet_readiness.passed:
            return RiskAuthorityGateDecision(
                status=RiskAuthorityGateDecisionStatus.FAILED,
                failure_mode=RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED,
                message=(
                    "Selected authority gate profile requires complete decision "
                    f"evidence packet support: {packet_readiness.message}"
                ),
                risk_tier=contract.risk_tier,
                gate_profile=contract.gate_profile,
                authority_metadata=selected_metadata,
                evidence=gate_evidence,
                expected_risk_tier=expected_contract.risk_tier,
                expected_gate_profile=expected_contract.gate_profile,
            )

    if decision_profile.requires_decision_evidence and not (
        gate_evidence.has_decision_evidence
    ):
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED,
            message="Selected authority gate profile requires decision evidence.",
            risk_tier=contract.risk_tier,
            gate_profile=contract.gate_profile,
            authority_metadata=selected_metadata,
            evidence=gate_evidence,
            expected_risk_tier=expected_contract.risk_tier,
            expected_gate_profile=expected_contract.gate_profile,
        )

    if decision_profile.requires_provenance_evidence and not (
        gate_evidence.has_provenance_evidence
    ):
        return RiskAuthorityGateDecision(
            status=RiskAuthorityGateDecisionStatus.FAILED,
            failure_mode=RiskAuthorityGateFailureMode.PROVENANCE_EVIDENCE_REQUIRED,
            message="Selected authority gate profile requires provenance evidence.",
            risk_tier=contract.risk_tier,
            gate_profile=contract.gate_profile,
            authority_metadata=selected_metadata,
            evidence=gate_evidence,
            expected_risk_tier=expected_contract.risk_tier,
            expected_gate_profile=expected_contract.gate_profile,
        )

    return RiskAuthorityGateDecision(
        status=RiskAuthorityGateDecisionStatus.PASSED,
        failure_mode=RiskAuthorityGateFailureMode.NONE,
        message="Risk authority gate profile selected from canonical metadata.",
        risk_tier=contract.risk_tier,
        gate_profile=contract.gate_profile,
        authority_metadata=selected_metadata,
        evidence=gate_evidence,
        expected_risk_tier=expected_contract.risk_tier,
        expected_gate_profile=expected_contract.gate_profile,
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


def _metadata_copy(
    authority_metadata: Mapping[str, object] | RiskAuthorityContract,
) -> Mapping[str, object]:
    if isinstance(authority_metadata, RiskAuthorityContract):
        return authority_metadata.to_metadata()
    return dict(authority_metadata)


def _clean_string_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    cleaned_values: list[str] = []
    for value in values:
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError(f"{field_name} cannot contain empty strings.")
        cleaned_values.append(cleaned_value)
    return tuple(cleaned_values)


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
