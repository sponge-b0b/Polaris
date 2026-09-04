from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class MacroAnalysisRequest:
    """
    Request payload for macro analysis orchestration.
    """

    include_raw_data: bool = True
