from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class TradeIntentContract:
    """
    Pure execution intent (NO risk logic, NO approvals).
    """

    symbol: str

    # Directional intent
    direction: str  # long | short | flat

    # Signal strength
    entry_bias: float  # -1 → +1

    # Sizing suggestion (NOT final size)
    position_sizing_hint: float  # 0 → 1

    # Trade structure
    stop_distance: float
    take_profit_distance: float

    # Quality signal
    trade_quality_score: float

    # Confidence in intent (not execution safety)
    confidence: float

    # Explainability
    reasoning: Dict[str, Any] = field(default_factory=dict)
