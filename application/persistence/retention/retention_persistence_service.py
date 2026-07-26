from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

from core.storage.persistence.lineage import (
    JsonObject,
    JsonValue,
    clean_optional_identifier,
)
from core.storage.persistence.retention import (
    PersistenceArchiveMarkerRecord,
    PersistenceRetentionCandidateRecord,
    PersistenceRetentionPeriod,
    PersistenceRetentionPlanAction,
    PersistenceRetentionPlanCandidate,
    PersistenceRetentionPlanResult,
    PersistenceRetentionPolicyRecord,
    new_persistence_archive_marker_id,
)
from domain.authority import (
    RISK_AUTHORITY_METADATA_KEY,
    RiskAuthorityContract,
    RiskTier,
    SourceOfTruthCategory,
    validate_risk_authority_metadata,
)

DECISION_EVIDENCE_PACKET_RETENTION_METADATA_KEY = "decision_evidence_packet_retention"


@dataclass(
    frozen=True,
    slots=True,
)
class RetentionPlanningFilters:
    """
    Typed filters for dry-run retention planning.
    """

    domains: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "domains",
            _normalize_domains(
                self.domains,
            ),
        )

    def allows_domain(
        self,
        domain: str,
    ) -> bool:
        if not self.domains:
            return True
        return domain.lower() in self.domains


class RetentionPersistenceService:
    """
    Application service for dry-run persistence retention planning.

    The service evaluates typed retention policies against typed candidate
    records and returns an advisory plan. It does not archive, delete, mutate,
    persist, or schedule lifecycle actions.
    """

    async def plan_retention(
        self,
        *,
        policies: Sequence[PersistenceRetentionPolicyRecord],
        candidates: Sequence[PersistenceRetentionCandidateRecord],
        as_of: datetime,
        filters: RetentionPlanningFilters | None = None,
    ) -> PersistenceRetentionPlanResult:
        active_filters = filters or RetentionPlanningFilters()
        policy_by_domain = _policy_by_domain(
            policies,
        )
        planned_candidates = tuple(
            _plan_candidate(
                candidate=candidate,
                policy=policy_by_domain.get(
                    candidate.domain,
                ),
                as_of=as_of,
            )
            for candidate in candidates
            if active_filters.allows_domain(
                candidate.domain,
            )
        )
        return PersistenceRetentionPlanResult(
            as_of=as_of,
            candidates=planned_candidates,
            dry_run=True,
            metadata={
                "policy_count": len(
                    policies,
                ),
                "input_candidate_count": len(
                    candidates,
                ),
                "planned_candidate_count": len(
                    planned_candidates,
                ),
                "domains": active_filters.domains,
                "service": "application.persistence.retention",
            },
        )

    def build_archive_markers(
        self,
        *,
        plan: PersistenceRetentionPlanResult,
        marked_timestamp: datetime,
    ) -> tuple[PersistenceArchiveMarkerRecord, ...]:
        """
        Build advisory archive markers from dry-run archive candidates only.

        Markers are typed audit metadata for future lifecycle review. This
        method does not persist markers, archive records, delete records, or
        mutate canonical PostgreSQL records.
        """

        return tuple(
            PersistenceArchiveMarkerRecord(
                marker_id=new_persistence_archive_marker_id(
                    domain=candidate.candidate.domain,
                    record_id=candidate.candidate.record_id,
                ),
                domain=candidate.candidate.domain,
                record_id=candidate.candidate.record_id,
                record_type=candidate.candidate.record_type,
                policy_id=(
                    candidate.policy.policy_id if candidate.policy is not None else None
                ),
                marked_timestamp=marked_timestamp,
                reason=candidate.reason,
                dry_run=True,
                metadata=_archive_marker_metadata(
                    candidate=candidate,
                ),
            )
            for candidate in plan.archive_candidates
        )


def _archive_marker_metadata(
    *,
    candidate: PersistenceRetentionPlanCandidate,
) -> JsonObject:
    action = (
        candidate.action
        if isinstance(
            candidate.action,
            PersistenceRetentionPlanAction,
        )
        else PersistenceRetentionPlanAction(
            candidate.action,
        )
    )
    metadata: dict[str, JsonValue] = {
        "source_action": action.value,
        "source_plan_dry_run": candidate.dry_run,
    }
    for key, value in candidate.metadata.items():
        metadata[key] = value
    return metadata


def _policy_by_domain(
    policies: Sequence[PersistenceRetentionPolicyRecord],
) -> dict[str, PersistenceRetentionPolicyRecord]:
    policy_by_domain: dict[str, PersistenceRetentionPolicyRecord] = {}
    for policy in policies:
        if policy.domain in policy_by_domain:
            raise ValueError(f"duplicate retention policy for domain: {policy.domain}.")
        policy_by_domain[policy.domain] = policy
    return policy_by_domain


def _plan_candidate(
    *,
    candidate: PersistenceRetentionCandidateRecord,
    policy: PersistenceRetentionPolicyRecord | None,
    as_of: datetime,
) -> PersistenceRetentionPlanCandidate:
    if policy is None:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=None,
            as_of=as_of,
            action=PersistenceRetentionPlanAction.RETAIN,
            reason="No retention policy exists for candidate domain.",
        )

    if not policy.enabled:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            as_of=as_of,
            action=PersistenceRetentionPlanAction.SKIP,
            reason="Retention policy is disabled.",
        )

    age = as_of - candidate.record_timestamp
    if age.total_seconds() < 0:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            as_of=as_of,
            action=PersistenceRetentionPlanAction.RETAIN,
            reason="Candidate timestamp is after the planning timestamp.",
        )

    if age < policy.retention_period.duration:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            as_of=as_of,
            action=PersistenceRetentionPlanAction.RETAIN,
            reason="Candidate remains within the configured retention period.",
            retention_period=policy.retention_period,
        )

    if policy.archive_before_delete:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            as_of=as_of,
            action=PersistenceRetentionPlanAction.ARCHIVE,
            reason=(
                "Candidate exceeds retention period and policy requires archive before "
                "deletion."
            ),
            retention_period=policy.retention_period,
        )

    if policy.deletion_eligible:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            as_of=as_of,
            action=PersistenceRetentionPlanAction.DELETE,
            reason="Candidate exceeds retention period and policy allows deletion.",
            retention_period=policy.retention_period,
        )

    return _retention_plan_candidate(
        candidate=candidate,
        policy=policy,
        as_of=as_of,
        action=PersistenceRetentionPlanAction.RETAIN,
        reason=(
            "Candidate exceeds retention period but policy does not allow archive or "
            "deletion."
        ),
        retention_period=policy.retention_period,
    )


def _retention_plan_candidate(
    *,
    candidate: PersistenceRetentionCandidateRecord,
    policy: PersistenceRetentionPolicyRecord | None,
    as_of: datetime,
    action: PersistenceRetentionPlanAction,
    reason: str,
    retention_period: PersistenceRetentionPeriod | None = None,
) -> PersistenceRetentionPlanCandidate:
    authority_assessment = _assess_candidate_authority_metadata(
        candidate,
    )
    planned_action = action
    planned_reason = reason
    if authority_assessment.action_override is not None:
        planned_action = authority_assessment.action_override
        planned_reason = authority_assessment.reason_override or planned_reason
    elif _canonical_authority_metadata_missing_for_boundary(
        action=planned_action,
        contract=authority_assessment.contract,
    ):
        planned_action = PersistenceRetentionPlanAction.SKIP
        planned_reason = (
            "Retention skipped because canonical risk authority metadata is "
            "missing for an archive/delete boundary."
        )
    elif _canonical_authority_blocks_delete(
        action=planned_action,
        contract=authority_assessment.contract,
    ):
        planned_action = PersistenceRetentionPlanAction.RETAIN
        planned_reason = (
            "Candidate exceeds retention period, but canonical risk authority "
            "metadata blocks deletion without archive-before-delete policy."
        )

    reconstruction_assessment = _assess_decision_evidence_packet_retention(
        candidate=candidate,
        action=planned_action,
        as_of=as_of,
    )
    if reconstruction_assessment.action_override is not None:
        planned_action = reconstruction_assessment.action_override
        planned_reason = reconstruction_assessment.reason_override or planned_reason

    metadata: dict[str, JsonValue] = (
        {
            "retention_period_days": retention_period.days,
        }
        if retention_period is not None
        else {}
    )
    metadata.update(
        authority_assessment.metadata,
    )
    metadata.update(
        reconstruction_assessment.metadata,
    )
    return PersistenceRetentionPlanCandidate(
        candidate=candidate,
        policy=policy,
        action=planned_action,
        reason=planned_reason,
        dry_run=True,
        metadata=metadata,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class _RetentionAuthorityAssessment:
    contract: RiskAuthorityContract | None = None
    action_override: PersistenceRetentionPlanAction | None = None
    reason_override: str | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(
    frozen=True,
    slots=True,
)
class _DecisionEvidencePacketRetentionAssessment:
    action_override: PersistenceRetentionPlanAction | None = None
    reason_override: str | None = None
    metadata: JsonObject = field(default_factory=dict)


def _assess_candidate_authority_metadata(
    candidate: PersistenceRetentionCandidateRecord,
) -> _RetentionAuthorityAssessment:
    raw_authority_metadata = candidate.metadata.get(
        RISK_AUTHORITY_METADATA_KEY,
    )
    if raw_authority_metadata is None:
        return _RetentionAuthorityAssessment(
            metadata={
                "risk_authority_metadata_status": "missing",
            },
        )

    try:
        validation = validate_risk_authority_metadata(
            raw_authority_metadata,
        )
    except ValueError as exc:
        return _RetentionAuthorityAssessment(
            action_override=PersistenceRetentionPlanAction.SKIP,
            reason_override=(
                "Retention skipped because canonical risk authority metadata "
                "is malformed."
            ),
            metadata={
                "risk_authority_metadata_status": "malformed",
                "risk_authority_metadata_error": str(
                    exc,
                ),
            },
        )

    contract = validation.contract
    if not validation.platform_consistent:
        return _RetentionAuthorityAssessment(
            contract=contract,
            action_override=PersistenceRetentionPlanAction.SKIP,
            reason_override=(
                "Retention skipped because canonical risk authority metadata "
                "does not match the platform classifier."
            ),
            metadata={
                **_authority_contract_metadata(
                    contract,
                    status="inconsistent",
                ),
                "expected_risk_authority_risk_tier": (
                    validation.expected_contract.risk_tier.value
                ),
                "expected_risk_authority_gate_profile": (
                    validation.expected_contract.gate_profile.value
                ),
            },
        )

    if validation.selected_profile.prohibits_boundary:
        return _RetentionAuthorityAssessment(
            contract=contract,
            action_override=PersistenceRetentionPlanAction.SKIP,
            reason_override=(
                "Retention skipped because canonical risk authority metadata "
                "marks the candidate as Prohibited / Outside Authority."
            ),
            metadata=_authority_contract_metadata(
                contract,
                status="prohibited_outside_authority",
            ),
        )

    return _RetentionAuthorityAssessment(
        contract=contract,
        metadata=_authority_contract_metadata(
            contract,
            status="valid",
        ),
    )


def _assess_decision_evidence_packet_retention(
    *,
    candidate: PersistenceRetentionCandidateRecord,
    action: PersistenceRetentionPlanAction,
    as_of: datetime,
) -> _DecisionEvidencePacketRetentionAssessment:
    raw_retention_metadata = candidate.metadata.get(
        DECISION_EVIDENCE_PACKET_RETENTION_METADATA_KEY,
    )
    if raw_retention_metadata is None:
        return _DecisionEvidencePacketRetentionAssessment()

    if not isinstance(raw_retention_metadata, Mapping):
        return _DecisionEvidencePacketRetentionAssessment(
            action_override=_retention_boundary_skip_action(action),
            reason_override=_retention_boundary_skip_reason(action),
            metadata={
                "decision_evidence_packet_retention_status": "malformed",
                "decision_evidence_packet_retention_error": (
                    "decision evidence packet retention metadata must be an object."
                ),
            },
        )

    try:
        packet_metadata = _decision_evidence_packet_retention_metadata(
            raw_retention_metadata,
            as_of=as_of,
        )
    except ValueError as exc:
        return _DecisionEvidencePacketRetentionAssessment(
            action_override=_retention_boundary_skip_action(action),
            reason_override=_retention_boundary_skip_reason(action),
            metadata={
                "decision_evidence_packet_retention_status": "malformed",
                "decision_evidence_packet_retention_error": str(exc),
            },
        )

    if action not in (
        PersistenceRetentionPlanAction.ARCHIVE,
        PersistenceRetentionPlanAction.DELETE,
    ):
        return _DecisionEvidencePacketRetentionAssessment(
            metadata=packet_metadata,
        )

    if packet_metadata["decision_evidence_packet_legal_hold"] is True:
        return _DecisionEvidencePacketRetentionAssessment(
            action_override=PersistenceRetentionPlanAction.RETAIN,
            reason_override=(
                "Candidate is under legal hold for decision evidence packet "
                "reconstruction."
            ),
            metadata=packet_metadata,
        )

    if packet_metadata["decision_evidence_packet_retention_status"] == "active":
        return _DecisionEvidencePacketRetentionAssessment(
            action_override=PersistenceRetentionPlanAction.RETAIN,
            reason_override=(
                "Candidate is required for decision evidence packet reconstruction "
                f"until {packet_metadata['decision_evidence_packet_retain_until']}."
            ),
            metadata=packet_metadata,
        )

    return _DecisionEvidencePacketRetentionAssessment(
        metadata=packet_metadata,
    )


def _retention_boundary_skip_action(
    action: PersistenceRetentionPlanAction,
) -> PersistenceRetentionPlanAction | None:
    if action in (
        PersistenceRetentionPlanAction.ARCHIVE,
        PersistenceRetentionPlanAction.DELETE,
    ):
        return PersistenceRetentionPlanAction.SKIP
    return None


def _retention_boundary_skip_reason(
    action: PersistenceRetentionPlanAction,
) -> str | None:
    if _retention_boundary_skip_action(action) is None:
        return None
    return (
        "Retention skipped because decision evidence packet retention metadata "
        "is malformed for an archive/delete boundary."
    )


def _decision_evidence_packet_retention_metadata(
    values: Mapping[str, JsonValue],
    *,
    as_of: datetime,
) -> JsonObject:
    packet_id = _required_packet_retention_string(values, "packet_id")
    retain_until = _required_packet_retention_string(values, "retain_until")
    policy_id = _required_packet_retention_string(values, "policy_id")
    risk_tier = _required_packet_retention_string(values, "risk_tier")
    legal_hold = _optional_packet_retention_bool(
        values,
        "legal_hold",
        default=False,
    )
    authority_boundary = _required_packet_retention_mapping(
        values,
        "authority_boundary",
    )
    boundary_metadata = {
        "canonical_owner": _required_packet_retention_string(
            authority_boundary,
            "canonical_owner",
        ),
        "source_of_truth": _required_packet_retention_string(
            authority_boundary,
            "source_of_truth",
        ),
        "intended_sink": _required_packet_retention_string(
            authority_boundary,
            "intended_sink",
        ),
        "gate_profile": _required_packet_retention_string(
            authority_boundary,
            "gate_profile",
        ),
    }
    retain_until_timestamp = _parse_packet_retention_timestamp(retain_until)
    planning_timestamp = _aware_utc(as_of)
    status = "expired"
    if legal_hold:
        status = "legal_hold"
    elif retain_until_timestamp >= planning_timestamp:
        status = "active"

    return {
        "decision_evidence_packet_retention_status": status,
        "decision_evidence_packet_id": packet_id,
        "decision_evidence_packet_retain_until": retain_until,
        "decision_evidence_packet_policy_id": policy_id,
        "decision_evidence_packet_legal_hold": legal_hold,
        "decision_evidence_packet_risk_tier": risk_tier,
        "decision_evidence_packet_authority_boundary": cast(
            JsonValue,
            boundary_metadata,
        ),
    }


def _required_packet_retention_string(
    values: Mapping[str, JsonValue],
    key: str,
) -> str:
    value = values.get(key)
    if not isinstance(value, str):
        raise ValueError(
            f"decision evidence packet retention metadata field {key!r} must be "
            "a string."
        )
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(
            f"decision evidence packet retention metadata field {key!r} cannot "
            "be empty."
        )
    return cleaned


def _optional_packet_retention_bool(
    values: Mapping[str, JsonValue],
    key: str,
    *,
    default: bool,
) -> bool:
    value = values.get(key, default)
    if isinstance(value, bool):
        return value
    raise ValueError(
        f"decision evidence packet retention metadata field {key!r} must be a boolean."
    )


def _required_packet_retention_mapping(
    values: Mapping[str, JsonValue],
    key: str,
) -> Mapping[str, JsonValue]:
    value = values.get(key)
    if isinstance(value, Mapping):
        return value
    raise ValueError(
        f"decision evidence packet retention metadata field {key!r} must be an object."
    )


def _parse_packet_retention_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            "decision evidence packet retention metadata field 'retain_until' "
            "must be an ISO-8601 timestamp."
        ) from exc
    return _aware_utc(parsed)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _canonical_authority_metadata_missing_for_boundary(
    *,
    action: PersistenceRetentionPlanAction,
    contract: RiskAuthorityContract | None,
) -> bool:
    return contract is None and action in (
        PersistenceRetentionPlanAction.ARCHIVE,
        PersistenceRetentionPlanAction.DELETE,
    )


def _canonical_authority_blocks_delete(
    *,
    action: PersistenceRetentionPlanAction,
    contract: RiskAuthorityContract | None,
) -> bool:
    if action is not PersistenceRetentionPlanAction.DELETE or contract is None:
        return False
    return (
        contract.risk_tier is RiskTier.VIGILANT
        or contract.durable_authority
        or contract.source_of_truth is SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD
    )


def _authority_contract_metadata(
    contract: RiskAuthorityContract,
    *,
    status: str,
) -> JsonObject:
    profile = validate_risk_authority_metadata(
        contract,
    ).selected_profile
    return {
        "risk_authority_metadata_status": status,
        "risk_authority": cast(
            JsonValue,
            contract.to_metadata(),
        ),
        "risk_authority_risk_tier": contract.risk_tier.value,
        "risk_authority_canonical_owner": contract.canonical_owner.value,
        "risk_authority_source_of_truth": contract.source_of_truth.value,
        "risk_authority_intended_sink": contract.intended_sink.value,
        "risk_authority_gate_profile": contract.gate_profile.value,
        "risk_authority_requires_provenance_evidence": (
            profile.requires_provenance_evidence
        ),
        "risk_authority_requires_decision_evidence": (
            profile.requires_decision_evidence
        ),
        "risk_authority_prohibits_boundary": profile.prohibits_boundary,
    }


def _normalize_domains(
    domains: Sequence[str],
) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for index, domain in enumerate(
        domains,
    ):
        cleaned = clean_optional_identifier(
            domain,
            f"domains[{index}]",
        )
        if cleaned is None:
            raise ValueError(f"domains[{index}] cannot be empty.")
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(
            lowered,
        )
        normalized.append(
            lowered,
        )
    return tuple(
        normalized,
    )
