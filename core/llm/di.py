from dishka import Provider, Scope, provide

from config.settings import Settings
from core.llm.llm_gateway import LLMGateway
from core.llm.llm_service import LLMService


class CoreLLMsDIProvider(Provider):
    """Core LLM service providers."""

    scope = Scope.APP

    @provide
    def provide_llm_service(
        self,
        settings: Settings,
        llm_gateway: LLMGateway,
    ) -> LLMService:
        return LLMService(
            gateway=llm_gateway,
            model=settings.DEFAULT_MODEL,
        )
