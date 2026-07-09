from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from integration.providers.market_data.market_data_provider import (
        MarketDataProvider,
    )

from application.services.base import ServiceRequest
from application.services.base import ServiceResult
from application.services.base.application_service import (
    ApplicationService,
    ValidatingApplicationService,
)

from application.services.technical import breadth_analysis
from application.services.technical import technical_calibration
from application.services.technical import technical_indicators
from application.services.technical import technical_regime
from application.services.technical import trend_analysis
from application.services.technical import volatility_analysis
from application.services.technical.technical_request import (
    TechnicalAnalysisRequest,
)
from application.services.technical.technical_result import (
    TechnicalAnalysisResult,
)


class TechnicalAnalysisService(ApplicationService, ValidatingApplicationService):
    """
    Polaris Technical Service.

    Responsibilities:
    - retrieve technical market data
    - compute indicator facts
    - perform trend analysis
    - perform volatility analysis
    - perform breadth analysis
    - synthesize technical regime
    - calibrate final technical signal
    """

    service_name = "technical_analysis_service"

    def __init__(
        self,
        data_provider: MarketDataProvider,
    ) -> None:
        self.data_provider = data_provider

    async def run(
        self,
        request: ServiceRequest[TechnicalAnalysisRequest],
    ) -> ServiceResult[TechnicalAnalysisResult]:
        result = await self._execute(
            request.payload,
        )

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=result,
        )

    async def validate_request(
        self,
        request: ServiceRequest[TechnicalAnalysisRequest],
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not isinstance(request.payload, TechnicalAnalysisRequest):
            return (f"Unsupported service request: {request.request_name}",)

        if not request.payload.symbol.strip():
            errors.append(
                "symbol is required.",
            )

        if request.payload.days < 1:
            errors.append(
                "days must be at least 1.",
            )

        return tuple(errors)

    async def _execute(
        self,
        request: TechnicalAnalysisRequest,
    ) -> TechnicalAnalysisResult:
        """
        Full deterministic technical intelligence pipeline.
        """

        symbol = request.symbol
        days = request.days

        symbol_df = await self.data_provider.get_symbol_data(
            symbol=symbol,
            days=days,
        )

        vix_df = await self.data_provider.get_vix_data(
            days=days,
        )

        vvix_df = await self.data_provider.get_vvix_data(
            days=days,
        )

        sp500_data = await self.data_provider.get_sp500_data(
            days=days,
        )

        technical_result = technical_indicators.compute(
            symbol_df=symbol_df,
            vix_df=vix_df,
            vvix_df=vvix_df,
            sp500_df=sp500_data.analytics,
        )

        snapshot = technical_result.get(
            "snapshot",
            {},
        )

        market_context = technical_result.get(
            "market_context",
            {},
        )

        # Enrich market context with additional SP500Data.
        market_context["top_50_constituents"] = sp500_data.top_50_constituents
        market_context["market_caps"] = sp500_data.market_caps

        micro_regime = technical_result.get(
            "micro_regime",
            {},
        )

        trend = trend_analysis.analyze(
            technical_result,
        )

        volatility = volatility_analysis.analyze(
            technical_result,
        )

        breadth = breadth_analysis.analyze(
            technical_result,
        )

        regime = technical_regime.build(
            {
                "trend": trend,
                "volatility": volatility,
                "breadth": breadth,
            }
        )

        calibrated = technical_calibration.calibrate(
            regime_output=regime,
            trend=trend,
            volatility=volatility,
            breadth=breadth,
        )

        technical_score = float(
            calibrated.get(
                "directional_technical_score",
                0.0,
            )
        )

        return TechnicalAnalysisResult(
            symbol=symbol,
            technical_score=technical_score,
            snapshot=snapshot,
            market_context=market_context,
            micro_regime=micro_regime,
            trend=trend,
            volatility=volatility,
            breadth=breadth,
            raw_regime=regime,
            regime=calibrated,
        )
