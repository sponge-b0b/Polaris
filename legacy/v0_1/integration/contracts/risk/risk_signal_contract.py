from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from numbers import Real
from typing import Any

_UNIT_RISK_FIELDS = (
    "volatility_risk",
    "drawdown_risk",
    "exposure_risk",
    "composite_risk",
    "risk_pressure",
    "stability_score",
)


@dataclass(frozen=True, slots=True)
class RiskSignalContract:
    """
    Polaris Risk Signal Contract (Canonical)

    PURPOSE:
    --------
    Unified deterministic representation of risk intensity and stability signals.

    RANGE STANDARD:
    ---------------
    Risk intensity fields are unit-interval values:
        0.0 → no risk or pressure
        1.0 → maximum risk or defensive pressure

    Stability is also unit interval, with opposite polarity:
        0.0 → unstable
        1.0 → stable

    Directional market posture is not represented by negative risk values. Convert
    risk to signed runtime direction explicitly at the adapter boundary.
    """

    # ============================================================
    # CORE RISK FIELDS (UNIT INTERVAL)
    # ============================================================

    volatility_risk: float = 0.0  # 0 no volatility risk → 1 high volatility risk
    drawdown_risk: float = 0.0  # 0 no drawdown risk → 1 severe drawdown risk
    exposure_risk: float = 0.0  # 0 low exposure risk → 1 high exposure risk

    # ============================================================
    # AGGREGATED RISK STATE
    # ============================================================

    composite_risk: float = 0.0  # 0 low aggregate risk → 1 high aggregate risk

    risk_regime: str = "neutral"  # low_risk / moderate_risk / high_risk / labels

    # ============================================================
    # SYSTEM IMPACT METRICS
    # ============================================================

    risk_pressure: float = 0.0  # 0 no defensive pressure → 1 maximum pressure
    stability_score: float = 1.0  # 0 unstable → 1 stable

    # ============================================================
    # ACTION GUIDANCE (NON-BINDING)
    # ============================================================

    risk_bias: str = "neutral"  # risk_on / risk_off / neutral

    recommendations: list[str] = field(default_factory=list)

    # ============================================================
    # TRACEABILITY
    # ============================================================

    features: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in _UNIT_RISK_FIELDS:
            object.__setattr__(
                self,
                field_name,
                _validate_unit_interval(getattr(self, field_name), field_name),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "volatility_risk": self.volatility_risk,
            "drawdown_risk": self.drawdown_risk,
            "exposure_risk": self.exposure_risk,
            "composite_risk": self.composite_risk,
            "risk_regime": self.risk_regime,
            "risk_pressure": self.risk_pressure,
            "stability_score": self.stability_score,
            "risk_bias": self.risk_bias,
            "recommendations": list(self.recommendations),
            "features": dict(self.features),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RiskSignalContract:
        recommendations = payload.get("recommendations")
        features = payload.get("features")
        return cls(
            volatility_risk=payload.get("volatility_risk", 0.0),
            drawdown_risk=payload.get("drawdown_risk", 0.0),
            exposure_risk=payload.get("exposure_risk", 0.0),
            composite_risk=payload.get("composite_risk", 0.0),
            risk_regime=str(payload.get("risk_regime", "neutral")),
            risk_pressure=payload.get("risk_pressure", 0.0),
            stability_score=payload.get("stability_score", 1.0),
            risk_bias=str(payload.get("risk_bias", "neutral")),
            recommendations=[str(value) for value in recommendations]
            if isinstance(recommendations, list)
            else [],
            features=dict(features) if isinstance(features, Mapping) else {},
        )


def _validate_unit_interval(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a finite numeric unit-interval value")

    numeric = float(value)
    if not isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")

    return numeric
