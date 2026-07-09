from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import cast

import pandas as pd
import pytest

from application.persistence.portfolio import PortfolioPersistenceService
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceBundle
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceRepository
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceResult

from application.services.base import ServiceRequest
from application.services.macro.macro_request import MacroAnalysisRequest
from application.services.macro.macro_result import MacroAnalysisResult
from application.services.macro.macro_service import MacroService
from application.services.market_events.market_events_request import (
    MarketEventsRequest,
)
from application.services.market_events.market_events_result import (
    MarketEventsResult,
)
from application.services.market_events.market_events_service import (
    MarketEventsService,
)
from application.services.news.news_request import NewsRequest
from application.services.news.news_result import NewsResult
from application.services.news.news_service import NewsService
from application.services.portfolio.portfolio_request import (
    PortfolioAnalysisRequest,
)
from application.services.portfolio.portfolio_result import (
    PortfolioAnalysisResult,
)
from application.services.portfolio.portfolio_service import PortfolioService
from application.services.sentiment.sentiment_request import (
    SentimentSnapshotRequest,
)
from application.services.sentiment.sentiment_result import (
    SentimentSnapshotResult,
)
from application.services.sentiment.sentiment_service import SentimentService
from application.services.technical.technical_request import (
    TechnicalAnalysisRequest,
)
from application.services.technical.technical_result import (
    TechnicalAnalysisResult,
)
from application.services.technical.technical_analysis_service import (
    TechnicalAnalysisService,
)
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
)
from domain.macro.models import MacroDataSnapshot
from domain.portfolio.models.portfolio_state import PortfolioState
from domain.market.models import SP500Data
from integration.providers.macro.macro_provider import MacroProvider
from integration.providers.market_events.market_events_provider import (
    MarketEventsProvider,
)
from integration.providers.news.news_provider import NewsProvider
from integration.providers.sentiment.sentiment_provider import SentimentProvider


class FakeMacroProvider:
    async def get_macro_snapshot(self) -> MacroDataSnapshot:
        return MacroDataSnapshot(
            cpi=3.2,
            core_cpi=3.4,
            pce=2.8,
            fed_funds_rate=5.0,
            treasury_2y=4.4,
            treasury_10y=4.6,
            unemployment_rate=3.8,
            m2_money_supply=20_000_000.0,
            vix=18.0,
        )


class FakeMarketDataProvider:
    def get_daily_bars(
        self,
        symbol: str,
        days: int,
    ) -> pd.DataFrame:
        row_count = max(days, 100)

        return pd.DataFrame(
            {
                "datetime": pd.date_range(
                    "2026-01-01",
                    periods=row_count,
                ),
                "open": [100.0 + idx for idx in range(row_count)],
                "high": [102.0 + idx for idx in range(row_count)],
                "low": [99.0 + idx for idx in range(row_count)],
                "close": [101.0 + idx for idx in range(row_count)],
                "volume": [1000 + idx for idx in range(row_count)],
            }
        )

    async def get_symbol_data(
        self,
        symbol: str,
        days: int,
    ) -> pd.DataFrame:
        return self.get_daily_bars(
            symbol=symbol,
            days=days,
        )

    async def get_vix_data(
        self,
        days: int,
    ) -> pd.DataFrame:
        return self.get_daily_bars(
            symbol="VIX",
            days=days,
        )

    async def get_vvix_data(
        self,
        days: int,
    ) -> pd.DataFrame:
        return self.get_daily_bars(
            symbol="VVIX",
            days=days,
        )

    async def get_sp500_data(
        self,
        days: int,
    ) -> SP500Data:
        row_count = max(
            days,
            300,
        )
        advances = [260 + (idx % 20) for idx in range(row_count)]
        declines = [220 - (idx % 10) for idx in range(row_count)]
        frame = pd.DataFrame(
            {
                "market_cap_index": [100.0 + idx for idx in range(row_count)],
                "advances_count": advances,
                "declines_count": declines,
                "unchanged_count": [20 for _ in range(row_count)],
            },
            index=pd.date_range(
                "2026-01-01",
                periods=row_count,
            ),
        )
        frame["active_count"] = frame["advances_count"] + frame["declines_count"]
        frame["net_breadth"] = frame["advances_count"] - frame["declines_count"]
        frame["ad_line"] = frame["net_breadth"].cumsum()
        frame["ad_ratio"] = frame["advances_count"] / frame["declines_count"]
        frame["breadth_percent"] = frame["advances_count"] / frame["active_count"]
        frame["pct_above_50dma"] = [
            0.56 + ((idx % 10) * 0.01) for idx in range(row_count)
        ]
        frame["pct_above_200dma"] = [
            0.52 + ((idx % 8) * 0.01) for idx in range(row_count)
        ]
        frame["new_highs"] = [25 + (idx % 6) for idx in range(row_count)]
        frame["new_lows"] = [8 + (idx % 4) for idx in range(row_count)]
        return SP500Data(
            analytics=frame,
            top_50_constituents=[f"STOCK{idx}" for idx in range(1, 51)],
            market_caps={f"STOCK{idx}": 1_000_000.0 + idx for idx in range(1, 51)},
        )


class FakeMarketEventsProvider:
    def __init__(self) -> None:
        self.earnings_symbols: set[str] | None = None

    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return []

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return []

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        self.earnings_symbols = symbols
        return []


class FakeNewsProvider:
    async def get_financial_news(
        self,
        query: str,
        sort_by: str = "publishedAt",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return [
            {
                "title": "Fed rates update",
                "description": "SPY market rates news",
                "source": "test",
            }
        ]

    async def get_market_news(
        self,
        symbol: str = "SPY",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return []


class FakePortfolioProvider:
    source = "test"

    async def get_positions(
        self,
    ) -> list[dict[str, Any]]:
        return []

    async def get_account(
        self,
    ) -> dict[str, Any]:
        return {
            "id": "account-1",
            "account_number": "account-1",
            "equity": 100_000.0,
            "portfolio_value": 100_000.0,
            "cash": 25_000.0,
            "buying_power": 50_000.0,
        }

    async def get_portfolio_history(
        self,
    ) -> dict[str, Any]:
        return {}


class FakePortfolioExpansionRepository:
    async def persist_portfolio_expansion_bundle(
        self,
        bundle: PortfolioExpansionPersistenceBundle,
    ) -> PortfolioExpansionPersistenceResult:
        return PortfolioExpansionPersistenceResult.succeeded(
            account_id=(
                bundle.equity_history_points[0].account_id
                if bundle.equity_history_points
                else "empty-portfolio-expansion-bundle"
            ),
            records_persisted=len(bundle.equity_history_points),
        )


class FakePortfolioRepository:
    async def get_latest(
        self,
        account_id: str,
    ) -> None:
        return None

    async def persist_snapshot(
        self,
        state: Any,
    ) -> None:
        return None

    async def get_history(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> list[PortfolioState]:
        return []


class FakeSentimentProvider:
    async def get_news_sentiment(
        self,
        symbol: str = "SPY",
    ) -> dict[str, Any]:
        return {
            "sentiment_score": 0.2,
            "overall_sentiment": "bullish",
            "components": {
                "news": 0.2,
                "social": 0.1,
                "insider": 0.0,
            },
        }

    async def get_fear_greed_sentiment(
        self,
    ) -> dict[str, Any]:
        return {
            "value": 60,
        }


@pytest.mark.asyncio
async def test_macro_service_canonical_run() -> None:
    service = MacroService(
        macro_provider=cast(
            MacroProvider,
            FakeMacroProvider(),
        ),
    )

    result = await service.run(
        ServiceRequest(
            payload=MacroAnalysisRequest(
                include_raw_data=False,
            ),
        )
    )

    assert result.success is True
    assert isinstance(result.result, MacroAnalysisResult)
    assert result.result.macro_data is None


@pytest.mark.asyncio
async def test_market_events_service_canonical_run() -> None:
    provider = FakeMarketEventsProvider()
    request = MarketEventsRequest(
        symbol_constituents=frozenset(
            {
                "AAPL",
                "MSFT",
            }
        ),
    )
    service = MarketEventsService(
        events_provider=cast(
            MarketEventsProvider,
            provider,
        ),
    )

    result = await service.run(
        ServiceRequest(
            payload=request,
        )
    )

    assert result.success is True
    assert isinstance(result.result, MarketEventsResult)
    assert isinstance(MarketEventsRequest().symbol_constituents, frozenset)
    assert provider.earnings_symbols == set(request.symbol_constituents)
    assert result.result.event_count == 0
    assert result.result.volatility_pressure == 0.0


@pytest.mark.asyncio
async def test_news_service_canonical_run() -> None:
    service = NewsService(
        news_provider=cast(
            NewsProvider,
            FakeNewsProvider(),
        ),
    )

    result = await service.run(
        ServiceRequest(
            payload=NewsRequest(
                limit=5,
            ),
        )
    )

    assert result.success is True
    assert isinstance(result.result, NewsResult)
    assert len(result.result.articles) == 1


@pytest.mark.asyncio
async def test_portfolio_service_canonical_run() -> None:
    service = PortfolioService(
        portfolio_provider=FakePortfolioProvider(),
        portfolio_persistence_service=PortfolioPersistenceService(
            expansion_repository=cast(
                PortfolioExpansionPersistenceRepository,
                FakePortfolioExpansionRepository(),
            ),
            state_repository=cast(
                PortfolioStateRepository,
                FakePortfolioRepository(),
            ),
        ),
    )

    result = await service.run(
        ServiceRequest(
            payload=PortfolioAnalysisRequest(),
        )
    )

    assert result.success is True
    assert isinstance(result.result, PortfolioAnalysisResult)
    assert result.result.portfolio_state


@pytest.mark.asyncio
async def test_sentiment_service_canonical_run() -> None:
    service = SentimentService(
        sentiment_provider=cast(
            SentimentProvider,
            FakeSentimentProvider(),
        ),
    )

    result = await service.run(
        ServiceRequest(
            payload=SentimentSnapshotRequest(),
        )
    )

    assert result.success is True
    assert isinstance(result.result, SentimentSnapshotResult)
    assert result.result.symbol == "SPY"


@pytest.mark.asyncio
async def test_technical_service_canonical_run() -> None:
    service = TechnicalAnalysisService(
        data_provider=FakeMarketDataProvider(),
    )

    result = await service.run(
        ServiceRequest(
            payload=TechnicalAnalysisRequest(
                days=100,
            ),
        )
    )

    assert result.success is True
    assert isinstance(result.result, TechnicalAnalysisResult)
    assert result.result.symbol == "SPY"
