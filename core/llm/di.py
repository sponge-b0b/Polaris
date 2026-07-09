from dishka import Provider, Scope, provide
from config.settings import Settings

from core.llm.ollama_client import OllamaClient
from core.llm.llm_service import LLMService


class CoreLLMsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    # Ollama Client
    @provide
    def provide_ollama_client(self, settings: Settings) -> OllamaClient:
        return OllamaClient(settings=settings)

    # LLM Client
    @provide
    def provide_llm_service(
        self,
        llm_client: OllamaClient,
    ) -> LLMService:
        return LLMService(llm_client=llm_client)
