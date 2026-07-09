from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ExecutionDecision:
    approved: bool
    execution_mode: str  # normal | reduced | blocked

    blocked_reason: Optional[List[str]] = None

    adjusted_position_size: float = 0.0
    final_leverage_allowed: float = 1.0

    risk_score: float = 0.0

    safety_flags: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)
