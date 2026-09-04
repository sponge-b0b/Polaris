import pandas as pd

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from domain.market.models import SP500Data
from integration.providers.market_data.market_data_provider import MarketDataProvider
from integration.providers.provider_telemetry import record_provider_call


class BacktestDataProvider(MarketDataProvider):
    def __init__(
        self,
        data_provider: MarketDataProvider,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.data_provider = data_provider
        self.telemetry = telemetry

    async def get_symbol_data(
        self,
        symbol: str,
        days: int,
    ) -> pd.DataFrame:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_symbol_data",
            lambda: self.data_provider.get_symbol_data(
                symbol=symbol,
                days=days,
            ),
        )

    async def get_vix_data(
        self,
        days: int,
    ) -> pd.DataFrame:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_vix_data",
            lambda: self.data_provider.get_vix_data(
                days=days,
            ),
        )

    async def get_vvix_data(
        self,
        days: int,
    ) -> pd.DataFrame:

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_vvix_data",
            lambda: self.data_provider.get_vvix_data(
                days=days,
            ),
        )

    async def get_sp500_data(
        self,
        days: int,
    ) -> SP500Data:
        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_sp500_data",
            lambda: self.data_provider.get_sp500_data(
                days=days,
            ),
        )
