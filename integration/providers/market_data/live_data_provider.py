import pandas as pd

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from domain.market.models import SP500Data
from integration.clients.market_data.massive_data_client import MassiveDataClient
from integration.clients.market_data.yfinance_data_client import YFinanceDataClient
from integration.providers.market_data.market_data_provider import MarketDataProvider
from integration.providers.provider_telemetry import record_provider_call


class LiveDataProvider(MarketDataProvider):
    def __init__(
        self,
        massive_data_client: MassiveDataClient,
        yfinance_data_client: YFinanceDataClient,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:

        self.massive_data_client = massive_data_client
        self.yfinance_data_client = yfinance_data_client
        self.telemetry = telemetry

    async def get_symbol_data(
        self,
        symbol: str,
        days: int,
    ) -> pd.DataFrame:

        if symbol is None or symbol != "SPY":
            raise ValueError(
                f"Invalid symbol for MarketDataProvider get_symbol_data: {symbol}"
            )

        return await record_provider_call(
            self.telemetry,
            self.__class__.__name__,
            "get_symbol_data",
            lambda: self.massive_data_client.get_symbol_data(
                symbol=symbol,
                multiplier=1,
                timespan="day",
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
            lambda: self.yfinance_data_client.get_symbol_data(
                symbol="^VIX",
                interval="1d",
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
            lambda: self.yfinance_data_client.get_symbol_data(
                symbol="^VVIX",
                interval="1d",
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
            lambda: self.yfinance_data_client.get_sp500_data(
                interval="1d",
                days=days,
            ),
        )
