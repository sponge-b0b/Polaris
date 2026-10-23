"""Portfolio-owned correction history for Evidence judgment targets and claims."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from polaris.domain.actors import ActorAttribution, is_actor_attribution
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.judgment_versions import JudgmentRevision
from polaris.domain.evidence.judgments import (
    ClaimId,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
)
from polaris.domain.evidence.observations import EvidenceFactRef, is_evidence_fact_ref
from polaris.domain.portfolio_consequences import ProjectedPortfolioConsequence
from polaris.domain.portfolio_risk import PortfolioRiskAssessment

type PortfolioJudgmentRoot = (
    ProjectedPortfolioConsequenceRef | PortfolioRiskAssessmentRef
)
type PortfolioJudgmentAssertion = (
    ProjectedPortfolioConsequence | PortfolioRiskAssessment
)


class InvalidPortfolioJudgmentHistory(ValueError):
    """A correction cannot yield one complete, coherent owner history."""


class PortfolioJudgmentNotYetEffective(ValueError):
    """The target is known, but no owner meaning is effective at this cut."""


class PortfolioJudgmentLane(StrEnum):
    TARGET = "target"
    CATALOG = "catalog"


class PendingDisposition(StrEnum):
    CANCEL = "cancel"
    RETAIN = "retain"


@dataclass(frozen=True, slots=True)
class PortfolioClaim:
    claim_id: ClaimId
    proposition: str
    surviving_support: frozenset[EvidenceFactRef]

    def __post_init__(self) -> None:
        if type(self.claim_id) is not ClaimId:
            raise TypeError("claim_id must be ClaimId")
        if not isinstance(self.proposition, str) or not self.proposition.strip():
            raise ValueError("claim proposition must be substantive")
        if type(self.surviving_support) is not frozenset or any(
            not is_evidence_fact_ref(item) for item in self.surviving_support
        ):
            raise TypeError("surviving_support must contain typed Evidence facts")


@dataclass(frozen=True, slots=True)
class PortfolioClaimCatalog:
    """One complete owner declaration; absence of a claim is meaningful."""

    claims: tuple[PortfolioClaim, ...]

    def __post_init__(self) -> None:
        if type(self.claims) is not tuple or any(
            type(item) is not PortfolioClaim for item in self.claims
        ):
            raise TypeError("claims must be a tuple of PortfolioClaim")
        if len({item.claim_id for item in self.claims}) != len(self.claims):
            raise ValueError("claim identities must be distinct")
        object.__setattr__(
            self,
            "claims",
            tuple(sorted(self.claims, key=lambda item: str(item.claim_id.value))),
        )

    def has(self, claim_id: ClaimId) -> bool:
        return any(item.claim_id == claim_id for item in self.claims)


@dataclass(frozen=True, slots=True)
class PendingResolution:
    lane: PortfolioJudgmentLane
    pending_act_id: UUID
    disposition: PendingDisposition

    def __post_init__(self) -> None:
        if type(self.lane) is not PortfolioJudgmentLane:
            raise TypeError("lane must be PortfolioJudgmentLane")
        _uuid4(self.pending_act_id, "pending_act_id")
        if type(self.disposition) is not PendingDisposition:
            raise TypeError("disposition must be PendingDisposition")


@dataclass(frozen=True, slots=True)
class PortfolioJudgmentAct:
    """One immutable owner act, distinct from either current owner version."""

    act_id: UUID
    root: PortfolioJudgmentRoot
    attribution: ActorAttribution
    basis: str
    effective_at: datetime
    recorded_at: datetime
    known_at: datetime
    ancestry: tuple[UUID, ...]
    assertion: PortfolioJudgmentAssertion | None = None
    catalog: PortfolioClaimCatalog | None = None
    target_predecessor: UUID | None = None
    catalog_predecessor: UUID | None = None
    pending_resolutions: tuple[PendingResolution, ...] = ()
    compatible_opposite_acts: tuple[UUID, ...] = ()
    target_interim_until: datetime | None = None
    catalog_interim_until: datetime | None = None
    contested_target: bool = False
    contested_catalog: bool = False

    def __post_init__(self) -> None:
        _uuid4(self.act_id, "act_id")
        if type(self.root) not in (
            ProjectedPortfolioConsequenceRef,
            PortfolioRiskAssessmentRef,
        ):
            raise TypeError("root must be a Portfolio Evidence target")
        if not is_actor_attribution(self.attribution):
            raise TypeError("attribution must identify an actor status")
        if not isinstance(self.basis, str) or not self.basis.strip():
            raise ValueError("correction basis must be substantive")
        for field in ("effective_at", "recorded_at", "known_at"):
            _aware(getattr(self, field), field)
        if self.recorded_at > self.known_at:
            raise ValueError("owner knowledge cannot precede recording")
        self._validate_meaning()
        self._validate_ancestry()
        self._validate_lanes()

    def _validate_meaning(self) -> None:
        if (
            self.assertion is None
            and self.catalog is None
            and not (self.contested_target or self.contested_catalog)
        ):
            raise ValueError("an act must change a target or catalog lane")
        if self.assertion is not None and _assertion_root(self.assertion) != self.root:
            raise ValueError("target assertion must belong to the typed root")
        if self.contested_target and self.assertion is not None:
            raise ValueError("contested target cannot carry a selected assertion")
        if self.contested_catalog and self.catalog is not None:
            raise ValueError("contested catalog cannot carry a selected catalog")

    def _validate_ancestry(self) -> None:
        if type(self.ancestry) is not tuple or any(
            type(item) is not UUID or item.version != 4 for item in self.ancestry
        ):
            raise TypeError("ancestry must contain owner act references")
        if len(set(self.ancestry)) != len(self.ancestry):
            raise ValueError("ancestry must not repeat an act")
        if type(self.pending_resolutions) is not tuple or any(
            type(item) is not PendingResolution for item in self.pending_resolutions
        ):
            raise TypeError("pending_resolutions must be typed")
        keys = {(item.lane, item.pending_act_id) for item in self.pending_resolutions}
        if len(keys) != len(self.pending_resolutions):
            raise ValueError("one pending lane may be resolved only once")
        if type(self.compatible_opposite_acts) is not tuple or any(
            item not in self.ancestry for item in self.compatible_opposite_acts
        ):
            raise ValueError("compatible opposite acts must be in complete ancestry")
        if len(set(self.compatible_opposite_acts)) != len(
            self.compatible_opposite_acts
        ):
            raise ValueError("compatible opposite acts must be distinct")

    def _validate_lanes(self) -> None:
        for lane, predecessor, until in (
            (
                PortfolioJudgmentLane.TARGET,
                self.target_predecessor,
                self.target_interim_until,
            ),
            (
                PortfolioJudgmentLane.CATALOG,
                self.catalog_predecessor,
                self.catalog_interim_until,
            ),
        ):
            changed = self.changes(lane)
            if changed != (predecessor is not None or not self.ancestry):
                raise ValueError(f"{lane.value} predecessor must match changed lane")
            if predecessor is not None and predecessor not in self.ancestry:
                raise ValueError("predecessor must be in complete ancestry")
            if until is not None:
                _aware(until, "interim_until")
                if not changed or until <= self.effective_at:
                    raise ValueError("interim bound must follow its act")

    def changes(self, lane: PortfolioJudgmentLane) -> bool:
        return (
            self.assertion is not None or self.contested_target
            if lane is PortfolioJudgmentLane.TARGET
            else self.catalog is not None or self.contested_catalog
        )

    def predecessor(self, lane: PortfolioJudgmentLane) -> UUID | None:
        return (
            self.target_predecessor
            if lane is PortfolioJudgmentLane.TARGET
            else self.catalog_predecessor
        )

    def interim_until(self, lane: PortfolioJudgmentLane) -> datetime | None:
        return (
            self.target_interim_until
            if lane is PortfolioJudgmentLane.TARGET
            else self.catalog_interim_until
        )


@dataclass(frozen=True, slots=True)
class PortfolioJudgmentSelection:
    target_act: PortfolioJudgmentAct
    catalog_act: PortfolioJudgmentAct
    judgment_revision: JudgmentRevision
    catalog_version: ClaimCatalogVersion
    known_ancestry: tuple[PortfolioJudgmentAct, ...]
    version_history: tuple[tuple[JudgmentRevision, ClaimCatalogVersion], ...]

    @property
    def assertion(self) -> PortfolioJudgmentAssertion | None:
        return self.target_act.assertion

    @property
    def catalog(self) -> PortfolioClaimCatalog | None:
        return self.catalog_act.catalog

    @property
    def target_support(self) -> tuple[PortfolioJudgmentAct, ...]:
        by_id = {item.act_id: item for item in self.known_ancestry}
        lineage = []
        current: PortfolioJudgmentAct | None = self.target_act
        while current is not None:
            lineage.append(current)
            predecessor = current.target_predecessor
            current = None if predecessor is None else by_id[predecessor]
        return tuple(reversed(lineage))


@dataclass(frozen=True, slots=True)
class PortfolioJudgmentHistory:
    """Complete, append-only owner history for one typed target root."""

    acts: tuple[PortfolioJudgmentAct, ...]
    versions: tuple[tuple[JudgmentRevision, ClaimCatalogVersion], ...]

    def __post_init__(self) -> None:
        if not self.acts or len(self.acts) != len(self.versions):
            raise InvalidPortfolioJudgmentHistory(
                "complete owner versions are required"
            )
        if any(item.root != self.acts[0].root for item in self.acts):
            raise InvalidPortfolioJudgmentHistory("history mixes target roots")

    @classmethod
    def form(cls, initial: PortfolioJudgmentAct) -> PortfolioJudgmentHistory:
        if initial.ancestry or initial.assertion is None or initial.catalog is None:
            raise InvalidPortfolioJudgmentHistory(
                "root act requires assertion and complete claim catalog"
            )
        if initial.effective_at > initial.known_at:
            raise InvalidPortfolioJudgmentHistory(
                "root formation must have current owner meaning"
            )
        return cls((initial,), ((JudgmentRevision(1), ClaimCatalogVersion(1)),))

    def append(self, act: PortfolioJudgmentAct) -> PortfolioJudgmentHistory:
        prior = self.acts
        if act.root != prior[0].root:
            raise InvalidPortfolioJudgmentHistory("correction has wrong typed root")
        if act.ancestry != tuple(item.act_id for item in prior):
            raise InvalidPortfolioJudgmentHistory("correction ancestry is incomplete")
        if act.known_at < prior[-1].known_at:
            raise InvalidPortfolioJudgmentHistory("owner knowledge must be ordered")
        if act.act_id in act.ancestry:
            raise InvalidPortfolioJudgmentHistory("act reference already exists")
        if act.assertion is not None and _lineage(act.assertion) != _lineage(
            prior[0].assertion
        ):
            raise InvalidPortfolioJudgmentHistory(
                "new material judgment or reassessment requires a new root"
            )
        if act.catalog is not None:
            previous_claims = {
                claim.claim_id: claim.proposition
                for item in prior
                if item.catalog is not None
                for claim in item.catalog.claims
            }
            if any(
                claim.claim_id in previous_claims
                and claim.proposition != previous_claims[claim.claim_id]
                for claim in act.catalog.claims
            ):
                raise InvalidPortfolioJudgmentHistory(
                    "a materially changed proposition requires a fresh ClaimId"
                )
        for lane in PortfolioJudgmentLane:
            self._check_pending_resolution(act, lane)
        before = self.select(act.known_at, act.known_at)
        candidate = PortfolioJudgmentHistory(
            (*prior, act), (*self.versions, self.versions[-1])
        )
        candidate._validate_timeline(act.known_at)
        after = candidate.select(act.known_at, act.known_at)
        target_changed = _target_meaning(before.target_act) != _target_meaning(
            after.target_act
        )
        catalog_changed = before.catalog != after.catalog
        current_target, current_catalog = self.versions[-1]
        versions = (
            JudgmentRevision(current_target.value + int(target_changed)),
            ClaimCatalogVersion(current_catalog.value + int(catalog_changed)),
        )
        return PortfolioJudgmentHistory((*prior, act), (*self.versions, versions))

    def select(
        self, effective_at: datetime, known_at: datetime
    ) -> PortfolioJudgmentSelection:
        _aware(effective_at, "effective_at")
        _aware(known_at, "known_at")
        known = tuple(item for item in self.acts if item.known_at <= known_at)
        if not known:
            raise InvalidPortfolioJudgmentHistory("target not known at cutoff")
        target = self._selected(known, PortfolioJudgmentLane.TARGET, effective_at)
        catalog = self._selected(known, PortfolioJudgmentLane.CATALOG, effective_at)
        if target is None or catalog is None:
            raise PortfolioJudgmentNotYetEffective("target not yet effective")
        if not _coherent(target, catalog):
            raise InvalidPortfolioJudgmentHistory("target and catalog are incompatible")
        index = len(known) - 1
        return PortfolioJudgmentSelection(
            target, catalog, *self.versions[index], known, self.versions[: index + 1]
        )

    def _selected(
        self,
        known: tuple[PortfolioJudgmentAct, ...],
        lane: PortfolioJudgmentLane,
        effective_at: datetime,
    ) -> PortfolioJudgmentAct | None:
        canceled = {
            resolution.pending_act_id
            for act in known
            for resolution in act.pending_resolutions
            if resolution.lane is lane
            and resolution.disposition is PendingDisposition.CANCEL
        }
        eligible = [
            act
            for act in known
            if act.changes(lane)
            and act.act_id not in canceled
            and act.effective_at <= effective_at
            and (
                act.interim_until(lane) is None
                or effective_at < act.interim_until(lane)
            )
        ]
        if not eligible:
            return None
        superseded = {act.predecessor(lane) for act in eligible}
        leaves = [act for act in eligible if act.act_id not in superseded]
        if len(leaves) != 1:
            raise InvalidPortfolioJudgmentHistory("lane has no unique selected act")
        return leaves[0]

    def _check_pending_resolution(
        self, act: PortfolioJudgmentAct, lane: PortfolioJudgmentLane
    ) -> None:
        resolutions = {
            item.pending_act_id: item.disposition
            for item in act.pending_resolutions
            if item.lane is lane
        }
        if not act.changes(lane):
            if resolutions:
                raise InvalidPortfolioJudgmentHistory(
                    "resolution cannot change an unaffected lane"
                )
            return
        canceled = {
            resolution.pending_act_id
            for item in self.acts
            for resolution in item.pending_resolutions
            if resolution.lane is lane
            and resolution.disposition is PendingDisposition.CANCEL
        }
        pending = [
            item
            for item in self.acts
            if item.changes(lane)
            and item.effective_at > act.known_at
            and item.act_id not in canceled
        ]
        if set(resolutions) != {item.act_id for item in pending}:
            raise InvalidPortfolioJudgmentHistory(
                "all known pending lane acts need explicit resolution"
            )
        retained = [
            item
            for item in pending
            if resolutions[item.act_id] is PendingDisposition.RETAIN
        ]
        if retained:
            bound = act.interim_until(lane)
            if bound != min(item.effective_at for item in retained):
                raise InvalidPortfolioJudgmentHistory(
                    "interim act must end at retained successor boundary"
                )
        elif act.interim_until(lane) is not None:
            raise InvalidPortfolioJudgmentHistory(
                "interim bound requires an explicitly retained successor"
            )

    def _validate_timeline(self, known_at: datetime) -> None:
        boundaries = {item.effective_at for item in self.acts}
        boundaries.update(
            bound
            for item in self.acts
            for bound in (
                item.target_interim_until,
                item.catalog_interim_until,
            )
            if bound is not None
        )
        for boundary in sorted(boundaries):
            for instant in (boundary - timedelta(microseconds=1), boundary):
                if instant < self.acts[0].effective_at:
                    continue
                self.select(instant, known_at)


def _coherent(target: PortfolioJudgmentAct, catalog: PortfolioJudgmentAct) -> bool:
    # An unchanged lane keeps its complete owner declaration. The affected act
    # must explicitly name the opposite selected lane when it changes alone.
    if target.act_id == catalog.act_id:
        return True
    return (
        target.act_id in catalog.compatible_opposite_acts
        or catalog.act_id in target.compatible_opposite_acts
    )


def _target_meaning(act: PortfolioJudgmentAct) -> tuple[object, ...]:
    return (act.assertion, act.attribution, act.basis, act.contested_target)


def _assertion_root(assertion: PortfolioJudgmentAssertion) -> PortfolioJudgmentRoot:
    if type(assertion) is ProjectedPortfolioConsequence:
        return assertion.consequence_id
    if type(assertion) is PortfolioRiskAssessment:
        return assertion.assessment_id
    raise TypeError("assertion must be a Portfolio Evidence target")


def _lineage(assertion: PortfolioJudgmentAssertion | None) -> tuple[object, ...]:
    if type(assertion) is ProjectedPortfolioConsequence:
        return (
            assertion.alternative,
            assertion.source_state_id,
            assertion.horizon,
        )
    if type(assertion) is PortfolioRiskAssessment:
        return (
            assertion.source_state_id,
            assertion.projected_consequence_id,
            assertion.horizon,
        )
    raise TypeError("assertion must be a Portfolio Evidence target")


def _uuid4(value: UUID, field: str) -> None:
    if type(value) is not UUID or value.version != 4:
        raise TypeError(f"{field} must be UUIDv4")


def _aware(value: datetime, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
