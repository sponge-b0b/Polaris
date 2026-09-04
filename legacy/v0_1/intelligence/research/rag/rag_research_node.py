from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from application.rag.contracts.rag_context import RagRetrievalFilters
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.storage.persistence.rag import JsonObject


class RagServicePort(Protocol):
    async def run(
        self,
        request: RagRequest,
    ) -> RagResult: ...


@dataclass(
    frozen=True,
    slots=True,
)
class RagResearchNodeConfig:
    """
    Runtime-boundary keys for the optional platform RAG research node.
    """

    request_key: str = "rag_request"
    query_key: str = "rag_query"
    filters_key: str = "rag_filters"
    route_key: str = "rag_route"
    top_k_key: str = "rag_top_k"
    output_key: str = "rag_result"
    requester: str = "rag_research_node"
    default_route: str = "hybrid"
    default_top_k: int = 8

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "request_key",
            "query_key",
            "filters_key",
            "route_key",
            "top_k_key",
            "output_key",
            "requester",
            "default_route",
        ):
            value = getattr(
                self,
                field_name,
            )
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value.strip()
            ):
                raise ValueError(f"{field_name} cannot be empty.")
        if self.default_top_k <= 0:
            raise ValueError("default_top_k must be positive.")


class RagResearchNode(RuntimeNode):
    """
    Optional runtime research node for platform-native RAG queries.

    The node converts serialized runtime input from ``RuntimeContext.workflow_inputs``
    into typed RAG request objects, calls ``RAGService``, and serializes the
    typed ``RagResult`` only when returning through ``RuntimeNodeOutput``.
    """

    node_name = "rag_research_node"
    node_type = "rag_research"

    def __init__(
        self,
        rag_service: RagServicePort,
        config: RagResearchNodeConfig | None = None,
    ) -> None:
        self._rag_service = rag_service
        self._config = config or RagResearchNodeConfig()

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        request = _request_from_context(
            context=context,
            config=self._config,
        )
        result = await self._rag_service.run(
            request,
        )

        return RuntimeNodeOutput.success_output(
            outputs={
                self._config.output_key: result.to_dict(),
            },
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "query_id": result.query_id,
                "rag_status": result.status,
                "route": result.route,
            },
        )


def _request_from_context(
    *,
    context: RuntimeContext,
    config: RagResearchNodeConfig,
) -> RagRequest:
    workflow_inputs = context.workflow_inputs
    request_payload = workflow_inputs.get(
        config.request_key,
    )
    if request_payload is not None:
        if not isinstance(
            request_payload,
            Mapping,
        ):
            raise TypeError(f"{config.request_key} must be an object.")
        return RagRequest.from_dict(
            request_payload,
        )

    query = _required_string(
        workflow_inputs=workflow_inputs,
        key=config.query_key,
    )
    filters = _filters_from_workflow_inputs(
        workflow_inputs=workflow_inputs,
        key=config.filters_key,
    )
    route = _optional_string(
        workflow_inputs=workflow_inputs,
        key=config.route_key,
        default=config.default_route,
    )
    top_k = _optional_positive_int(
        workflow_inputs=workflow_inputs,
        key=config.top_k_key,
        default=config.default_top_k,
    )

    metadata = _json_object(
        {
            "runtime_id": context.runtime_id,
            "workflow_id": context.workflow_id,
            "mode": context.mode,
            "node_name": RagResearchNode.node_name,
            "node_type": RagResearchNode.node_type,
        }
    )

    return RagRequest(
        query=query,
        filters=filters,
        route=route,
        top_k=top_k,
        requester=config.requester,
        workflow_name=context.workflow_id,
        execution_id=context.execution_id,
        metadata=metadata,
    )


def _filters_from_workflow_inputs(
    *,
    workflow_inputs: Mapping[str, Any],
    key: str,
) -> RagRetrievalFilters:
    value = workflow_inputs.get(
        key,
    )
    if value is None:
        return RagRetrievalFilters()
    if isinstance(
        value,
        RagRetrievalFilters,
    ):
        return value
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError(f"{key} must be a RagRetrievalFilters object or mapping.")
    return RagRetrievalFilters.from_dict(
        value,
    )


def _required_string(
    *,
    workflow_inputs: Mapping[str, Any],
    key: str,
) -> str:
    value = workflow_inputs.get(
        key,
    )
    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ValueError(f"{key} is required and must be a non-empty string.")
    return value


def _optional_string(
    *,
    workflow_inputs: Mapping[str, Any],
    key: str,
    default: str,
) -> str:
    value = workflow_inputs.get(
        key,
        default,
    )
    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ValueError(f"{key} must be a non-empty string.")
    return value


def _optional_positive_int(
    *,
    workflow_inputs: Mapping[str, Any],
    key: str,
    default: int,
) -> int:
    value = workflow_inputs.get(
        key,
        default,
    )
    if isinstance(
        value,
        bool,
    ):
        raise TypeError(f"{key} must be a positive integer.")
    top_k = int(
        value,
    )
    if top_k <= 0:
        raise ValueError(f"{key} must be positive.")
    return top_k


def _json_object(
    value: object,
) -> JsonObject:
    return cast(
        JsonObject,
        value,
    )
