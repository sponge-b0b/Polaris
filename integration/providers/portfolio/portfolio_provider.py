from typing import Protocol, Dict, List, Any, runtime_checkable


@runtime_checkable
class PortfolioProvider(Protocol):
    """
    Canonical portfolio provider interface.

    ALL portfolio providers MUST implement this interface.
    """

    @property
    def source(self) -> str: ...

    async def get_account(self) -> Dict[str, Any]: ...

    async def get_positions(self) -> List[Dict[str, Any]]: ...

    async def get_portfolio_history(self) -> Dict[str, Any]: ...
