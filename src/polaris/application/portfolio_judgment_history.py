"""Portfolio owner reads, corrections, and Evidence meaning witnesses."""

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
    JudgmentRevision,
    PortfolioRiskAssessmentVersionRef,
    ProjectedPortfolioConsequenceVersionRef,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
)
from polaris.domain.portfolio_judgment_history import (
    InvalidPortfolioJudgmentHistory,
    PortfolioClaim,
    PortfolioJudgmentAct,
    PortfolioJudgmentHistory,
    PortfolioJudgmentNotYetEffective,
    PortfolioJudgmentRoot,
    PortfolioJudgmentSelection,
)


class PortfolioJudgmentHistoryStore(Protocol):
    async def load(
        self, root: PortfolioJudgmentRoot
    ) -> PortfolioJudgmentHistory | None: ...

    async def append(self, act: PortfolioJudgmentAct) -> PortfolioJudgmentHistory: ...


class PortfolioJudgmentHistoryUnavailable(Exception):
    """The durable owner history cannot be read or committed."""


class PortfolioJudgmentCorrectionService:
    """Admit one complete owner act through an atomic same-root store."""

    def __init__(self, store: PortfolioJudgmentHistoryStore) -> None:
        self._store = store

    async def correct(self, act: PortfolioJudgmentAct) -> PortfolioJudgmentHistory:
        if type(act) is not PortfolioJudgmentAct or act.ancestry == ():
            raise TypeError("correction requires a typed non-root owner act")
        return await self._store.append(act)


def _version(selection: PortfolioJudgmentSelection):
    revision = JudgmentRevision(selection.judgment_revision.value)
    root = selection.target_act.root
    if type(root) is ProjectedPortfolioConsequenceRef:
        return ProjectedPortfolioConsequenceVersionRef(root, revision)
    return PortfolioRiskAssessmentVersionRef(root, revision)


class PortfolioJudgmentTargetReader:
    """Evidence-facing target read with complete owner history validation."""

    def __init__(self, store: PortfolioJudgmentHistoryStore) -> None:
        self._store = store

    async def read_at(
        self,
        target: PortfolioJudgmentRoot,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> TargetJudgmentResolution:
        if type(target) not in (
            ProjectedPortfolioConsequenceRef,
            PortfolioRiskAssessmentRef,
        ):
            raise TypeError("target must be a Portfolio Evidence target")
        try:
            history = await self._store.load(target)
        except PortfolioJudgmentHistoryUnavailable as error:
            return TargetJudgmentUnavailable(target, str(error))
        except (ValueError, TypeError) as error:
            return TargetJudgmentInvalidHistory(target, str(error))
        if history is None or history.acts[0].known_at > known_at:
            return TargetJudgmentMissing(target)
        try:
            selection = history.select(effective_at, known_at)
        except PortfolioJudgmentNotYetEffective:
            return TargetJudgmentNotYetEffective(target)
        except InvalidPortfolioJudgmentHistory as error:
            return TargetJudgmentInvalidHistory(target, str(error))
        if selection.target_act.contested_target:
            return TargetJudgmentContested(target, "owner assertion is contested")
        return ResolvedTargetJudgment(
            target,
            _version(selection),
            selection.assertion,
            selection.target_support,
            effective_at,
            known_at,
        )


class PortfolioJudgmentClaimResolver:
    """Select complete Portfolio claim catalogs from owner correction acts."""

    def __init__(self, store: PortfolioJudgmentHistoryStore) -> None:
        self._store = store

    async def resolve(
        self,
        target: PortfolioJudgmentRoot,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ClaimMembershipResolution:
        if (
            type(target)
            not in (
                ProjectedPortfolioConsequenceRef,
                PortfolioRiskAssessmentRef,
            )
            or type(claim_id) is not ClaimId
        ):
            raise TypeError("Portfolio claim requires typed target and ClaimId")
        try:
            history = await self._store.load(target)
        except PortfolioJudgmentHistoryUnavailable as error:
            return UnavailableClaimCatalog(target, str(error))
        except (ValueError, TypeError) as error:
            return InvalidClaimHistory(target, str(error))
        if history is None or history.acts[0].known_at > known_at:
            return ClaimTargetNotKnownAtCutoff(target)
        try:
            selection = history.select(effective_at, known_at)
        except PortfolioJudgmentNotYetEffective:
            return ClaimTargetNotYetEffective(target)
        except InvalidPortfolioJudgmentHistory as error:
            return InvalidClaimHistory(target, str(error))
        if (
            selection.catalog_act.contested_catalog
            or selection.target_act.contested_target
        ):
            return ContestedClaimHistory(target, "owner catalog is contested")
        if selection.catalog is not None and selection.catalog.has(claim_id):
            return ResolvedClaimMembership(target, claim_id, selection.catalog_version)
        return _absent_claim(history, target, claim_id, effective_at, known_at)


@dataclass(frozen=True, slots=True)
class PortfolioSelectionGuard:
    key: BasisScopeKey
    target_act_id: UUID
    catalog_act_id: UUID
    version_history: tuple[tuple[JudgmentRevision, ClaimCatalogVersion], ...]
    claim_id: ClaimId | None
    claim_selected: bool | None


@dataclass(frozen=True, slots=True)
class PortfolioOwnerProvenance:
    attribution: ActorAttribution
    basis: str
    selected_act_id: UUID


class PortfolioJudgmentMeaningReader:
    """Attest exact Portfolio temporal cause for Evidence revalidation."""

    def __init__(self, store: PortfolioJudgmentHistoryStore) -> None:
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
            ProjectedPortfolioConsequenceRef,
            PortfolioRiskAssessmentRef,
        ):
            raise TypeError("Portfolio owner witness requires exact typed basis key")
        if type(subject) not in (TargetJudgmentMeaning, ClaimMembershipMeaning):
            raise TypeError("Portfolio owner witnesses cover target and claim meaning")

        def no_basis(
            reason: OwnerMeaningNoBasisReason, detail: str | None = None
        ) -> OwnerMeaningNoBasis:
            # duplicate-code: Portfolio failure mapping is local to its owner
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
        except PortfolioJudgmentHistoryUnavailable as error:
            return no_basis(OwnerMeaningNoBasisReason.UNAVAILABLE, str(error))
        except ValueError, TypeError:
            return no_basis(OwnerMeaningNoBasisReason.INVALID_HISTORY)
        if history is None or history.acts[0].known_at > known_at:
            return no_basis(OwnerMeaningNoBasisReason.MISSING)
        try:
            selected = history.select(effective_at, known_at)
        except PortfolioJudgmentNotYetEffective:
            return no_basis(OwnerMeaningNoBasisReason.NOT_YET_EFFECTIVE)
        except InvalidPortfolioJudgmentHistory:
            return no_basis(OwnerMeaningNoBasisReason.INVALID_HISTORY)
        if (
            selected.target_act.contested_target
            or selected.catalog_act.contested_catalog
        ):
            return no_basis(OwnerMeaningNoBasisReason.CONTESTED)
        return _witness(key, subject, selected, effective_at, known_at, read_at)

    async def verify_cause(
        self, witness: OwnerMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        # duplicate-code: each owner rechecks its own history; sharing this
        # re-read would erase the Portfolio-specific validation boundary.
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
    history: PortfolioJudgmentHistory,
    target: PortfolioJudgmentRoot,
    claim_id: ClaimId,
    effective_at: datetime,
    known_at: datetime,
) -> ClaimMembershipResolution:
    for act in history.acts:
        if act.catalog is None or not act.catalog.has(claim_id):
            continue
        if act.known_at > known_at:
            return ClaimNotKnownAtCutoff(target, claim_id)
        if act.effective_at > effective_at:
            return ClaimNotYetEffective(target, claim_id)
        return ClaimNotCurrent(target, claim_id)
    return InvalidClaimReference(target, claim_id)


def _witness(
    key: BasisScopeKey,
    subject: OwnerMeaningSubject,
    selected: PortfolioJudgmentSelection,
    effective_at: datetime,
    known_at: datetime,
    read_at: datetime,
) -> OwnerMeaningWitness:
    claim_id = subject.claim_id if type(subject) is ClaimMembershipMeaning else None
    claim: PortfolioClaim | None = None
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
            PortfolioSelectionGuard(
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
    # duplicate-code: Portfolio and Decisions construct owner-specific meaning;
    # sharing the witness assembly would couple independent provenance rules.
    # arid: disable
    return OwnerMeaningWitness(
        key,
        subject,
        effective_at,
        known_at,
        read_at,
        meaning,
        PortfolioOwnerProvenance(act.attribution, act.basis, act.act_id),
        cause,
    )
    # arid: enable
