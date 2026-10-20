from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from polaris.domain.evidence.context_versions import (
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
)
from polaris.domain.evidence.judgments import ClaimId
from polaris.domain.evidence.observations import EvidenceObservationId
from polaris.domain.portfolio_consequences import ProjectedChange
from polaris.domain.portfolio_judgment_history import (
    InvalidPortfolioJudgmentHistory,
    PendingDisposition,
    PendingResolution,
    PortfolioClaim,
    PortfolioClaimCatalog,
    PortfolioJudgmentAct,
    PortfolioJudgmentHistory,
    PortfolioJudgmentLane,
)
from tests.domain.test_portfolio_consequences import _consequence, _state
from tests.domain.test_portfolio_risk import _assess

K0 = datetime(2026, 10, 20, 0, tzinfo=UTC)
K1 = datetime(2026, 10, 21, 0, tzinfo=UTC)
K2 = datetime(2026, 10, 22, 0, tzinfo=UTC)
T3 = datetime(2026, 10, 23, 0, tzinfo=UTC)


def _assertion(family: str):
    state = _state()
    if family == "consequence":
        return _consequence(
            state,
            DecisionAlternativeVersionRef(
                DecisionAlternativeId(uuid4()), DecisionAlternativeRevision(1)
            ),
            ProjectedChange(Decimal("10000")),
        )
    return _assess(state)


def _root(assertion):
    return getattr(assertion, "consequence_id", None) or assertion.assessment_id


def _catalog(proposition: str, claim_id: ClaimId | None = None):
    claim_id = ClaimId(uuid4()) if claim_id is None else claim_id
    return PortfolioClaimCatalog(
        (
            PortfolioClaim(
                claim_id,
                proposition,
                frozenset({EvidenceObservationId(uuid4())}),
            ),
        )
    )


def _history(family: str):
    assertion = _assertion(family)
    initial = PortfolioJudgmentAct(
        uuid4(),
        _root(assertion),
        assertion.attribution,
        "initial owner basis",
        K0,
        K0,
        K0,
        (),
        assertion=assertion,
        catalog=_catalog("original proposition"),
    )
    return PortfolioJudgmentHistory.form(initial)


def _correction(
    history: PortfolioJudgmentHistory,
    *,
    effective_at: datetime,
    known_at: datetime,
    scenario: str,
    proposition: str,
    disposition: PendingDisposition | None = None,
):
    initial = history.acts[0]
    pending = history.acts[-1] if len(history.acts) > 1 else None
    resolutions = ()
    interim_until = None
    if disposition is not None and pending is not None:
        resolutions = tuple(
            PendingResolution(lane, pending.act_id, disposition)
            for lane in PortfolioJudgmentLane
        )
        if disposition is PendingDisposition.RETAIN:
            interim_until = pending.effective_at
    return PortfolioJudgmentAct(
        uuid4(),
        initial.root,
        initial.attribution,
        f"{scenario} owner basis",
        effective_at,
        known_at,
        known_at,
        tuple(item.act_id for item in history.acts),
        assertion=replace(initial.assertion, scenario=scenario),
        catalog=_catalog(proposition),
        target_predecessor=initial.act_id,
        catalog_predecessor=initial.act_id,
        pending_resolutions=resolutions,
        target_interim_until=interim_until,
        catalog_interim_until=interim_until,
    )


@pytest.mark.parametrize("family", ["consequence", "risk"])
@pytest.mark.parametrize("disposition", list(PendingDisposition))
def test_future_and_immediate_overlap_preserves_every_history_cut(
    family: str, disposition: PendingDisposition
) -> None:
    history = _history(family)
    future = _correction(
        history,
        effective_at=T3,
        known_at=K1,
        scenario="B",
        proposition="future proposition",
    )
    history = history.append(future)
    assert history.select(K1, K1).assertion == history.acts[0].assertion
    assert history.select(T3, K1).assertion == future.assertion
    assert history.select(T3, K1).judgment_revision.value == 1
    assert history.select(T3, K0).assertion == history.acts[0].assertion
    immediate = _correction(
        history,
        effective_at=K2,
        known_at=K2,
        scenario="C",
        proposition="interim proposition",
        disposition=disposition,
    )
    history = history.append(immediate)
    assert history.select(K1, K2).assertion == history.acts[0].assertion
    assert history.select(K2, K2).assertion == immediate.assertion
    assert history.select(K2, K2).judgment_revision.value == 2
    assert history.select(K2, K2).catalog_version.value == 2
    assert history.select(T3, K1).assertion == future.assertion
    selected_at_t3 = history.select(T3, T3)
    expected = immediate if disposition is PendingDisposition.CANCEL else future
    assert selected_at_t3.assertion == expected.assertion
    assert selected_at_t3.catalog == expected.catalog
    assert selected_at_t3.judgment_revision.value == 2
    assert selected_at_t3.catalog_version.value == 2


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_independent_lanes_keep_versions_and_pairing_coherent(family: str) -> None:
    history = _history(family)
    initial = history.acts[0]
    future_target = PortfolioJudgmentAct(
        uuid4(),
        initial.root,
        initial.attribution,
        "future target basis",
        T3,
        K1,
        K1,
        (initial.act_id,),
        assertion=replace(initial.assertion, scenario="Future target only"),
        target_predecessor=initial.act_id,
        compatible_opposite_acts=(initial.act_id,),
    )
    history = history.append(future_target)
    assert history.versions[-1][0].value == 1
    assert history.versions[-1][1].value == 1
    catalog_only = PortfolioJudgmentAct(
        uuid4(),
        initial.root,
        initial.attribution,
        "catalog only basis",
        K2,
        K2,
        K2,
        (initial.act_id, future_target.act_id),
        catalog=_catalog("independent catalog proposition"),
        catalog_predecessor=initial.act_id,
        compatible_opposite_acts=(initial.act_id, future_target.act_id),
    )
    history = history.append(catalog_only)
    assert history.versions[-1][0].value == 1
    assert history.versions[-1][1].value == 2
    selected = history.select(T3, T3)
    assert selected.assertion == future_target.assertion
    assert selected.catalog == catalog_only.catalog
    assert selected.judgment_revision.value == 1
    assert selected.catalog_version.value == 2
    bad = replace(
        catalog_only,
        compatible_opposite_acts=(initial.act_id,),
    )
    with pytest.raises(InvalidPortfolioJudgmentHistory, match="incompatible"):
        PortfolioJudgmentHistory.form(initial).append(future_target).append(bad)


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_implicit_overlap_and_wrong_root_are_rejected_without_history_write(
    family: str,
) -> None:
    history = _history(family)
    # duplicate-code: rejection reconstructs the overlap independently of
    # successful selection so a shared fixture cannot mask admission errors.
    # arid: disable
    future = _correction(
        history,
        effective_at=T3,
        known_at=K1,
        scenario="B",
        proposition="future proposition",
    )
    history = history.append(future)
    immediate = _correction(
        history,
        effective_at=K2,
        known_at=K2,
        scenario="C",
        proposition="current proposition",
    )
    # arid: enable
    with pytest.raises(InvalidPortfolioJudgmentHistory, match="pending"):
        history.append(immediate)
    assert len(history.acts) == 2
    assert history.select(T3, K1).assertion == future.assertion
    with pytest.raises(ValueError, match="typed root"):
        replace(immediate, root=_root(_assertion(family)))
