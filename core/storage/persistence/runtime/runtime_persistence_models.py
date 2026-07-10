from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Mapping
from typing import Sequence
from typing import TypeAlias
from uuid import uuid4

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]


@dataclass(
    frozen=True,
    slots=True,
)
class WorkflowRunRecord:
    """
    Typed persistence boundary record for a workflow execution summary.

    The runtime should continue to work with canonical runtime/domain objects.
    This DTO is used only when crossing into durable persistence.
    """

    workflow_name: str
    execution_id: str
    status: str
    runtime_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    mode: str | None = None
    error: str | None = None
    metadata: JsonObject = field(default_factory=dict)
    state_payload: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.workflow_name,
            "workflow_name",
        )
        _require_non_empty(
            self.execution_id,
            "execution_id",
        )
        _require_non_empty(
            self.status,
            "status",
        )
        _require_non_negative_optional(
            self.duration_seconds,
            "duration_seconds",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class WorkflowNodeRunRecord:
    """
    Typed persistence boundary record for a single runtime node execution.
    """

    workflow_name: str
    execution_id: str
    node_name: str
    status: str
    runtime_id: str | None = None
    wave_index: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error: str | None = None
    metadata: JsonObject = field(default_factory=dict)
    outputs: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.workflow_name,
            "workflow_name",
        )
        _require_non_empty(
            self.execution_id,
            "execution_id",
        )
        _require_non_empty(
            self.node_name,
            "node_name",
        )
        _require_non_empty(
            self.status,
            "status",
        )
        _require_non_negative_optional(
            self.wave_index,
            "wave_index",
        )
        _require_non_negative_optional(
            self.duration_seconds,
            "duration_seconds",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class WorkflowEventRecord:
    """
    Typed persistence boundary record for a canonical runtime event.
    """

    event_type: str
    workflow_name: str
    execution_id: str
    timestamp: datetime
    event_id: str = field(default_factory=lambda: uuid4().hex)
    runtime_id: str | None = None
    node_name: str | None = None
    wave_index: int | None = None
    payload: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.event_id,
            "event_id",
        )
        _require_non_empty(
            self.event_type,
            "event_type",
        )
        _require_non_empty(
            self.workflow_name,
            "workflow_name",
        )
        _require_non_empty(
            self.execution_id,
            "execution_id",
        )
        _require_non_negative_optional(
            self.wave_index,
            "wave_index",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class WorkflowStateSnapshotRecord:
    """
    Typed persistence boundary record for workflow state snapshots.

    The snapshot captures serialized workflow state at an audit/checkpoint
    boundary without changing runtime execution semantics. The state payload is
    intentionally JSON-shaped because it crosses into durable persistence;
    runtime internals should continue to use canonical typed runtime objects.
    """

    snapshot_id: str
    workflow_name: str
    execution_id: str
    workflow_status: str
    timestamp: datetime
    runtime_id: str | None = None
    wave_index: int | None = None
    checkpoint_reference: str | None = None
    state_payload: JsonObject = field(default_factory=dict)
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "snapshot_id",
            require_non_empty_identifier(
                self.snapshot_id,
                "snapshot_id",
            ),
        )
        object.__setattr__(
            self,
            "workflow_name",
            require_non_empty_identifier(
                self.workflow_name,
                "workflow_name",
            ),
        )
        object.__setattr__(
            self,
            "execution_id",
            require_non_empty_identifier(
                self.execution_id,
                "execution_id",
            ),
        )
        object.__setattr__(
            self,
            "workflow_status",
            require_non_empty_identifier(
                self.workflow_status,
                "workflow_status",
            ),
        )
        object.__setattr__(
            self,
            "runtime_id",
            clean_optional_identifier(
                self.runtime_id,
                "runtime_id",
            ),
        )
        object.__setattr__(
            self,
            "checkpoint_reference",
            clean_optional_identifier(
                self.checkpoint_reference,
                "checkpoint_reference",
            ),
        )
        _require_non_negative_optional(
            self.wave_index,
            "wave_index",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RuntimePersistenceResult:
    """
    Typed result returned by runtime persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative_optional(
            self.records_persisted,
            "records_persisted",
        )

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if not self.success:
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        records_persisted: int = 1,
    ) -> RuntimePersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> RuntimePersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_workflow_state_snapshot_id(
    *,
    workflow_name: str,
    execution_id: str,
    timestamp: datetime,
    wave_index: int | None = None,
    checkpoint_reference: str | None = None,
) -> str:
    """
    Build a deterministic workflow-state snapshot id from snapshot context.
    """

    clean_workflow_name = require_non_empty_identifier(
        workflow_name,
        "workflow_name",
    )
    clean_execution_id = require_non_empty_identifier(
        execution_id,
        "execution_id",
    )
    clean_checkpoint_reference = clean_optional_identifier(
        checkpoint_reference,
        "checkpoint_reference",
    )
    _require_non_negative_optional(
        wave_index,
        "wave_index",
    )
    id_parts = [
        "workflow_state_snapshot",
        clean_workflow_name,
        clean_execution_id,
        f"wave-{wave_index if wave_index is not None else 'none'}",
        timestamp.isoformat(),
    ]
    if clean_checkpoint_reference is not None:
        id_parts.append(
            clean_checkpoint_reference,
        )

    return ":".join(
        id_parts,
    )


def new_random_workflow_state_snapshot_id() -> str:
    """
    Build a unique workflow-state snapshot id when no stable key is available.
    """

    return f"workflow_state_snapshot:{uuid4().hex}"


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _require_non_negative_optional(
    value: int | float | None,
    field_name: str,
) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} cannot be negative.")
