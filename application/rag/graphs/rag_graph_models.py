from __future__ import annotations

from typing import Protocol

from application.rag.routing.query_routing_models import RagConversationMemory
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_quality_models import RagContextEvaluation
from application.rag.contracts.rag_quality_models import RagContextQuality
from application.rag.contracts.rag_quality_models import RagCorrectiveAction
from application.rag.contracts.rag_quality_models import RagSelfReflection
from application.rag.contracts.rag_request import RagRequest


class RagConversationMemoryProvider(Protocol):
    async def load(self, request: RagRequest) -> RagConversationMemory: ...


class RagContextEvaluator(Protocol):
    async def evaluate(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
        loop_count: int,
    ) -> RagContextEvaluation: ...


class RagCorrectiveQueryRewriter(Protocol):
    async def rewrite(
        self,
        *,
        request: RagRequest,
        query: str,
        loop_count: int,
    ) -> str: ...


class RagAnswerReflector(Protocol):
    async def reflect(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
        answer_text: str,
    ) -> RagSelfReflection: ...


class RagWebFallbackRetriever(Protocol):
    async def retrieve(
        self,
        request: RagRequest,
    ) -> tuple[RagRetrievedContext, ...]: ...


class EmptyRagConversationMemoryProvider:
    async def load(self, request: RagRequest) -> RagConversationMemory:
        del request
        return RagConversationMemory()


class PresenceRagContextEvaluator:
    """Deterministic fail-closed fallback when model-backed CRAG is not composed."""

    async def evaluate(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
        loop_count: int,
    ) -> RagContextEvaluation:
        del request, loop_count
        if contexts:
            return RagContextEvaluation(
                quality=RagContextQuality.CORRECT,
                action=RagCorrectiveAction.PROCEED,
                retained_context_ids=tuple(context.context_id for context in contexts),
            )
        return RagContextEvaluation(
            quality=RagContextQuality.MISSING,
            action=RagCorrectiveAction.FAIL_CLOSED,
        )
