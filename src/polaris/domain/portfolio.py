from __future__ import annotations

from dataclasses import dataclass
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
