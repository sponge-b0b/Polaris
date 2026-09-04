from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.models.workflow_node_definition import WorkflowNodeDefinition


class ExampleMarketNode(RuntimeNode):
    node_name = "example_market_node"
    node_type = "example_market"
    node_version = "1.0.0"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "trend_regime": "bullish",
                "volatility_regime": "normal",
                "market_breadth_score": 0.62,
                "message": "Example market analysis completed.",
            },
        )


class ExampleRiskNode(RuntimeNode):
    node_name = "example_risk_node"
    node_type = "example_risk"
    node_version = "1.0.0"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        market_outputs = _node_outputs(context, "example_market_node")
        risk_band = (
            "normal"
            if market_outputs.get("volatility_regime") == "normal"
            else "elevated"
        )
        return RuntimeNodeOutput.success_output(
            outputs={
                "risk_regime": "risk_on",
                "risk_band": risk_band,
                "overall_risk_score": 0.35,
                "message": "Example risk analysis completed.",
            },
        )


class ExampleStrategyNode(RuntimeNode):
    node_name = "example_strategy_node"
    node_type = "example_strategy"
    node_version = "1.0.0"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        market_outputs = _node_outputs(context, "example_market_node")
        risk_outputs = _node_outputs(context, "example_risk_node")
        execution_signal = (
            "review_long_bias"
            if market_outputs.get("trend_regime") == "bullish"
            and risk_outputs.get("risk_band") == "normal"
            else "hold"
        )
        return RuntimeNodeOutput.success_output(
            outputs={
                "final_directional_bias": 0.45,
                "final_confidence": 0.68,
                "portfolio_tilt": "moderate_long",
                "execution_signal": execution_signal,
                "recommendation": execution_signal,
                "message": "Example strategy synthesis completed.",
            },
        )


def _node_outputs(
    context: RuntimeContext,
    node_name: str,
) -> Mapping[str, Any]:
    node_result = context.node_outputs.get(node_name)
    if not isinstance(node_result, Mapping):
        return {}
    outputs = node_result.get("outputs")
    return outputs if isinstance(outputs, Mapping) else {}


class ExampleWorkflow(WorkflowGraphDefinition):
    """Minimal example workflow for validating canonical node-output flow."""

    @property
    def workflow_name(self) -> str:
        return "example_workflow"

    @property
    def workflow_description(self) -> str:
        return "Example three-node market, risk, and strategy workflow."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="example_market_node",
                node_type=ExampleMarketNode,
                dependencies=(),
                tags=("example", "market"),
            ),
            WorkflowNodeDefinition(
                name="example_risk_node",
                node_type=ExampleRiskNode,
                dependencies=("example_market_node",),
                tags=("example", "risk"),
            ),
            WorkflowNodeDefinition(
                name="example_strategy_node",
                node_type=ExampleStrategyNode,
                dependencies=("example_market_node", "example_risk_node"),
                tags=("example", "strategy"),
            ),
        ]
