from typing import Any, Dict, Optional

from core.llm.ollama_client import OllamaClient


class LLMService:
    """
    Centralized LLM service.

    This class should be the ONLY place where direct
    LLM calls are made.

    All runtime nodes and workflows should use this service.
    """

    def __init__(
        self,
        llm_client: OllamaClient,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> None:

        self.model = model
        self.temperature = temperature
        self.llm_client = llm_client

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate standard text response.
        """

        return self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.model,
            temperature=self.temperature,
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        """

        return self.llm_client.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.model,
            temperature=self.temperature,
        )

    def chat(
        self,
        messages: list,
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None,
    ) -> Any:
        """
        Chat helper wrapper.
        """

        return self.llm_client.chat(
            messages=messages,
            system_prompt=system_prompt,
            model=self.model,
            temperature=self.temperature,
            response_format=response_format,
        )
