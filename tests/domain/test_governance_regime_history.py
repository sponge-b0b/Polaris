from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.evidence.context_versions import InvestmentAuthorityRegimeId
from polaris.domain.governance_authority import (
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
)
from polaris.domain.governance_regime_history import (
    AuthorityRegimeCorrectionDraft,
    AuthorityRegimeHistory,
    AuthorityRegimeNeedsReevaluation,
    AuthorityRegimeStatus,
    InvalidAuthorityRegimeHistory,
)
from polaris.domain.portfolio import PortfolioId

AT = datetime(2026, 11, 1, 12, tzinfo=UTC)


def _root() -> InvestmentAuthorityRegime:
    # duplicate-code: Regime history and authority validity tests require independent
    # regime fixtures so their falsifiers do not share construction.
    # arid: disable
    return InvestmentAuthorityRegime(
        InvestmentAuthorityRegimeId(uuid4()),
        ActorId(uuid4()),
        PortfolioId(uuid4()),
        InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
        # arid: enable
        AT - timedelta(days=1),
        None,
    )


def _correction(
    root: InvestmentAuthorityRegime,
    *,
    effective_at: datetime = AT,
    status: AuthorityRegimeStatus = AuthorityRegimeStatus.DETERMINATE,
    replacement: InvestmentAuthorityRegime | None = None,
) -> AuthorityRegimeCorrectionDraft:
    return AuthorityRegimeCorrectionDraft(
        uuid4(),
        root.regime_id,
        KnownActorAttribution(root.actor_id),
        "attributable authority review",
        effective_at,
        status,
        replacement if status is AuthorityRegimeStatus.DETERMINATE else None,
    )


def test_root_revision_and_historical_selection() -> None:
    root = _root()
    history = AuthorityRegimeHistory.form(root, AT)
    selected = history.select(AT, AT)
    assert selected is not None
    assert selected.reference.revision.value == 1
    assert selected.regime == root
    assert history.select(AT, AT - timedelta(microseconds=1)) is None


def test_current_scope_change_advances_once_and_retains_history() -> None:
    root = _root()
    changed = replace(root, actor_id=ActorId(uuid4()))
    draft = _correction(root, replacement=changed)
    committed = AT + timedelta(seconds=1)
    history = AuthorityRegimeHistory.form(root, AT).append(draft.at_boundary(committed))
    before = history.select(AT, AT)
    after = history.select(committed, committed)
    assert before is not None and before.regime == root
    assert after is not None and after.regime == changed
    assert after.reference.revision.value == 2
    assert after.support == (draft.correction_id,)


def test_contested_and_withdrawn_authority_never_returns_a_grant() -> None:
    root = _root()
    for status in (AuthorityRegimeStatus.CONTESTED, AuthorityRegimeStatus.WITHDRAWN):
        committed = AT + timedelta(seconds=1)
        history = AuthorityRegimeHistory.form(root, AT).append(
            _correction(root, status=status).at_boundary(committed)
        )
        selected = history.select(committed, committed)
        assert selected is not None
        assert selected.status is status
        assert selected.regime is None
        assert selected.reference.revision.value == 2


def test_future_effect_does_not_issue_clock_revision() -> None:
    root = _root()
    future = AT + timedelta(days=1)
    history = AuthorityRegimeHistory.form(root, AT).append(
        _correction(
            root,
            effective_at=future,
            replacement=replace(root, actor_id=ActorId(uuid4())),
        ).at_boundary(AT + timedelta(seconds=1))
    )
    current = history.select(AT + timedelta(seconds=1), AT + timedelta(seconds=1))
    assert current is not None and current.reference.revision.value == 1
    with pytest.raises(AuthorityRegimeNeedsReevaluation):
        history.select(future, future)


def test_wrong_root_correction_fails_closed() -> None:
    root = _root()
    other = _root()
    with pytest.raises(InvalidAuthorityRegimeHistory, match="root"):
        AuthorityRegimeHistory.form(root, AT).append(
            _correction(other, replacement=other).at_boundary(AT)
        )
