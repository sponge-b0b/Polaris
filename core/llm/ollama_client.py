import json
from typing import Any, Dict, List, Optional

import requests

from config.settings import Settings


class OllamaClient:
    """
    Centralized Ollama client for Polaris.

    This class should be the ONLY place where direct
    Ollama API calls are made.

    All agents and workflows should use this client.
    """

    def __init__(
        self,
        settings: Settings,
        timeout: int = 60,
    ) -> None:

        self.base_url = settings.OLLAMA_HOST
        self.llm_model = settings.DEFAULT_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL
        self.timeout = timeout

    # ============================================================
    # CORE GENERATION
    # ============================================================

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        think: bool = False,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Basic text generation.
        """

        model = model or self.llm_model

        request_options: Dict[str, Any] = {
            "temperature": temperature,
            "num_ctx": 8192,
        }

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "think": think,
            "stream": stream,
            "options": request_options,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if options:
            request_options.update(options)

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return data.get("response", "").strip()

    # ============================================================
    # CHAT API
    # ============================================================

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        think: bool = False,
        stream: bool = False,
        response_format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Chat-based generation with optional system prompt
        and optional JSON response formatting.
        """

        model = model or self.llm_model

        final_messages: List[Dict[str, str]] = []

        # Add system prompt first if provided
        if system_prompt:
            final_messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        # Add conversation messages
        final_messages.extend(messages)

        request_options: Dict[str, Any] = {
            "temperature": temperature,
            "num_ctx": 8192,
        }

        payload: Dict[str, Any] = {
            "model": model,
            "messages": final_messages,
            "think": think,
            "stream": stream,
            "options": request_options,
        }

        # Optional structured JSON output
        if response_format == "json":
            payload["format"] = "json"

        # Merge additional options
        if options:
            request_options.update(options)

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        content = data.get("message", {}).get("content", "").strip()

        # Parse JSON if requested
        if response_format == "json":
            try:
                return json.loads(content)

            except json.JSONDecodeError:
                return {
                    "error": "Invalid JSON returned by model",
                    "raw_response": content,
                }

        return content

    # ============================================================
    # JSON GENERATION
    # ============================================================

    def generate_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Forces JSON output from the model.
        """

        model = model or self.llm_model

        request_options: Dict[str, Any] = {
            "temperature": temperature,
            "num_ctx": 8192,
        }

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "think": False,
            "stream": False,
            "format": "json",
            "options": request_options,
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        response_text = data.get("response", "{}")

        try:
            return json.loads(response_text)

        except json.JSONDecodeError:
            return {
                "error": "Invalid JSON returned by model",
                "raw_response": response_text,
            }

    # ============================================================
    # EMBEDDINGS
    # ============================================================

    def embeddings(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """
        Generate embeddings for vector storage.
        """

        model = model or self.embedding_model

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": text,
        }

        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json=payload,
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return data.get("embedding", [])

    # ============================================================
    # MODEL MANAGEMENT
    # ============================================================

    def list_models(self) -> List[str]:
        """
        Return installed Ollama models.
        """

        response = requests.get(
            f"{self.base_url}/api/tags",
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        return [model["name"] for model in data.get("models", [])]

    def health_check(self) -> bool:
        """
        Simple Ollama health check.
        """

        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )

            return response.status_code == 200

        except Exception:
            return False
