from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class SentimentSnapshotRequest:
    """
    Request payload for sentiment snapshot orchestration.
    """

    symbol: str = "SPY"
    previous_snapshot: dict[str, Any] | None = None
    risk_state: dict[str, Any] | None = None
