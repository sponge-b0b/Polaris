from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.domain.actors import (
    ActorId,
    ContestedActorAttribution,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.governance_authority import (
    InvestmentAuthorityCheck,
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
    check_investment_authority,
)
from polaris.domain.portfolio import PortfolioId

NOW = datetime(2026, 10, 31, 12, tzinfo=UTC)


def _regime() -> InvestmentAuthorityRegime:
    return InvestmentAuthorityRegime(
        InvestmentAuthorityRegimeId(uuid4()),
        ActorId(uuid4()),
        PortfolioId(uuid4()),
        InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
        NOW,
        NOW + timedelta(days=1),
    )


def test_exact_power_actor_portfolio_and_time_establish_authority() -> None:
    regime = _regime()
    actor = KnownActorAttribution(regime.actor_id)
    for at in (
        regime.effective_from,
        regime.effective_until - timedelta(microseconds=1),
    ):
        assert (
            check_investment_authority(
                regime,
                actor,
                regime.portfolio_id,
                InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
                at,
            )
            is InvestmentAuthorityCheck.ESTABLISHED
        )


def test_missing_wrong_scope_or_unattributable_authority_fails_closed() -> None:
    regime = _regime()
    actor = KnownActorAttribution(regime.actor_id)
    cases = (
        (None, actor, regime.portfolio_id, NOW),
        (regime, KnownActorAttribution(ActorId(uuid4())), regime.portfolio_id, NOW),
        (regime, UnknownActorAttribution(), regime.portfolio_id, NOW),
        (
            regime,
            ContestedActorAttribution(frozenset({regime.actor_id})),
            regime.portfolio_id,
            NOW,
        ),
        (regime, actor, PortfolioId(uuid4()), NOW),
        (regime, actor, regime.portfolio_id, NOW - timedelta(microseconds=1)),
        (regime, actor, regime.portfolio_id, regime.effective_until),
    )
    for candidate, attribution, portfolio_id, at in cases:
        assert (
            check_investment_authority(
                candidate,
                attribution,
                portfolio_id,
                InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
                at,
            )
            is InvestmentAuthorityCheck.UNESTABLISHED
        )


def test_regime_rejects_invalid_scope_and_time() -> None:
    regime = _regime()
    with pytest.raises(ValueError, match="effective_until"):
        replace(regime, effective_until=NOW)
    with pytest.raises(ValueError, match="effective_from"):
        replace(regime, effective_from=NOW.replace(tzinfo=None))
    with pytest.raises(TypeError, match="portfolio_id"):
        replace(regime, portfolio_id=ActorId(uuid4()))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="check time"):
        check_investment_authority(
            regime,
            KnownActorAttribution(regime.actor_id),
            regime.portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            NOW.replace(tzinfo=None),
        )
