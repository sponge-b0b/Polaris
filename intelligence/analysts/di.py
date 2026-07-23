from dishka import Provider, Scope, provide

from application.services.base import ServiceRunner
from application.services.macro.macro_service import MacroService
from application.services.technical.technical_analysis_service import (
    TechnicalAnalysisService,
)
from core.llm.llm_service import LLMService
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.analysts.fundamental.fundamental_agent import FundamentalAgent
from intelligence.analysts.technical.technical_agent import TechnicalAgent


class IntelligenceAnalystsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Fundamental Agent
    @provide
    def provide_fundamental_agent(
        self,
        llm_service: LLMService,
        macro_service: MacroService,
        service_runner: ServiceRunner,
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> FundamentalAgent:

        return FundamentalAgent(
            llm_service=llm_service,
            macro_service=macro_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
        )

    # Technical Agent
    @provide
    def provide_technical_agent(
        self,
        llm_service: LLMService,
        technical_service: TechnicalAnalysisService,
        service_runner: ServiceRunner,
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> TechnicalAgent:

        return TechnicalAgent(
            llm_service=llm_service,
            technical_service=technical_service,
            service_runner=service_runner,
            intelligence_telemetry=intelligence_telemetry,
        )
