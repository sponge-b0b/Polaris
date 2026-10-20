"""Attributable, multidimensional Portfolio Risk judgments for the R3 slice."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from polaris.domain.actors import ActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.evidence.judgments import (
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
)
from polaris.domain.evidence.observations import EvidenceObservationId
from polaris.domain.portfolio import PortfolioState, PortfolioStateId
from polaris.domain.portfolio_consequences import (
    ProjectedPortfolioConsequence,
    _aware,
    _text,
    _texts,
    _validate_portfolio_judgment,
)


class RiskDimensionKind(StrEnum):
    """R3 measures retain their distinct units and economic interpretation."""

    EXPOSURE_CONCENTRATION = "exposure_concentration"  # fraction of capital
    DOWNSIDE_SENSITIVITY = "downside_sensitivity"  # amount in State currency
    LIQUIDITY_BUFFER = "liquidity_buffer"  # fraction of capital
    MARKET_SENSITIVITY = "market_sensitivity"  # amount in State currency
    OBJECTIVE_SHORTFALL = "objective_shortfall"  # amount in State currency


def _finite(value: Decimal, field: str) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError(f"{field} must be a finite Decimal")


def _evidence(values: tuple[EvidenceObservationId, ...]) -> None:
    if type(values) is not tuple or any(
        type(item) is not EvidenceObservationId for item in values
    ):
        raise TypeError("evidence must contain typed observation identities")
    if len(set(values)) != len(values):
        raise ValueError("evidence identities must be distinct")


def _support_ranges(support: RiskSupport) -> None:
    if (
        support.downside_fraction is not None
        and not 0 <= support.downside_fraction <= 1
    ):
        raise ValueError("downside_fraction must be within [0, 1]")
    if (
        support.market_volatility_fraction is not None
        and support.market_volatility_fraction < 0
    ):
        raise ValueError("market_volatility_fraction cannot be negative")
    if (
        support.objective_shortfall_amount is not None
        and support.objective_shortfall_amount < 0
    ):
        raise ValueError("objective_shortfall_amount cannot be negative")


@dataclass(frozen=True, slots=True)
class RiskDimension:
    kind: RiskDimensionKind
    value: Decimal | None
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not RiskDimensionKind:
            raise TypeError("kind must be RiskDimensionKind")
        if (self.value is None) == (self.unresolved_reason is None):
            raise ValueError("Risk dimension needs a value or unresolved reason")
        if self.value is not None:
            _finite(self.value, "Risk dimension value")
        if self.unresolved_reason is not None:
            _text(self.unresolved_reason, "Risk dimension unresolved reason")


@dataclass(frozen=True, slots=True)
class RiskSupport:
    """Scenario support; absent material support remains unresolved."""

    basis: str
    evidence: tuple[EvidenceObservationId, ...]
    material_dimensions: tuple[RiskDimensionKind, ...]
    downside_fraction: Decimal | None
    market_volatility_fraction: Decimal | None = None
    objective_shortfall_amount: Decimal | None = None
    assumptions: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.basis, "Risk support basis")
        _evidence(self.evidence)
        if type(self.material_dimensions) is not tuple or not self.material_dimensions:
            raise ValueError("material Risk dimensions are required")
        if any(
            type(item) is not RiskDimensionKind for item in self.material_dimensions
        ):
            raise TypeError("material dimensions must be typed")
        if len(set(self.material_dimensions)) != len(self.material_dimensions):
            raise ValueError("material dimensions must be distinct")
        for field in ("assumptions", "uncertainty"):
            _texts(getattr(self, field), field)
        for field in (
            "downside_fraction",
            "market_volatility_fraction",
            "objective_shortfall_amount",
        ):
            value = getattr(self, field)
            if value is not None:
                _finite(value, field)
        _support_ranges(self)


@dataclass(frozen=True, slots=True)
class PortfolioRiskAssessment:
    """One historical judgment on an actual State or a hypothetical consequence."""

    assessment_id: PortfolioRiskAssessmentRef
    source_state_id: PortfolioStateId
    source_as_of: datetime
    projected_consequence_id: ProjectedPortfolioConsequenceRef | None
    horizon: InvestmentHorizon
    scenario: str
    support: RiskSupport
    dimensions: tuple[RiskDimension, ...]
    uncertainty: tuple[str, ...]
    attribution: ActorAttribution
    formed_at: datetime

    def __post_init__(self) -> None:
        if type(self.assessment_id) is not PortfolioRiskAssessmentRef:
            raise TypeError("assessment_id must be PortfolioRiskAssessmentRef")
        if type(self.source_state_id) is not PortfolioStateId:
            raise TypeError("source_state_id must be PortfolioStateId")
        if (
            self.projected_consequence_id is not None
            and type(self.projected_consequence_id)
            is not ProjectedPortfolioConsequenceRef
        ):
            raise TypeError("projected_consequence_id must be typed")
        if type(self.support) is not RiskSupport:
            raise TypeError("support must be RiskSupport")
        _validate_portfolio_judgment(
            self.horizon, self.attribution, self.source_as_of, self.formed_at
        )
        _text(self.scenario, "scenario")
        if not self.dimensions or any(
            type(item) is not RiskDimension for item in self.dimensions
        ):
            raise ValueError("material typed Risk dimensions are required")
        if len({item.kind for item in self.dimensions}) != len(self.dimensions):
            raise ValueError("Risk dimensions must be distinct")
        if (
            tuple(item.kind for item in self.dimensions)
            != self.support.material_dimensions
        ):
            raise ValueError(
                "Risk dimensions must match the material support selection"
            )
        _texts(self.uncertainty, "uncertainty")

    @property
    def unresolved(self) -> bool:
        return any(item.value is None for item in self.dimensions)


@dataclass(frozen=True, slots=True)
class RecordedPortfolioRiskAssessment:
    assessment: PortfolioRiskAssessment
    known_at: datetime

    def __post_init__(self) -> None:
        if type(self.assessment) is not PortfolioRiskAssessment:
            raise TypeError("assessment must be PortfolioRiskAssessment")
        _aware(self.known_at, "known_at")


def assess_portfolio_risk(
    *,
    assessment_id: PortfolioRiskAssessmentRef,
    state: PortfolioState,
    consequence: ProjectedPortfolioConsequence | None,
    horizon: InvestmentHorizon,
    scenario: str,
    support: RiskSupport,
    attribution: ActorAttribution,
    formed_at: datetime,
) -> PortfolioRiskAssessment:
    """Produce distinct R3 Risk measures without inventing missing support."""
    if type(state) is not PortfolioState:
        raise TypeError("state must be PortfolioState")
    if type(support) is not RiskSupport:
        raise TypeError("support must be RiskSupport")
    if consequence is not None:
        if type(consequence) is not ProjectedPortfolioConsequence:
            raise TypeError("consequence must be ProjectedPortfolioConsequence")
        if (
            consequence.source_state_id != state.state_id
            or consequence.source_as_of != state.as_of
            or consequence.horizon != horizon
        ):
            raise ValueError("projected Risk must use its exact State and horizon")

    exposure, cash, exposure_reason, cash_reason = _risk_values(state, consequence)
    dimensions = _risk_dimensions(
        state, support, exposure, cash, exposure_reason, cash_reason
    )
    uncertainty = list(support.uncertainty)
    if consequence is not None:
        uncertainty.append(consequence.uncertainty)
    return PortfolioRiskAssessment(
        assessment_id=assessment_id,
        source_state_id=state.state_id,
        source_as_of=state.as_of,
        projected_consequence_id=(
            None if consequence is None else consequence.consequence_id
        ),
        horizon=horizon,
        scenario=scenario,
        support=support,
        dimensions=dimensions,
        uncertainty=tuple(uncertainty),
        attribution=attribution,
        formed_at=formed_at,
    )


def _risk_values(
    state: PortfolioState,
    consequence: ProjectedPortfolioConsequence | None,
) -> tuple[Decimal | None, Decimal | None, str, str]:
    exposure: Decimal | None = state.exposure_value
    cash: Decimal | None = state.cash
    exposure_reason = "projected exposure change is unresolved"
    cash_reason = "projected cash effect is unresolved"
    if consequence is not None:
        if consequence.exposure_change is not None:
            change = consequence.exposure_change
            exposure = (
                state.exposure_value + change.value
                if change.value is not None
                else None
            )
            exposure_reason = change.unresolved_reason or exposure_reason
        else:
            exposure = None
        if consequence.cash_effect is not None:
            change = consequence.cash_effect
            cash = state.cash + change.value if change.value is not None else None
            cash_reason = change.unresolved_reason or cash_reason
        elif any(
            change is not None and change.value != Decimal(0)
            for change in (
                consequence.exposure_change,
                consequence.allocation_change,
            )
        ):
            cash = None
            cash_reason = "material projected cash effect is not established"
    return exposure, cash, exposure_reason, cash_reason


def _risk_dimensions(
    state: PortfolioState,
    support: RiskSupport,
    exposure: Decimal | None,
    cash: Decimal | None,
    exposure_reason: str,
    cash_reason: str,
) -> tuple[RiskDimension, ...]:
    dimensions = {
        RiskDimensionKind.EXPOSURE_CONCENTRATION: RiskDimension(
            RiskDimensionKind.EXPOSURE_CONCENTRATION,
            None if exposure is None else abs(exposure) / state.capital_basis,
            exposure_reason if exposure is None else None,
        ),
        RiskDimensionKind.DOWNSIDE_SENSITIVITY: RiskDimension(
            RiskDimensionKind.DOWNSIDE_SENSITIVITY,
            None
            if exposure is None or support.downside_fraction is None
            else abs(exposure) * support.downside_fraction,
            (
                exposure_reason
                if exposure is None
                else "material downside support is unavailable"
                if support.downside_fraction is None
                else None
            ),
        ),
        RiskDimensionKind.LIQUIDITY_BUFFER: RiskDimension(
            RiskDimensionKind.LIQUIDITY_BUFFER,
            None if cash is None else cash / state.capital_basis,
            cash_reason if cash is None else None,
        ),
        RiskDimensionKind.MARKET_SENSITIVITY: RiskDimension(
            RiskDimensionKind.MARKET_SENSITIVITY,
            None
            if exposure is None or support.market_volatility_fraction is None
            else abs(exposure) * support.market_volatility_fraction,
            (
                exposure_reason
                if exposure is None
                else "material market sensitivity support is unavailable"
                if support.market_volatility_fraction is None
                else None
            ),
        ),
        RiskDimensionKind.OBJECTIVE_SHORTFALL: RiskDimension(
            RiskDimensionKind.OBJECTIVE_SHORTFALL,
            support.objective_shortfall_amount,
            "material objective shortfall support is unavailable"
            if support.objective_shortfall_amount is None
            else None,
        ),
    }
    return tuple(dimensions[kind] for kind in support.material_dimensions)
