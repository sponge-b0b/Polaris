from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PortfolioId:
    """Opaque durable identity for a Portfolio."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TypeError("PortfolioId.value must be UUID")
        if self.value.version != 4:
            raise ValueError("PortfolioId.value must be UUIDv4")


@dataclass(frozen=True, slots=True)
class FinancialInstrumentId:
    """Opaque durable identity for a Financial Instrument."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TypeError("FinancialInstrumentId.value must be UUID")
        if self.value.version != 4:
            raise ValueError("FinancialInstrumentId.value must be UUIDv4")


@dataclass(frozen=True, slots=True)
class PortfolioStateId:
    """Identity of one attributable actual Portfolio State at an as-of boundary."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TypeError("PortfolioStateId.value must be UUID")
        if self.value.version != 4:
            raise ValueError("PortfolioStateId.value must be UUIDv4")


# duplicate-code: Portfolio source/as-of validation and Decision lifecycle time
# validation have separate domain failure contracts; sharing would couple them.
# arid: disable
def _aware(value: datetime, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable


def _finite(value: Decimal, field: str) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError(f"{field} must be a finite Decimal")


@dataclass(frozen=True, slots=True)
class PortfolioSource:
    """External operational source retains authority for the observed facts."""

    system: str
    record_reference: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.system.strip() or not self.record_reference.strip():
            raise ValueError("source system and record reference are required")
        _aware(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Immutable decision-grade reading of externally sourced Portfolio facts.

    Monetary amounts use the stated currency; exposure_value is the interpreted
    economic sensitivity in that currency and remains distinct from Position value.
    allocation_fraction is relative to capital_basis. The interpretation basis
    records how source facts were attributed and interpreted by Polaris.
    """

    state_id: PortfolioStateId
    portfolio_id: PortfolioId
    as_of: datetime
    source: PortfolioSource
    currency: str
    capital_basis: Decimal
    cash: Decimal
    instrument_id: FinancialInstrumentId
    position_quantity: Decimal
    position_value: Decimal
    exposure_value: Decimal
    allocation_fraction: Decimal
    interpretation_basis: str
    uncertainty: str | None = None

    def __post_init__(self) -> None:
        for field, expected_type in (
            ("state_id", PortfolioStateId),
            ("portfolio_id", PortfolioId),
            ("source", PortfolioSource),
            ("instrument_id", FinancialInstrumentId),
        ):
            if type(getattr(self, field)) is not expected_type:
                raise TypeError(f"{field} must be {expected_type.__name__}")
        _aware(self.as_of, "as_of")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("currency must be a three-letter code")
        if not self.interpretation_basis.strip():
            raise ValueError("interpretation_basis is required")
        if self.uncertainty is not None and not self.uncertainty.strip():
            raise ValueError("uncertainty cannot be empty")
        for field in (
            "capital_basis",
            "cash",
            "position_quantity",
            "position_value",
            "exposure_value",
            "allocation_fraction",
        ):
            _finite(getattr(self, field), field)
        if self.capital_basis <= 0:
            raise ValueError("capital_basis must be positive")


@dataclass(frozen=True, slots=True)
class RecordedPortfolioState:
    """A State and the trusted boundary at which Polaris first knew it."""

    state: PortfolioState
    known_at: datetime

    def __post_init__(self) -> None:
        if type(self.state) is not PortfolioState:
            raise TypeError("state must be PortfolioState")
        _aware(self.known_at, "known_at")
        if self.known_at < self.state.source.observed_at:
            raise ValueError("known_at cannot precede source observation")
