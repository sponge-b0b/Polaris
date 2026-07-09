from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from collections.abc import Sequence
from typing import Mapping

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_context import RagSource
from application.rag.contracts.rag_quality_models import RagCorrectiveAction
from application.rag.contracts.rag_quality_models import RagReflectionScores
from application.rag.contracts.rag_request import RagRequest
from core.storage.persistence.rag import JsonObject


@dataclass(
    frozen=True,
    slots=True,
)
class RagResult:
    """
    Canonical platform-facing RAG result.
    """

    query_id: str
    request: RagRequest
    answer_text: str
    status: str
    route: str
    contexts: tuple[RagRetrievedContext, ...] = ()
    citations: tuple[RagSource, ...] = ()
    confidence_score: float | None = None
    grounding_score: float | None = None
    utility_score: float | None = None
    injection_detected: bool = False
    reflection_scores: RagReflectionScores | None = None
    corrective_actions: tuple[RagCorrectiveAction, ...] = ()
    error: str | None = None
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "query_id",
            "answer_text",
            "status",
            "route",
        ):
            _require_non_empty(
                getattr(
                    self,
                    field_name,
                ),
                field_name,
            )
        if (
            self.confidence_score is not None
            and not 0.0 <= self.confidence_score <= 1.0
        ):
            raise ValueError("confidence_score must be between 0.0 and 1.0.")
        for field_name in ("grounding_score", "utility_score"):
            value = getattr(self, field_name)
            if value is not None and not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
        if self.status == "failed":
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def answered(
        cls,
        *,
        request: RagRequest,
        answer_text: str,
        contexts: tuple[RagRetrievedContext, ...],
        confidence_score: float | None = None,
        metadata: JsonObject | None = None,
    ) -> RagResult:
        return cls(
            query_id=request.request_id,
            request=request,
            answer_text=answer_text,
            status="answered",
            route=request.route,
            contexts=contexts,
            citations=_unique_citations(
                contexts,
            ),
            confidence_score=confidence_score,
            metadata=metadata or {},
        )

    @classmethod
    def no_results(
        cls,
        *,
        request: RagRequest,
        answer_text: str = "No relevant curated RAG context was found.",
    ) -> RagResult:
        return cls(
            query_id=request.request_id,
            request=request,
            answer_text=answer_text,
            status="no_results",
            route=request.route,
        )

    @classmethod
    def failed(
        cls,
        *,
        request: RagRequest,
        error: str,
    ) -> RagResult:
        return cls(
            query_id=request.request_id,
            request=request,
            answer_text=f"RAG request failed: {error}",
            status="failed",
            route=request.route,
            error=error,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "request": self.request.to_dict(),
            "answer_text": self.answer_text,
            "status": self.status,
            "route": self.route,
            "contexts": [context.to_dict() for context in self.contexts],
            "citations": [citation.to_dict() for citation in self.citations],
            "confidence_score": self.confidence_score,
            "grounding_score": self.grounding_score,
            "utility_score": self.utility_score,
            "injection_detected": self.injection_detected,
            "reflection_scores": (
                None
                if self.reflection_scores is None
                else self.reflection_scores.to_dict()
            ),
            "corrective_actions": [action.value for action in self.corrective_actions],
            "error": self.error,
            "generated_at": self.generated_at.isoformat(),
            "metadata": deepcopy(
                dict(self.metadata),
            ),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RagResult:
        request_payload = payload.get(
            "request",
        )
        if not isinstance(
            request_payload,
            Mapping,
        ):
            raise TypeError("request must be an object.")

        return cls(
            query_id=_required_str(
                payload,
                "query_id",
            ),
            request=RagRequest.from_dict(
                request_payload,
            ),
            answer_text=_required_str(
                payload,
                "answer_text",
            ),
            status=_required_str(
                payload,
                "status",
            ),
            route=_required_str(
                payload,
                "route",
            ),
            contexts=_contexts_from_payload(
                payload.get(
                    "contexts",
                    (),
                )
            ),
            citations=_citations_from_payload(
                payload.get(
                    "citations",
                    (),
                )
            ),
            confidence_score=_optional_float(
                payload.get(
                    "confidence_score",
                )
            ),
            grounding_score=_optional_float(payload.get("grounding_score")),
            utility_score=_optional_float(payload.get("utility_score")),
            injection_detected=_bool_from_payload(
                payload.get("injection_detected", False),
                "injection_detected",
            ),
            reflection_scores=_reflection_scores_from_payload(
                payload.get("reflection_scores")
            ),
            corrective_actions=_corrective_actions_from_payload(
                payload.get("corrective_actions", ())
            ),
            error=_optional_str(
                payload.get(
                    "error",
                )
            ),
            generated_at=_datetime_from_payload(
                payload.get(
                    "generated_at",
                )
            ),
            metadata=_metadata_from_payload(
                payload.get(
                    "metadata",
                )
            ),
        )


def _unique_citations(
    contexts: tuple[RagRetrievedContext, ...],
) -> tuple[RagSource, ...]:
    seen: set[tuple[str, str, str | None]] = set()
    citations: list[RagSource] = []
    for context in contexts:
        key = (
            context.source.document_id,
            context.source.source_id,
            context.source.chunk_id,
        )
        if key in seen:
            continue
        seen.add(
            key,
        )
        citations.append(
            context.source,
        )
    return tuple(citations)


def _contexts_from_payload(
    value: object,
) -> tuple[RagRetrievedContext, ...]:
    if value is None:
        return ()
    if not isinstance(
        value,
        Sequence,
    ) or isinstance(
        value,
        str,
    ):
        raise TypeError("contexts must be a sequence of objects.")
    return tuple(
        RagRetrievedContext.from_dict(
            _require_mapping(
                item,
            )
        )
        for item in value
    )


def _citations_from_payload(
    value: object,
) -> tuple[RagSource, ...]:
    if value is None:
        return ()
    if not isinstance(
        value,
        Sequence,
    ) or isinstance(
        value,
        str,
    ):
        raise TypeError("citations must be a sequence of objects.")
    return tuple(
        RagSource.from_dict(
            _require_mapping(
                item,
            )
        )
        for item in value
    )


def _reflection_scores_from_payload(
    value: object,
) -> RagReflectionScores | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError("reflection_scores must be an object or None.")
    return RagReflectionScores.from_dict(value)


def _corrective_actions_from_payload(
    value: object,
) -> tuple[RagCorrectiveAction, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise TypeError("corrective_actions must be a sequence of strings.")
    result: list[RagCorrectiveAction] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TypeError("corrective_actions must contain non-empty strings.")
        result.append(RagCorrectiveAction(item))
    return tuple(result)


def _bool_from_payload(
    value: object,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean.")
    return value


def _datetime_from_payload(
    value: object,
) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(
        value,
        datetime,
    ):
        return value
    if isinstance(
        value,
        str,
    ):
        return datetime.fromisoformat(
            value,
        )
    raise TypeError("generated_at must be an ISO datetime string or datetime object.")


def _metadata_from_payload(
    value: object,
) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError("metadata must be an object.")
    return dict(value)


def _optional_float(
    value: object,
) -> float | None:
    if value is None:
        return None
    if isinstance(
        value,
        int | float | str,
    ):
        return float(value)
    raise TypeError("optional float payload values must be numeric or strings.")


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


def _require_mapping(
    value: object,
) -> Mapping[str, Any]:
    if not isinstance(
        value,
        Mapping,
    ):
        raise TypeError("sequence values must be objects.")
    return value


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
