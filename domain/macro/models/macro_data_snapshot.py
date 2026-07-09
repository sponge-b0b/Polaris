from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class MacroDataSnapshot:
    """Canonical normalized macroeconomic input for platform analysis."""

    cpi: float | None
    core_cpi: float | None
    pce: float | None
    fed_funds_rate: float | None
    treasury_2y: float | None
    treasury_10y: float | None
    unemployment_rate: float | None
    m2_money_supply: float | None
    vix: float | None
    failed_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the snapshot at a runtime, persistence, or presentation boundary."""

        result: dict[str, Any] = {
            "cpi": self.cpi,
            "core_cpi": self.core_cpi,
            "pce": self.pce,
            "fed_funds_rate": self.fed_funds_rate,
            "treasury_2y": self.treasury_2y,
            "treasury_10y": self.treasury_10y,
            "unemployment_rate": self.unemployment_rate,
            "m2_money_supply": self.m2_money_supply,
            "vix": self.vix,
        }
        if self.failed_fields:
            result["failed_fields"] = list(self.failed_fields)
        return result
