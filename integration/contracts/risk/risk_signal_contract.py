from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
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

    recommendations: list = field(default_factory=list)

    # ============================================================
    # TRACEABILITY
    # ============================================================

    features: Dict[str, Any] = field(default_factory=dict)
