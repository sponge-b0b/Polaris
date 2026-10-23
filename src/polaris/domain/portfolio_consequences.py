"""Portfolio-owned hypothetical consequences of material Decision Alternatives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from polaris.domain.actors import ActorAttribution, is_actor_attribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.evidence.context_versions import DecisionAlternativeVersionRef
from polaris.domain.evidence.judgments import ProjectedPortfolioConsequenceRef
from polaris.domain.portfolio import PortfolioStateId


def _aware(value: datetime, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be substantive")


def _texts(values: tuple[str, ...], field: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{field} must be a tuple")
    for value in values:
        _text(value, field)


def _validate_portfolio_judgment(
    horizon: InvestmentHorizon,
    attribution: ActorAttribution,
    source_as_of: datetime,
    formed_at: datetime,
) -> None:
    if type(horizon) is not InvestmentHorizon:
        raise TypeError("horizon must be InvestmentHorizon")
    if not is_actor_attribution(attribution):
        raise TypeError("attribution must identify an actor status")
    _aware(source_as_of, "source_as_of")
    _aware(formed_at, "formed_at")


@dataclass(frozen=True, slots=True)
class ProjectedChange:
    """A consequence delta, or an explicitly unresolved material delta."""

    value: Decimal | None
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        if (self.value is None) == (self.unresolved_reason is None):
            raise ValueError("projected change needs a value or unresolved reason")
        if self.value is not None and (
            type(self.value) is not Decimal or not self.value.is_finite()
        ):
            raise ValueError("projected change must be a finite Decimal")
        if self.unresolved_reason is not None:
            _text(self.unresolved_reason, "unresolved reason")


@dataclass(frozen=True, slots=True)
class ProjectedPortfolioConsequence:
    """An immutable hypothetical judgment relative to one exact actual State."""

    consequence_id: ProjectedPortfolioConsequenceRef
    alternative: DecisionAlternativeVersionRef
    source_state_id: PortfolioStateId
    source_as_of: datetime
    horizon: InvestmentHorizon
    scenario: str
    assumptions: tuple[str, ...]
    exposure_change: ProjectedChange | None
    allocation_change: ProjectedChange | None
    cash_effect: ProjectedChange | None
    economic_benefits: tuple[str, ...]
    adverse_possibilities: tuple[str, ...]
    material_risk_changes: tuple[str, ...]
    attribution: ActorAttribution
    formed_at: datetime
    uncertainty: str

    def __post_init__(self) -> None:
        if type(self.consequence_id) is not ProjectedPortfolioConsequenceRef:
            raise TypeError("consequence_id must be ProjectedPortfolioConsequenceRef")
        if type(self.alternative) is not DecisionAlternativeVersionRef:
            raise TypeError("alternative must be DecisionAlternativeVersionRef")
        if type(self.source_state_id) is not PortfolioStateId:
            raise TypeError("source_state_id must be PortfolioStateId")
        _validate_portfolio_judgment(
            self.horizon, self.attribution, self.source_as_of, self.formed_at
        )
        if self.exposure_change is None and self.allocation_change is None:
            raise ValueError("SPY exposure or allocation change is required")
        for field in ("exposure_change", "allocation_change", "cash_effect"):
            value = getattr(self, field)
            if value is not None and type(value) is not ProjectedChange:
                raise TypeError(f"{field} must be ProjectedChange")
        _text(self.scenario, "scenario")
        _text(self.uncertainty, "uncertainty")
        _texts(self.assumptions, "assumptions")
        _texts(self.economic_benefits, "economic_benefits")
        _texts(self.adverse_possibilities, "adverse_possibilities")
        _texts(self.material_risk_changes, "material_risk_changes")
        if not (
            self.assumptions and self.economic_benefits and self.adverse_possibilities
        ):
            raise ValueError(
                "assumptions, benefits, and adverse possibilities are required"
            )


@dataclass(frozen=True, slots=True)
class RecordedProjectedPortfolioConsequence:
    consequence: ProjectedPortfolioConsequence
    known_at: datetime

    def __post_init__(self) -> None:
        if type(self.consequence) is not ProjectedPortfolioConsequence:
            raise TypeError("consequence must be ProjectedPortfolioConsequence")
        _aware(self.known_at, "known_at")
