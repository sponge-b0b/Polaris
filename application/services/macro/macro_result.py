from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from domain.macro.models import MacroDataSnapshot


@dataclass(
    frozen=True,
    slots=True,
)
class MacroAnalysisResult:
    """Typed result for deterministic macro-analysis orchestration."""

    macro_data: MacroDataSnapshot | None
    inflation_analysis: dict[str, Any]
    fed_analysis: dict[str, Any]
    liquidity_analysis: dict[str, Any]
    yield_curve_analysis: dict[str, Any]
    economic_regime: dict[str, Any]
    inflation_regime: str
    fed_stance: str
    liquidity_regime: str
    yield_curve_regime: str

    def to_dict(
        self,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "inflation_analysis": deepcopy(self.inflation_analysis),
            "fed_analysis": deepcopy(self.fed_analysis),
            "liquidity_analysis": deepcopy(self.liquidity_analysis),
            "yield_curve_analysis": deepcopy(self.yield_curve_analysis),
            "economic_regime": deepcopy(self.economic_regime),
            "inflation_regime": self.inflation_regime,
            "fed_stance": self.fed_stance,
            "liquidity_regime": self.liquidity_regime,
            "yield_curve_regime": self.yield_curve_regime,
        }
        if self.macro_data is not None:
            result["macro_data"] = self.macro_data.to_dict()
        return result
