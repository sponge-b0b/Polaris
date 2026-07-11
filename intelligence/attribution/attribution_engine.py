from __future__ import annotations

from typing import Any, Dict


from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from domain.workflow_outputs import (
    ATTRIBUTION_EXPLANATION_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


class AttributionEngine(RuntimeNode):
    """
    Polaris Attribution Engine

    PURPOSE:
    --------
    Explain HOW upstream agents contributed
    to the market interpretation layer.

    IMPORTANT:
    ----------
    Attribution is:
        - observational
        - diagnostic
        - explainability-only

    Attribution is NOT:
        - synthesis
        - execution logic
        - signal mutation
        - portfolio construction

    ARCHITECTURE RULE:
    ------------------
    This engine ONLY consumes upstream RuntimeNodeOutput.outputs payloads.

    It MUST NOT depend on:
        - StrategySynthesisAgent
        - ExecutionAgent
        - PortfolioAgent
    """

    node_name = "attribution_engine"
    node_type = "strategy_attribution"

    # ============================================================
    # MAIN EXECUTION
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # FETCH UPSTREAM AGENT OUTPUTS
        # ========================================================

        technical_output = context.node_outputs.get("technical_agent")

        fundamental_output = context.node_outputs.get("fundamental_agent")

        sentiment_output = context.node_outputs.get("sentiment_agent")

        news_output = context.node_outputs.get("news_agent")

        risk_output = context.node_outputs.get("risk_aggregator_agent")

        # ========================================================
        # SAFE UNWRAP
        # ========================================================

        technical = technical_output.get("outputs", {}) if technical_output else None

        fundamental = (
            fundamental_output.get("outputs", {}) if fundamental_output else None
        )

        sentiment = sentiment_output.get("outputs", {}) if sentiment_output else None

        news = news_output.get("outputs", {}) if news_output else None

        risk = risk_output.get("outputs", {}) if risk_output else None

        # ========================================================
        # EXTRACT DIRECTIONAL SCORES
        # ========================================================

        technical_score = self._extract_score(technical)

        fundamental_score = self._extract_score(fundamental)

        sentiment_score = self._extract_score(sentiment)

        news_score = self._extract_score(news)

        # ========================================================
        # RISK IS INVERSE CONTRIBUTION
        # ========================================================

        risk_score = self._extract_score(risk)

        # ========================================================
        # BUILD CONTRIBUTION MAP
        # ========================================================

        contribution_map = {
            "technical": technical_score,
            "fundamental": fundamental_score,
            "sentiment": sentiment_score,
            "news": news_score,
            "risk": risk_score,
        }

        # ========================================================
        # DETERMINE DOMINANT DRIVER
        # ========================================================

        dominant_driver = max(
            contribution_map,
            key=lambda k: abs(contribution_map[k]),
        )

        dominant_score = abs(contribution_map[dominant_driver])

        # ========================================================
        # AGREEMENT / DISPERSION ANALYSIS
        # ========================================================

        agreement_score = self._agreement_score(contribution_map)

        # ========================================================
        # OVERALL ATTRIBUTION CONFIDENCE
        # ========================================================

        attribution_confidence = 0.50 + (agreement_score * 0.50)

        attribution_confidence = max(
            0.0,
            min(
                attribution_confidence,
                1.0,
            ),
        )

        # ========================================================
        # REGIME CLASSIFICATION
        # ========================================================

        attribution_regime = self._classify_regime(agreement_score)

        # ========================================================
        # BUILD SIGNALS
        # ========================================================

        signals = [
            "attribution_generated",
            f"dominant_driver:{dominant_driver}",
            f"agreement:{agreement_score}",
        ]

        # ========================================================
        # BUILD RISKS
        # ========================================================

        risks = []

        if agreement_score < 0.35:
            risks.append("cross_agent_disagreement")

        if dominant_score > 0.85:
            risks.append("single_factor_dominance")

        # ========================================================
        # BUILD RECOMMENDATIONS
        # ========================================================

        recommendations = [
            "use attribution for explainability only",
            "cross-check dominant drivers against regime conditions",
        ]

        if agreement_score < 0.35:
            recommendations.append("reduce conviction during signal dispersion")

        # ========================================================
        # BUILD RESULT
        # ========================================================

        result = dict(
            directional_score=0.0,
            confidence=attribution_confidence,
            regime=attribution_regime,
            signals=signals,
            risks=risks,
            recommendations=recommendations,
            features={
                "contribution_map": contribution_map,
                "dominant_driver": dominant_driver,
                "dominant_driver_strength": dominant_score,
                "agreement_score": agreement_score,
                "agent_count": len(contribution_map),
            },
        )

        # ========================================================
        # RETURN OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": attribution_confidence,
                **(
                    {
                        "engine": "AttributionEngine",
                        "purpose": "explainability",
                        "quality_status": "normal",
                    }
                ),
            },
            output_contract=ATTRIBUTION_EXPLANATION_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

    # ============================================================
    # SAFE SCORE EXTRACTION
    # ============================================================

    def _extract_score(
        self,
        result: dict[str, Any] | None,
    ) -> float:

        if result is None:
            return 0.0

        return float(
            result.get(
                "directional_score",
                0.0,
            )
        )

    # ============================================================
    # AGREEMENT SCORE
    # ============================================================

    def _agreement_score(
        self,
        contribution_map: Dict[str, float],
    ) -> float:
        """
        Measures directional agreement across agents.

        OUTPUT:
            1.0 = full alignment
            0.0 = severe disagreement
        """

        values = list(contribution_map.values())

        positives = len([v for v in values if v > 0.15])

        negatives = len([v for v in values if v < -0.15])

        total = len(values)

        dominant = max(
            positives,
            negatives,
        )

        return dominant / total

    # ============================================================
    # REGIME CLASSIFIER
    # ============================================================

    def _classify_regime(
        self,
        agreement_score: float,
    ) -> str:

        if agreement_score >= 0.80:
            return "high_alignment"

        if agreement_score >= 0.60:
            return "moderate_alignment"

        if agreement_score >= 0.40:
            return "mixed_signals"

        return "fragmented"
