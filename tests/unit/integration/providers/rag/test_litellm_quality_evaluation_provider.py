from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from integration.clients.llm import LiteLlmGatewayClient
from integration.providers.rag.litellm_quality_evaluation_provider import (
    LiteLlmRagQualityModelProvider,
)
from integration.providers.rag.quality_evaluation_provider import RagQualityModelConfig
from integration.providers.rag.quality_evaluation_provider import (
    RagQualityModelOperation,
)
from integration.providers.rag.quality_evaluation_provider import RagQualityModelRequest


class _FakeCompletionClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            model=kwargs["model"],
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=' {"ok": true} '))
            ],
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_model"),
    [
        (RagQualityModelOperation.CRAG_GRADE, "grader"),
        (RagQualityModelOperation.CRAG_QUERY_REWRITE, "rewriter"),
        (RagQualityModelOperation.SELF_REFLECTION, "reflector"),
    ],
)
async def test_litellm_quality_provider_uses_operation_specific_model(
    operation: RagQualityModelOperation,
    expected_model: str,
) -> None:
    completion_client = _FakeCompletionClient()
    provider = LiteLlmRagQualityModelProvider(
        LiteLlmGatewayClient(
            completion_client=completion_client,
            default_model="default-model",
        ),
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
    assert result.provider_name == "litellm"
    assert result.operation is operation
    assert result.payload == {"ok": True}
    assert completion_client.calls == [
        {
            "model": expected_model,
            "messages": [
                {"role": "system", "content": "Return JSON."},
                {"role": "user", "content": "Evaluate."},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
    ]
