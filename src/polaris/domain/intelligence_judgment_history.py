"""Investment Intelligence-owned target and claim correction history."""

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
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.evidence.observations import EvidenceFactRef, is_evidence_fact_ref
from polaris.domain.investment_intelligence import (
    InvestmentHypothesis,
    InvestmentView,
    MeaningfulChallengeResult,
)
from polaris.domain.investment_recommendation import (
    InvestmentRecommendation,
    RecommendationWithholdingJudgment,
)

type IntelligenceJudgmentRoot = (
    InvestmentHypothesisRef
    | InvestmentViewRef
    | MeaningfulChallengeResultRef
    | InvestmentRecommendationRef
    | RecommendationWithholdingJudgmentRef
)
type IntelligenceJudgmentAssertion = (
    InvestmentHypothesis
    | InvestmentView
    | MeaningfulChallengeResult
    | InvestmentRecommendation
    | RecommendationWithholdingJudgment
)


class InvalidIntelligenceJudgmentHistory(ValueError):
    """A correction cannot yield one complete, coherent owner history."""


class IntelligenceJudgmentNotYetEffective(ValueError):
    """The target is known, but no owner meaning is effective at this cut."""


# duplicate-code: Sharing would couple distinct owner statuses.
# arid: disable
class IntelligenceJudgmentLane(StrEnum):
    TARGET = "target"
    CATALOG = "catalog"


class PendingDisposition(StrEnum):
    CANCEL = "cancel"
    RETAIN = "retain"


# arid: enable


class IntelligenceJudgmentStatus(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    CONTESTED = "contested"
    INVALID = "invalid"


# duplicate-code: Sharing would couple distinct owner statuses.
# arid: disable
# jscpd:ignore-start
@dataclass(frozen=True, slots=True)
class IntelligenceClaim:
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
class IntelligenceClaimCatalog:
    """One complete owner declaration; absence of a claim is meaningful."""

    claims: tuple[IntelligenceClaim, ...]

    def __post_init__(self) -> None:
        if type(self.claims) is not tuple or any(
            type(item) is not IntelligenceClaim for item in self.claims
        ):
            raise TypeError("claims must be a tuple of IntelligenceClaim")
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
    lane: IntelligenceJudgmentLane
    pending_act_id: UUID
    disposition: PendingDisposition

    def __post_init__(self) -> None:
        if type(self.lane) is not IntelligenceJudgmentLane:
            raise TypeError("lane must be IntelligenceJudgmentLane")
        _uuid4(self.pending_act_id, "pending_act_id")
        if type(self.disposition) is not PendingDisposition:
            raise TypeError("disposition must be PendingDisposition")


# jscpd:ignore-end
# arid: enable


@dataclass(frozen=True, slots=True)
class IntelligenceJudgmentAct:
    """One immutable owner act, distinct from either current owner version."""

    act_id: UUID
    root: IntelligenceJudgmentRoot
    # duplicate-code: Sharing would couple distinct owner statuses.
    # arid: disable
    attribution: ActorAttribution
    basis: str
    effective_at: datetime
    recorded_at: datetime
    known_at: datetime
    # arid: enable
    ancestry: tuple[UUID, ...]
    assertion: IntelligenceJudgmentAssertion | None = None
    catalog: IntelligenceClaimCatalog | None = None
    # duplicate-code: Sharing would couple distinct owner statuses.
    # arid: disable
    target_predecessor: UUID | None = None
    catalog_predecessor: UUID | None = None
    pending_resolutions: tuple[PendingResolution, ...] = ()
    compatible_opposite_acts: tuple[UUID, ...] = ()
    target_interim_until: datetime | None = None
    # arid: enable
    catalog_interim_until: datetime | None = None
    target_status: IntelligenceJudgmentStatus | None = None
    contested_catalog: bool = False

    # duplicate-code: Sharing would couple distinct owner statuses.
    # arid: disable
    # jscpd:ignore-start
    def __post_init__(self) -> None:
        _uuid4(self.act_id, "act_id")
        if type(self.root) not in (
            InvestmentHypothesisRef,
            InvestmentViewRef,
            MeaningfulChallengeResultRef,
            InvestmentRecommendationRef,
            RecommendationWithholdingJudgmentRef,
        ):
            raise TypeError("root must be an Investment Intelligence Evidence target")
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
            and self.target_status is None
            and not self.contested_catalog
        ):
            raise ValueError("an act must change a target or catalog lane")
        if self.assertion is not None and _assertion_root(self.assertion) != self.root:
            raise ValueError("target assertion must belong to the typed root")
        if (
            self.target_status is not None
            and type(self.target_status) is not IntelligenceJudgmentStatus
        ):
            raise TypeError("target status must be closed")
        if (self.assertion is None) == (
            self.target_status is IntelligenceJudgmentStatus.ACTIVE
        ):
            raise ValueError("active target needs an assertion; other statuses omit it")
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
                IntelligenceJudgmentLane.TARGET,
                self.target_predecessor,
                self.target_interim_until,
            ),
            (
                IntelligenceJudgmentLane.CATALOG,
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

    def changes(self, lane: IntelligenceJudgmentLane) -> bool:
        return (
            self.target_status is not None
            if lane is IntelligenceJudgmentLane.TARGET
            else self.catalog is not None or self.contested_catalog
        )

    # jscpd:ignore-end
    # arid: enable

    def predecessor(self, lane: IntelligenceJudgmentLane) -> UUID | None:
        return (
            self.target_predecessor
            if lane is IntelligenceJudgmentLane.TARGET
            else self.catalog_predecessor
        )

    def interim_until(self, lane: IntelligenceJudgmentLane) -> datetime | None:
        return (
            self.target_interim_until
            if lane is IntelligenceJudgmentLane.TARGET
            else self.catalog_interim_until
        )


@dataclass(frozen=True, slots=True)
class IntelligenceJudgmentActDraft:
    """An owner correction awaiting its trusted durable knowledge boundary."""

    # duplicate-code: The Intelligence and Portfolio owner act shapes evolve
    # independently; sharing these fields would couple distinct domain histories.
    # arid: disable
    act_id: UUID
    root: IntelligenceJudgmentRoot
    attribution: ActorAttribution
    basis: str
    effective_at: datetime
    ancestry: tuple[UUID, ...]
    assertion: IntelligenceJudgmentAssertion | None = None
    catalog: IntelligenceClaimCatalog | None = None
    target_predecessor: UUID | None = None
    catalog_predecessor: UUID | None = None
    pending_resolutions: tuple[PendingResolution, ...] = ()
    compatible_opposite_acts: tuple[UUID, ...] = ()
    target_interim_until: datetime | None = None
    catalog_interim_until: datetime | None = None
    # arid: enable
    target_status: IntelligenceJudgmentStatus | None = None
    contested_catalog: bool = False

    def at_boundary(self, known_at: datetime) -> IntelligenceJudgmentAct:
        """Build an act at a supplied knowledge boundary for validation or read."""
        return IntelligenceJudgmentAct(
            act_id=self.act_id,
            root=self.root,
            attribution=self.attribution,
            basis=self.basis,
            effective_at=self.effective_at,
            recorded_at=known_at,
            known_at=known_at,
            ancestry=self.ancestry,
            assertion=self.assertion,
            catalog=self.catalog,
            target_predecessor=self.target_predecessor,
            catalog_predecessor=self.catalog_predecessor,
            pending_resolutions=self.pending_resolutions,
            compatible_opposite_acts=self.compatible_opposite_acts,
            target_interim_until=self.target_interim_until,
            catalog_interim_until=self.catalog_interim_until,
            target_status=self.target_status,
            contested_catalog=self.contested_catalog,
        )


@dataclass(frozen=True, slots=True)
class IntelligenceJudgmentSelection:
    target_act: IntelligenceJudgmentAct
    catalog_act: IntelligenceJudgmentAct
    judgment_revision: JudgmentRevision
    catalog_version: ClaimCatalogVersion
    known_ancestry: tuple[IntelligenceJudgmentAct, ...]
    # duplicate-code: Sharing would couple distinct owner statuses.
    # arid: disable
    version_history: tuple[tuple[JudgmentRevision, ClaimCatalogVersion], ...]

    @property
    def assertion(self) -> IntelligenceJudgmentAssertion | None:
        return self.target_act.assertion

    @property
    def catalog(self) -> IntelligenceClaimCatalog | None:
        return self.catalog_act.catalog

    @property
    def target_support(self) -> tuple[IntelligenceJudgmentAct, ...]:
        by_id = {item.act_id: item for item in self.known_ancestry}
        lineage = []
        current: IntelligenceJudgmentAct | None = self.target_act
        while current is not None:
            lineage.append(current)
            predecessor = current.target_predecessor
            current = None if predecessor is None else by_id[predecessor]
        return tuple(reversed(lineage))

    # arid: enable


# duplicate-code: Sharing would couple distinct owner statuses.
# arid: disable
# jscpd:ignore-start
@dataclass(frozen=True, slots=True)
class IntelligenceJudgmentHistory:
    """Complete, append-only owner history for one typed target root."""

    acts: tuple[IntelligenceJudgmentAct, ...]
    versions: tuple[tuple[JudgmentRevision, ClaimCatalogVersion], ...]

    def __post_init__(self) -> None:
        if not self.acts or len(self.acts) != len(self.versions):
            raise InvalidIntelligenceJudgmentHistory(
                "complete owner versions are required"
            )
        if any(item.root != self.acts[0].root for item in self.acts):
            raise InvalidIntelligenceJudgmentHistory("history mixes target roots")

    @classmethod
    def form(cls, initial: IntelligenceJudgmentAct) -> IntelligenceJudgmentHistory:
        if (
            initial.ancestry
            or initial.assertion is None
            or initial.catalog is None
            or initial.target_status is not IntelligenceJudgmentStatus.ACTIVE
        ):
            raise InvalidIntelligenceJudgmentHistory(
                "root act requires assertion and complete claim catalog"
            )
        if initial.effective_at > initial.known_at:
            raise InvalidIntelligenceJudgmentHistory(
                "root formation must have current owner meaning"
            )
        return cls((initial,), ((JudgmentRevision(1), ClaimCatalogVersion(1)),))

    def append(self, act: IntelligenceJudgmentAct) -> IntelligenceJudgmentHistory:
        prior = self.acts
        if act.root != prior[0].root:
            raise InvalidIntelligenceJudgmentHistory("correction has wrong typed root")
        if act.ancestry != tuple(item.act_id for item in prior):
            raise InvalidIntelligenceJudgmentHistory(
                "correction ancestry is incomplete"
            )
        if act.known_at < prior[-1].known_at:
            raise InvalidIntelligenceJudgmentHistory("owner knowledge must be ordered")
        if act.act_id in act.ancestry:
            raise InvalidIntelligenceJudgmentHistory("act reference already exists")
        if act.assertion is not None and _lineage(act.assertion) != _lineage(
            prior[0].assertion
        ):
            raise InvalidIntelligenceJudgmentHistory(
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
                raise InvalidIntelligenceJudgmentHistory(
                    "a materially changed proposition requires a fresh ClaimId"
                )
        for lane in IntelligenceJudgmentLane:
            self._check_pending_resolution(act, lane)
        before = self.select(act.known_at, act.known_at)
        candidate = IntelligenceJudgmentHistory(
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
        return IntelligenceJudgmentHistory((*prior, act), (*self.versions, versions))

    def select(
        self, effective_at: datetime, known_at: datetime
    ) -> IntelligenceJudgmentSelection:
        _aware(effective_at, "effective_at")
        _aware(known_at, "known_at")
        known = tuple(item for item in self.acts if item.known_at <= known_at)
        if not known:
            raise InvalidIntelligenceJudgmentHistory("target not known at cutoff")
        target = self._selected(known, IntelligenceJudgmentLane.TARGET, effective_at)
        catalog = self._selected(known, IntelligenceJudgmentLane.CATALOG, effective_at)
        if target is None or catalog is None:
            raise IntelligenceJudgmentNotYetEffective("target not yet effective")
        if not _coherent(target, catalog):
            raise InvalidIntelligenceJudgmentHistory(
                "target and catalog are incompatible"
            )
        index = len(known) - 1
        return IntelligenceJudgmentSelection(
            target, catalog, *self.versions[index], known, self.versions[: index + 1]
        )

    def _selected(
        self,
        known: tuple[IntelligenceJudgmentAct, ...],
        lane: IntelligenceJudgmentLane,
        effective_at: datetime,
    ) -> IntelligenceJudgmentAct | None:
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
            raise InvalidIntelligenceJudgmentHistory("lane has no unique selected act")
        return leaves[0]

    def _check_pending_resolution(
        self, act: IntelligenceJudgmentAct, lane: IntelligenceJudgmentLane
    ) -> None:
        resolutions = {
            item.pending_act_id: item.disposition
            for item in act.pending_resolutions
            if item.lane is lane
        }
        if not act.changes(lane):
            if resolutions:
                raise InvalidIntelligenceJudgmentHistory(
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
            and item.effective_at >= act.effective_at
            and item.act_id not in canceled
        ]
        if set(resolutions) != {item.act_id for item in pending}:
            raise InvalidIntelligenceJudgmentHistory(
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
                raise InvalidIntelligenceJudgmentHistory(
                    "interim act must end at retained successor boundary"
                )
        elif act.interim_until(lane) is not None:
            raise InvalidIntelligenceJudgmentHistory(
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


def _coherent(
    target: IntelligenceJudgmentAct, catalog: IntelligenceJudgmentAct
) -> bool:
    # An unchanged lane keeps its complete owner declaration. The affected act
    # must explicitly name the opposite selected lane when it changes alone.
    if target.act_id == catalog.act_id:
        return True
    return (
        target.act_id in catalog.compatible_opposite_acts
        or catalog.act_id in target.compatible_opposite_acts
    )


# jscpd:ignore-end
# arid: enable


def _target_meaning(act: IntelligenceJudgmentAct) -> tuple[object, ...]:
    return (act.assertion, act.attribution, act.basis, act.target_status)


def _assertion_root(
    assertion: IntelligenceJudgmentAssertion,
) -> IntelligenceJudgmentRoot:
    if type(assertion) not in (
        InvestmentHypothesis,
        InvestmentView,
        MeaningfulChallengeResult,
        InvestmentRecommendation,
        RecommendationWithholdingJudgment,
    ):
        raise TypeError("assertion must be an Investment Intelligence target")
    return assertion.evidence_target


def _lineage(assertion: IntelligenceJudgmentAssertion | None) -> tuple[object, ...]:
    if assertion is None:
        raise TypeError("assertion must be an Investment Intelligence target")
    return (type(assertion), assertion.decision_id)


# duplicate-code: Sharing would couple distinct owner statuses.
# arid: disable
def _uuid4(value: UUID, field: str) -> None:
    if type(value) is not UUID or value.version != 4:
        raise TypeError(f"{field} must be UUIDv4")


def _aware(value: datetime, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable
