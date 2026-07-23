from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

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
            action=PersistenceRetentionPlanAction.RETAIN,
            reason="No retention policy exists for candidate domain.",
        )

    if not policy.enabled:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            action=PersistenceRetentionPlanAction.SKIP,
            reason="Retention policy is disabled.",
        )

    age = as_of - candidate.record_timestamp
    if age.total_seconds() < 0:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            action=PersistenceRetentionPlanAction.RETAIN,
            reason="Candidate timestamp is after the planning timestamp.",
        )

    if age < policy.retention_period.duration:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
            action=PersistenceRetentionPlanAction.RETAIN,
            reason="Candidate remains within the configured retention period.",
            retention_period=policy.retention_period,
        )

    if policy.archive_before_delete:
        return _retention_plan_candidate(
            candidate=candidate,
            policy=policy,
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
            action=PersistenceRetentionPlanAction.DELETE,
            reason="Candidate exceeds retention period and policy allows deletion.",
            retention_period=policy.retention_period,
        )

    return _retention_plan_candidate(
        candidate=candidate,
        policy=policy,
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
    action: PersistenceRetentionPlanAction,
    reason: str,
    retention_period: PersistenceRetentionPeriod | None = None,
) -> PersistenceRetentionPlanCandidate:
    metadata = (
        {
            "retention_period_days": retention_period.days,
        }
        if retention_period is not None
        else {}
    )
    return PersistenceRetentionPlanCandidate(
        candidate=candidate,
        policy=policy,
        action=action,
        reason=reason,
        dry_run=True,
        metadata=metadata,
    )


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
