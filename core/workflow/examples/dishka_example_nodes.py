from __future__ import annotations

from dataclasses import dataclass

from dishka import Provider, Scope, provide

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


@dataclass(frozen=True, slots=True)
class ExampleMarketDataService:
    symbol: str = "SPY"

    def get_latest_price(self) -> float:
        return 743.25


class DishkaMarketDataNode(RuntimeNode):
    node_name = "dishka_market_data"
    node_type = "example.market_data"
    node_version = "1.0.0"

    parallel_safe = True

    def __init__(
        self,
        market_data_service: ExampleMarketDataService,
    ) -> None:
        self.market_data_service = market_data_service

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        price = self.market_data_service.get_latest_price()

        return RuntimeNodeOutput.success_output(
            outputs={
                "symbol": self.market_data_service.symbol,
                "latest_price": price,
            },
        )


class ExampleWorkflowNodeProvider(Provider):
    scope = Scope.APP

    @provide
    def provide_market_data_service(
        self,
    ) -> ExampleMarketDataService:
        return ExampleMarketDataService()

    @provide
    def provide_market_data_node(
        self,
        market_data_service: ExampleMarketDataService,
    ) -> DishkaMarketDataNode:
        return DishkaMarketDataNode(
            market_data_service=market_data_service,
        )
