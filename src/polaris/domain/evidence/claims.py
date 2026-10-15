from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .judgments import ClaimId, EvidenceJudgmentRef, is_evidence_judgment_ref


class InvalidClaimCatalog(ValueError):
    pass


class ContestedClaimCatalogHistory(InvalidClaimCatalog):
    pass


class InvalidClaimCatalogHistory(InvalidClaimCatalog):
    pass


@dataclass(frozen=True, slots=True)
class ClaimCatalogVersion:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise InvalidClaimCatalog("ClaimCatalogVersion.value must be positive")


@dataclass(frozen=True, slots=True)
class ClaimCatalogRevision:
    """One complete target-owned claim catalog at a committed version."""

    target: EvidenceJudgmentRef
    version: ClaimCatalogVersion
    claim_ids: frozenset[ClaimId]
    effective_at: datetime
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not is_evidence_judgment_ref(self.target):
            raise TypeError("target must be an EvidenceJudgmentRef")
        if type(self.version) is not ClaimCatalogVersion:
            raise TypeError("version must be ClaimCatalogVersion")
        if type(self.claim_ids) is not frozenset or any(
            type(claim_id) is not ClaimId for claim_id in self.claim_ids
        ):
            raise TypeError("claim_ids must be a frozenset of ClaimId")
        _aware(self.effective_at, "ClaimCatalogRevision.effective_at")
        _aware(self.recorded_at, "ClaimCatalogRevision.recorded_at")


@dataclass(frozen=True, slots=True)
class ClaimCatalog:
    """Reusable history mechanics embedded and persisted by a target owner."""

    revisions: tuple[ClaimCatalogRevision, ...]

    def __post_init__(self) -> None:
        validate_claim_catalog_history(self.revisions)

    @classmethod
    def form(
        cls,
        target: EvidenceJudgmentRef,
        claim_ids: tuple[ClaimId, ...],
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        members = _fresh_members(claim_ids, frozenset())
        return cls(
            (
                ClaimCatalogRevision(
                    target=target,
                    version=ClaimCatalogVersion(1),
                    claim_ids=members,
                    effective_at=effective_at,
                    recorded_at=recorded_at,
                ),
            )
        )

    @property
    def current(self) -> ClaimCatalogRevision:
        return self.revisions[-1]

    def declare_claim(
        self,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        # duplicate-code: declaration and material replacement are distinct
        # target-owner operations; their shared freshness policy already lives
        # in _append_fresh, so extracting this argument mapping adds no owner.
        # arid: disable
        return self._append_fresh(
            (claim_id,),
            self.current.claim_ids,
            effective_at=effective_at,
            recorded_at=recorded_at,
        )
        # arid: enable

    def correct_same_proposition(
        self,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        # duplicate-code: correction and retraction have different identity and
        # membership semantics; only their centralized append invocation matches.
        # arid: disable
        self._require_current(claim_id)
        return self._append(
            self.current.claim_ids,
            effective_at=effective_at,
            recorded_at=recorded_at,
        )
        # arid: enable

    def replace_material_proposition(
        self,
        claim_id: ClaimId,
        replacement_id: ClaimId,
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        # duplicate-code: declaration and material replacement are distinct
        # target-owner operations; their shared freshness policy already lives
        # in _append_fresh, so extracting this argument mapping adds no owner.
        # arid: disable
        self._require_current(claim_id)
        return self._append_fresh(
            (replacement_id,),
            self.current.claim_ids - {claim_id},
            effective_at=effective_at,
            recorded_at=recorded_at,
        )
        # arid: enable

    def retract_claim(
        self,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        # duplicate-code: correction and retraction have different identity and
        # membership semantics; only their centralized append invocation matches.
        # arid: disable
        self._require_current(claim_id)
        return self._append(
            self.current.claim_ids - {claim_id},
            effective_at=effective_at,
            recorded_at=recorded_at,
        )
        # arid: enable

    def start_new_root(
        self,
        target: EvidenceJudgmentRef,
        claim_ids: tuple[ClaimId, ...],
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        if target == self.current.target:
            raise InvalidClaimCatalog(
                "a new target root must have a new typed identity"
            )
        _fresh_members(claim_ids, self._all_claim_ids())
        return ClaimCatalog.form(
            target,
            claim_ids,
            effective_at=effective_at,
            recorded_at=recorded_at,
        )

    def _append(
        self,
        claim_ids: frozenset[ClaimId],
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        if recorded_at < self.current.recorded_at:
            raise InvalidClaimCatalog(
                "claim catalog recording time cannot precede its prior version"
            )
        revision = ClaimCatalogRevision(
            target=self.current.target,
            version=ClaimCatalogVersion(self.current.version.value + 1),
            claim_ids=claim_ids,
            effective_at=effective_at,
            recorded_at=recorded_at,
        )
        return ClaimCatalog((*self.revisions, revision))

    def _append_fresh(
        self,
        claim_ids: tuple[ClaimId, ...],
        current_claim_ids: frozenset[ClaimId],
        *,
        effective_at: datetime,
        recorded_at: datetime,
    ) -> ClaimCatalog:
        members = _fresh_members(claim_ids, self._all_claim_ids())
        return self._append(
            current_claim_ids | members,
            effective_at=effective_at,
            recorded_at=recorded_at,
        )

    def _all_claim_ids(self) -> frozenset[ClaimId]:
        return frozenset(
            claim_id for revision in self.revisions for claim_id in revision.claim_ids
        )

    def _require_current(self, claim_id: ClaimId) -> None:
        if type(claim_id) is not ClaimId:
            raise TypeError("claim_id must be ClaimId")
        if claim_id not in self.current.claim_ids:
            raise InvalidClaimCatalog("claim_id must be current in this target catalog")


def validate_claim_catalog_history(
    revisions: tuple[ClaimCatalogRevision, ...],
    *,
    target: EvidenceJudgmentRef | None = None,
) -> None:
    if not revisions:
        raise InvalidClaimCatalogHistory("claim catalog history must not be empty")
    if target is not None and not is_evidence_judgment_ref(target):
        raise TypeError("target must be an EvidenceJudgmentRef or None")

    expected_target = revisions[0].target if target is None else target
    by_version: dict[int, ClaimCatalogRevision] = {}
    for revision in revisions:
        if type(revision) is not ClaimCatalogRevision:
            raise TypeError("revisions must contain ClaimCatalogRevision")
        if revision.target != expected_target:
            raise InvalidClaimCatalogHistory(
                "claim catalog history must belong to one typed target"
            )
        version = revision.version.value
        if version in by_version:
            raise ContestedClaimCatalogHistory(
                f"claim catalog version {version} has competing revisions"
            )
        by_version[version] = revision

    expected_versions = tuple(range(1, len(revisions) + 1))
    if tuple(sorted(by_version)) != expected_versions:
        raise InvalidClaimCatalogHistory(
            "claim catalog versions must be complete and contiguous from 1"
        )
    if tuple(revision.version.value for revision in revisions) != expected_versions:
        raise InvalidClaimCatalogHistory(
            "claim catalog revisions must be ordered by version"
        )
    ordered = tuple(by_version[version] for version in expected_versions)
    if any(
        current.recorded_at < previous.recorded_at
        for previous, current in zip(ordered, ordered[1:], strict=False)
    ):
        raise InvalidClaimCatalogHistory(
            "claim catalog recording time must follow version order"
        )


def _fresh_members(
    claim_ids: tuple[ClaimId, ...],
    prior_claim_ids: frozenset[ClaimId],
) -> frozenset[ClaimId]:
    if any(type(claim_id) is not ClaimId for claim_id in claim_ids):
        raise TypeError("claim_ids must contain ClaimId")
    members = frozenset(claim_ids)
    if len(members) != len(claim_ids):
        raise InvalidClaimCatalog("claim_ids must be distinct")
    if members & prior_claim_ids:
        raise InvalidClaimCatalog(
            "new propositions and target roots require fresh ClaimId values"
        )
    return members


# duplicate-code: target-owned claim validation raises InvalidClaimCatalog;
# sharing another domain/application time validator would erase that contract.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidClaimCatalog(f"{field} must be timezone-aware")


# arid: enable
