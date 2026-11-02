"""Governance target root revisions and historical correction interpretation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.domain.evidence.judgment_versions import JudgmentRevision
from polaris.domain.governance_judgment_history import (
    HumanDecisionTargetCorrectionDraft,
    HumanDecisionTargetEffect,
    HumanDecisionTargetHistory,
    HumanDecisionTargetNeedsReevaluation,
    HumanDecisionTargetNotKnown,
    HumanDecisionTargetStatus,
    InvalidHumanDecisionTargetHistory,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from tests.domain.test_human_investment_decision import _fact

ROOT_COMMIT = datetime(2026, 11, 1, 12, tzinfo=UTC)


def _correction(
    fact,
    *,
    target=None,
    choice=EconomicDisposition.INCREASE,
    effect=HumanDecisionTargetEffect.REVISE,
    effective_at=ROOT_COMMIT,
):
    return HumanDecisionTargetCorrectionDraft(
        uuid4(),
        fact.decision_ref,
        fact.decision_ref if target is None else target,
        fact.actor,
        "Correct the recorded human choice",
        effective_at,
        effect,
        replace(fact, choice=choice)
        if effect is HumanDecisionTargetEffect.REVISE
        else None,
    )


def test_owner_revision_stays_with_root_and_historical_cutoff() -> None:
    fact = _fact()
    history = HumanDecisionTargetHistory.form(fact, ROOT_COMMIT)
    initial = history.select(ROOT_COMMIT, ROOT_COMMIT)
    assert initial.version.revision == JudgmentRevision(1)
    assert initial.assertion == fact
    with pytest.raises(HumanDecisionTargetNotKnown):
        history.select(ROOT_COMMIT, ROOT_COMMIT - timedelta(microseconds=1))

    correction = _correction(fact)
    later = ROOT_COMMIT + timedelta(seconds=1)
    history = history.append(correction.at_boundary(later))
    assert history.select(later, later).version.revision == JudgmentRevision(2)
    assert history.select(later, later).assertion == correction.replacement
    assert history.select(later, ROOT_COMMIT).assertion == fact
    assert history.select(later, ROOT_COMMIT).version.revision == JudgmentRevision(1)

    another_root = HumanDecisionTargetHistory.form(_fact(), later)
    assert another_root.select(later, later).version.revision == JudgmentRevision(1)


def test_future_only_correction_does_not_advance_current_revision() -> None:
    fact = _fact()
    history = HumanDecisionTargetHistory.form(fact, ROOT_COMMIT)
    later = ROOT_COMMIT + timedelta(seconds=1)
    future = _correction(fact, effective_at=later + timedelta(days=1))
    history = history.append(future.at_boundary(later))
    current = history.select(later, later)
    assert current.assertion == fact
    assert current.version.revision == JudgmentRevision(1)
    future_read = history.select(future.effective_at, later)
    assert future_read.assertion == future.replacement
    assert future_read.version.revision == JudgmentRevision(1)
    with pytest.raises(HumanDecisionTargetNeedsReevaluation):
        history.select(future.effective_at, future.effective_at)

    revalidated_at = future.effective_at + timedelta(seconds=1)
    next_future = _correction(fact, effective_at=revalidated_at + timedelta(days=1))
    history = history.append(next_future.at_boundary(revalidated_at))
    current_after_commit = history.select(revalidated_at, revalidated_at)
    assert current_after_commit.assertion == future.replacement
    assert current_after_commit.version.revision == JudgmentRevision(2)


def test_retraction_of_pending_correction_keeps_current_root() -> None:
    fact = _fact()
    history = HumanDecisionTargetHistory.form(fact, ROOT_COMMIT)
    one = ROOT_COMMIT + timedelta(seconds=1)
    two = ROOT_COMMIT + timedelta(seconds=2)
    future = _correction(fact, effective_at=two + timedelta(days=1))
    history = history.append(future.at_boundary(one))
    cancel = _correction(
        fact,
        target=future.correction_id,
        effect=HumanDecisionTargetEffect.RETRACT,
        effective_at=two,
    )
    history = history.append(cancel.at_boundary(two))
    assert history.select(two, two).assertion == fact
    assert history.select(two, two).version.revision == JudgmentRevision(1)
    assert history.select(future.effective_at, two).assertion == fact


def test_competing_corrections_contest_and_retraction_restores_branch() -> None:
    fact = _fact()
    history = HumanDecisionTargetHistory.form(fact, ROOT_COMMIT)
    first = _correction(fact, choice=EconomicDisposition.INCREASE)
    second = _correction(fact, choice=EconomicDisposition.REDUCE)
    one = ROOT_COMMIT + timedelta(seconds=1)
    two = ROOT_COMMIT + timedelta(seconds=2)
    history = history.append(first.at_boundary(one))
    history = history.append(second.at_boundary(two))
    contested = history.select(two, two)
    assert contested.status is HumanDecisionTargetStatus.CONTESTED
    assert contested.assertion is None
    assert contested.version.revision == JudgmentRevision(3)

    retract = _correction(
        fact,
        target=first.correction_id,
        effect=HumanDecisionTargetEffect.RETRACT,
    )
    three = ROOT_COMMIT + timedelta(seconds=3)
    history = history.append(retract.at_boundary(three))
    assert history.select(three, three).status is HumanDecisionTargetStatus.CONTESTED
    assert history.select(three, two).status is HumanDecisionTargetStatus.CONTESTED


def test_correction_cannot_change_root_or_target_missing_ancestry() -> None:
    fact = _fact()
    history = HumanDecisionTargetHistory.form(fact, ROOT_COMMIT)
    with pytest.raises(ValueError, match="root"):
        replace(_correction(fact), replacement=_fact())
    missing = _correction(fact, target=uuid4())
    with pytest.raises(InvalidHumanDecisionTargetHistory, match="ancestry"):
        history.append(missing.at_boundary(ROOT_COMMIT + timedelta(seconds=1)))
