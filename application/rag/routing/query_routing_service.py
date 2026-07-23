from __future__ import annotations

import json
from collections.abc import Mapping
from time import perf_counter

from application.observability import (
    DEFAULT_SOURCE_CONTROLLED_PROMPT_SOURCE,
    DEFAULT_STATIC_PROMPT_VERSION,
    static_prompt_hash,
)
from application.rag.routing.query_routing_models import (
    RagAdaptiveTriage,
    RagHydeExpansion,
    RagQueryComplexity,
    RagQueryContext,
    RagQueryModelExecution,
    RagQueryRoutingDecision,
    RagRetrievalRoute,
    RagRouteSelection,
    RagStandaloneQueryRewrite,
)
from core.storage.persistence.rag import JsonObject
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.query_routing_provider import (
    RagQueryModelOperation,
    RagQueryModelProvider,
    RagQueryModelRequest,
    RagQueryModelResult,
)


class RagRoutingModelOutputError(ValueError):
    """Raised when model output does not satisfy the routing contract."""


class RagQueryRoutingService:
    """Rewrites conversational queries and selects a typed retrieval route."""

    def __init__(
        self,
        model_provider: RagQueryModelProvider,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._model_provider = model_provider
        self._telemetry = telemetry

    async def route(self, context: RagQueryContext) -> RagQueryRoutingDecision:
        started_at = perf_counter()
        model_executions: list[RagQueryModelExecution] = []
        await self._emit_started(context)
        try:
            rewrite, rewrite_execution = await self.rewrite(context)
            if rewrite_execution is not None:
                model_executions.append(rewrite_execution)
            triage, triage_execution = await self.triage(
                context=context,
                query=rewrite.standalone_query,
            )
            model_executions.append(triage_execution)
            route_selection, route_execution = await self.select_route(
                context=context,
                query=rewrite.standalone_query,
                triage=triage,
            )
            model_executions.append(route_execution)
            hyde = None
            if route_selection.route is RagRetrievalRoute.DEEP_RESEARCH:
                hyde, hyde_execution = await self.generate_hyde(
                    context=context,
                    query=rewrite.standalone_query,
                )
                model_executions.append(hyde_execution)
            decision = RagQueryRoutingDecision(
                context=context,
                rewrite=rewrite,
                triage=triage,
                route_selection=route_selection,
                model_executions=tuple(model_executions),
                hyde=hyde,
            )
        except Exception as exc:
            await self._emit_failed(
                context,
                exc,
                perf_counter() - started_at,
                tuple(model_executions),
            )
            raise
        await self._emit_completed(context, decision, perf_counter() - started_at)
        return decision

    async def rewrite(
        self,
        context: RagQueryContext,
    ) -> tuple[RagStandaloneQueryRewrite, RagQueryModelExecution | None]:
        operation = RagQueryModelOperation.REWRITE
        started_at = perf_counter()
        await self._emit_stage_started(context, operation)
        if context.memory.is_empty:
            rewrite = RagStandaloneQueryRewrite(
                original_query=context.query,
                standalone_query=context.query,
                rewritten=False,
            )
            await self._emit_stage_completed(
                context,
                operation,
                duration_seconds=perf_counter() - started_at,
                attributes={"model_invoked": False, "rewritten": False},
            )
            return rewrite, None
        try:
            result = await self._model_provider.generate_structured(
                RagQueryModelRequest(
                    request_id=context.request_id,
                    operation=operation,
                    system_prompt=_REWRITE_SYSTEM_PROMPT,
                    user_prompt=_rewrite_prompt(context),
                )
            )
            _require_operation(result.operation, operation)
            payload = _require_payload(result.payload, {"standalone_query"})
            standalone_query = _require_text(payload, "standalone_query")
            rewrite = RagStandaloneQueryRewrite(
                original_query=context.query,
                standalone_query=standalone_query,
                rewritten=standalone_query != context.query,
            )
        except Exception as exc:
            await self._emit_stage_failed(
                context, operation, exc, perf_counter() - started_at
            )
            raise
        await self._emit_stage_completed(
            context,
            operation,
            duration_seconds=perf_counter() - started_at,
            result=result,
            attributes={"model_invoked": True, "rewritten": rewrite.rewritten},
        )
        return rewrite, _model_execution(result)

    async def triage(
        self,
        *,
        context: RagQueryContext,
        query: str,
    ) -> tuple[RagAdaptiveTriage, RagQueryModelExecution]:
        operation = RagQueryModelOperation.ADAPTIVE_TRIAGE
        started_at = perf_counter()
        await self._emit_stage_started(context, operation)
        try:
            result = await self._model_provider.generate_structured(
                RagQueryModelRequest(
                    request_id=context.request_id,
                    operation=operation,
                    system_prompt=_ADAPTIVE_TRIAGE_SYSTEM_PROMPT,
                    user_prompt=f"Query: {query}",
                )
            )
            _require_operation(result.operation, operation)
            payload = _require_payload(result.payload, {"complexity"})
            triage = RagAdaptiveTriage(
                complexity=_require_enum(payload, "complexity", RagQueryComplexity),
            )
        except Exception as exc:
            await self._emit_stage_failed(
                context, operation, exc, perf_counter() - started_at
            )
            raise
        await self._emit_stage_completed(
            context,
            operation,
            duration_seconds=perf_counter() - started_at,
            result=result,
            attributes={"complexity": triage.complexity.value},
        )
        return triage, _model_execution(result)

    async def select_route(
        self,
        *,
        context: RagQueryContext,
        query: str,
        triage: RagAdaptiveTriage,
    ) -> tuple[RagRouteSelection, RagQueryModelExecution]:
        operation = RagQueryModelOperation.ROUTE_SELECTION
        started_at = perf_counter()
        await self._emit_stage_started(context, operation)
        try:
            result = await self._model_provider.generate_structured(
                RagQueryModelRequest(
                    request_id=context.request_id,
                    operation=operation,
                    system_prompt=_ROUTE_SELECTION_SYSTEM_PROMPT,
                    user_prompt=(
                        f"Query: {query}\n"
                        f"Adaptive triage complexity: {triage.complexity.value}"
                    ),
                )
            )
            _require_operation(result.operation, operation)
            payload = _require_payload(result.payload, {"route"})
            selection = RagRouteSelection(
                route=_require_enum(payload, "route", RagRetrievalRoute),
            )
        except Exception as exc:
            await self._emit_stage_failed(
                context, operation, exc, perf_counter() - started_at
            )
            raise
        await self._emit_stage_completed(
            context,
            operation,
            duration_seconds=perf_counter() - started_at,
            result=result,
            attributes={"route": selection.route.value},
        )
        return selection, _model_execution(result)

    async def generate_hyde(
        self,
        *,
        context: RagQueryContext,
        query: str,
    ) -> tuple[RagHydeExpansion, RagQueryModelExecution]:
        operation = RagQueryModelOperation.HYDE
        started_at = perf_counter()
        await self._emit_stage_started(context, operation)
        try:
            result = await self._model_provider.generate_structured(
                RagQueryModelRequest(
                    request_id=context.request_id,
                    operation=operation,
                    system_prompt=_HYDE_SYSTEM_PROMPT,
                    user_prompt=f"Research query: {query}",
                )
            )
            _require_operation(result.operation, operation)
            payload = _require_payload(result.payload, {"hypothetical_document"})
            expansion = RagHydeExpansion(
                query=query,
                hypothetical_document=_require_text(payload, "hypothetical_document"),
            )
        except Exception as exc:
            await self._emit_stage_failed(
                context, operation, exc, perf_counter() - started_at
            )
            raise
        await self._emit_stage_completed(
            context,
            operation,
            duration_seconds=perf_counter() - started_at,
            result=result,
        )
        return expansion, _model_execution(result)

    async def _emit_stage_started(
        self,
        context: RagQueryContext,
        operation: RagQueryModelOperation,
    ) -> None:
        if self._telemetry is not None:
            await self._telemetry.emit_operation_started(
                component_name=self.__class__.__name__,
                operation=_stage_operation(operation),
                correlation_id=context.request_id,
                attributes={"model_operation": operation.value},
            )

    async def _emit_stage_completed(
        self,
        context: RagQueryContext,
        operation: RagQueryModelOperation,
        *,
        duration_seconds: float,
        result: RagQueryModelResult | None = None,
        attributes: dict[str, object] | None = None,
    ) -> None:
        if self._telemetry is not None:
            await self._telemetry.emit_operation_completed(
                component_name=self.__class__.__name__,
                operation=_stage_operation(operation),
                duration_seconds=duration_seconds,
                correlation_id=context.request_id,
                attributes={
                    "model_operation": operation.value,
                    **(
                        {
                            "configured_model": result.model,
                            "provider_name": result.provider_name,
                            "provider_success": result.success,
                        }
                        if result is not None
                        else {}
                    ),
                    **dict(attributes or {}),
                },
            )

    async def _emit_stage_failed(
        self,
        context: RagQueryContext,
        operation: RagQueryModelOperation,
        error: Exception,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is not None:
            await self._telemetry.emit_operation_failed(
                component_name=self.__class__.__name__,
                operation=_stage_operation(operation),
                error=error,
                duration_seconds=duration_seconds,
                correlation_id=context.request_id,
                attributes={"model_operation": operation.value},
            )

    async def _emit_started(self, context: RagQueryContext) -> None:
        if self._telemetry is not None:
            await self._telemetry.emit_operation_started(
                component_name=self.__class__.__name__,
                operation="rag.query_routing.route",
                correlation_id=context.request_id,
                attributes={"has_memory": not context.memory.is_empty},
            )

    async def _emit_completed(
        self,
        context: RagQueryContext,
        decision: RagQueryRoutingDecision,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is not None:
            await self._telemetry.emit_operation_completed(
                component_name=self.__class__.__name__,
                operation="rag.query_routing.route",
                duration_seconds=duration_seconds,
                correlation_id=context.request_id,
                attributes={
                    "complexity": decision.triage.complexity.value,
                    "route": decision.route_selection.route.value,
                    "rewritten": decision.rewrite.rewritten,
                    "hyde_generated": decision.hyde is not None,
                    "model_operation_count": len(decision.model_executions),
                },
                payload=dict(decision.persistence_metadata()),
            )

    async def _emit_failed(
        self,
        context: RagQueryContext,
        error: Exception,
        duration_seconds: float,
        model_executions: tuple[RagQueryModelExecution, ...],
    ) -> None:
        if self._telemetry is not None:
            await self._telemetry.emit_operation_failed(
                component_name=self.__class__.__name__,
                operation="rag.query_routing.route",
                error=error,
                duration_seconds=duration_seconds,
                correlation_id=context.request_id,
                attributes={"model_operation_count": len(model_executions)},
                payload={
                    "model_executions": [
                        execution.to_dict() for execution in model_executions
                    ]
                },
            )


def _stage_operation(operation: RagQueryModelOperation) -> str:
    return f"rag.query_routing.{operation.value}"


def _model_execution(result: RagQueryModelResult) -> RagQueryModelExecution:
    prompt_name, prompt_hash = _prompt_metadata_for_operation(result.operation)
    return RagQueryModelExecution(
        operation=result.operation.value,
        configured_model=result.model,
        provider_name=result.provider_name,
        duration_ms=result.duration_ms,
        success=result.success,
        prompt_name=prompt_name,
        prompt_version=DEFAULT_STATIC_PROMPT_VERSION,
        prompt_hash=prompt_hash,
        prompt_source=DEFAULT_SOURCE_CONTROLLED_PROMPT_SOURCE,
    )


def _prompt_metadata_for_operation(
    operation: RagQueryModelOperation,
) -> tuple[str, str]:
    try:
        return _RAG_ROUTING_PROMPT_REFERENCES[operation]
    except KeyError as exc:
        raise RagRoutingModelOutputError(
            f"Unsupported prompt metadata operation: {operation.value}."
        ) from exc


def _rewrite_prompt(context: RagQueryContext) -> str:
    conversation = [
        {"role": turn.role.value, "content": turn.content}
        for turn in context.memory.turns
    ]
    return (
        "Conversation history JSON:\n"
        f"{json.dumps(conversation, separators=(',', ':'))}\n"
        f"Follow-up query: {context.query}"
    )


def _require_operation(
    actual: RagQueryModelOperation,
    expected: RagQueryModelOperation,
) -> None:
    if actual is not expected:
        raise RagRoutingModelOutputError(
            f"Expected {expected.value} model output, got {actual.value}."
        )


def _require_payload(
    payload: JsonObject,
    expected_keys: set[str],
) -> Mapping[str, object]:
    allowed_extra_keys = {"reasoning"}
    actual_keys = set(payload)
    missing_keys = expected_keys - actual_keys
    unexpected_keys = actual_keys - expected_keys - allowed_extra_keys
    if missing_keys or unexpected_keys:
        raise RagRoutingModelOutputError(
            f"Expected model output keys {sorted(expected_keys)}, got {sorted(actual_keys)}."  # noqa: E501
        )
    return {key: payload[key] for key in expected_keys}


def _require_text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RagRoutingModelOutputError(f"{key} must be a non-empty string.")
    return value.strip()


def _require_enum(payload: Mapping[str, object], key: str, enum_type: type):
    value = _require_text(payload, key)
    try:
        return enum_type(value)
    except ValueError as exc:
        raise RagRoutingModelOutputError(f"Unsupported {key}: {value}.") from exc


_REWRITE_SYSTEM_PROMPT = """Rewrite the follow-up into a standalone query.
Return JSON with exactly one key: standalone_query. Preserve the user's intent and facts."""  # noqa: E501

_ADAPTIVE_TRIAGE_SYSTEM_PROMPT = """Classify the query's research complexity.
Return JSON with exactly one key: complexity.
complexity must be low, moderate, or high."""

_ROUTE_SELECTION_SYSTEM_PROMPT = """Select the retrieval route for the query.
Return JSON with exactly one key: route.
route must be direct_answer, retrieval, or deep_research.
Use direct_answer only when external evidence is unnecessary, retrieval for evidence lookup,
and deep_research for multi-source analysis."""  # noqa: E501

_HYDE_SYSTEM_PROMPT = """Create a concise hypothetical evidence document for retrieval only.
Do not present it as verified fact. Return JSON with exactly one key: hypothetical_document."""  # noqa: E501

_REWRITE_PROMPT_NAME = "rag_query_rewrite_system_prompt"
_ADAPTIVE_TRIAGE_PROMPT_NAME = "rag_adaptive_triage_system_prompt"
_ROUTE_SELECTION_PROMPT_NAME = "rag_route_selection_system_prompt"
_HYDE_PROMPT_NAME = "rag_hyde_system_prompt"

_RAG_ROUTING_PROMPT_REFERENCES: dict[RagQueryModelOperation, tuple[str, str]] = {
    RagQueryModelOperation.REWRITE: (
        _REWRITE_PROMPT_NAME,
        static_prompt_hash(_REWRITE_SYSTEM_PROMPT),
    ),
    RagQueryModelOperation.ADAPTIVE_TRIAGE: (
        _ADAPTIVE_TRIAGE_PROMPT_NAME,
        static_prompt_hash(_ADAPTIVE_TRIAGE_SYSTEM_PROMPT),
    ),
    RagQueryModelOperation.ROUTE_SELECTION: (
        _ROUTE_SELECTION_PROMPT_NAME,
        static_prompt_hash(_ROUTE_SELECTION_SYSTEM_PROMPT),
    ),
    RagQueryModelOperation.HYDE: (
        _HYDE_PROMPT_NAME,
        static_prompt_hash(_HYDE_SYSTEM_PROMPT),
    ),
}
