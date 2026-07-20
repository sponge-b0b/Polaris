from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from integration.clients.llm import LiteLlmGatewayClient
from integration.providers.rag.litellm_quality_evaluation_provider import (
    LiteLlmRagQualityModelProvider,
)
from integration.providers.rag.quality_evaluation_provider import (
    RagQualityModelConfig,
    RagQualityModelOperation,
    RagQualityModelRequest,
)


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
            structured_max_tokens=384,
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
            "max_tokens": 384,
            "response_format": {"type": "json_object"},
        }
    ]


@pytest.mark.asyncio
async def test_litellm_quality_provider_defaults_to_approved_logical_aliases() -> None:
    completion_client = _FakeCompletionClient()
    model_config = RagQualityModelConfig(
        crag_grader_model="polaris-local-structured",
        crag_query_rewrite_model="polaris-local-structured",
        self_reflection_model="polaris-local-structured",
        structured_max_tokens=512,
    )
    provider = LiteLlmRagQualityModelProvider(
        LiteLlmGatewayClient(
            completion_client=completion_client,
            default_model="default-model",
        ),
        model_config,
    )

    results = [
        await provider.generate_structured(
            RagQualityModelRequest(
                request_id="rag-quality-default-aliases",
                operation=operation,
                system_prompt="Return JSON.",
                user_prompt="Evaluate.",
            )
        )
        for operation in (
            RagQualityModelOperation.CRAG_GRADE,
            RagQualityModelOperation.CRAG_QUERY_REWRITE,
            RagQualityModelOperation.SELF_REFLECTION,
        )
    ]

    assert [result.model for result in results] == [
        "polaris-local-structured",
        "polaris-local-structured",
        "polaris-local-structured",
    ]
    assert [call["model"] for call in completion_client.calls] == [
        "polaris-local-structured",
        "polaris-local-structured",
        "polaris-local-structured",
    ]
