import pandas as pd
from typing import Protocol, runtime_checkable

from domain.market.models import SP500Data


@runtime_checkable
class MarketDataProvider(Protocol):
    """
    Canonical market data provider interface.

    ALL market data providers MUST implement this interface.
    """

    async def get_symbol_data(
        self,
        symbol: str,
        days: int,
    ) -> pd.DataFrame: ...

    async def get_vix_data(
        self,
        days: int,
    ) -> pd.DataFrame: ...

    async def get_vvix_data(
        self,
        days: int,
    ) -> pd.DataFrame: ...

    async def get_sp500_data(
        self,
        days: int,
    ) -> SP500Data: ...
