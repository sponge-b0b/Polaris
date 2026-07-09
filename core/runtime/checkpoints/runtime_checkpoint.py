from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any

from core.runtime.state.runtime_context import RuntimeContext
from core.security.sensitive_data import sanitize_sensitive_mapping


@dataclass(frozen=True, slots=True)
class RuntimeCheckpoint:
    """
    Immutable runtime execution checkpoint.

    Used for:
    - replay
    - recovery
    - resumability
    - audit trails
    - debugging
    """

    checkpoint_id: str

    workflow_id: str

    execution_id: str

    runtime_id: str

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    wave_index: int = 0

    completed_nodes: tuple[str, ...] = ()

    failed_nodes: tuple[str, ...] = ()

    skipped_nodes: tuple[str, ...] = ()

    runtime_context: RuntimeContext | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    def validate(
        self,
    ) -> None:
        if not self.checkpoint_id.strip():
            raise ValueError("checkpoint_id cannot be empty.")

        if not self.workflow_id.strip():
            raise ValueError("workflow_id cannot be empty.")

        if not self.execution_id.strip():
            raise ValueError("execution_id cannot be empty.")

        if not self.runtime_id.strip():
            raise ValueError("runtime_id cannot be empty.")

        if self.wave_index < 0:
            raise ValueError("wave_index cannot be negative.")

    # ========================================================
    # LOOKUPS
    # ========================================================

    def has_completed(
        self,
        node_name: str,
    ) -> bool:
        return node_name in self.completed_nodes

    def has_failed(
        self,
        node_name: str,
    ) -> bool:
        return node_name in self.failed_nodes

    def has_skipped(
        self,
        node_name: str,
    ) -> bool:
        return node_name in self.skipped_nodes

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return sanitize_sensitive_mapping(
            {
                "checkpoint_id": self.checkpoint_id,
                "workflow_id": self.workflow_id,
                "execution_id": self.execution_id,
                "runtime_id": self.runtime_id,
                "created_at": self.created_at.isoformat(),
                "wave_index": self.wave_index,
                "completed_nodes": list(self.completed_nodes),
                "failed_nodes": list(self.failed_nodes),
                "skipped_nodes": list(self.skipped_nodes),
                "runtime_context": (
                    self.runtime_context.to_dict()
                    if self.runtime_context is not None
                    else None
                ),
                "metadata": deepcopy(self.metadata),
            }
        )

    # ========================================================
    # FACTORIES
    # ========================================================

    @classmethod
    def from_context(
        cls,
        checkpoint_id: str,
        context: RuntimeContext,
        wave_index: int = 0,
        completed_nodes: tuple[str, ...] | None = None,
        failed_nodes: tuple[str, ...] | None = None,
        skipped_nodes: tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeCheckpoint:
        checkpoint = cls(
            checkpoint_id=checkpoint_id,
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            runtime_id=context.runtime_id,
            wave_index=wave_index,
            completed_nodes=completed_nodes or (),
            failed_nodes=failed_nodes or (),
            skipped_nodes=skipped_nodes or (),
            runtime_context=context,
            metadata=deepcopy(metadata or {}),
        )

        checkpoint.validate()

        return checkpoint

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> RuntimeCheckpoint:
        """
        Restore RuntimeCheckpoint from serialized checkpoint data.

        Supports both:
        - RuntimeCheckpoint.to_dict() payloads
        - CheckpointManager payloads containing runtime_context + saved_at
        """

        runtime_context_data = data.get(
            "runtime_context",
        )

        runtime_context = (
            RuntimeContext.from_dict(
                runtime_context_data,
            )
            if runtime_context_data is not None
            else None
        )

        created_at_raw = data.get("created_at") or data.get("saved_at")

        created_at = (
            datetime.fromisoformat(
                created_at_raw,
            )
            if created_at_raw
            else datetime.now(timezone.utc)
        )

        workflow_id = data.get("workflow_id")
        execution_id = data.get("execution_id")
        runtime_id = data.get("runtime_id")

        if workflow_id is None and runtime_context is not None:
            workflow_id = runtime_context.workflow_id

        if execution_id is None and runtime_context is not None:
            execution_id = runtime_context.execution_id

        if runtime_id is None and runtime_context is not None:
            runtime_id = runtime_context.runtime_id

        if workflow_id is None:
            raise ValueError("Checkpoint payload missing workflow_id.")

        if execution_id is None:
            raise ValueError("Checkpoint payload missing execution_id.")

        if runtime_id is None:
            raise ValueError("Checkpoint payload missing runtime_id.")

        checkpoint = cls(
            checkpoint_id=str(data["checkpoint_id"]),
            workflow_id=str(workflow_id),
            execution_id=str(execution_id),
            runtime_id=str(runtime_id),
            created_at=created_at,
            wave_index=int(data.get("wave_index", 0)),
            completed_nodes=tuple(data.get("completed_nodes", ())),
            failed_nodes=tuple(data.get("failed_nodes", ())),
            skipped_nodes=tuple(data.get("skipped_nodes", ())),
            runtime_context=runtime_context,
            metadata=deepcopy(data.get("metadata", {})),
        )

        checkpoint.validate()

        return checkpoint
