from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class MacroIndicatorObservation:
    """Canonical source observation backing one macro indicator value."""

    indicator_name: str
    value: float
    observation_timestamp: datetime
    source: str
    indicator_category: str | None = None
    region: str | None = None
    unit: str | None = None
    frequency: str | None = None
    release_timestamp: datetime | None = None
    vintage_timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if not self.indicator_name.strip():
            raise ValueError("indicator_name cannot be empty.")
        if not self.source.strip():
            raise ValueError("source cannot be empty.")
        object.__setattr__(
            self,
            "observation_timestamp",
            _ensure_aware_datetime(self.observation_timestamp),
        )
        if self.release_timestamp is not None:
            object.__setattr__(
                self,
                "release_timestamp",
                _ensure_aware_datetime(self.release_timestamp),
            )
        if self.vintage_timestamp is not None:
            object.__setattr__(
                self,
                "vintage_timestamp",
                _ensure_aware_datetime(self.vintage_timestamp),
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the observation at a runtime or persistence boundary."""

        result: dict[str, Any] = {
            "indicator_name": self.indicator_name,
            "value": self.value,
            "observation_timestamp": self.observation_timestamp.isoformat(),
            "source": self.source,
        }
        if self.indicator_category is not None:
            result["indicator_category"] = self.indicator_category
        if self.region is not None:
            result["region"] = self.region
        if self.unit is not None:
            result["unit"] = self.unit
        if self.frequency is not None:
            result["frequency"] = self.frequency
        if self.release_timestamp is not None:
            result["release_timestamp"] = self.release_timestamp.isoformat()
        if self.vintage_timestamp is not None:
            result["vintage_timestamp"] = self.vintage_timestamp.isoformat()
        return result


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
    observations: tuple[MacroIndicatorObservation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the snapshot at a runtime, persistence, or presentation boundary.
        """

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
        if self.observations:
            result["observations"] = [
                observation.to_dict() for observation in self.observations
            ]
        return result


def _ensure_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
