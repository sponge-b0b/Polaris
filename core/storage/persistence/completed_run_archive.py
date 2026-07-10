from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping
from typing import Sequence
from typing import TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]
JsonArray: TypeAlias = Sequence[JsonValue]


class CompletedRunExecutionMode(str, Enum):
    """First-class execution classification for completed workflow runs."""

    NORMAL = "normal"
    REPLAY = "replay"
    BACKTEST = "backtest"
    SIMULATED = "simulated"


def coerce_completed_run_execution_mode(
    value: CompletedRunExecutionMode | str | None,
) -> CompletedRunExecutionMode:
    """Normalize completed-run execution mode at persistence boundaries."""

    if value is None:
        return CompletedRunExecutionMode.NORMAL
    if isinstance(value, CompletedRunExecutionMode):
        return value

    normalized = value.strip().lower()
    if normalized == "live":
        return CompletedRunExecutionMode.NORMAL

    try:
        return CompletedRunExecutionMode(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported completed-run execution mode: {value!r}."
        ) from exc


@dataclass(frozen=True, slots=True)
class CompletedRunRecord:
    """Canonical typed record for one completed workflow execution."""

    run_id: str
    workflow_name: str
    workflow_id: str | None
    execution_id: str
    runtime_id: str | None
    status: str
    success: bool
    context_json: JsonObject
    inputs_json: JsonObject
    outputs_json: JsonObject
    metadata: JsonObject
    errors_json: JsonArray
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    node_count: int | None
    completed_node_count: int | None
    failed_node_count: int | None
    schema_version: int = 2
    execution_mode: CompletedRunExecutionMode | str = CompletedRunExecutionMode.NORMAL

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "execution_mode",
            coerce_completed_run_execution_mode(self.execution_mode),
        )


@dataclass(frozen=True, slots=True)
class CompletedNodeOutputRecord:
    """Canonical typed record for one persisted runtime node output."""

    node_output_id: str
    run_id: str
    workflow_name: str
    execution_id: str
    node_name: str
    node_type: str | None
    output_contract: str | None
    output_schema_version: int | None
    status: str
    success: bool | None
    outputs: JsonObject
    metadata: JsonObject
    errors_json: JsonArray
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None


@dataclass(frozen=True, slots=True)
class CompletedRunArtifactRecord:
    """Canonical typed record for an artifact attached to a completed run."""

    artifact_id: str
    run_id: str
    workflow_name: str
    execution_id: str
    artifact_type: str
    artifact_name: str
    artifact_path: str
    mime_type: str | None
    size_bytes: int | None
    metadata: JsonObject


@dataclass(frozen=True, slots=True)
class CompletedRunBundle:
    """Typed aggregate persisted as a single completed-run archive unit."""

    run: CompletedRunRecord
    node_outputs: tuple[CompletedNodeOutputRecord, ...] = ()
    artifacts: tuple[CompletedRunArtifactRecord, ...] = ()


class CompletedRunArchive(ABC):
    """
    Canonical completed run archive contract.

    Archives completed workflow executions for:
    - audit trail
    - historical analysis
    - RAG source material
    - observability

    Completed run archives are not checkpoint/replay state.
    """

    @abstractmethod
    async def archive_run(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        raise NotImplementedError

    @abstractmethod
    async def list_archived_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def delete_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def cleanup_archived_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        raise NotImplementedError
