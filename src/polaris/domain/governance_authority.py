"""The minimum R3 power check for a Human Investment Decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from polaris.domain.actors import ActorAttribution, ActorId, KnownActorAttribution
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.portfolio import PortfolioId


class InvestmentAuthorityPower(StrEnum):
    HUMAN_INVESTMENT_DECISION = "human-investment-decision"


class InvestmentAuthorityCheck(StrEnum):
    ESTABLISHED = "established"
    UNESTABLISHED = "unestablished"


@dataclass(frozen=True, slots=True)
class InvestmentAuthorityRegime:
    """One attributable R3 grant for one Portfolio and an explicit time span."""

    regime_id: InvestmentAuthorityRegimeId
    actor_id: ActorId
    portfolio_id: PortfolioId
    power: InvestmentAuthorityPower
    effective_from: datetime
    effective_until: datetime | None

    def __post_init__(self) -> None:
        if type(self.regime_id) is not InvestmentAuthorityRegimeId:
            raise TypeError("regime_id must be InvestmentAuthorityRegimeId")
        if type(self.actor_id) is not ActorId:
            raise TypeError("actor_id must be ActorId")
        if type(self.portfolio_id) is not PortfolioId:
            raise TypeError("portfolio_id must be PortfolioId")
        if type(self.power) is not InvestmentAuthorityPower:
            raise TypeError("power must be InvestmentAuthorityPower")
        if not _aware(self.effective_from):
            raise ValueError("effective_from must be timezone-aware")
        if self.effective_until is not None:
            if not _aware(self.effective_until):
                raise ValueError("effective_until must be timezone-aware")
            if self.effective_until <= self.effective_from:
                raise ValueError("effective_until must follow effective_from")


def _aware(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def check_investment_authority(
    regime: InvestmentAuthorityRegime | None,
    actor: ActorAttribution,
    portfolio_id: PortfolioId,
    power: InvestmentAuthorityPower,
    at: datetime,
) -> InvestmentAuthorityCheck:
    """Establish only the exact R3 power, actor, Portfolio, and time requested."""

    if not _aware(at):
        raise ValueError("authority check time must be timezone-aware")
    if (
        type(regime) is not InvestmentAuthorityRegime
        or type(actor) is not KnownActorAttribution
        or type(portfolio_id) is not PortfolioId
        or type(power) is not InvestmentAuthorityPower
    ):
        return InvestmentAuthorityCheck.UNESTABLISHED
    if (
        regime.actor_id != actor.actor_id
        or regime.portfolio_id != portfolio_id
        or regime.power is not power
        or at < regime.effective_from
        or (regime.effective_until is not None and at >= regime.effective_until)
    ):
        return InvestmentAuthorityCheck.UNESTABLISHED
    return InvestmentAuthorityCheck.ESTABLISHED
