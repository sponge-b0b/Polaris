from __future__ import annotations

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from domain.macro.models import MacroDataSnapshot
from integration.providers.backtesting.macro.simulated_macro_provider import (
    SimulatedMacroProvider,
)
from integration.providers.provider_telemetry import record_provider_call


class BacktestMacroProvider:
    def __init__(
        self,
        macro_provider: SimulatedMacroProvider,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self.macro_provider = macro_provider
        self.telemetry = telemetry

    async def get_macro_snapshot(self) -> MacroDataSnapshot:
        return await record_provider_call(
            telemetry=self.telemetry,
            provider_name=self.__class__.__name__,
            operation="get_macro_snapshot",
            call=self.macro_provider.get_macro_snapshot,
            attributes={"source": "simulated"},
        )
