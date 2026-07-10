from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from enum import Enum

from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import JsonValue
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRetentionPeriod:
    """
    Typed retention duration for persisted platform records.

    Retention policy storage can persist the day count, while internal callers
    work with a typed duration contract instead of an unlabelled integer.
    """

    days: int

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.days,
                bool,
            )
            or self.days <= 0
        ):
            raise ValueError("retention period days must be positive.")

    @property
    def duration(
        self,
    ) -> timedelta:
        return timedelta(
            days=self.days,
        )

    def as_dict(
        self,
    ) -> dict[str, int]:
        return {
            "days": self.days,
            "seconds": int(
                self.duration.total_seconds(),
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRetentionPolicyRecord:
    """
    Typed retention policy for one persistence domain.

    These contracts describe lifecycle policy only. They do not archive, delete,
    mutate, or physically remove canonical PostgreSQL records.
    """

    policy_id: str
    domain: str
    retention_period: PersistenceRetentionPeriod
    archive_before_delete: bool
    deletion_eligible: bool
    enabled: bool = True
    description: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "policy_id",
            require_non_empty_identifier(
                self.policy_id,
                "policy_id",
            ),
        )
        object.__setattr__(
            self,
            "domain",
            require_non_empty_identifier(
                self.domain,
                "domain",
            ).lower(),
        )
        if not isinstance(
            self.retention_period,
            PersistenceRetentionPeriod,
        ):
            raise TypeError("retention_period must be a PersistenceRetentionPeriod.")
        object.__setattr__(
            self,
            "description",
            clean_optional_identifier(
                self.description,
                "description",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def can_archive(
        self,
    ) -> bool:
        return self.enabled and self.archive_before_delete

    @property
    def can_delete(
        self,
    ) -> bool:
        return self.enabled and self.deletion_eligible

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {
            "policy_id": self.policy_id,
            "domain": self.domain,
            "retention_period": self.retention_period.as_dict(),
            "archive_before_delete": self.archive_before_delete,
            "deletion_eligible": self.deletion_eligible,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }
        if self.description is not None:
            result["description"] = self.description
        return result


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRetentionCandidateRecord:
    """
    Typed persisted-record candidate for dry-run retention planning.

    The timestamp represents the domain timestamp used for retention age
    evaluation, such as generated, published, observed, or created time.
    """

    domain: str
    record_id: str
    record_timestamp: datetime
    record_type: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "domain",
            require_non_empty_identifier(
                self.domain,
                "domain",
            ).lower(),
        )
        object.__setattr__(
            self,
            "record_id",
            require_non_empty_identifier(
                self.record_id,
                "record_id",
            ),
        )
        object.__setattr__(
            self,
            "record_type",
            clean_optional_identifier(
                self.record_type,
                "record_type",
            ),
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {
            "domain": self.domain,
            "record_id": self.record_id,
            "record_timestamp": self.record_timestamp.isoformat(),
            "metadata": self.metadata,
        }
        if self.record_type is not None:
            result["record_type"] = self.record_type
        return result


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceArchiveMarkerRecord:
    """
    Typed advisory marker for records selected for future archive handling.

    Archive markers are metadata/audit payloads only. They do not archive,
    delete, mutate, or physically remove canonical PostgreSQL records.
    """

    marker_id: str
    domain: str
    record_id: str
    marked_timestamp: datetime
    reason: str
    record_type: str | None = None
    policy_id: str | None = None
    dry_run: bool = True
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "marker_id",
            require_non_empty_identifier(
                self.marker_id,
                "marker_id",
            ),
        )
        object.__setattr__(
            self,
            "domain",
            require_non_empty_identifier(
                self.domain,
                "domain",
            ).lower(),
        )
        object.__setattr__(
            self,
            "record_id",
            require_non_empty_identifier(
                self.record_id,
                "record_id",
            ),
        )
        object.__setattr__(
            self,
            "reason",
            require_non_empty_identifier(
                self.reason,
                "reason",
            ),
        )
        object.__setattr__(
            self,
            "record_type",
            clean_optional_identifier(
                self.record_type,
                "record_type",
            ),
        )
        object.__setattr__(
            self,
            "policy_id",
            clean_optional_identifier(
                self.policy_id,
                "policy_id",
            ),
        )
        if not self.dry_run:
            raise ValueError("archive marker records must be dry-run only in V3.")
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def audit_metadata(
        self,
    ) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {
            "archive_marker_id": self.marker_id,
            "domain": self.domain,
            "record_id": self.record_id,
            "marked_timestamp": self.marked_timestamp.isoformat(),
            "reason": self.reason,
            "dry_run": self.dry_run,
            "marker_type": "persistence_archive_marker",
            "metadata": self.metadata,
        }
        if self.record_type is not None:
            result["record_type"] = self.record_type
        if self.policy_id is not None:
            result["policy_id"] = self.policy_id
        return result

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        result = dict(
            self.audit_metadata,
        )
        result["marker_id"] = self.marker_id
        return result


class PersistenceRetentionPlanAction(str, Enum):
    """
    Dry-run lifecycle actions reported by retention planning.
    """

    RETAIN = "retain"
    ARCHIVE = "archive"
    DELETE = "delete"
    SKIP = "skip"


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRetentionPlanCandidate:
    """
    Dry-run planning decision for one candidate record.
    """

    candidate: PersistenceRetentionCandidateRecord
    action: PersistenceRetentionPlanAction | str
    reason: str
    policy: PersistenceRetentionPolicyRecord | None = None
    dry_run: bool = True
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "action",
            _coerce_retention_action(
                self.action,
            ),
        )
        object.__setattr__(
            self,
            "reason",
            require_non_empty_identifier(
                self.reason,
                "reason",
            ),
        )
        if self.policy is not None and not isinstance(
            self.policy,
            PersistenceRetentionPolicyRecord,
        ):
            raise TypeError("policy must be a PersistenceRetentionPolicyRecord.")
        if not self.dry_run:
            raise ValueError("retention planning candidates must be dry-run only.")
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def is_archive_candidate(
        self,
    ) -> bool:
        return self.action is PersistenceRetentionPlanAction.ARCHIVE

    @property
    def is_delete_candidate(
        self,
    ) -> bool:
        return self.action is PersistenceRetentionPlanAction.DELETE

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        action = _coerce_retention_action(
            self.action,
        )
        result: dict[str, JsonValue] = {
            "candidate": self.candidate.as_dict(),
            "action": action.value,
            "reason": self.reason,
            "dry_run": self.dry_run,
            "metadata": self.metadata,
        }
        if self.policy is not None:
            result["policy"] = self.policy.as_dict()
        return result


@dataclass(
    frozen=True,
    slots=True,
)
class PersistenceRetentionPlanResult:
    """
    Dry-run retention plan result.

    This result is advisory only and never represents executed archive/delete
    operations.
    """

    as_of: datetime
    candidates: tuple[PersistenceRetentionPlanCandidate, ...]
    dry_run: bool = True
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "candidates",
            tuple(
                self.candidates,
            ),
        )
        if not self.dry_run:
            raise ValueError("retention planning results must be dry-run only.")
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def archive_candidates(
        self,
    ) -> tuple[PersistenceRetentionPlanCandidate, ...]:
        return tuple(
            candidate for candidate in self.candidates if candidate.is_archive_candidate
        )

    @property
    def delete_candidates(
        self,
    ) -> tuple[PersistenceRetentionPlanCandidate, ...]:
        return tuple(
            candidate for candidate in self.candidates if candidate.is_delete_candidate
        )

    @property
    def retained_candidates(
        self,
    ) -> tuple[PersistenceRetentionPlanCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.candidates
            if candidate.action is PersistenceRetentionPlanAction.RETAIN
        )

    @property
    def skipped_candidates(
        self,
    ) -> tuple[PersistenceRetentionPlanCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.candidates
            if candidate.action is PersistenceRetentionPlanAction.SKIP
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "as_of": self.as_of.isoformat(),
            "dry_run": self.dry_run,
            "candidate_count": len(
                self.candidates,
            ),
            "archive_candidate_count": len(
                self.archive_candidates,
            ),
            "delete_candidate_count": len(
                self.delete_candidates,
            ),
            "retained_candidate_count": len(
                self.retained_candidates,
            ),
            "skipped_candidate_count": len(
                self.skipped_candidates,
            ),
            "candidates": tuple(candidate.as_dict() for candidate in self.candidates),
            "metadata": self.metadata,
        }


def new_persistence_retention_policy_id(
    *,
    domain: str,
) -> str:
    return (
        "persistence_retention_policy:"
        + require_non_empty_identifier(
            domain,
            "domain",
        ).lower()
    )


def new_persistence_archive_marker_id(
    *,
    domain: str,
    record_id: str,
) -> str:
    normalized_domain = require_non_empty_identifier(
        domain,
        "domain",
    ).lower()
    normalized_record_id = require_non_empty_identifier(
        record_id,
        "record_id",
    )
    return f"persistence_archive_marker:{normalized_domain}:{normalized_record_id}"


def _coerce_retention_action(
    action: PersistenceRetentionPlanAction | str,
) -> PersistenceRetentionPlanAction:
    if isinstance(
        action,
        PersistenceRetentionPlanAction,
    ):
        return action

    normalized = action.strip().lower()
    try:
        return PersistenceRetentionPlanAction(
            normalized,
        )
    except ValueError as exc:
        raise ValueError(
            "retention plan action must be one of: retain, archive, delete, skip."
        ) from exc
