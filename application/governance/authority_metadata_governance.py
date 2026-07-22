from __future__ import annotations

from collections.abc import Mapping
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
    reclassify_risk_authority_contract,
    risk_authority_contract_from_metadata,
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
            contract = _coerce_authority_contract(extraction.raw_authority_metadata)
        except ValueError as exc:
            return _malformed_authority_result(
                rule_name=self.rule_name,
                subject_family=subject_family,
                metadata_source=extraction.metadata_source,
                error=exc,
            )

        expected_contract = reclassify_risk_authority_contract(contract)
        if _authority_profile_is_inconsistent(contract, expected_contract):
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


def _authority_profile_is_inconsistent(
    contract: RiskAuthorityContract,
    expected_contract: RiskAuthorityContract,
) -> bool:
    return (
        contract.risk_tier is not expected_contract.risk_tier
        or contract.gate_profile is not expected_contract.gate_profile
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
) -> GovernanceResult:
    if contract.ignored_model_authority_claims:
        return _ignored_model_claims_result(
            rule_name=rule_name,
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        )
    if contract.risk_tier is RiskTier.PROHIBITED_OUTSIDE_AUTHORITY:
        return _prohibited_authority_result(
            rule_name=rule_name,
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        )
    if contract.risk_tier is RiskTier.BASELINE:
        return _baseline_authority_result(
            rule_name=rule_name,
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        )
    if contract.risk_tier is RiskTier.ENHANCED:
        return _enhanced_authority_result(
            rule_name=rule_name,
            subject_family=subject_family,
            metadata_source=metadata_source,
            contract=contract,
        )
    return _vigilant_authority_result(
        rule_name=rule_name,
        subject_family=subject_family,
        metadata_source=metadata_source,
        contract=contract,
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


def _coerce_authority_contract(raw_authority_metadata: object) -> RiskAuthorityContract:
    if isinstance(raw_authority_metadata, RiskAuthorityContract):
        return raw_authority_metadata
    if not isinstance(raw_authority_metadata, Mapping):
        raise ValueError("risk_authority must be a metadata object.")
    return risk_authority_contract_from_metadata(
        cast(Mapping[str, object], raw_authority_metadata),
    )


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
