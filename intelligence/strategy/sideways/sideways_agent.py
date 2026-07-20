from __future__ import annotations

from config.strategy_model_config import (
    DEFAULT_STRATEGY_MODEL_CONFIG,
    StrategyModelConfig,
)
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from domain.workflow_outputs import (
    STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.runtime import (
    strategy_evidence_context_from_node_outputs,
)
from intelligence.strategy.model_usage import perspective_reasoning_usage
from intelligence.strategy.sideways.sideways_hypothesis_policy import (
    build_sideways_hypothesis,
)


class SidewaysAgent(RuntimeNode):
    """
    Polaris Sideways Agent

    Produces the sideways strategy perspective from the canonical shared
    StrategyEvidenceContext created by StrategyEvidenceBuilder.
    """

    node_name = "sideways_agent"
    node_type = "sideways_strategy"

    def __init__(
        self,
        strategy_model_config: StrategyModelConfig | None = None,
    ) -> None:
        self.strategy_model_config = (
            strategy_model_config or DEFAULT_STRATEGY_MODEL_CONFIG
        )

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        evidence_context = strategy_evidence_context_from_node_outputs(
            context.node_outputs,
            consumer_name="SidewaysAgent",
        )
        decision = build_sideways_hypothesis(evidence_context)

        model_usage = perspective_reasoning_usage(
            perspective=StrategyPerspective.SIDEWAYS,
            model_config=self.strategy_model_config,
        )

        return RuntimeNodeOutput.success_output(
            outputs=decision.to_runtime_outputs(),
            execution_metadata={
                **model_usage.to_metadata(),
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": decision.hypothesis.confidence,
                "evidence_fingerprint": decision.hypothesis.evidence_fingerprint,
                "hypothesis_strength": decision.hypothesis.hypothesis_strength,
                "invalidated": decision.hypothesis.invalidated,
            },
            output_contract=STRATEGY_SIDEWAYS_HYPOTHESIS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )
