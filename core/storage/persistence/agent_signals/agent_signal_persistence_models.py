from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Mapping
from typing import Sequence
from typing import TypeAlias
from uuid import uuid4

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]


@dataclass(
    frozen=True,
    slots=True,
)
class AgentSignalRecord:
    """
    Typed persistence-boundary record for a curated agent signal.

    Intelligence/agent layers should work with their typed signal objects and
    convert to this record only when crossing into durable persistence. Full
    reasoning and LLM text are preserved without truncation for attribution and
    future curated RAG ingestion.
    """

    signal_id: str
    agent_name: str
    agent_type: str
    timestamp: datetime
    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None
    symbol: str | None = None
    universe: tuple[str, ...] = ()
    directional_score: float | None = None
    confidence: float | None = None
    regime: str | None = None
    signals: JsonObject = field(default_factory=dict)
    risks: JsonObject = field(default_factory=dict)
    recommendations: JsonObject = field(default_factory=dict)
    features: JsonObject = field(default_factory=dict)
    reasoning_text: str | None = None
    llm_response: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.signal_id,
            "signal_id",
        )
        _require_non_empty(
            self.agent_name,
            "agent_name",
        )
        _require_non_empty(
            self.agent_type,
            "agent_type",
        )
        _require_score_range(
            self.directional_score,
            "directional_score",
            minimum=-1.0,
            maximum=1.0,
        )
        _require_score_range(
            self.confidence,
            "confidence",
            minimum=0.0,
            maximum=1.0,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentSignalPersistenceResult:
    """
    Typed result returned by agent signal persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    signal_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative(
            self.records_persisted,
            "records_persisted",
        )

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            _require_non_empty(
                self.signal_id,
                "signal_id",
            )

        if not self.success:
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        signal_id: str,
        records_persisted: int = 1,
    ) -> AgentSignalPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            signal_id=signal_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> AgentSignalPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_agent_signal_id(
    agent_name: str,
    execution_id: str | None = None,
    node_name: str | None = None,
    signal_key: str | None = None,
) -> str:
    """
    Build a stable id when workflow lineage is available, otherwise use UUID.
    """

    _require_non_empty(
        agent_name,
        "agent_name",
    )
    clean_agent_name = agent_name.strip()
    clean_execution_id = _clean_identifier_part(execution_id)
    clean_node_name = _clean_identifier_part(node_name)
    clean_signal_key = _clean_identifier_part(signal_key)

    if clean_execution_id is not None:
        parts: list[str] = [
            "agent_signal",
            clean_execution_id,
            clean_agent_name,
        ]
        if clean_node_name is not None:
            parts.append(clean_node_name)
        if clean_signal_key is not None:
            parts.append(clean_signal_key)
        return ":".join(parts)

    return f"agent_signal:{clean_agent_name}:{uuid4().hex}"


def _clean_identifier_part(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    return stripped


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _require_non_negative(
    value: int,
    field_name: str,
) -> None:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_score_range(
    value: float | None,
    field_name: str,
    *,
    minimum: float,
    maximum: float,
) -> None:
    if value is None:
        return

    if value < minimum or value > maximum:
        raise ValueError(f"{field_name} must be between {minimum} and {maximum}.")
