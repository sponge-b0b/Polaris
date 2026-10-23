"""Portfolio-owned facts that may enter a typed R3 Evidence context basis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from polaris.domain.evidence.context_versions import (
    InvestmentMandateVersionRef,
    InvestmentStrategyVersionRef,
    PortfolioBoundaryVersionRef,
    PortfolioStateVersionRef,
    ProjectedPortfolioStateVersionRef,
)
from polaris.domain.investment_intelligence import InvestmentHorizon
from polaris.domain.portfolio import (
    FinancialInstrumentId,
    PortfolioId,
    PortfolioStateId,
    RecordedPortfolioState,
)

# duplicate-code: Portfolio owns this narrower typed reference boundary.
# arid: disable
type PortfolioContextVersionRef = (
    PortfolioBoundaryVersionRef
    | PortfolioStateVersionRef
    | ProjectedPortfolioStateVersionRef
    | InvestmentMandateVersionRef
    | InvestmentStrategyVersionRef
)
# arid: enable


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _statement(value: str, name: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be nonempty")


@dataclass(frozen=True, slots=True)
class PortfolioBoundaryMeaning:
    portfolio_id: PortfolioId
    instrument_id: FinancialInstrumentId
    boundary: str

    def __post_init__(self) -> None:
        if type(self.portfolio_id) is not PortfolioId:
            raise TypeError("portfolio_id must be PortfolioId")
        if type(self.instrument_id) is not FinancialInstrumentId:
            raise TypeError("instrument_id must be FinancialInstrumentId")
        _statement(self.boundary, "boundary")


@dataclass(frozen=True, slots=True)
class ActualPortfolioStateMeaning:
    recorded: RecordedPortfolioState

    def __post_init__(self) -> None:
        if type(self.recorded) is not RecordedPortfolioState:
            raise TypeError("recorded must be RecordedPortfolioState")


@dataclass(frozen=True, slots=True)
class ProjectedPortfolioStateMeaning:
    portfolio_id: PortfolioId
    source_state_id: PortfolioStateId
    horizon: InvestmentHorizon
    scenario: str
    projected_exposure_value: Decimal | None
    projected_cash: Decimal | None
    uncertainty: str | None

    def __post_init__(self) -> None:
        if type(self.portfolio_id) is not PortfolioId:
            raise TypeError("portfolio_id must be PortfolioId")
        if type(self.source_state_id) is not PortfolioStateId:
            raise TypeError("source_state_id must be PortfolioStateId")
        if type(self.horizon) is not InvestmentHorizon:
            raise TypeError("horizon must be InvestmentHorizon")
        _statement(self.scenario, "scenario")
        for name in ("projected_exposure_value", "projected_cash"):
            value = getattr(self, name)
            if value is not None and (
                type(value) is not Decimal or not value.is_finite()
            ):
                raise ValueError(f"{name} must be a finite Decimal")
        if self.uncertainty is not None:
            _statement(self.uncertainty, "uncertainty")


class MandateMemberKind(StrEnum):
    OBJECTIVE = "objective"
    PRINCIPLE = "principle"


@dataclass(frozen=True, slots=True)
class MandateMemberRef:
    kind: MandateMemberKind
    value: UUID

    def __post_init__(self) -> None:
        if type(self.kind) is not MandateMemberKind:
            raise TypeError("kind must be MandateMemberKind")
        if type(self.value) is not UUID or self.value.version != 4:
            raise ValueError("member identity must be UUIDv4")


@dataclass(frozen=True, slots=True)
class MandateMember:
    reference: MandateMemberRef
    content: str
    effective_from: datetime
    effective_until: datetime | None
    depends_on: tuple[MandateMemberRef, ...] = ()

    def __post_init__(self) -> None:
        if type(self.reference) is not MandateMemberRef:
            raise TypeError("reference must be MandateMemberRef")
        _statement(self.content, "content")
        _aware(self.effective_from, "effective_from")
        if self.effective_until is not None:
            _aware(self.effective_until, "effective_until")
            if self.effective_until <= self.effective_from:
                raise ValueError("effective_until must follow effective_from")
        if type(self.depends_on) is not tuple or any(
            type(item) is not MandateMemberRef for item in self.depends_on
        ):
            raise TypeError("depends_on must contain typed MandateMemberRef values")
        if len(set(self.depends_on)) != len(self.depends_on):
            raise ValueError("dependent member references must be unique")


@dataclass(frozen=True, slots=True)
class InvestmentMandateMeaning:
    portfolio_id: PortfolioId
    members: tuple[MandateMember, ...]

    def __post_init__(self) -> None:
        if type(self.portfolio_id) is not PortfolioId:
            raise TypeError("portfolio_id must be PortfolioId")
        if type(self.members) is not tuple or any(
            type(item) is not MandateMember for item in self.members
        ):
            raise TypeError("members must contain MandateMember values")
        references = {member.reference for member in self.members}
        if len(references) != len(self.members):
            raise ValueError("mandate member references must be unique")
        if any(
            dependency not in references
            for member in self.members
            for dependency in member.depends_on
        ):
            raise ValueError("every dependent member must belong to the mandate")


@dataclass(frozen=True, slots=True)
class InvestmentStrategyMeaning:
    portfolio_id: PortfolioId
    strategy: str

    def __post_init__(self) -> None:
        if type(self.portfolio_id) is not PortfolioId:
            raise TypeError("portfolio_id must be PortfolioId")
        _statement(self.strategy, "strategy")


type PortfolioContextMeaning = (
    PortfolioBoundaryMeaning
    | ActualPortfolioStateMeaning
    | ProjectedPortfolioStateMeaning
    | InvestmentMandateMeaning
    | InvestmentStrategyMeaning
)


_MEANING_BY_REFERENCE = {
    PortfolioBoundaryVersionRef: PortfolioBoundaryMeaning,
    PortfolioStateVersionRef: ActualPortfolioStateMeaning,
    ProjectedPortfolioStateVersionRef: ProjectedPortfolioStateMeaning,
    InvestmentMandateVersionRef: InvestmentMandateMeaning,
    InvestmentStrategyVersionRef: InvestmentStrategyMeaning,
}


def validate_portfolio_context_meaning(
    reference: PortfolioContextVersionRef, meaning: PortfolioContextMeaning
) -> None:
    expected = _MEANING_BY_REFERENCE.get(type(reference))
    if expected is None or type(meaning) is not expected:
        raise TypeError("Portfolio context meaning must match its typed reference")
    if type(reference) is PortfolioStateVersionRef:
        if not isinstance(meaning, ActualPortfolioStateMeaning):
            raise TypeError("actual State context requires canonical State meaning")
        if reference.root != meaning.recorded.state.state_id:
            raise ValueError("actual State context root must match canonical State")
