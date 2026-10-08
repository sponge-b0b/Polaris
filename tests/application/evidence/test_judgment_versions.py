from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application.evidence.judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentContested,
    TargetJudgmentInvalidHistory,
    TargetJudgmentMissing,
    TargetJudgmentOwnerReadUnavailable,
    TargetJudgmentResolver,
    TargetJudgmentUnavailable,
    TargetJudgmentWithdrawn,
)
from polaris.domain.evidence import (
    ClaimCatalogVersion,
    InvestmentViewRef,
    InvestmentViewVersionRef,
    JudgmentRevision,
)

NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)
ROOT = InvestmentViewRef(uuid4())


@dataclass
class OwnerDouble:
    result: object
    unavailable: bool = False
    received: tuple[object, datetime, datetime] | None = None

    async def read_at(
        self,
        target: InvestmentViewRef,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> object:
        self.received = (target, effective_at, known_at)
        if self.unavailable:
            raise TargetJudgmentOwnerReadUnavailable("owner offline")
        return self.result


def resolved(
    root: InvestmentViewRef = ROOT,
    revision: int = 1,
    *,
    effective_at: datetime = NOW,
    known_at: datetime = NOW,
    assertion: str = "hold",
    support: tuple[str, ...] = ("original",),
) -> ResolvedTargetJudgment[str, str]:
    return ResolvedTargetJudgment(
        root,
        InvestmentViewVersionRef(root, JudgmentRevision(revision)),
        assertion,
        support,
        effective_at,
        known_at,
    )


def test_owner_read_uses_explicit_historical_boundary_and_owner_version() -> None:
    earlier = NOW - timedelta(days=1)
    owner = OwnerDouble(resolved(effective_at=earlier, known_at=earlier))
    resolver = TargetJudgmentResolver(owner)

    result = asyncio.run(
        resolver.read_historical(ROOT, effective_at=earlier, known_at=earlier)
    )

    assert result == owner.result
    assert result.version.revision == JudgmentRevision(1)
    assert result.assertion == "hold"
    assert result.correction_support == ("original",)
    assert owner.received == (ROOT, earlier, earlier)

    owner.result = resolved(revision=2, assertion="buy")
    current = asyncio.run(resolver.read_current(ROOT, at=NOW))
    assert current == owner.result
    assert owner.received == (ROOT, NOW, NOW)


def test_same_root_correction_and_new_root_have_distinct_owner_versions() -> None:
    corrected = resolved(
        revision=2, assertion="hold cautiously", support=("correction",)
    )
    successor_root = InvestmentViewRef(uuid4())
    successor = resolved(successor_root, assertion="reduce", support=("reassessment",))

    assert corrected.version.root == ROOT
    assert corrected.version.revision == JudgmentRevision(2)
    assert successor.version.root == successor_root
    assert successor.version.revision == JudgmentRevision(1)
    assert corrected.version != successor.version

    # The owner's separate catalog epoch can change without changing the root.
    catalog_before = ClaimCatalogVersion(1)
    catalog_after = ClaimCatalogVersion(2)
    root_before = resolved().version
    root_after = resolved().version
    assert catalog_after != catalog_before
    assert root_after == root_before


@dataclass(frozen=True)
class OwnerMeaning:
    assertion: str
    support: tuple[str, ...]
    validity: str
    applicable: bool
    fit_until: datetime | None = None
    provenance: str = "source-1"
    successor: InvestmentViewRef | None = None


@dataclass(frozen=True)
class OwnerRecord:
    root: InvestmentViewRef
    effective_at: datetime
    recorded_at: datetime
    meaning: OwnerMeaning
    revision: JudgmentRevision


class HistoricalOwnerDouble:
    """Linear owner history for contract scenarios, not target fact persistence."""

    def __init__(self) -> None:
        self.records: list[OwnerRecord] = []
        self.current_revisions: dict[InvestmentViewRef, JudgmentRevision] = {}
        self.selected_current: InvestmentViewRef | None = None

    def form(
        self, root: InvestmentViewRef, meaning: OwnerMeaning, *, at: datetime
    ) -> None:
        assert root not in self.current_revisions
        revision = JudgmentRevision(1)
        self.current_revisions[root] = revision
        self.records.append(OwnerRecord(root, at, at, meaning, revision))

    def commit(
        self,
        root: InvestmentViewRef,
        *,
        at: datetime,
        effective_at: datetime,
        changes: tuple[OwnerMeaning, ...],
    ) -> JudgmentRevision:
        """Compare interpreted meaning twice at one command boundary."""
        before = self._meaning(root, effective_at=at, known_at=at)
        assert before is not None
        revision = self.current_revisions[root]
        for meaning in changes:
            self.records.append(OwnerRecord(root, effective_at, at, meaning, revision))
        after = self._meaning(root, effective_at=at, known_at=at)
        assert after is not None
        if self._command_meaning(before.meaning, at) != self._command_meaning(
            after.meaning, at
        ):
            revision = JudgmentRevision(revision.value + 1)
        self.current_revisions[root] = revision
        for index, record in enumerate(self.records):
            if record.root == root and record.recorded_at == at:
                self.records[index] = OwnerRecord(
                    root, record.effective_at, at, record.meaning, revision
                )
        return revision

    def relate_successor(
        self,
        predecessor: InvestmentViewRef,
        successor: InvestmentViewRef,
        *,
        at: datetime,
    ) -> JudgmentRevision:
        """Commit an explicit owner relationship that changes predecessor meaning."""
        assert predecessor != successor
        assert successor in self.current_revisions
        current = self._meaning(predecessor, effective_at=at, known_at=at)
        assert current is not None
        assert current.meaning.successor is None
        return self.commit(
            predecessor,
            at=at,
            effective_at=at,
            changes=(replace(current.meaning, successor=successor, applicable=False),),
        )

    def choose_current(self, root: InvestmentViewRef) -> None:
        assert root in self.current_revisions
        self.selected_current = root

    def read_selected(self, *, at: datetime) -> InvestmentViewRef | None:
        root = self.selected_current
        if root is None:
            return None
        record = self._meaning(root, effective_at=at, known_at=at)
        if record is None or record.meaning.validity != "current":
            return None
        if not record.meaning.applicable or record.meaning.successor is not None:
            return None
        return root

    def selection_guard_holds(
        self, protected: InvestmentViewRef, *, at: datetime
    ) -> bool:
        return self.read_selected(at=at) == protected

    def _meaning(
        self, root: InvestmentViewRef, *, effective_at: datetime, known_at: datetime
    ) -> OwnerRecord | None:
        selected: OwnerRecord | None = None
        for record in self.records:
            if (
                record.root == root
                and record.effective_at <= effective_at
                and record.recorded_at <= known_at
                and (selected is None or record.recorded_at >= selected.recorded_at)
            ):
                selected = record
        return selected

    @staticmethod
    def _command_meaning(meaning: OwnerMeaning, at: datetime) -> tuple[object, ...]:
        fit = meaning.fit_until is None or at < meaning.fit_until
        return (
            meaning.assertion,
            meaning.support,
            meaning.validity,
            meaning.applicable,
            fit,
            meaning.provenance,
            meaning.successor,
        )

    async def read_at(
        self,
        target: InvestmentViewRef,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> object:
        record = self._meaning(target, effective_at=effective_at, known_at=known_at)
        if record is None:
            return TargetJudgmentMissing(target)
        if record.meaning.validity == "withdrawn":
            return TargetJudgmentWithdrawn(target)
        if record.meaning.validity == "contested":
            return TargetJudgmentContested(target, "competing owner support")
        return ResolvedTargetJudgment(
            target,
            InvestmentViewVersionRef(target, record.revision),
            record.meaning,
            record.meaning.support,
            effective_at,
            known_at,
        )


def test_owner_double_advances_once_for_current_material_commit_changes() -> None:
    """Absent owners must meet this epoch contract when they implement facts."""
    owner = HistoricalOwnerDouble()
    start = NOW - timedelta(days=6)
    initial = OwnerMeaning("hold", ("original",), "current", True)
    owner.form(ROOT, initial, at=start)
    assert owner.current_revisions[ROOT] == JudgmentRevision(1)

    correction = OwnerMeaning("hold", ("correction-a",), "current", True)
    combined = OwnerMeaning("hold", ("correction-a", "correction-b"), "current", True)
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=1),
        effective_at=start + timedelta(days=1),
        changes=(correction, combined),
    ) == JudgmentRevision(2)  # Two correction acts in one atomic owner commit.

    assertion_change = OwnerMeaning("reduce", combined.support, "current", True)
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=2),
        effective_at=start + timedelta(days=2),
        changes=(assertion_change,),
    ) == JudgmentRevision(3)
    provenance_change = OwnerMeaning(
        "reduce", combined.support, "current", True, provenance="source-2"
    )
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=2, hours=1),
        effective_at=start + timedelta(days=2, hours=1),
        changes=(provenance_change,),
    ) == JudgmentRevision(4)
    applicability_change = OwnerMeaning(
        "reduce", combined.support, "current", False, provenance="source-2"
    )
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=2, hours=2),
        effective_at=start + timedelta(days=2, hours=2),
        changes=(applicability_change,),
    ) == JudgmentRevision(5)
    withdrawn = OwnerMeaning("reduce", ("retraction",), "withdrawn", False)
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=3),
        effective_at=start + timedelta(days=3),
        changes=(withdrawn,),
    ) == JudgmentRevision(6)
    restored = OwnerMeaning("reduce", ("restoration",), "current", True)
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=4),
        effective_at=start + timedelta(days=4),
        changes=(restored,),
    ) == JudgmentRevision(7)
    contested = OwnerMeaning("reduce", ("branch-a", "branch-b"), "contested", True)
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=5),
        effective_at=start + timedelta(days=5),
        changes=(contested,),
    ) == JudgmentRevision(8)


def test_owner_double_does_not_advance_for_query_clock_or_future_only_append() -> None:
    owner = HistoricalOwnerDouble()
    start = NOW - timedelta(days=2)
    initial = OwnerMeaning(
        "hold", ("original",), "current", True, start + timedelta(days=1)
    )
    owner.form(ROOT, initial, at=start)
    resolver = TargetJudgmentResolver(owner)

    before = asyncio.run(resolver.read_current(ROOT, at=start))
    after_clock = asyncio.run(resolver.read_current(ROOT, at=start + timedelta(days=1)))
    assert before.version.revision == JudgmentRevision(1)
    assert after_clock.version.revision == JudgmentRevision(1)

    future = OwnerMeaning("reduce", ("future",), "current", True)
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=1),
        effective_at=start + timedelta(days=4),
        changes=(future,),
    ) == JudgmentRevision(1)
    # An irrelevant append on another root leaves this root's epoch alone.
    owner.form(InvestmentViewRef(uuid4()), initial, at=start + timedelta(days=1))
    assert owner.current_revisions[ROOT] == JudgmentRevision(1)

    fitness_repaired = OwnerMeaning(
        "hold", ("original",), "current", True, start + timedelta(days=5)
    )
    # duplicate-code: this fitness falsifier keeps the command and effective
    # instants visible; sharing a helper with assertion or relationship proof
    # would hide the independent temporal condition being tested.
    # arid: disable
    assert owner.commit(
        ROOT,
        at=start + timedelta(days=2),
        effective_at=start + timedelta(days=2),
        changes=(fitness_repaired,),
    ) == JudgmentRevision(2)
    # arid: enable


def test_later_root_affects_exact_root_only_through_owner_relationship() -> None:
    owner = HistoricalOwnerDouble()
    start = NOW - timedelta(days=3)
    initial = OwnerMeaning("hold", ("original",), "current", True)
    owner.form(ROOT, initial, at=start)
    owner.choose_current(ROOT)
    old_basis = asyncio.run(TargetJudgmentResolver(owner).read_current(ROOT, at=start))
    assert old_basis.version.revision == JudgmentRevision(1)
    protected_selection = owner.read_selected(at=start)
    assert protected_selection == ROOT

    unrelated = InvestmentViewRef(uuid4())
    owner.form(unrelated, initial, at=start + timedelta(hours=1))
    assert owner.selection_guard_holds(
        protected_selection, at=start + timedelta(hours=1)
    )
    assert owner.current_revisions[ROOT] == JudgmentRevision(1)

    successor = InvestmentViewRef(uuid4())
    owner.form(
        successor,
        OwnerMeaning("reduce", ("reassessment",), "current", True),
        at=start + timedelta(days=1),
    )
    later = start + timedelta(days=1)
    same_exact_root = asyncio.run(
        TargetJudgmentResolver(owner).read_current(ROOT, at=later)
    )
    assert same_exact_root.version == old_basis.version
    assert owner.current_revisions[successor] == JudgmentRevision(1)
    assert owner.selection_guard_holds(protected_selection, at=later)

    # A changed authoritative selection breaks the protected current guard,
    # even though the predecessor's exact-root version has not changed.
    owner.choose_current(successor)
    assert owner.read_selected(at=later) == successor
    assert not owner.selection_guard_holds(protected_selection, at=later)
    assert same_exact_root.version == old_basis.version

    # Linking the successor is a separate owner commit. Its typed relationship
    # changes the predecessor's interpreted applicability and advances that root.
    assert owner.relate_successor(
        ROOT,
        successor,
        at=start + timedelta(days=2),
    ) == JudgmentRevision(2)
    relationship = owner._meaning(
        ROOT,
        effective_at=start + timedelta(days=2),
        known_at=start + timedelta(days=2),
    )
    assert relationship is not None
    assert relationship.meaning.successor == successor
    assert relationship.meaning.support == initial.support
    changed_exact_root = asyncio.run(
        TargetJudgmentResolver(owner).read_current(ROOT, at=start + timedelta(days=2))
    )
    assert changed_exact_root.version.root == ROOT
    assert changed_exact_root.version.revision == JudgmentRevision(2)
    assert changed_exact_root.assertion.successor == successor
    assert not changed_exact_root.assertion.applicable


def test_historical_owner_read_uses_independent_cutoffs() -> None:
    owner = HistoricalOwnerDouble()
    formed = NOW - timedelta(days=4)
    original = OwnerMeaning("hold", ("original",), "current", True)
    owner.form(ROOT, original, at=formed)
    corrected_effective = formed + timedelta(days=1)
    correction_recorded = formed + timedelta(days=2)
    corrected = OwnerMeaning("reduce", ("original", "late-correction"), "current", True)
    assert owner.commit(
        ROOT,
        at=correction_recorded,
        effective_at=corrected_effective,
        changes=(corrected,),
    ) == JudgmentRevision(2)
    resolver = TargetJudgmentResolver(owner)

    before_known = asyncio.run(
        resolver.read_historical(
            ROOT, effective_at=corrected_effective, known_at=formed
        )
    )
    before_effective = asyncio.run(
        resolver.read_historical(
            ROOT, effective_at=formed, known_at=correction_recorded
        )
    )
    corrected_at_boundary = asyncio.run(
        resolver.read_historical(
            ROOT, effective_at=corrected_effective, known_at=correction_recorded
        )
    )
    assert before_known.version.revision == JudgmentRevision(1)
    assert before_effective.version.revision == JudgmentRevision(1)
    assert corrected_at_boundary.version.revision == JudgmentRevision(2)
    assert corrected_at_boundary.assertion.assertion == "reduce"
    assert corrected_at_boundary.correction_support == ("original", "late-correction")

    later = formed + timedelta(days=3)
    assert owner.commit(
        ROOT,
        at=later,
        effective_at=later,
        changes=(OwnerMeaning("reduce", ("restored-support",), "current", True),),
    ) == JudgmentRevision(3)
    earlier_replay = asyncio.run(
        resolver.read_historical(
            ROOT, effective_at=corrected_effective, known_at=correction_recorded
        )
    )
    assert earlier_replay.version.revision == JudgmentRevision(2)
    assert earlier_replay.correction_support == ("original", "late-correction")
    assert owner.current_revisions[ROOT] == JudgmentRevision(3)

    before_formation_effective = asyncio.run(
        resolver.read_historical(
            ROOT, effective_at=formed - timedelta(seconds=1), known_at=later
        )
    )
    before_formation_known = asyncio.run(
        resolver.read_historical(
            ROOT, effective_at=later, known_at=formed - timedelta(seconds=1)
        )
    )
    assert isinstance(before_formation_effective, TargetJudgmentMissing)
    assert isinstance(before_formation_known, TargetJudgmentMissing)


@pytest.mark.parametrize(
    "result",
    [
        TargetJudgmentWithdrawn(ROOT),
        TargetJudgmentContested(ROOT, "incompatible support"),
        TargetJudgmentMissing(ROOT),
        TargetJudgmentInvalidHistory(ROOT, "incomplete ancestry"),
        TargetJudgmentUnavailable(ROOT, "owner offline"),
    ],
)
def test_non_current_owner_results_never_yield_a_command_version(
    result: object,
) -> None:
    read = asyncio.run(
        TargetJudgmentResolver(OwnerDouble(result)).read_current(ROOT, at=NOW)
    )
    assert read == result
    assert not isinstance(read, ResolvedTargetJudgment)


def test_unavailable_and_mismatched_owner_reads_fail_closed() -> None:
    offline = OwnerDouble(resolved(), unavailable=True)
    read = asyncio.run(TargetJudgmentResolver(offline).read_current(ROOT, at=NOW))
    assert read == TargetJudgmentUnavailable(ROOT, "owner offline")

    other = InvestmentViewRef(uuid4())
    owner = OwnerDouble(resolved(other))
    read = asyncio.run(TargetJudgmentResolver(owner).read_current(ROOT, at=NOW))
    assert read == TargetJudgmentInvalidHistory(ROOT, "owner result did not match read")

    owner.result = resolved(effective_at=NOW - timedelta(days=1))
    read = asyncio.run(TargetJudgmentResolver(owner).read_current(ROOT, at=NOW))
    assert isinstance(read, TargetJudgmentInvalidHistory)

    owner.result = TargetJudgmentMissing(other)
    read = asyncio.run(TargetJudgmentResolver(owner).read_current(ROOT, at=NOW))
    assert isinstance(read, TargetJudgmentInvalidHistory)


def test_bad_consumer_inputs_and_mismatched_version_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        asyncio.run(
            TargetJudgmentResolver(OwnerDouble(resolved())).read_current(
                ROOT, at=datetime(2026, 10, 7)
            )
        )
    with pytest.raises(ValueError, match="version root"):
        ResolvedTargetJudgment(
            ROOT,
            InvestmentViewVersionRef(InvestmentViewRef(uuid4()), JudgmentRevision(1)),
            "hold",
            (),
            NOW,
            NOW,
        )
    with pytest.raises(ValueError, match="assertion cannot be missing"):
        ResolvedTargetJudgment(
            ROOT,
            InvestmentViewVersionRef(ROOT, JudgmentRevision(1)),
            None,
            (),
            NOW,
            NOW,
        )
