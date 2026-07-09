from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Mapping
from uuid import uuid4

from application.rag.contracts.rag_context import RagRetrievalFilters
from core.storage.persistence.rag import JsonObject


@dataclass(
    frozen=True,
    slots=True,
)
class RagRequest:
    """
    Canonical platform-facing request for RAG retrieval and generation.
    """

    query: str
    filters: RagRetrievalFilters = field(default_factory=RagRetrievalFilters)
    route: str = "hybrid"
    top_k: int = 8
    allow_web: bool = False
    requester: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: f"rag_query:{uuid4().hex}")

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.query,
            "query",
        )
        _require_non_empty(
            self.route,
            "route",
        )
        if self.top_k <= 0:
            raise ValueError("top_k must be positive.")
        _validate_optional_non_empty(
            self.requester,
            "requester",
        )
        _validate_optional_non_empty(
            self.workflow_name,
            "workflow_name",
        )
        _validate_optional_non_empty(
            self.execution_id,
            "execution_id",
        )
        _require_non_empty(
            self.request_id,
            "request_id",
        )

    @property
    def normalized_query(
        self,
    ) -> str:
        return " ".join(
            self.query.split(),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "query": self.query,
            "normalized_query": self.normalized_query,
            "filters": self.filters.to_dict(),
            "route": self.route,
            "top_k": self.top_k,
            "allow_web": self.allow_web,
            "requester": self.requester,
            "workflow_name": self.workflow_name,
            "execution_id": self.execution_id,
            "metadata": deepcopy(
                dict(self.metadata),
            ),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RagRequest:
        filters_payload = payload.get(
            "filters",
            {},
        )
        if not isinstance(
            filters_payload,
            Mapping,
        ):
            raise TypeError("filters must be an object.")
        metadata_payload = payload.get(
            "metadata",
            {},
        )
        if not isinstance(
            metadata_payload,
            Mapping,
        ):
            raise TypeError("metadata must be an object.")

        return cls(
            query=_required_str(
                payload,
                "query",
            ),
            filters=RagRetrievalFilters.from_dict(
                filters_payload,
            ),
            route=str(
                payload.get(
                    "route",
                    "hybrid",
                )
            ),
            top_k=int(
                payload.get(
                    "top_k",
                    8,
                )
            ),
            allow_web=_bool_from_payload(
                payload,
                "allow_web",
                default=False,
            ),
            requester=_optional_str(
                payload.get(
                    "requester",
                )
            ),
            workflow_name=_optional_str(
                payload.get(
                    "workflow_name",
                )
            ),
            execution_id=_optional_str(
                payload.get(
                    "execution_id",
                )
            ),
            metadata=dict(
                metadata_payload,
            ),
            request_id=str(
                payload.get(
                    "request_id",
                    f"rag_query:{uuid4().hex}",
                )
            ),
        )


def _bool_from_payload(
    payload: Mapping[str, Any],
    key: str,
    *,
    default: bool,
) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a boolean.")
    return value


def _required_str(
    payload: Mapping[str, Any],
    key: str,
) -> str:
    value = payload.get(
        key,
    )
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(f"{key} must be a string.")
    _require_non_empty(
        value,
        key,
    )
    return value


def _optional_str(
    value: object,
) -> str | None:
    if value is None:
        return None
    if not isinstance(
        value,
        str,
    ):
        raise TypeError("optional string payload values must be strings or None.")
    if not value.strip():
        return None
    return value


def _validate_optional_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
