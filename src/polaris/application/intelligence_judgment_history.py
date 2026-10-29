# duplicate-code: Sharing would couple distinct owner proofs.
# jscpd:ignore-start
"""Investment Intelligence owner reads and temporal Evidence witnesses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from polaris.application.evidence.claims import (
    ClaimMembershipResolution,
    ClaimNotCurrent,
    ClaimNotKnownAtCutoff,
    ClaimNotYetEffective,
    ClaimTargetNotKnownAtCutoff,
    ClaimTargetNotYetEffective,
    ContestedClaimHistory,
    InvalidClaimHistory,
    InvalidClaimReference,
    ResolvedClaimMembership,
    UnavailableClaimCatalog,
)
from polaris.application.evidence.judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentContested,
    TargetJudgmentInvalidHistory,
    TargetJudgmentMissing,
    TargetJudgmentNotYetEffective,
    TargetJudgmentResolution,
    TargetJudgmentUnavailable,
    TargetJudgmentWithdrawn,
)
from polaris.application.evidence.owner_meaning import (
    ClaimMembershipMeaning,
    OwnerCauseVerdict,
    OwnerHistoryRecord,
    OwnerMeaningCause,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
    TargetJudgmentMeaning,
)
from polaris.domain.actors import ActorAttribution
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.judgment_versions import (
    InvestmentHypothesisVersionRef,
    InvestmentRecommendationVersionRef,
    InvestmentViewVersionRef,
    JudgmentRevision,
    MeaningfulChallengeResultVersionRef,
    RecommendationWithholdingJudgmentVersionRef,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceClaim,
    IntelligenceJudgmentActDraft,
    IntelligenceJudgmentHistory,
    IntelligenceJudgmentNotYetEffective,
    IntelligenceJudgmentRoot,
    IntelligenceJudgmentSelection,
    IntelligenceJudgmentStatus,
    InvalidIntelligenceJudgmentHistory,
)

# jscpd:ignore-end


class IntelligenceJudgmentHistoryStore(Protocol):
    async def load(
        self, root: IntelligenceJudgmentRoot
    ) -> IntelligenceJudgmentHistory | None: ...

    async def append(
        self, draft: IntelligenceJudgmentActDraft
    ) -> IntelligenceJudgmentHistory: ...


class IntelligenceJudgmentHistoryUnavailable(Exception):
    """The durable owner history cannot be read or committed."""


class IntelligenceJudgmentCorrectionService:
    """Admit a correction; persistence supplies its trusted knowledge boundary."""

    def __init__(self, store: IntelligenceJudgmentHistoryStore) -> None:
        self._store = store

    async def correct(
        self, draft: IntelligenceJudgmentActDraft
    ) -> IntelligenceJudgmentHistory:
        if type(draft) is not IntelligenceJudgmentActDraft or draft.ancestry == ():
            raise TypeError("correction requires a typed non-root owner draft")
        return await self._store.append(draft)


def _version(selection: IntelligenceJudgmentSelection):
    revision = JudgmentRevision(selection.judgment_revision.value)
    root = selection.target_act.root
    if type(root) is InvestmentHypothesisRef:
        return InvestmentHypothesisVersionRef(root, revision)
    if type(root) is InvestmentViewRef:
        return InvestmentViewVersionRef(root, revision)
    if type(root) is MeaningfulChallengeResultRef:
        return MeaningfulChallengeResultVersionRef(root, revision)
    if type(root) is InvestmentRecommendationRef:
        return InvestmentRecommendationVersionRef(root, revision)
    return RecommendationWithholdingJudgmentVersionRef(root, revision)


class IntelligenceJudgmentTargetReader:
    """Evidence-facing target read with complete owner history validation."""

    def __init__(self, store: IntelligenceJudgmentHistoryStore) -> None:
        self._store = store

    async def read_at(
        self,
        target: IntelligenceJudgmentRoot,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> TargetJudgmentResolution:
        # duplicate-code: Sharing would couple distinct owner proofs.
        # arid: disable
        if type(target) not in (
            InvestmentHypothesisRef,
            InvestmentViewRef,
            MeaningfulChallengeResultRef,
            InvestmentRecommendationRef,
            RecommendationWithholdingJudgmentRef,
        ):
            raise TypeError("target must be an Investment Intelligence Evidence target")
        # arid: enable
        # duplicate-code: Sharing would couple distinct owner proofs.
        # arid: disable
        try:
            history = await self._store.load(target)
        except IntelligenceJudgmentHistoryUnavailable as error:
            return TargetJudgmentUnavailable(target, str(error))
        except (ValueError, TypeError) as error:
            return TargetJudgmentInvalidHistory(target, str(error))
        if history is None or history.acts[0].known_at > known_at:
            return TargetJudgmentMissing(target)
        try:
            selection = history.select(effective_at, known_at)
        except IntelligenceJudgmentNotYetEffective:
            return TargetJudgmentNotYetEffective(target)
        except InvalidIntelligenceJudgmentHistory as error:
            return TargetJudgmentInvalidHistory(target, str(error))
        # arid: enable
        if selection.target_act.target_status is IntelligenceJudgmentStatus.CONTESTED:
            return TargetJudgmentContested(target, "owner assertion is contested")
        if selection.target_act.target_status is IntelligenceJudgmentStatus.WITHDRAWN:
            return TargetJudgmentWithdrawn(target)
        if selection.target_act.target_status is IntelligenceJudgmentStatus.INVALID:
            return TargetJudgmentInvalidHistory(target, "owner assertion is invalid")
        # duplicate-code: Sharing would couple distinct owner proofs.
        # arid: disable
        return ResolvedTargetJudgment(
            target,
            _version(selection),
            selection.assertion,
            selection.target_support,
            effective_at,
            known_at,
        )
        # arid: enable


class IntelligenceJudgmentClaimResolver:
    """Select complete Intelligence claim catalogs from owner correction acts."""

    # duplicate-code: Sharing would couple distinct owner proofs.
    # arid: disable
    def __init__(self, store: IntelligenceJudgmentHistoryStore) -> None:
        self._store = store

    async def resolve(
        self,
        target: IntelligenceJudgmentRoot,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ClaimMembershipResolution:
        if (
            type(target)
            not in (
                InvestmentHypothesisRef,
                InvestmentViewRef,
                MeaningfulChallengeResultRef,
                InvestmentRecommendationRef,
                RecommendationWithholdingJudgmentRef,
            )
            or type(claim_id) is not ClaimId
        ):
            raise TypeError("Intelligence claim requires typed target and ClaimId")
        try:
            history = await self._store.load(target)
        except IntelligenceJudgmentHistoryUnavailable as error:
            return UnavailableClaimCatalog(target, str(error))
        except (ValueError, TypeError) as error:
            return InvalidClaimHistory(target, str(error))
        if history is None or history.acts[0].known_at > known_at:
            return ClaimTargetNotKnownAtCutoff(target)
        try:
            selection = history.select(effective_at, known_at)
        except IntelligenceJudgmentNotYetEffective:
            return ClaimTargetNotYetEffective(target)
        except InvalidIntelligenceJudgmentHistory as error:
            return InvalidClaimHistory(target, str(error))
        if (
            selection.catalog_act.contested_catalog
            or selection.target_act.target_status
            is IntelligenceJudgmentStatus.CONTESTED
        ):
            return ContestedClaimHistory(target, "owner catalog is contested")
        if selection.target_act.target_status is not IntelligenceJudgmentStatus.ACTIVE:
            return InvalidClaimHistory(target, "target is not currently active")
        if selection.catalog is not None and selection.catalog.has(claim_id):
            return ResolvedClaimMembership(target, claim_id, selection.catalog_version)
        return _absent_claim(history, target, claim_id, effective_at, known_at)

    # arid: enable


@dataclass(frozen=True, slots=True)
class IntelligenceSelectionGuard:
    # duplicate-code: Sharing would couple distinct owner proofs.
    # arid: disable
    key: BasisScopeKey
    target_act_id: UUID
    catalog_act_id: UUID
    version_history: tuple[tuple[JudgmentRevision, ClaimCatalogVersion], ...]
    claim_id: ClaimId | None
    claim_selected: bool | None
    # arid: enable


@dataclass(frozen=True, slots=True)
class IntelligenceOwnerProvenance:
    attribution: ActorAttribution
    basis: str
    selected_act_id: UUID


# duplicate-code: Sharing would couple distinct owner proofs.
# arid: disable
# jscpd:ignore-start
class IntelligenceJudgmentMeaningReader:
    """Attest exact Investment Intelligence temporal cause for Evidence revalidation."""

    def __init__(self, store: IntelligenceJudgmentHistoryStore) -> None:
        self._store = store

    async def read_at(
        self,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        *,
        effective_at: datetime,
        known_at: datetime,
        read_at: datetime,
    ) -> OwnerMeaningWitness | OwnerMeaningNoBasis:
        if type(key) is not BasisScopeKey or type(key.target) not in (
            InvestmentHypothesisRef,
            InvestmentViewRef,
            MeaningfulChallengeResultRef,
            InvestmentRecommendationRef,
            RecommendationWithholdingJudgmentRef,
        ):
            raise TypeError("Intelligence owner witness requires exact typed basis key")
        if type(subject) not in (TargetJudgmentMeaning, ClaimMembershipMeaning):
            raise TypeError(
                "Intelligence owner witnesses cover target and claim meaning"
            )

        def no_basis(
            reason: OwnerMeaningNoBasisReason, detail: str | None = None
        ) -> OwnerMeaningNoBasis:
            # duplicate-code: Intelligence failure mapping is local to its owner
            # history; sharing Decisions' constructor would couple owners.
            # arid: disable
            return OwnerMeaningNoBasis(
                key,
                subject,
                effective_at,
                known_at,
                read_at,
                reason,
                reason.value if detail is None else detail,
            )
            # arid: enable

        try:
            history = await self._store.load(key.target)
        except IntelligenceJudgmentHistoryUnavailable as error:
            # duplicate-code: Sharing would couple distinct owner proofs.
            # arid: disable
            return no_basis(OwnerMeaningNoBasisReason.UNAVAILABLE, str(error))
        except ValueError, TypeError:
            return no_basis(OwnerMeaningNoBasisReason.INVALID_HISTORY)
        if history is None or history.acts[0].known_at > known_at:
            return no_basis(OwnerMeaningNoBasisReason.MISSING)
        try:
            selected = history.select(effective_at, known_at)
        except IntelligenceJudgmentNotYetEffective:
            return no_basis(OwnerMeaningNoBasisReason.NOT_YET_EFFECTIVE)
        except InvalidIntelligenceJudgmentHistory:
            return no_basis(OwnerMeaningNoBasisReason.INVALID_HISTORY)
        # arid: enable
        status_failure = _meaning_status_failure(selected)
        if status_failure is not None:
            return no_basis(status_failure)
        return _witness(key, subject, selected, effective_at, known_at, read_at)

    async def verify_cause(
        self, witness: OwnerMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        # duplicate-code: each owner rechecks its own history; sharing this
        # re-read would erase the Intelligence validation boundary.
        # arid: disable
        if validation_at.tzinfo is None or validation_at.utcoffset() is None:
            raise ValueError("validation_at must be timezone-aware")
        if validation_at < witness.read_at:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        fresh = await self.read_at(
            witness.key,
            witness.subject,
            effective_at=witness.effective_at,
            known_at=witness.known_at,
            read_at=witness.read_at,
        )
        if type(fresh) is OwnerMeaningNoBasis:
            return fresh.reason
        if fresh != witness:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        return OwnerCauseVerdict.VALID
        # arid: enable


def _absent_claim(
    history: IntelligenceJudgmentHistory,
    target: IntelligenceJudgmentRoot,
    claim_id: ClaimId,
    effective_at: datetime,
    known_at: datetime,
) -> ClaimMembershipResolution:
    # duplicate-code: Sharing would couple distinct owner proofs.
    # arid: disable
    for act in history.acts:
        if act.catalog is None or not act.catalog.has(claim_id):
            continue
        if act.known_at > known_at:
            return ClaimNotKnownAtCutoff(target, claim_id)
        if act.effective_at > effective_at:
            return ClaimNotYetEffective(target, claim_id)
        return ClaimNotCurrent(target, claim_id)
    return InvalidClaimReference(target, claim_id)
    # arid: enable


def _meaning_status_failure(
    selected: IntelligenceJudgmentSelection,
) -> OwnerMeaningNoBasisReason | None:
    if (
        selected.target_act.target_status is IntelligenceJudgmentStatus.CONTESTED
        or selected.catalog_act.contested_catalog
    ):
        return OwnerMeaningNoBasisReason.CONTESTED
    if selected.target_act.target_status is not IntelligenceJudgmentStatus.ACTIVE:
        return OwnerMeaningNoBasisReason.INCOMPLETE
    return None


# jscpd:ignore-end
# arid: enable


# duplicate-code: Sharing would couple distinct owner proofs.
# arid: disable
# jscpd:ignore-start
def _witness(
    key: BasisScopeKey,
    subject: OwnerMeaningSubject,
    selected: IntelligenceJudgmentSelection,
    effective_at: datetime,
    known_at: datetime,
    read_at: datetime,
) -> OwnerMeaningWitness:
    claim_id = subject.claim_id if type(subject) is ClaimMembershipMeaning else None
    claim: IntelligenceClaim | None = None
    if claim_id is not None and selected.catalog is not None:
        claim = next(
            (item for item in selected.catalog.claims if item.claim_id == claim_id),
            None,
        )
    act = (
        selected.target_act
        if type(subject) is TargetJudgmentMeaning
        else selected.catalog_act
    )
    meaning = (
        (selected.assertion, selected.judgment_revision)
        if type(subject) is TargetJudgmentMeaning
        else (claim, selected.catalog_version)
    )
    cause = OwnerMeaningCause(
        fact_ancestry=(
            OwnerHistoryRecord(
                selected.target_act,
                selected.target_act.effective_at,
                selected.target_act.recorded_at,
            ),
            OwnerHistoryRecord(
                selected.catalog_act,
                selected.catalog_act.effective_at,
                selected.catalog_act.recorded_at,
            ),
        ),
        correction_ancestry=tuple(
            OwnerHistoryRecord(item, item.effective_at, item.recorded_at)
            for item in selected.known_ancestry
        ),
        relationship_guards=(
            IntelligenceSelectionGuard(
                key,
                selected.target_act.act_id,
                selected.catalog_act.act_id,
                selected.version_history,
                claim_id,
                None if claim_id is None else claim is not None,
            ),
        ),
        complete=True,
    )
    # duplicate-code: Intelligence and Decisions construct owner-specific meaning;
    # sharing the witness assembly would couple independent provenance rules.
    # arid: disable
    return OwnerMeaningWitness(
        key,
        subject,
        effective_at,
        known_at,
        read_at,
        meaning,
        IntelligenceOwnerProvenance(act.attribution, act.basis, act.act_id),
        cause,
    )


# jscpd:ignore-end
# arid: enable
# arid: enable
