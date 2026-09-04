from __future__ import annotations

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class ExamplePluginMarketNode(RuntimeNode):
    node_name = "example_plugin_market_node"
    node_type = "plugin.example.market"
    node_version = "1.0.0"

    parallel_safe = True

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "source": "example_market_plugin",
                "symbol": "SPY",
                "latest_price": 743.25,
                "signal": "neutral",
            },
            execution_metadata={
                "plugin_name": "example_market_plugin",
            },
        )
