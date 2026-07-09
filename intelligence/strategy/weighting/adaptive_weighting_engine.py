from __future__ import annotations


from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class AdaptiveStrategyWeightingEngine(RuntimeNode):
    """
    GRAPH-BASED STRATEGY WEIGHTING ENGINE (CANONICAL)

    PURPOSE:
    --------
    - derive weights ONLY from ExecutionGraph outputs
    - fully deterministic
    - no external state dependencies
    - no evolution snapshots

    INPUT:
    ------
    RuntimeContext.node_outputs → serialized RuntimeNodeOutput payloads

    OUTPUT:
    -------
    normalized strategy weights (bull/bear/sideways)
    """

    node_name = "weighting_engine"
    node_type = "adaptive_strategy_weighting_engine"

    # ============================================================
    # MAIN EXECUTION
    # ============================================================

    async def _execute(self, context: RuntimeContext) -> RuntimeNodeOutput:

        # RuntimeContext.node_outputs is the canonical execution graph snapshot.

        sentiment_agent_output = context.node_outputs["sentiment_agent"]

        if sentiment_agent_output is None:
            raise ValueError("Missing sentiment_agent in context.")

        sentiment_result = sentiment_agent_output.get("outputs", {})

        bull = 0.33
        bear = 0.33
        sideways = 0.34

        # ============================================================
        # SENTIMENT DRIVER (PRIMARY SIGNAL)
        # ============================================================

        directional = 0.0
        confidence = 0.5

        if sentiment_result:
            directional = sentiment_result.get("directional_score", 0.0)
            confidence = sentiment_result.get("confidence", 0.0)

        # ============================================================
        # RISK SIGNAL EXTRACTION (FROM GRAPH)
        # ============================================================

        risk_nodes = [
            "risk_aggregator_agent",
            "volatility_risk_agent",
            "drawdown_risk_agent",
            "exposure_risk_agent",
        ]

        risk_pressure = 0.0

        for node in risk_nodes:
            output = context.node_outputs[node]
            if not output:
                continue

            result = output.get("outputs", {})
            if result and isinstance(result, dict):
                risk_pressure += 1.0 - result.get("confidence", 0.0)

        risk_pressure = min(risk_pressure, 1.0)

        # ============================================================
        # GRAPH MOMENTUM (CONSENSUS SIGNAL)
        # ============================================================

        bull_votes = 0
        bear_votes = 0
        sideways_votes = 0

        for _, output in context.node_outputs.items():
            result = output.get("outputs", {})
            if not isinstance(result, dict):
                continue

            score = result.get("directional_score", 0.0)

            if score > 0.2:
                bull_votes += 1
            elif score < -0.2:
                bear_votes += 1
            else:
                sideways_votes += 1

        total_votes = bull_votes + bear_votes + sideways_votes or 1

        bull_vote_ratio = bull_votes / total_votes
        bear_vote_ratio = bear_votes / total_votes
        sideways_vote_ratio = sideways_votes / total_votes

        # ============================================================
        # CORE WEIGHT COMPUTATION
        # ============================================================

        bull *= 1.0 + max(0.0, directional)
        bear *= 1.0 + max(0.0, -directional)
        sideways *= 1.0 + (1.0 - confidence)

        # risk dampening
        bull *= 1.0 - risk_pressure * 0.5
        bear *= 1.0 - risk_pressure * 0.5
        sideways *= 1.0 - risk_pressure * 0.2

        # graph consensus reinforcement
        bull *= 1.0 + bull_vote_ratio * 0.3
        bear *= 1.0 + bear_vote_ratio * 0.3
        sideways *= 1.0 + sideways_vote_ratio * 0.2

        # ============================================================
        # NORMALIZATION
        # ============================================================

        total = bull + bear + sideways or 1.0

        bull_w = bull / total
        bear_w = bear / total
        side_w = sideways / total

        # ============================================================
        # RESULT CONSTRUCTION
        # ============================================================

        result = dict(
            directional_score=0.0,  # weighting engine is NOT directional
            confidence=round(confidence, 3),
            regime="strategy_weighting",
            signals=[
                "graph_weighting_applied",
                f"bull_vote_ratio_{bull_vote_ratio:.2f}",
                f"bear_vote_ratio_{bear_vote_ratio:.2f}",
            ],
            risks=[
                "risk_pressure_detected" if risk_pressure > 0.5 else "normal_risk",
            ],
            recommendations=[
                "use weights as allocation multipliers only",
                "do not interpret as directional signal",
            ],
            features={
                "bull_weight": round(bull_w, 4),
                "bear_weight": round(bear_w, 4),
                "sideways_weight": round(side_w, 4),
                "directional_input": directional,
                "confidence_input": confidence,
                "risk_pressure": risk_pressure,
                "graph_votes": {
                    "bull": bull_votes,
                    "bear": bear_votes,
                    "sideways": sideways_votes,
                },
            },
        )

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": (confidence),
                **({}),
            },
        )
