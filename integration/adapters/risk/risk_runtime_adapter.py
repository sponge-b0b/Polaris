from __future__ import annotations

from integration.contracts.risk.risk_signal_contract import RiskSignalContract
from core.runtime.state.runtime_node_output import RuntimeNodeOutput

"""
Converts RiskSignalContract → RuntimeNodeOutput

PURPOSE:
--------
Bridges deterministic risk engine outputs into ExecutionGraph format
WITHOUT modifying risk logic.
"""


def to_runtime_output(
    node_name: str,
    node_type: str,
    contract: RiskSignalContract,
) -> RuntimeNodeOutput:

    # ============================================================
    # CORE SIGNAL MAPPING
    # ============================================================

    directional_score = float(contract.composite_risk * -1.0)
    # NOTE: risk → execution inversion:
    # high risk = bearish pressure on exposure

    confidence = float(1.0 - abs(contract.composite_risk))

    regime = contract.risk_regime

    # ============================================================
    # SIGNALS (EXPLANATION LAYER ONLY)
    # ============================================================

    signals = [
        f"risk_pressure:{contract.risk_pressure:.3f}",
        f"volatility:{contract.volatility_risk:.3f}",
        f"drawdown:{contract.drawdown_risk:.3f}",
        f"exposure:{contract.exposure_risk:.3f}",
    ]

    # ============================================================
    # RISKS (EXPLICIT FLAGS)
    # ============================================================

    risks = []

    if contract.volatility_risk > 0.7:
        risks.append("high_volatility")

    if contract.drawdown_risk > 0.7:
        risks.append("drawdown_risk_high")

    if contract.exposure_risk > 0.7:
        risks.append("overexposure")

    if contract.stability_score < 0.3:
        risks.append("system_instability")

    # ============================================================
    # RECOMMENDATIONS (NON-EXECUTIONAL)
    # ============================================================

    recommendations = contract.recommendations or []

    if contract.risk_bias == "risk_off":
        recommendations.append("reduce_exposure")

    if contract.stability_score < 0.4:
        recommendations.append("decrease_position_size")

    # ============================================================
    # FEATURES PASSTHROUGH
    # ============================================================

    features = {
        "volatility_risk": contract.volatility_risk,
        "drawdown_risk": contract.drawdown_risk,
        "exposure_risk": contract.exposure_risk,
        "composite_risk": contract.composite_risk,
        "risk_pressure": contract.risk_pressure,
        "stability_score": contract.stability_score,
        "risk_regime": contract.risk_regime,
        "risk_bias": contract.risk_bias,
        **(contract.features or {}),
    }

    # ============================================================
    # BUILD RUNTIME RESULT
    # ============================================================

    result = dict(
        directional_score=directional_score,
        confidence=confidence,
        regime=regime,
        signals=signals,
        risks=risks,
        recommendations=recommendations,
        features=features,
    )

    # ============================================================
    # WRAP INTO NODE OUTPUT
    # ============================================================

    return RuntimeNodeOutput.success_output(
        outputs=result,
        execution_metadata={
            "node_name": node_name,
            "node_type": node_type,
            "confidence": (confidence),
            **({}),
        },
    )
