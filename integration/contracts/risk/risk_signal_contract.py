from dataclasses import dataclass, field
from typing import Any
from typing import Mapping


@dataclass(frozen=True, slots=True)
class RiskSignalContract:
    """
    Polaris Risk Signal Contract (Canonical)

    PURPOSE:
    --------
    Unified deterministic representation of all risk signals.

    RANGE STANDARD:
    ---------------
        -1.0 → risk-on / favorable
         0.0 → neutral
        +1.0 → extreme risk / defensive pressure

    NOTE:
    -----
    This is NOT a penalty system.
    This is a directional risk pressure field.
    """

    # ============================================================
    # CORE RISK FIELDS (NORMALIZED)
    # ============================================================

    volatility_risk: float = 0.0  # -1 safe → +1 unstable
    drawdown_risk: float = 0.0  # -1 stable → +1 severe risk
    exposure_risk: float = 0.0  # -1 underexposed → +1 overexposed

    # ============================================================
    # AGGREGATED RISK STATE
    # ============================================================

    composite_risk: float = 0.0  # -1 → +1

    risk_regime: str = "neutral"  # safe / neutral / stressed / extreme

    # ============================================================
    # SYSTEM IMPACT METRICS
    # ============================================================

    risk_pressure: float = 0.0  # overall directional force
    stability_score: float = 1.0  # 0 → unstable, 1 → stable

    # ============================================================
    # ACTION GUIDANCE (NON-BINDING)
    # ============================================================

    risk_bias: str = "neutral"  # risk_on / risk_off / neutral

    recommendations: list[str] = field(default_factory=list)

    # ============================================================
    # TRACEABILITY
    # ============================================================

    features: dict[str, Any] = field(default_factory=dict)

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
    def from_dict(cls, payload: Mapping[str, Any]) -> "RiskSignalContract":
        recommendations = payload.get("recommendations")
        features = payload.get("features")
        return cls(
            volatility_risk=float(payload.get("volatility_risk", 0.0)),
            drawdown_risk=float(payload.get("drawdown_risk", 0.0)),
            exposure_risk=float(payload.get("exposure_risk", 0.0)),
            composite_risk=float(payload.get("composite_risk", 0.0)),
            risk_regime=str(payload.get("risk_regime", "neutral")),
            risk_pressure=float(payload.get("risk_pressure", 0.0)),
            stability_score=float(payload.get("stability_score", 1.0)),
            risk_bias=str(payload.get("risk_bias", "neutral")),
            recommendations=[str(value) for value in recommendations]
            if isinstance(recommendations, list)
            else [],
            features=dict(features) if isinstance(features, Mapping) else {},
        )
