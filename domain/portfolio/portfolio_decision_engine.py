from typing import Any


class PortfolioDecisionEngine:
    """
    FINAL FORM

    Converts risk-shaped synthesis output into a structured trade ticket
    for human execution on external trading platforms.

    No execution logic. No broker integration.
    """

    def __init__(
        self,
        max_position_size: float = 0.3,
    ) -> None:

        self.max_position_size = max_position_size

    # ============================================================
    # MAIN ENTRY POINT
    # ============================================================

    def generate_trade_ticket(
        self,
        symbol: str,
        synthesis: dict[str, Any],
    ) -> dict[str, Any]:

        bias = synthesis.get("bias", "neutral")
        confidence = synthesis.get("confidence", 0.5)

        position_scalar = synthesis.get(
            "position_size_scalar",
            confidence,
        )

        risk_multiplier = synthesis.get(
            "risk_multiplier",
            1.0,
        )

        strategy_breakdown = synthesis.get(
            "strategy_breakdown",
            {},
        )

        reasoning = synthesis.get(
            "reasoning",
            [],
        )

        # ========================================================
        # DIRECTION
        # ========================================================

        if bias == "bullish":
            direction = "LONG"
        elif bias == "bearish":
            direction = "SHORT"
        else:
            direction = "FLAT"

        # ========================================================
        # POSITION SIZING (RISK-ADJUSTED)
        # ========================================================

        raw_size = position_scalar * self.max_position_size

        adjusted_size = raw_size * risk_multiplier

        position_size = max(
            0.0,
            min(adjusted_size, self.max_position_size),
        )

        # ========================================================
        # CONVICTION SCORE
        # ========================================================

        conviction = confidence * risk_multiplier

        # ========================================================
        # RISK NOTES (EXPLANABILITY LAYER)
        # ========================================================

        risk_notes = self._generate_risk_notes(synthesis)

        # ========================================================
        # FINAL TRADE TICKET
        # ========================================================

        return {
            "symbol": symbol,
            "direction": direction,
            "conviction": conviction,
            "suggested_position_size": position_size,
            "risk_multiplier": risk_multiplier,
            "strategy_breakdown": strategy_breakdown,
            "reasoning": reasoning,
            "risk_notes": risk_notes,
        }

    # ============================================================
    # RISK EXPLANATION GENERATOR
    # ============================================================

    def _generate_risk_notes(
        self,
        synthesis: dict[str, Any],
    ) -> list[str]:

        notes = []

        risk_multiplier = synthesis.get(
            "risk_multiplier",
            1.0,
        )

        if risk_multiplier < 0.8:
            notes.append("Risk conditions are restrictive — position size reduced")

        if synthesis.get("bias") == "bullish":
            notes.append("Bullish bias confirmed by strategy consensus")

        if synthesis.get("bias") == "bearish":
            notes.append("Bearish bias dominates strategy signals")

        if not synthesis.get("strategy_breakdown"):
            notes.append("Low strategy agreement — reduced conviction")

        return notes
