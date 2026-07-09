from __future__ import annotations

from typing import TYPE_CHECKING

from application.services.base import ServiceRequest, ServiceResult
from application.services.base.application_service import (
    ApplicationService,
    ValidatingApplicationService,
)
from application.services.macro.economic_regime import classify_economic_regime
from application.services.macro.fed_analysis import analyze_fed_environment
from application.services.macro.inflation_analysis import analyze_inflation_environment
from application.services.macro.liquidity_analysis import analyze_liquidity_environment
from application.services.macro.macro_request import MacroAnalysisRequest
from application.services.macro.macro_result import MacroAnalysisResult
from application.services.macro.yield_curve import analyze_yield_curve

if TYPE_CHECKING:
    from integration.providers.macro.macro_provider import MacroProvider


class MacroService(ApplicationService, ValidatingApplicationService):
    """Orchestrate deterministic macroeconomic analysis."""

    service_name = "macro_service"

    def __init__(
        self,
        macro_provider: MacroProvider,
    ) -> None:
        self.macro_provider = macro_provider

    async def run(
        self,
        request: ServiceRequest[MacroAnalysisRequest],
    ) -> ServiceResult[MacroAnalysisResult]:
        result = await self._execute(request.payload)

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=result,
        )

    async def validate_request(
        self,
        request: ServiceRequest[MacroAnalysisRequest],
    ) -> tuple[str, ...]:
        if isinstance(request.payload, MacroAnalysisRequest):
            return ()

        return (f"Unsupported service request: {request.request_name}",)

    async def _execute(
        self,
        request: MacroAnalysisRequest,
    ) -> MacroAnalysisResult:
        macro_data = await self.macro_provider.get_macro_snapshot()

        inflation_analysis = analyze_inflation_environment(macro_data)
        fed_analysis = analyze_fed_environment(macro_data)
        liquidity_analysis = analyze_liquidity_environment(macro_data)
        yield_curve_analysis = analyze_yield_curve(macro_data)

        economic_regime = classify_economic_regime(
            inflation_analysis=inflation_analysis,
            fed_analysis=fed_analysis,
            liquidity_analysis=liquidity_analysis,
            yield_curve_analysis=yield_curve_analysis,
        )

        return MacroAnalysisResult(
            macro_data=macro_data if request.include_raw_data else None,
            inflation_analysis=inflation_analysis,
            fed_analysis=fed_analysis,
            liquidity_analysis=liquidity_analysis,
            yield_curve_analysis=yield_curve_analysis,
            economic_regime=economic_regime,
            inflation_regime=str(inflation_analysis.get("inflation_regime", "unknown")),
            fed_stance=str(fed_analysis.get("fed_stance", "neutral")),
            liquidity_regime=str(liquidity_analysis.get("liquidity_regime", "unknown")),
            yield_curve_regime=str(yield_curve_analysis.get("curve_regime", "unknown")),
        )
