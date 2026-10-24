"""Exact known/effective correction histories for Intelligence Evidence targets."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application.evidence.claims import InvalidClaimReference
from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentClaimResolver,
)
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.decisions import InvestmentDecisionId
from polaris.domain.evidence import ClaimId
from polaris.domain.evidence.judgments import (
    InvestmentHypothesisRef,
    InvestmentViewRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceClaim,
    IntelligenceClaimCatalog,
    IntelligenceJudgmentAct,
    IntelligenceJudgmentHistory,
    IntelligenceJudgmentLane,
    IntelligenceJudgmentRoot,
    IntelligenceJudgmentStatus,
    InvalidIntelligenceJudgmentHistory,
    PendingDisposition,
    PendingResolution,
)
from polaris.domain.investment_intelligence import InvestmentHypothesis

K0 = datetime(2026, 10, 23, tzinfo=UTC)
K1 = K0 + timedelta(days=1)
K2 = K0 + timedelta(days=2)
T3 = K0 + timedelta(days=3)
T4 = K0 + timedelta(days=4)


def _initial() -> IntelligenceJudgmentHistory:
    root = InvestmentHypothesisRef(uuid4())
    assertion = InvestmentHypothesis(
        root,
        InvestmentDecisionId(uuid4()),
        "A",
        InvestmentViewRef(uuid4()),
        UnknownActorAttribution(),
        K0,
    )
    act = IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=root,
        attribution=UnknownActorAttribution(),
        basis="initial material judgment",
        effective_at=K0,
        recorded_at=K0,
        known_at=K0,
        ancestry=(),
        assertion=assertion,
        catalog=IntelligenceClaimCatalog(
            (IntelligenceClaim(ClaimId(uuid4()), "A means growth", frozenset()),)
        ),
        target_status=IntelligenceJudgmentStatus.ACTIVE,
    )
    return IntelligenceJudgmentHistory.form(act)


def _future(history: IntelligenceJudgmentHistory) -> IntelligenceJudgmentAct:
    initial = history.acts[0]
    # duplicate-code: Sharing would couple correction falsifiers.
    # arid: disable
    assert initial.assertion is not None
    return IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=initial.root,
        attribution=UnknownActorAttribution(),
        basis="future owner correction",
        effective_at=T3,
        recorded_at=K1,
        known_at=K1,
        ancestry=(initial.act_id,),
        # arid: enable
        assertion=replace(initial.assertion, statement="B"),
        target_predecessor=initial.act_id,
        compatible_opposite_acts=(initial.act_id,),
        target_status=IntelligenceJudgmentStatus.ACTIVE,
    )


def _immediate(
    history: IntelligenceJudgmentHistory,
    disposition: PendingDisposition | None,
) -> IntelligenceJudgmentAct:
    initial, future = history.acts
    assert initial.assertion is not None
    return IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=initial.root,
        attribution=UnknownActorAttribution(),
        basis="current owner correction",
        # duplicate-code: Sharing would couple correction falsifiers.
        # arid: disable
        effective_at=K2,
        recorded_at=K2,
        known_at=K2,
        ancestry=(initial.act_id, future.act_id),
        # arid: enable
        assertion=replace(initial.assertion, statement="C"),
        target_predecessor=initial.act_id,
        pending_resolutions=(
            ()
            if disposition is None
            else (
                PendingResolution(
                    IntelligenceJudgmentLane.TARGET, future.act_id, disposition
                ),
            )
        ),
        compatible_opposite_acts=(initial.act_id,),
        target_interim_until=(T3 if disposition is PendingDisposition.RETAIN else None),
        target_status=IntelligenceJudgmentStatus.ACTIVE,
    )


def test_future_correction_needs_explicit_overlap_resolution() -> None:
    history = _initial()
    future = _future(history)
    history = history.append(future)
    assert history.versions[-1] == history.versions[0]
    assert history.select(K1, K1).assertion.statement == "A"
    assert history.select(T3, K1).assertion.statement == "B"
    with pytest.raises(InvalidIntelligenceJudgmentHistory):
        history.append(_immediate(history, None))


# duplicate-code: Sharing would couple correction falsifiers.
# arid: disable
@pytest.mark.parametrize(
    ("disposition", "expected"),
    [
        (PendingDisposition.CANCEL, "C"),
        (PendingDisposition.RETAIN, "B"),
    ],
)
def test_cancellation_or_interim_retention_preserves_exact_t_k(
    disposition: PendingDisposition, expected: str
) -> None:
    history = _initial()
    # arid: enable
    history = history.append(_future(history))
    history = history.append(_immediate(history, disposition))
    assert history.versions[-1][0].value == 2
    assert history.versions[-1][1].value == 1
    assert history.select(K2, K2).assertion.statement == "C"
    assert history.select(T3, K1).assertion.statement == "B"
    assert history.select(T3, K2).assertion.statement == expected
    assert history.select(T3, K2).judgment_revision.value == 2


@pytest.mark.parametrize(
    ("disposition", "expected"),
    [
        (PendingDisposition.CANCEL, "C"),
        (PendingDisposition.RETAIN, "B"),
    ],
)
def test_complete_claim_catalog_requires_explicit_overlap_resolution(
    disposition: PendingDisposition, expected: str
) -> None:
    history = _initial()
    initial = history.acts[0]
    assert initial.catalog is not None
    claim_id = initial.catalog.claims[0].claim_id
    added_claim = ClaimId(uuid4())
    future = IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=initial.root,
        attribution=UnknownActorAttribution(),
        basis="future complete catalog",
        effective_at=T3,
        recorded_at=K1,
        known_at=K1,
        ancestry=(initial.act_id,),
        catalog=IntelligenceClaimCatalog(
            (
                IntelligenceClaim(claim_id, "A means growth", frozenset()),
                IntelligenceClaim(added_claim, "B adds material support", frozenset()),
            )
        ),
        catalog_predecessor=initial.act_id,
        compatible_opposite_acts=(initial.act_id,),
    )
    history = history.append(future)
    assert history.versions[-1] == history.versions[0]
    assert history.select(T3, K1).catalog_act.act_id == future.act_id

    def immediate(resolution: PendingDisposition | None) -> IntelligenceJudgmentAct:
        # duplicate-code: Sharing would couple correction falsifiers.
        # arid: disable
        return IntelligenceJudgmentAct(
            act_id=uuid4(),
            root=initial.root,
            attribution=UnknownActorAttribution(),
            basis="current complete catalog",
            effective_at=K2,
            recorded_at=K2,
            known_at=K2,
            ancestry=(initial.act_id, future.act_id),
            catalog=IntelligenceClaimCatalog(()),
            catalog_predecessor=initial.act_id,
            pending_resolutions=(
                ()
                if resolution is None
                else (
                    PendingResolution(
                        IntelligenceJudgmentLane.CATALOG,
                        future.act_id,
                        resolution,
                    ),
                )
            ),
            compatible_opposite_acts=(initial.act_id,),
            catalog_interim_until=(
                T3 if resolution is PendingDisposition.RETAIN else None
            ),
        )
        # arid: enable

    with pytest.raises(InvalidIntelligenceJudgmentHistory):
        history.append(immediate(None))
    history = history.append(immediate(disposition))
    assert history.versions[-1][0].value == 1
    assert history.versions[-1][1].value == 2
    assert history.select(K2, K2).catalog == IntelligenceClaimCatalog(())
    selected = history.select(T3, K2)
    assert selected.catalog_act.act_id == (
        history.acts[-1].act_id if expected == "C" else future.act_id
    )
    assert selected.catalog.has(added_claim) is (expected == "B")
    assert selected.catalog_version.value == 2


def test_clock_activation_changes_meaning_without_issuing_owner_version() -> None:
    history = _initial()
    history = history.append(_future(history))
    prior = history.select(K1, K1)
    activated = history.select(T3, K1)
    assert prior.assertion.statement == "A"
    assert activated.assertion.statement == "B"
    assert activated.judgment_revision == prior.judgment_revision
    assert activated.version_history == prior.version_history


def test_later_scheduled_successor_preserves_prior_pending_interval() -> None:
    history = _initial()
    initial = history.acts[0]
    future = _future(history)
    history = history.append(future)
    assert future.assertion is not None
    # duplicate-code: Target and catalog successors prove separate lanes.
    # arid: disable
    successor = IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=initial.root,
        attribution=UnknownActorAttribution(),
        basis="later scheduled owner correction",
        effective_at=T4,
        recorded_at=K2,
        known_at=K2,
        ancestry=(initial.act_id, future.act_id),
        assertion=replace(future.assertion, statement="C"),
        target_predecessor=future.act_id,
        compatible_opposite_acts=(initial.act_id,),
        target_status=IntelligenceJudgmentStatus.ACTIVE,
    )
    # arid: enable
    history = history.append(successor)
    assert history.select(K2, K2).assertion == initial.assertion
    assert history.select(T3, K2).assertion == future.assertion
    assert history.select(T4, K2).assertion == successor.assertion


def test_later_catalog_successor_preserves_prior_pending_interval() -> None:
    history = _initial()
    initial = history.acts[0]
    assert initial.catalog is not None
    future_catalog = IntelligenceClaimCatalog(
        (*initial.catalog.claims, IntelligenceClaim(ClaimId(uuid4()), "B", frozenset()))
    )
    # duplicate-code: The catalog lane must keep its own explicit chronology.
    # arid: disable
    future = IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=initial.root,
        attribution=UnknownActorAttribution(),
        basis="future catalog",
        effective_at=T3,
        recorded_at=K1,
        known_at=K1,
        ancestry=(initial.act_id,),
        catalog=future_catalog,
        catalog_predecessor=initial.act_id,
        compatible_opposite_acts=(initial.act_id,),
    )
    history = history.append(future)
    successor = IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=initial.root,
        attribution=UnknownActorAttribution(),
        basis="later catalog",
        effective_at=T4,
        recorded_at=K2,
        known_at=K2,
        ancestry=(initial.act_id, future.act_id),
        catalog=initial.catalog,
        catalog_predecessor=future.act_id,
        compatible_opposite_acts=(initial.act_id,),
    )
    # arid: enable
    history = history.append(successor)
    assert history.select(K2, K2).catalog == initial.catalog
    assert history.select(T3, K2).catalog == future_catalog
    assert history.select(T4, K2).catalog == successor.catalog


def test_claim_resolver_never_infers_claims_or_reuses_another_target_claim() -> None:
    first = _initial()
    second = _initial()
    first_act = first.acts[0]
    second_act = second.acts[0]
    assert first_act.catalog is not None
    claim_id = first_act.catalog.claims[0].claim_id
    assert second_act.assertion is not None
    narrative_only = IntelligenceJudgmentHistory.form(
        replace(
            second_act,
            assertion=replace(second_act.assertion, statement="A means growth"),
            catalog=IntelligenceClaimCatalog(()),
        )
    )

    class Store:
        async def load(
            self, root: IntelligenceJudgmentRoot
        ) -> IntelligenceJudgmentHistory | None:
            return {
                first_act.root: first,
                second_act.root: narrative_only,
            }.get(root)

        async def append(
            self, act: IntelligenceJudgmentAct
        ) -> IntelligenceJudgmentHistory:
            raise AssertionError("claim read cannot append owner history")

    resolver = IntelligenceJudgmentClaimResolver(Store())
    result = asyncio.run(
        resolver.resolve(second_act.root, claim_id, effective_at=K0, known_at=K0)
    )
    assert type(result) is InvalidClaimReference
    with pytest.raises(TypeError, match="typed target and ClaimId"):
        asyncio.run(
            resolver.resolve(
                second_act.root,
                str(claim_id.value),  # type: ignore[arg-type]
                effective_at=K0,
                known_at=K0,
            )
        )
