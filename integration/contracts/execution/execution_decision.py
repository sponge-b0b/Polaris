from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionDecision:
    approved: bool
    execution_mode: str  # normal | reduced | blocked

    blocked_reason: list[str] | None = None

    adjusted_position_size: float = 0.0
    final_leverage_allowed: float = 1.0

    risk_score: float = 0.0

    safety_flags: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)
