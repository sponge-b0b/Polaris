from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from integration.adapters.risk import risk_runtime_adapter
from intelligence.risk.breadth_annotations import annotate_risk_runtime_output
from intelligence.risk.volatility.volatility_risk_policy import (
    VolatilityRiskInputs,
    evaluate_volatility_risk,
)


class VolatilityRiskAgent(RuntimeNode):
    """Orchestrates canonical volatility-risk evaluation for the runtime."""

    node_name = "volatility_risk_agent"
    node_type = "risk_agent"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        inputs = VolatilityRiskInputs.from_runtime_outputs(context.node_outputs)
        decision = evaluate_volatility_risk(inputs)
        runtime_output = risk_runtime_adapter.to_runtime_output(
            node_name=self.node_name,
            node_type=self.node_type,
            contract=decision.to_contract(),
        )
        return annotate_risk_runtime_output(
            runtime_output=runtime_output,
            breadth_context=inputs.breadth_context,
        )
