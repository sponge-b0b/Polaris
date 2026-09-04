from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import pytest

from application.rag.contracts.rag_context import RagRetrievedContext, RagSource
from application.rag.contracts.rag_request import RagRequest
from application.rag.graphs import RagContextQuality, RagCorrectiveAction
from application.rag.quality.rag_quality_service import (
    RagQualityModelOutputError,
    RagQualityService,
)
from core.storage.persistence.rag import JsonObject
from integration.providers.rag.quality_evaluation_provider import (
    RagQualityModelOperation,
    RagQualityModelRequest,
    RagQualityModelResult,
)


@pytest.mark.asyncio
async def test_crag_evaluation_parses_typed_quality_and_retained_contexts() -> None:
    provider = FakeQualityProvider(
        payloads=(
            {
                "quality": "ambiguous",
                "action": "discard_weak_context",
                "retained_context_ids": ["context-1"],
            },
        )
    )
    service = RagQualityService(provider)

    result = await service.evaluate(
        request=_request(),
        contexts=(_context(),),
        loop_count=0,
    )

    assert result.quality is RagContextQuality.AMBIGUOUS
    assert result.action is RagCorrectiveAction.DISCARD_WEAK_CONTEXT
    assert result.retained_context_ids == ("context-1",)
    assert provider.requests[0].operation is RagQualityModelOperation.CRAG_GRADE
    assert "Do not answer the user query" in provider.requests[0].system_prompt
    assert "Do not include any other keys" in provider.requests[0].system_prompt


@pytest.mark.asyncio
async def test_crag_evaluation_maps_model_aliases_to_canonical_context_ids() -> None:
    provider = FakeQualityProvider(
        payloads=(
            {
                "quality": "correct",
                "action": "proceed",
                "retained_context_ids": ["context-1"],
            },
        )
    )
    service = RagQualityService(provider)

    result = await service.evaluate(
        request=_request(),
        contexts=(_context(context_id="opaque-runtime-context-id"),),
        loop_count=0,
    )

    user_payload = json.loads(provider.requests[0].user_prompt)
    assert user_payload["allowed_context_ids"] == ["context-1"]
    assert user_payload["contexts"][0]["context_id"] == "context-1"
    assert result.retained_context_ids == ("opaque-runtime-context-id",)


@pytest.mark.asyncio
async def test_missing_context_requests_bounded_rewrite_without_model_call() -> None:
    provider = FakeQualityProvider(payloads=())
    service = RagQualityService(provider)

    result = await service.evaluate(
        request=_request(),
        contexts=(),
        loop_count=0,
    )

    assert result.quality is RagContextQuality.MISSING
    assert result.action is RagCorrectiveAction.REWRITE
    assert provider.requests == ()


@pytest.mark.asyncio
async def test_quality_service_rejects_unknown_retained_context() -> None:
    service = RagQualityService(
        FakeQualityProvider(
            payloads=(
                {
                    "quality": "correct",
                    "action": "proceed",
                    "retained_context_ids": ["unknown"],
                },
            )
        )
    )

    with pytest.raises(RagQualityModelOutputError, match="unknown context"):
        await service.evaluate(
            request=_request(),
            contexts=(_context(),),
            loop_count=0,
        )


@pytest.mark.asyncio
async def test_quality_service_rewrites_query_and_reflects_answer() -> None:
    provider = FakeQualityProvider(
        payloads=(
            {"rewritten_query": "SPY breadth participation trend"},
            {
                "retrieval_necessity": 0.9,
                "source_relevance": 0.8,
                "answer_support": 0.7,
                "usefulness": 0.6,
                "answer_supported": True,
                "injection_detected": False,
            },
        )
    )
    service = RagQualityService(provider)

    rewritten = await service.rewrite(
        request=_request(),
        query="SPY breadth",
        loop_count=1,
    )
    reflection = await service.reflect(
        request=_request(),
        contexts=(_context(),),
        answer_text="Participation improved [C1].",
    )

    assert rewritten == "SPY breadth participation trend"
    assert reflection.scores.answer_support == 0.7
    assert reflection.scores.usefulness == 0.6
    assert reflection.answer_supported is True
    assert reflection.injection_detected is False
    assert [request.operation for request in provider.requests] == [
        RagQualityModelOperation.CRAG_QUERY_REWRITE,
        RagQualityModelOperation.SELF_REFLECTION,
    ]


@dataclass(slots=True)
class FakeQualityProvider:
    payloads: tuple[dict[str, object], ...]
    requests: tuple[RagQualityModelRequest, ...] = ()

    async def generate_structured(
        self,
        request: RagQualityModelRequest,
    ) -> RagQualityModelResult:
        index = len(self.requests)
        self.requests = (*self.requests, request)
        return RagQualityModelResult(
            operation=request.operation,
            payload=cast(JsonObject, self.payloads[index]),
            model="quality-test-model",
            provider_name="fake",
            duration_ms=1.0,
            success=True,
        )


def _request() -> RagRequest:
    return RagRequest(
        query="Summarize SPY breadth.",
        request_id="rag_query:quality-service",
    )


def _context(context_id: str = "context-1") -> RagRetrievedContext:
    return RagRetrievedContext(
        context_id=context_id,
        text="SPY breadth improved.",
        source=RagSource(
            source_table="curated_rag_documents",
            source_id="source-1",
            source_type="market_context",
            document_id="document-1",
            title="Market context",
            generated_at=datetime(2026, 6, 24, tzinfo=UTC),
        ),
        score=0.9,
        rank=0,
        retrieval_route="hybrid",
    )
