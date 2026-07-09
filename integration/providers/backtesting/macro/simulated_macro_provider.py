from __future__ import annotations

from domain.macro.models import MacroDataSnapshot
from integration.providers.macro.macro_provider import MacroProvider


class SimulatedMacroProvider(MacroProvider):
    """Deterministic macro data source for backtesting."""

    async def get_macro_snapshot(self) -> MacroDataSnapshot:
        return MacroDataSnapshot(
            cpi=0.0,
            core_cpi=0.0,
            pce=0.0,
            fed_funds_rate=0.0,
            treasury_2y=0.0,
            treasury_10y=0.0,
            unemployment_rate=0.0,
            m2_money_supply=0.0,
            vix=0.0,
        )
