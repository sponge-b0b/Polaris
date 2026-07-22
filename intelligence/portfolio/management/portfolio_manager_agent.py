from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from domain.authority import (
    authority_contract_metadata,
    model_authority_claims_from_payloads,
    portfolio_allocation_intent_runtime_authority,
)
from domain.workflow_outputs import (
    PORTFOLIO_ALLOCATION_INTENT_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.synthesis.contracts import (
    StrategySynthesisDecision,
    StrategySynthesisSelectionStatus,
)


def _required_mapping(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping.")
    return {str(key): mapped_value for key, mapped_value in value.items()}


def _optional_mapping(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): mapped_value for key, mapped_value in value.items()}


def _required_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(f"{field_name} must be numeric.")
    return float(value)


def _synthesis_decision_from_features(
    features: Mapping[str, object],
) -> StrategySynthesisDecision:
    raw_decision = features.get("strategy_synthesis_decision")
    if not isinstance(raw_decision, Mapping):
        raise ValueError(
            "portfolio_manager_agent requires "
            "strategy_synthesis_agent.features.strategy_synthesis_decision."
        )
    return StrategySynthesisDecision.from_dict(
        {str(key): mapped_value for key, mapped_value in raw_decision.items()}
    )


def _synthesis_allocation(
    decision: StrategySynthesisDecision,
) -> dict[str, float]:
    allocation = {"bull": 0.0, "bear": 0.0, "sideways": 0.0}
    for evaluation in decision.evaluations:
        allocation[evaluation.perspective.value] = evaluation.synthesis_weight
    return allocation


def _synthesis_allows_execution(decision: StrategySynthesisDecision) -> bool:
    return (
        decision.selection_status is StrategySynthesisSelectionStatus.SELECTED
        and decision.selected_perspective is not None
        and not decision.degraded_reasons
    )


class PortfolioManagerAgent(RuntimeNode):
    """
    Polaris Portfolio Manager Agent

    ============================================================
    PURPOSE
    ============================================================
    - enforce portfolio-level execution governance
    - apply risk-aware capital scaling
    - validate synthesized regime posture
    - determine deployable portfolio posture

    ============================================================
    THIS NODE DOES NOT
    ============================================================
    - generate alpha
    - create signals
    - modify strategy synthesis
    - override risk layer

    ============================================================
    INPUTS
    ============================================================
    StrategySynthesisAgent
    RiskAggregatorAgent

    ============================================================
    OUTPUT
    ============================================================
    RuntimeNodeOutput.outputs portfolio intent payload
    """

    node_name = "portfolio_manager_agent"
    node_type = "portfolio_manager"

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # UPSTREAM RESULTS
        # ========================================================

        synthesis_result = _required_mapping(
            context.node_outputs["strategy_synthesis_agent"].get("outputs", {}),
            "strategy_synthesis_agent.outputs",
        )

        risk_result = _required_mapping(
            context.node_outputs["risk_aggregator_agent"].get("outputs", {}),
            "risk_aggregator_agent.outputs",
        )

        # ========================================================
        # SYNTHESIS OUTPUTS
        # ========================================================

        synthesis_features = _required_mapping(
            synthesis_result.get("features", {}),
            "strategy_synthesis_agent.outputs.features",
        )
        synthesis_decision = _synthesis_decision_from_features(synthesis_features)
        synthesis_allows_execution = _synthesis_allows_execution(synthesis_decision)

        selected_perspective = (
            None
            if synthesis_decision.selected_perspective is None
            else synthesis_decision.selected_perspective.value
        )
        selection_status = synthesis_decision.selection_status.value
        synthesis_degraded_reasons = [
            reason.value for reason in synthesis_decision.degraded_reasons
        ]

        posture = synthesis_decision.regime

        synthesis_confidence = synthesis_decision.confidence

        directional_score = synthesis_decision.directional_score

        # ========================================================
        # TARGET ALLOCATION VECTOR
        # ========================================================

        target_allocation = _synthesis_allocation(synthesis_decision)

        # ========================================================
        # RISK STATE
        # ========================================================

        risk_features = _optional_mapping(risk_result.get("features"))

        composite_risk = _required_float(
            risk_features.get("composite_risk", 0.0), "composite_risk"
        )

        risk_pressure = _required_float(
            risk_features.get("risk_pressure", 0.0), "risk_pressure"
        )

        stability_score = _required_float(
            risk_features.get("stability_score", 0.0), "stability_score"
        )

        risk_regime = risk_features.get("risk_regime")

        # ========================================================
        # PORTFOLIO V2 RISK CONTEXT
        # ========================================================

        portfolio_output = _optional_mapping(
            context.node_outputs.get(
                "portfolio_state_builder",
                {},
            )
        )

        portfolio_outputs = _optional_mapping(portfolio_output.get("outputs"))
        portfolio_features = _optional_mapping(portfolio_outputs.get("features"))

        portfolio_risk_features = _optional_mapping(
            portfolio_features.get("risk_features")
        )

        portfolio_heat = _required_float(
            portfolio_risk_features.get(
                "portfolio_heat",
                0.0,
            ),
            "portfolio_heat",
        )

        risk_intensity = _required_float(
            portfolio_risk_features.get(
                "risk_intensity",
                0.0,
            ),
            "risk_intensity",
        )

        margin_utilization_ratio = _required_float(
            portfolio_risk_features.get(
                "margin_utilization_ratio",
                0.0,
            ),
            "margin_utilization_ratio",
        )

        account_restricted = any(
            bool(
                portfolio_risk_features.get(
                    flag,
                    False,
                )
            )
            for flag in (
                "trading_blocked",
                "account_blocked",
                "trade_suspended_by_user",
            )
        )

        composite_risk = max(
            composite_risk,
            portfolio_heat,
            risk_intensity,
            margin_utilization_ratio,
        )

        risk_pressure = max(
            risk_pressure,
            portfolio_heat,
            risk_intensity,
            margin_utilization_ratio,
        )

        if account_restricted:
            composite_risk = 1.0
            risk_pressure = 1.0
            stability_score = 0.0

        # ========================================================
        # DRIFT ANALYSIS
        # ========================================================

        baseline = 1.0 / 3.0

        drift = {k: abs(v - baseline) for k, v in target_allocation.items()}

        total_drift = sum(drift.values())

        # ========================================================
        # EXECUTION STATUS
        # ========================================================

        execution_status = self._execution_status(
            total_drift=total_drift,
            composite_risk=composite_risk,
            risk_pressure=risk_pressure,
            stability_score=stability_score,
        )
        if not synthesis_allows_execution:
            execution_status = "rejected"

        # ========================================================
        # CAPITAL SCALE FACTOR
        # ========================================================

        scale_factor = self._scale_factor(
            risk_pressure=risk_pressure,
            stability_score=stability_score,
            execution_status=execution_status,
        )

        # ========================================================
        # PORTFOLIO REGIME
        # ========================================================

        portfolio_regime = self._portfolio_regime(
            posture=posture,
            composite_risk=composite_risk,
        )

        # ========================================================
        # CONFIDENCE
        # ========================================================

        confidence = (
            synthesis_confidence * 0.60
            + stability_score * 0.25
            + (1.0 - risk_pressure) * 0.15
        )

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        # ========================================================
        # RESULT
        # ========================================================

        result = dict(
            directional_score=directional_score,
            confidence=confidence,
            regime=portfolio_regime,
            signals=[
                execution_status,
                posture,
                risk_regime,
                f"drift_{total_drift}",
                f"scale_{scale_factor}",
                f"synthesis_{selection_status}",
            ],
            risks=[
                (
                    "elevated_risk_pressure"
                    if risk_pressure > 0.5
                    else "risk_pressure_normal"
                ),
                ("allocation_drift" if total_drift > 0.25 else "allocation_stable"),
                ("low_stability" if stability_score < 0.4 else "stability_normal"),
                (
                    "account_restricted"
                    if account_restricted
                    else "account_unrestricted"
                ),
                (
                    "high_portfolio_heat"
                    if portfolio_heat > 0.60
                    else "portfolio_heat_normal"
                ),
                (
                    "high_margin_utilization"
                    if margin_utilization_ratio > 0.60
                    else "margin_utilization_normal"
                ),
                (
                    "synthesis_selected"
                    if synthesis_allows_execution
                    else "synthesis_unresolved"
                ),
            ],
            recommendations=[
                (
                    "reduce_capital_deployment"
                    if scale_factor < 0.5
                    else "normal_capital_deployment"
                ),
                (
                    "preserve_capital"
                    if execution_status == "rejected"
                    else "allow_execution_pipeline"
                ),
                (
                    "respect_account_restrictions"
                    if account_restricted
                    else "account_restrictions_clear"
                ),
                (
                    "strategy_synthesis_selected"
                    if synthesis_allows_execution
                    else "resolve_strategy_synthesis_before_execution"
                ),
            ],
            features={
                # =================================================
                # ALLOCATION
                # =================================================
                "target_allocation": target_allocation,
                "drift": drift,
                "total_drift": total_drift,
                # =================================================
                # EXECUTION CONTROL
                # =================================================
                "execution_status": execution_status,
                "scale_factor": scale_factor,
                "portfolio_regime": portfolio_regime,
                # =================================================
                # RISK
                # =================================================
                "composite_risk": composite_risk,
                "risk_pressure": risk_pressure,
                "stability_score": stability_score,
                "risk_regime": risk_regime,
                "portfolio_heat": portfolio_heat,
                "risk_intensity": risk_intensity,
                "margin_utilization_ratio": margin_utilization_ratio,
                "account_restricted": account_restricted,
                # =================================================
                # SYNTHESIS DECISION
                # =================================================
                "selected_perspective": selected_perspective,
                "selection_status": selection_status,
                "synthesis_degraded_reasons": synthesis_degraded_reasons,
                "hypothesis_synthesis_weights": target_allocation,
                "synthesis_execution_blocked": not synthesis_allows_execution,
            },
        )

        # ========================================================
        # OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": (confidence),
                **(
                    {
                        "execution_status": execution_status,
                        "portfolio_regime": portfolio_regime,
                        "quality_status": "normal",
                        **authority_contract_metadata(
                            portfolio_allocation_intent_runtime_authority(
                                model_authority_claims_from_payloads(
                                    result,
                                    cast(Mapping[str, object], result["features"]),
                                )
                            )
                        ),
                    }
                ),
            },
            output_contract=PORTFOLIO_ALLOCATION_INTENT_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

    # ============================================================
    # EXECUTION STATUS
    # ============================================================

    def _execution_status(
        self,
        total_drift: float,
        composite_risk: float,
        risk_pressure: float,
        stability_score: float,
    ) -> str:

        if composite_risk > 0.80 or risk_pressure > 0.80 or stability_score < 0.20:
            return "rejected"

        if composite_risk > 0.60 or risk_pressure > 0.60 or total_drift > 0.35:
            return "restricted"

        if composite_risk > 0.40 or risk_pressure > 0.40 or total_drift > 0.20:
            return "approved_with_caution"

        return "approved"

    # ============================================================
    # SCALE FACTOR
    # ============================================================

    def _scale_factor(
        self,
        risk_pressure: float,
        stability_score: float,
        execution_status: str,
    ) -> float:

        scale = (1.0 - risk_pressure) * stability_score

        if execution_status == "rejected":
            scale *= 0.0

        elif execution_status == "restricted":
            scale *= 0.50

        elif execution_status == "approved_with_caution":
            scale *= 0.75

        return max(
            0.0,
            min(1.0, scale),
        )

    # ============================================================
    # PORTFOLIO REGIME
    # ============================================================

    def _portfolio_regime(
        self,
        posture: str,
        composite_risk: float,
    ) -> str:

        if composite_risk >= 0.75:
            return "capital_preservation"

        if posture == "risk_on":
            return "offensive"

        if posture == "risk_off":
            return "defensive"

        return "balanced"
