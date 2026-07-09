from __future__ import annotations

from typing import Any
from typing import cast

import pytest

from core.llm.ollama_client import OllamaClient
from integration.providers.rag.ollama_quality_evaluation_provider import (
    OllamaRagQualityModelProvider,
)
from integration.providers.rag.quality_evaluation_provider import RagQualityModelConfig
from integration.providers.rag.quality_evaluation_provider import (
    RagQualityModelOperation,
)
from integration.providers.rag.quality_evaluation_provider import RagQualityModelRequest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_model"),
    [
        (RagQualityModelOperation.CRAG_GRADE, "grader"),
        (RagQualityModelOperation.CRAG_QUERY_REWRITE, "rewriter"),
        (RagQualityModelOperation.SELF_REFLECTION, "reflector"),
    ],
)
async def test_quality_provider_uses_operation_specific_model(
    operation: RagQualityModelOperation,
    expected_model: str,
) -> None:
    client = FakeOllamaClient()
    provider = OllamaRagQualityModelProvider(
        cast(OllamaClient, client),
        RagQualityModelConfig(
            crag_grader_model="grader",
            crag_query_rewrite_model="rewriter",
            self_reflection_model="reflector",
        ),
    )

    result = await provider.generate_structured(
        RagQualityModelRequest(
            request_id="rag-quality-1",
            operation=operation,
            system_prompt="Return JSON.",
            user_prompt="Evaluate.",
        )
    )

    assert result.model == expected_model
    assert result.operation is operation
    assert client.calls == [
        {
            "prompt": "Evaluate.",
            "model": expected_model,
            "system_prompt": "Return JSON.",
            "temperature": 0.0,
        }
    ]


class FakeOllamaClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"ok": True}
