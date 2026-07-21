from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from config.strategy_model_config import StrategyModelConfig
from intelligence.strategy.hypothesis.contracts import StrategyPerspective

StrategyModelRole = Literal["perspective_reasoning", "strategy_synthesis"]
CalculationAuthority = Literal["code"]
LlmOutputAuthority = Literal["none"]
StrategyModelExecutionMode = Literal["not_executed"]
StrategyModelAliasPurpose = Literal["configured_lane_reference"]


@dataclass(frozen=True, slots=True)
class StrategyModelUsage:
    """Externally visible strategy model-lane policy metadata.

    Current strategy hypotheses, synthesis scores, and explanations are
    code-owned. The configured alias identifies the lane that future LLM-backed
    behavior must use; it is not proof that a model call occurred.
    """

    role: StrategyModelRole
    model_alias: str
    calculation_authority: CalculationAuthority = "code"
    llm_output_authority: LlmOutputAuthority = "none"
    execution_mode: StrategyModelExecutionMode = "not_executed"
    alias_purpose: StrategyModelAliasPurpose = "configured_lane_reference"
    perspective: StrategyPerspective | None = None

    def __post_init__(self) -> None:
        if not self.model_alias.strip():
            raise ValueError("model_alias cannot be empty.")
        object.__setattr__(self, "model_alias", self.model_alias.strip())

    def to_metadata(self) -> dict[str, object]:
        metadata: dict[str, object] = {
            "strategy_model_role": self.role,
            "strategy_model_alias": self.model_alias,
            "strategy_model_execution_mode": self.execution_mode,
            "strategy_model_alias_purpose": self.alias_purpose,
            "calculation_authority": self.calculation_authority,
            "llm_output_authority": self.llm_output_authority,
        }
        if self.perspective is not None:
            metadata["strategy_perspective"] = self.perspective.value
        return metadata


def perspective_reasoning_usage(
    *,
    perspective: StrategyPerspective,
    model_config: StrategyModelConfig,
) -> StrategyModelUsage:
    return StrategyModelUsage(
        role="perspective_reasoning",
        model_alias=model_config.perspective_reasoning_model,
        perspective=perspective,
    )


def strategy_synthesis_usage(
    *,
    model_config: StrategyModelConfig,
) -> StrategyModelUsage:
    return StrategyModelUsage(
        role="strategy_synthesis",
        model_alias=model_config.synthesis_model,
    )
