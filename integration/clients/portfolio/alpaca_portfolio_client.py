from __future__ import annotations

import asyncio
from typing import Any, cast

from alpaca.trading.client import TradingClient
from alpaca.trading.models import PortfolioHistory, Position, TradeAccount
from alpaca.trading.requests import GetPortfolioHistoryRequest

from config.settings import Settings


class AlpacaPortfolioClient:
    """
    Polaris Alpaca Client (Paper Trading Adapter)

    PURPOSE:
    --------
    - Fetch account equity state
    - Fetch positions
    - Normalize Alpaca API → Polaris Portfolio Schema
    - Provide deterministic portfolio state inputs
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        self.api_key = settings.ALPACA_API_KEY
        if not self.api_key:
            raise ValueError("ALPACA_API_KEY not found in environment variables.")

        self.secret_key = settings.ALPACA_API_SECRET_KEY
        if not self.secret_key:
            raise ValueError(
                "ALPACA_API_SECRET_KEY not found in environment variables."
            )

        self.client = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=True,
        )

    # ============================================================
    # ACCOUNT STATE
    # ============================================================

    async def get_account(self) -> dict[str, Any]:
        """
        Returns normalized account-level metrics
        required by PortfolioStateBuilder.

        Attributes:
            id (UUID): The account ID
            account_number (str): The account number
            status (AccountStatus): The current status of the account
            crypto_status (Optional[AccountStatus]): The status of the account in regards to trading crypto. Only present if
            crypto trading is enabled for your brokerage account.
            currency (Optional[str]): Currently will always be the value "USD".
            buying_power (Optional[str]): Current available cash buying power. If multiplier = 2 then
            buying_power = max(equity-initial_margin(0) * 2). If multiplier = 1 then buying_power = cash.
            regt_buying_power (Optional[str]): User’s buying power under Regulation T
            (excess equity - (equity - margin value) - * margin multiplier)
            daytrading_buying_power (Optional[str]): The buying power for day trades for the account
            non_marginable_buying_power (Optional[str]): The non marginable buying power for the account
            cash (Optional[str]): Cash balance in the account
            accrued_fees (Optional[str]): Fees accrued in this account
            pending_transfer_out (Optional[str]): Cash pending transfer out of this account
            pending_transfer_in (Optional[str]): Cash pending transfer into this account
            portfolio_value (str): Total value of cash + holding positions.
            (This field is deprecated. It is equivalent to the equity field.)
            pattern_day_trader (Optional[bool]): Whether the account is flagged as pattern day trader or not.
            trading_blocked (Optional[bool]): If true, the account is not allowed to place orders.
            transfers_blocked (Optional[bool]): If true, the account is not allowed to request money transfers.
            account_blocked (Optional[bool]): If true, the account activity by user is prohibited.
            created_at (Optional[datetime]): Timestamp this account was created at
            trade_suspended_by_user (Optional[bool]): If true, the account is not allowed to place orders.
            multiplier (Optional[str]): Multiplier value for this account.
            shorting_enabled (Optional[bool]): Flag to denote whether or not the account is permitted to short
            equity (Optional[str]): This value is cash + long_market_value + short_market_value. This value isn't calculated in the
            SDK it is computed on the server and we return the raw value here.
            last_equity (Optional[str]): Equity as of previous trading day at 16:00:00 ET
            long_market_value (Optional[str]): Real-time MtM value of all long positions held in the account
            short_market_value (Optional[str]): Real-time MtM value of all short positions held in the account
            initial_margin (Optional[str]): Reg T initial margin requirement
            maintenance_margin (Optional[str]): Maintenance margin requirement
            last_maintenance_margin (Optional[str]): Maintenance margin requirement on the previous trading day
            sma (Optional[str]): Value of Special Memorandum Account (will be used at a later date to provide additional buying_power)
            daytrade_count (Optional[int]): The current number of daytrades that have been made in the last 5 trading days
            (inclusive of today)
            options_buying_power (Optional[str]): Your buying power for options trading
            options_approved_level (Optional[int]): The options trading level that was approved for this account.
            0=disabled, 1=Covered Call/Cash-Secured Put, 2=Long Call/Put, 3=Spreads/Straddles.
            options_trading_level (Optional[int]): The effective options trading level of the account. This is the minimum between account options_approved_level and account configurations max_options_trading_level.
            0=disabled, 1=Covered Call/Cash-Secured Put, 2=Long, 3=Spreads/Straddles.
        """  # noqa: E501
        account = cast(TradeAccount, await asyncio.to_thread(self.client.get_account))

        return account.model_dump(mode="json")

    # ============================================================
    # POSITIONS
    # ============================================================

    async def get_positions(self) -> list[dict[str, Any]]:
        """
        Returns normalized position list for PortfolioService.

        Attributes:
            asset_id (UUID): ID of the asset.
            symbol (str): Symbol of the asset.
            exchange (AssetExchange): Exchange name of the asset.
            asset_class (AssetClass): Name of the asset's asset class.
            asset_marginable (Optional[bool]): Indicates if this asset is marginable.
            avg_entry_price (str): The average entry price of the position.
            qty (str): The number of shares of the position.
            side (PositionSide): "long" or "short" representing the side of the position.
            market_value (Optional[str]): Total dollar amount of the position.
            cost_basis (str): Total cost basis in dollars.
            unrealized_pl (Optional[str]): Unrealized profit/loss in dollars.
            unrealized_plpc (Optional[str]): Unrealized profit/loss percent.
            unrealized_intraday_pl (Optional[str]): Unrealized profit/loss in dollars for the day.
            unrealized_intraday_plpc (Optional[str]): Unrealized profit/loss percent for the day.
            current_price (Optional[str]): Current asset price per share.
            lastday_price (Optional[str]): Last day’s asset price per share based on the closing value of the last trading day.
            change_today (Optional[str]): Percent change from last day's price.
            swap_rate (Optional[str]): Swap rate is the exchange rate (without mark-up) used to convert the price into local currency or crypto asset.
            avg_entry_swap_rate (Optional[str]): The average exchange rate the price was converted into the local currency at.
            usd (USDPositionValues): Represents the position in USD values.
            qty_available (Optional[str]): Total number of shares available minus open orders.
        """  # noqa: E501

        positions = cast(
            list[Position], await asyncio.to_thread(self.client.get_all_positions)
        )

        normalized: list[dict[str, Any]] = []
        for p in positions:
            normalized.append(
                {
                    **p.model_dump(mode="json"),
                    # not provided by Alpaca → deterministic placeholders
                    "sector": "multi_sector",
                    "beta": 1.0,
                }
            )

        return normalized

    # ============================================================
    # PORTFOLIO HISTORY
    # ============================================================

    async def get_portfolio_history(
        self,
        *,
        period: str = "1A",
        timeframe: str = "1D",
    ) -> dict[str, Any]:
        """
        Returns portfolio history metrics
        required by PortfolioService.

        Attributes:
            timestamp (list[int]): Time of each data element, left-labeled.
            equity (list[float]): Equity value as of the end of each window.
            profit_loss (list[float]): Profit/loss in dollars from the base value.
            profit_loss_pct (list[float | None]): Profit/loss percentage.
            base_value (float | None): Basis for profit/loss calculation.
            timeframe (str): Time window size of each data element.
            cashflow (dict[str, list[float]]): Cash flow amounts, if any.
        """

        history_request = GetPortfolioHistoryRequest(
            period=period,
            timeframe=timeframe,
        )
        portfolio_history = cast(
            PortfolioHistory,
            await asyncio.to_thread(
                self.client.get_portfolio_history,
                history_filter=history_request,
            ),
        )

        return portfolio_history.model_dump(mode="json")

    # ============================================================
    # COMBINED PORTFOLIO SNAPSHOT
    # ============================================================

    async def get_full_portfolio_snapshot(self) -> dict[str, Any]:
        """
        Convenience method for PortfolioStateBuilder.
        """

        account, positions, portfolio = await asyncio.gather(
            self.get_account(),
            self.get_positions(),
            self.get_portfolio_history(),
        )

        return {
            "account": account,
            "positions": positions,
            "portfolio": portfolio,
        }
