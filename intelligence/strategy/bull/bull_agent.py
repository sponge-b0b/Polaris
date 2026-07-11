from __future__ import annotations

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from domain.workflow_outputs import (
    STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.bull.bull_hypothesis_policy import build_bull_hypothesis
from intelligence.strategy.hypothesis.runtime import (
    strategy_evidence_context_from_node_outputs,
)


class BullAgent(RuntimeNode):
    """
    Polaris Bull Agent

    Produces the bull strategy perspective from the canonical shared
    StrategyEvidenceContext created by StrategyEvidenceBuilder.
    """

    node_name = "bull_agent"
    node_type = "bull_strategy"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        evidence_context = strategy_evidence_context_from_node_outputs(
            context.node_outputs,
            consumer_name="BullAgent",
        )
        decision = build_bull_hypothesis(evidence_context)

        return RuntimeNodeOutput.success_output(
            outputs=decision.to_runtime_outputs(),
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": decision.hypothesis.confidence,
                "evidence_fingerprint": decision.hypothesis.evidence_fingerprint,
                "hypothesis_strength": decision.hypothesis.hypothesis_strength,
                "invalidated": decision.hypothesis.invalidated,
            },
            output_contract=STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )
