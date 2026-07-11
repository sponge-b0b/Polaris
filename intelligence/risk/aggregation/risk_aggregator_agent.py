from __future__ import annotations

from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from domain.workflow_outputs import (
    RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)

from integration.contracts.risk.risk_signal_contract import (
    RiskSignalContract,
)

from intelligence.risk.regime import (
    risk_regime_coupling,
)
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
    extract_technical_breadth_context,
)

from integration.adapters.risk import (
    risk_runtime_adapter,
)
from intelligence.risk.breadth_annotations import (
    annotate_risk_runtime_output,
    deduplicate_strings,
)


class RiskAggregatorAgent(RuntimeNode):
    """
    Polaris Risk Aggregator Agent V4

    PURPOSE:
    --------
    Final regime-aware calibration layer for portfolio risk.

    IMPORTANT:
    ----------
    This node DOES NOT aggregate primitive risk agents directly.

    Aggregation responsibility belongs to:
        RiskSignalBuilder

    This node ONLY:
    - consumes aggregated RiskSignalContract
    - applies technical regime coupling
    - contextualizes risk for execution layer
    - converts canonical contract -> RuntimeNodeOutput
    """

    node_name = "risk_aggregator_agent"
    node_type = "risk_aggregator"

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # FETCH RISK SIGNAL BUILDER OUTPUT
        # ========================================================

        risk_builder_output = context.node_outputs.get("risk_signal_builder")

        if risk_builder_output is None:
            raise ValueError(
                "RiskAggregatorAgent requires 'risk_signal_builder' in context."
            )

        base_result: dict[str, Any] = risk_builder_output.get("outputs", {})

        # ========================================================
        # REBUILD CANONICAL RISK CONTRACT
        # ========================================================

        features = base_result.get("features", {}) or {}

        base_risk = RiskSignalContract(
            volatility_risk=float(
                features.get(
                    "volatility_risk",
                    0.5,
                )
            ),
            drawdown_risk=float(
                features.get(
                    "drawdown_risk",
                    0.5,
                )
            ),
            exposure_risk=float(
                features.get(
                    "exposure_risk",
                    0.5,
                )
            ),
            composite_risk=float(
                features.get(
                    "composite_risk",
                    0.0,
                )
            ),
            risk_pressure=float(
                features.get(
                    "risk_pressure",
                    0.0,
                )
            ),
            stability_score=float(
                features.get(
                    "stability_score",
                    0.5,
                )
            ),
            risk_regime=str(
                features.get(
                    "risk_regime",
                    "neutral",
                )
            ),
            risk_bias=str(
                features.get(
                    "risk_bias",
                    "neutral",
                )
            ),
            recommendations=list(base_result.get("recommendations", []) or []),
            features=features,
        )

        # ========================================================
        # FETCH TECHNICAL AGENT OUTPUT
        # ========================================================

        technical_output = context.node_outputs.get("technical_agent")

        technical_regime = {}

        volatility = {}

        breadth_context = extract_technical_breadth_context(
            technical_output,
        )

        if technical_output is not None:
            technical_features = (
                technical_output.get("outputs", {}).get("features", {}) or {}
            )

            # ====================================================
            # IMPORTANT:
            # USE CALIBRATED REGIME OUTPUT
            # NOT raw_regime
            # ====================================================

            technical_regime = technical_features.get("regime", {})

            volatility = technical_features.get("volatility", {})

        # ========================================================
        # APPLY REGIME COUPLING
        # ========================================================

        coupled = risk_regime_coupling.apply(
            risk={
                "composite_risk": base_risk.composite_risk,
                "risk_pressure": base_risk.risk_pressure,
                "stability_score": base_risk.stability_score,
            },
            technical_regime=technical_regime,
            volatility=volatility,
            breadth_context=breadth_context,
        )

        # ========================================================
        # BUILD ENRICHED CONTRACT
        # ========================================================

        enriched_contract = RiskSignalContract(
            volatility_risk=(base_risk.volatility_risk),
            drawdown_risk=(base_risk.drawdown_risk),
            exposure_risk=(base_risk.exposure_risk),
            composite_risk=float(coupled["adjusted_composite_risk"]),
            risk_pressure=float(coupled["adjusted_risk_pressure"]),
            stability_score=(base_risk.stability_score),
            risk_regime=str(coupled["risk_intensity"]),
            risk_bias=(base_risk.risk_bias),
            recommendations=deduplicate_strings(
                list(base_risk.recommendations)
                + _breadth_recommendations(
                    breadth_context,
                )
            ),
            features={
                **(base_risk.features or {}),
                # ================================================
                # COUPLING OUTPUTS
                # ================================================
                "adjusted_risk_score": coupled.get("adjusted_risk_score"),
                "adjusted_composite_risk": coupled.get("adjusted_composite_risk"),
                "adjusted_risk_pressure": coupled.get("adjusted_risk_pressure"),
                # ================================================
                # REGIME MODULATION
                # ================================================
                "regime_modulation": coupled.get(
                    "modifiers",
                    {},
                ),
                "regime_inputs": coupled.get(
                    "inputs",
                    {},
                ),
                # ================================================
                # TRACEABILITY
                # ================================================
                "technical_regime": technical_regime,
                "volatility_context": volatility,
                # ================================================
                # BREADTH CONTEXT
                # ================================================
                "breadth_context": breadth_context.to_dict(),
                "breadth_confirmation_score": breadth_context.confirmation_score,
                "breadth_risk_pressure": breadth_context.risk_pressure,
                "breadth_risk_flags": list(
                    breadth_context.risk_flags(),
                ),
                "breadth_regime_modifier": coupled.get(
                    "modifiers",
                    {},
                ).get(
                    "breadth_modifier",
                ),
                "breadth_pressure_adjustment": coupled.get(
                    "modifiers",
                    {},
                ).get(
                    "breadth_pressure_adjustment",
                ),
            },
        )

        # ========================================================
        # FINAL OUTPUT
        # ========================================================

        runtime_output = risk_runtime_adapter.to_runtime_output(
            node_name=self.node_name,
            node_type=self.node_type,
            contract=enriched_contract,
            output_contract=RISK_AGGREGATE_SIGNAL_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

        return annotate_risk_runtime_output(
            runtime_output=runtime_output,
            breadth_context=breadth_context,
        )


def _breadth_recommendations(
    breadth_context: TechnicalBreadthContext,
) -> list[str]:
    if not breadth_context.has_breadth_data:
        return []

    recommendations: list[str] = []
    if breadth_context.price_ad_divergence:
        recommendations.append("risk_regime_requires_breadth_divergence_review")
    if breadth_context.risk_pressure >= 0.65:
        recommendations.append("elevated_breadth_risk_increases_portfolio_risk")
    if breadth_context.participation_score <= -0.25:
        recommendations.append("reduce_risk_until_market_participation_improves")
    if breadth_context.is_strong:
        recommendations.append("breadth_confirms_lower_risk_pressure")
    return recommendations
