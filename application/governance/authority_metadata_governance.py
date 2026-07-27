from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, cast

from core.runtime.governance import (
    BaseGovernanceRule,
    GovernanceDecision,
    GovernanceResult,
)
from domain.authority import (
    RISK_AUTHORITY_METADATA_KEY,
    RiskAuthorityContract,
    RiskTier,
    validate_risk_authority_metadata,
)
from domain.decision_evidence import (
    DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY,
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
    EvidenceClaimReference,
    assess_decision_evidence_packet_readiness,
    evidence_claim_references_from_metadata,
)

AUTHORITY_GOVERNANCE_RULE_NAME: Final = "authority_metadata_governance"
AUTHORITY_METADATA_REQUIRED_CONTEXT_KEY: Final = "authority_metadata_required"
AUTHORITY_SUBJECT_FAMILY_CONTEXT_KEY: Final = "authority_subject_family"


class AuthorityGovernanceFailureMode(StrEnum):
    """Stable governance failure modes for canonical authority metadata."""

    NONE = "none"
    AUTHORITY_METADATA_REQUIRED = "authority_metadata_required"
    AUTHORITY_METADATA_MALFORMED = "authority_metadata_malformed"
    AUTHORITY_METADATA_INCONSISTENT = "authority_metadata_inconsistent"
    MODEL_AUTHORITY_CLAIMS_IGNORED = "model_authority_claims_ignored"
    PROHIBITED_OUTSIDE_AUTHORITY = "prohibited_outside_authority"
    ENHANCED_AUTHORITY_EVIDENCE_REQUIRED = "enhanced_authority_evidence_required"
    VIGILANT_AUTHORITY_EVIDENCE_REQUIRED = "vigilant_authority_evidence_required"


@dataclass(frozen=True, slots=True)
class _AuthorityExtraction:
    raw_authority_metadata: object | None
    metadata_source: str | None = None


@dataclass(frozen=True, slots=True)
class _PacketSupportExtraction:
    packets: tuple[DecisionEvidencePacket, ...] = ()
    claim_references: tuple[EvidenceClaimReference, ...] = ()
    rejected_evidence_ids: tuple[str, ...] = ()
    error: str | None = None


class AuthorityMetadataGovernanceRule(BaseGovernanceRule):
    """Evaluate governance outcomes from canonical risk authority metadata."""

    rule_name = AUTHORITY_GOVERNANCE_RULE_NAME
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        evaluation_context = context or {}
        subject_family = _subject_family(
            subject,
            evaluation_context,
        )
        extraction = _extract_authority_metadata(subject)
        if extraction.raw_authority_metadata is None:
            return _missing_authority_result(
                rule_name=self.rule_name,
                subject_family=subject_family,
                metadata_required=_metadata_required(evaluation_context),
            )

        try:
            validation = validate_risk_authority_metadata(
                extraction.raw_authority_metadata,
            )
        except ValueError as exc:
            return _malformed_authority_result(
                rule_name=self.rule_name,
                subject_family=subject_family,
                metadata_source=extraction.metadata_source,
                error=exc,
            )

        contract = validation.contract
        expected_contract = validation.expected_contract
        packet_support = _extract_packet_support(subject)
        if not validation.platform_consistent:
            return _inconsistent_authority_result(
                rule_name=self.rule_name,
                subject_family=subject_family,
                metadata_source=extraction.metadata_source,
                contract=contract,
                expected_contract=expected_contract,
            )

        return _authority_governance_result(
            rule_name=self.rule_name,
            subject_family=subject_family,
            metadata_source=extraction.metadata_source,
            contract=contract,
            packet_support=packet_support,
        )


def _missing_authority_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_required: bool,
) -> GovernanceResult:
    metadata = _result_metadata(
        subject_family=subject_family,
        metadata_source=None,
        contract=None,
        failure_mode=AuthorityGovernanceFailureMode.AUTHORITY_METADATA_REQUIRED,
        authority_metadata_present=False,
    )
    if metadata_required:
        return GovernanceResult.deny(
            rule_name=rule_name,
            message=(
                "Governance denied the subject because canonical risk "
                "authority metadata is required but absent."
            ),
            reason=AuthorityGovernanceFailureMode.AUTHORITY_METADATA_REQUIRED,
            metadata=metadata,
        )
    return GovernanceResult.skip(
        rule_name=rule_name,
        message="No canonical risk authority metadata was present.",
        reason=AuthorityGovernanceFailureMode.AUTHORITY_METADATA_REQUIRED,
        metadata=metadata,
    )


def _malformed_authority_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    error: ValueError,
) -> GovernanceResult:
    return GovernanceResult.deny(
        rule_name=rule_name,
        message="Governance denied malformed risk authority metadata.",
        reason=AuthorityGovernanceFailureMode.AUTHORITY_METADATA_MALFORMED,
        metadata={
            **_result_metadata(
                subject_family=subject_family,
                metadata_source=metadata_source,
                contract=None,
                failure_mode=AuthorityGovernanceFailureMode.AUTHORITY_METADATA_MALFORMED,
                authority_metadata_present=True,
            ),
            "authority_metadata_error": str(error),
        },
    )


def _inconsistent_authority_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
    expected_contract: RiskAuthorityContract,
) -> GovernanceResult:
    return GovernanceResult.deny(
        rule_name=rule_name,
        message=(
            "Governance denied risk authority metadata that does not "
            "match the canonical platform classifier."
        ),
        reason=AuthorityGovernanceFailureMode.AUTHORITY_METADATA_INCONSISTENT,
        metadata={
            **_result_metadata(
                subject_family=subject_family,
                metadata_source=metadata_source,
                contract=contract,
                failure_mode=AuthorityGovernanceFailureMode.AUTHORITY_METADATA_INCONSISTENT,
            ),
            "expected_risk_tier": expected_contract.risk_tier.value,
            "observed_risk_tier": contract.risk_tier.value,
            "expected_gate_profile": expected_contract.gate_profile.value,
            "observed_gate_profile": contract.gate_profile.value,
        },
    )


def _authority_governance_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
    packet_support: _PacketSupportExtraction,
) -> GovernanceResult:
    if contract.ignored_model_authority_claims:
        return _ignored_model_claims_result(
            rule_name=rule_name,
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        )

    if contract.risk_tier in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
        if packet_support.error is not None:
            return _packet_readiness_denial(
                rule_name=rule_name,
                subject_family=subject_family,
                metadata_source=metadata_source,
                contract=contract,
                message=(
                    "Governance denied authority output because decision evidence "
                    f"packet metadata is malformed: {packet_support.error}"
                ),
            )
        readiness = assess_decision_evidence_packet_readiness(
            packets=packet_support.packets,
            claim_references=packet_support.claim_references,
            rejected_evidence_ids=packet_support.rejected_evidence_ids,
            required_risk_tier=contract.risk_tier,
        )
        if not readiness.passed:
            return _packet_readiness_denial(
                rule_name=rule_name,
                subject_family=subject_family,
                metadata_source=metadata_source,
                contract=contract,
                message=(
                    "Governance denied authority output because complete decision "
                    f"evidence packet support is absent: {readiness.message}"
                ),
                readiness_metadata={
                    "decision_evidence_packet_readiness_failure_mode": (
                        readiness.failure_mode.value
                    ),
                    "decision_evidence_packet_readiness_message": readiness.message,
                    "decision_evidence_provenance_reconstruction_complete": (
                        readiness.provenance_reconstruction_complete
                    ),
                    "decision_evidence_claim_support_complete": (
                        readiness.claim_support_complete
                    ),
                    "decision_evidence_correctness_support_complete": (
                        readiness.correctness_support_complete
                    ),
                    "decision_evidence_provenance_reconstruction_failure_mode": (
                        readiness.provenance_reconstruction_failure_mode.value
                    ),
                    "decision_evidence_claim_support_failure_mode": (
                        readiness.claim_support_failure_mode.value
                    ),
                    "decision_evidence_correctness_support_failure_mode": (
                        readiness.correctness_support_failure_mode.value
                    ),
                    "decision_evidence_packet_ids": list(readiness.packet_ids),
                    "decision_evidence_supporting_evidence_ids": list(
                        readiness.supporting_evidence_ids
                    ),
                    "decision_evidence_reconstruction_reference_ids": list(
                        readiness.reconstruction_reference_ids
                    ),
                    "decision_evidence_reconstruction_reference_kinds": list(
                        readiness.reconstruction_reference_kinds
                    ),
                    "rejected_supporting_evidence_ids": list(
                        readiness.rejected_supporting_evidence_ids
                    ),
                },
            )

    result_builder = _AUTHORITY_GOVERNANCE_RESULT_BY_TIER[contract.risk_tier]
    return result_builder(
        rule_name=rule_name,
        subject_family=subject_family,
        metadata_source=metadata_source,
        contract=contract,
    )


def _packet_readiness_denial(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
    message: str,
    readiness_metadata: Mapping[str, object] | None = None,
) -> GovernanceResult:
    failure_mode = (
        AuthorityGovernanceFailureMode.ENHANCED_AUTHORITY_EVIDENCE_REQUIRED
        if contract.risk_tier is RiskTier.ENHANCED
        else AuthorityGovernanceFailureMode.VIGILANT_AUTHORITY_EVIDENCE_REQUIRED
    )
    return GovernanceResult.deny(
        rule_name=rule_name,
        message=message,
        reason=failure_mode,
        metadata={
            **_result_metadata(
                subject_family=subject_family,
                metadata_source=metadata_source,
                contract=contract,
                failure_mode=failure_mode,
            ),
            **dict(readiness_metadata or {}),
        },
    )


def _ignored_model_claims_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
) -> GovernanceResult:
    return GovernanceResult.deny(
        rule_name=rule_name,
        message=(
            "Governance denied the subject because model-provided "
            "authority claims were ignored by the platform contract."
        ),
        reason=AuthorityGovernanceFailureMode.MODEL_AUTHORITY_CLAIMS_IGNORED,
        metadata=_result_metadata(
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
            failure_mode=AuthorityGovernanceFailureMode.MODEL_AUTHORITY_CLAIMS_IGNORED,
        ),
    )


def _prohibited_authority_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
) -> GovernanceResult:
    return GovernanceResult.deny(
        rule_name=rule_name,
        message=(
            "Governance denied the subject because its canonical "
            "authority tier is prohibited_outside_authority."
        ),
        reason=AuthorityGovernanceFailureMode.PROHIBITED_OUTSIDE_AUTHORITY,
        metadata=_result_metadata(
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
            failure_mode=AuthorityGovernanceFailureMode.PROHIBITED_OUTSIDE_AUTHORITY,
        ),
    )


def _baseline_authority_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
) -> GovernanceResult:
    return GovernanceResult(
        rule_name=rule_name,
        decision=GovernanceDecision.ALLOW,
        message="Governance allowed Baseline authority output.",
        reason="baseline_authority_allowed",
        metadata=_result_metadata(
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        ),
    )


def _enhanced_authority_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
) -> GovernanceResult:
    if not contract.evidence_sufficient:
        return GovernanceResult.require_approval(
            rule_name=rule_name,
            message=(
                "Governance requires approval because Enhanced authority "
                "metadata reports insufficient evidence."
            ),
            reason=AuthorityGovernanceFailureMode.ENHANCED_AUTHORITY_EVIDENCE_REQUIRED,
            metadata=_result_metadata(
                subject_family=subject_family,
                metadata_source=metadata_source,
                contract=contract,
                failure_mode=(
                    AuthorityGovernanceFailureMode.ENHANCED_AUTHORITY_EVIDENCE_REQUIRED
                ),
            ),
        )
    return GovernanceResult.warn(
        rule_name=rule_name,
        message=(
            "Governance allowed Enhanced authority output with provenance controls."
        ),
        reason="enhanced_authority_requires_provenance",
        metadata=_result_metadata(
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        ),
    )


def _vigilant_authority_result(
    *,
    rule_name: str,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract,
) -> GovernanceResult:
    if not contract.evidence_sufficient:
        return GovernanceResult.deny(
            rule_name=rule_name,
            message=(
                "Governance denied Vigilant authority output because required "
                "decision evidence is absent."
            ),
            reason=AuthorityGovernanceFailureMode.VIGILANT_AUTHORITY_EVIDENCE_REQUIRED,
            metadata=_result_metadata(
                subject_family=subject_family,
                metadata_source=metadata_source,
                contract=contract,
                failure_mode=(
                    AuthorityGovernanceFailureMode.VIGILANT_AUTHORITY_EVIDENCE_REQUIRED
                ),
            ),
        )
    return GovernanceResult.require_approval(
        rule_name=rule_name,
        message=(
            "Governance requires approval for Vigilant authority output. This "
            "result does not record human approval or residual-risk acceptance."
        ),
        reason="vigilant_authority_requires_approval",
        metadata=_result_metadata(
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        ),
    )


type _AuthorityGovernanceResultBuilder = Callable[..., GovernanceResult]

_AUTHORITY_GOVERNANCE_RESULT_BY_TIER: Final[
    dict[RiskTier, _AuthorityGovernanceResultBuilder]
] = {
    RiskTier.BASELINE: _baseline_authority_result,
    RiskTier.ENHANCED: _enhanced_authority_result,
    RiskTier.VIGILANT: _vigilant_authority_result,
    RiskTier.PROHIBITED_OUTSIDE_AUTHORITY: _prohibited_authority_result,
}


def _metadata_required(context: Mapping[str, Any]) -> bool:
    value = context.get(AUTHORITY_METADATA_REQUIRED_CONTEXT_KEY)
    return isinstance(value, bool) and value


def _subject_family(
    subject: Any,
    context: Mapping[str, Any],
) -> str:
    family = context.get(AUTHORITY_SUBJECT_FAMILY_CONTEXT_KEY)
    if isinstance(family, str) and family.strip():
        return family.strip()
    return subject.__class__.__name__


def _extract_packet_support(subject: Any) -> _PacketSupportExtraction:
    packets: list[DecisionEvidencePacket] = []
    claim_references: list[EvidenceClaimReference] = []
    rejected_evidence_ids: list[str] = []

    if isinstance(subject, DecisionEvidencePacket):
        packets.append(subject)

    evidence_packet = getattr(subject, "evidence_packet", None)
    if isinstance(evidence_packet, DecisionEvidencePacket):
        packets.append(evidence_packet)

    for mapping in _packet_support_mappings(subject):
        mapping_packet = mapping.get("decision_evidence_packet") or mapping.get(
            "evidence_packet"
        )
        if isinstance(mapping_packet, DecisionEvidencePacket):
            packets.append(mapping_packet)

        raw_rejected_ids = mapping.get("rejected_evidence_ids")
        if isinstance(raw_rejected_ids, str):
            rejected_evidence_ids.append(raw_rejected_ids)
        elif isinstance(raw_rejected_ids, tuple | list | frozenset | set):
            rejected_evidence_ids.extend(
                value for value in raw_rejected_ids if isinstance(value, str)
            )

        raw_references = mapping.get(DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY)
        if raw_references is None:
            continue
        try:
            parsed = evidence_claim_references_from_metadata(raw_references)
        except DecisionEvidencePacketValidationError as exc:
            return _PacketSupportExtraction(error=str(exc))
        claim_references.extend(parsed.claim_references)

    return _PacketSupportExtraction(
        packets=tuple(dict.fromkeys(packets)),
        claim_references=tuple(dict.fromkeys(claim_references)),
        rejected_evidence_ids=tuple(dict.fromkeys(rejected_evidence_ids)),
    )


def _packet_support_mappings(subject: Any) -> tuple[Mapping[object, object], ...]:
    mappings: list[Mapping[object, object]] = []
    subject_mapping = _mapping_from_object(subject)
    if subject_mapping is not None:
        mappings.append(subject_mapping)

    metadata = getattr(subject, "metadata", None)
    metadata_mapping = _mapping_from_object(metadata)
    if metadata_mapping is not None:
        mappings.append(metadata_mapping)

    if subject_mapping is not None:
        nested_metadata = _mapping_from_object(subject_mapping.get("metadata"))
        if nested_metadata is not None:
            mappings.append(nested_metadata)

    return tuple(mappings)


def _extract_authority_metadata(subject: Any) -> _AuthorityExtraction:
    if isinstance(subject, RiskAuthorityContract):
        return _AuthorityExtraction(
            raw_authority_metadata=subject,
            metadata_source="subject",
        )

    authority = getattr(subject, "authority", None)
    if isinstance(authority, RiskAuthorityContract):
        return _AuthorityExtraction(
            raw_authority_metadata=authority,
            metadata_source="authority",
        )

    authority_contract = getattr(subject, "authority_contract", None)
    if isinstance(authority_contract, RiskAuthorityContract):
        return _AuthorityExtraction(
            raw_authority_metadata=authority_contract,
            metadata_source="authority_contract",
        )

    authority_metadata = getattr(subject, "authority_metadata", None)
    if authority_metadata is not None:
        return _AuthorityExtraction(
            raw_authority_metadata=authority_metadata,
            metadata_source="authority_metadata",
        )

    subject_mapping = _mapping_from_object(subject)
    if subject_mapping is not None:
        extracted = _extract_from_mapping(subject_mapping)
        if extracted.raw_authority_metadata is not None:
            return extracted

    metadata = getattr(subject, "metadata", None)
    metadata_mapping = _mapping_from_object(metadata)
    if metadata_mapping is None:
        return _AuthorityExtraction(raw_authority_metadata=None)
    extracted = _extract_from_mapping(
        metadata_mapping,
        prefix="metadata.",
    )
    if extracted.raw_authority_metadata is not None:
        return extracted
    return _AuthorityExtraction(raw_authority_metadata=None)


def _extract_from_mapping(
    metadata: Mapping[object, object],
    *,
    prefix: str = "",
) -> _AuthorityExtraction:
    risk_authority = metadata.get(RISK_AUTHORITY_METADATA_KEY)
    if risk_authority is not None:
        return _AuthorityExtraction(
            raw_authority_metadata=risk_authority,
            metadata_source=f"{prefix}{RISK_AUTHORITY_METADATA_KEY}",
        )

    if "risk_tier" in metadata:
        return _AuthorityExtraction(
            raw_authority_metadata=metadata,
            metadata_source=prefix[:-1] or "mapping",
        )

    nested_metadata = _mapping_from_object(metadata.get("metadata"))
    if nested_metadata is not None:
        nested = _extract_from_mapping(
            nested_metadata,
            prefix=f"{prefix}metadata.",
        )
        if nested.raw_authority_metadata is not None:
            return nested

    authority_boundary = _mapping_from_object(metadata.get("authority_boundary"))
    if authority_boundary is not None:
        boundary = _extract_from_mapping(
            authority_boundary,
            prefix=f"{prefix}authority_boundary.",
        )
        if boundary.raw_authority_metadata is not None:
            return boundary

    return _AuthorityExtraction(raw_authority_metadata=None)


def _mapping_from_object(value: object) -> Mapping[object, object] | None:
    if isinstance(value, Mapping):
        return cast(Mapping[object, object], value)
    return None


def _result_metadata(
    *,
    subject_family: str,
    metadata_source: str | None,
    contract: RiskAuthorityContract | None,
    failure_mode: AuthorityGovernanceFailureMode = AuthorityGovernanceFailureMode.NONE,
    authority_metadata_present: bool = True,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "authority_subject_family": subject_family,
        "authority_metadata_present": authority_metadata_present,
        "authority_metadata_source": metadata_source,
        "governance_authority_failure_mode": failure_mode.value,
        "approval_subsystem_claimed": False,
    }
    if contract is not None:
        metadata[RISK_AUTHORITY_METADATA_KEY] = contract.to_metadata()
    return metadata
