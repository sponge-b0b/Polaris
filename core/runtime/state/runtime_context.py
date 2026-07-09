from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import ClassVar
from typing import Mapping

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from core.telemetry.tracing.trace_context import TraceContext


RUNTIME_CONTEXT_SCHEMA_VERSION = 2


class UnsupportedRuntimeContextSchemaError(ValueError):
    """Raised when persisted runtime context cannot be safely reconstructed."""


class RuntimeContext(BaseModel):
    """Immutable, replayable runtime execution context."""

    schema_version: ClassVar[int] = RUNTIME_CONTEXT_SCHEMA_VERSION

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    runtime_id: str
    workflow_id: str
    execution_id: str

    mode: str = "live"

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    simulation_time: datetime | None = None

    context_version: int = 0

    workflow_inputs: dict[str, Any] = Field(
        default_factory=dict,
    )

    artifact_refs: dict[str, Any] = Field(
        default_factory=dict,
    )

    node_outputs: dict[str, Any] = Field(
        default_factory=dict,
    )

    errors: list[dict[str, Any]] = Field(
        default_factory=list,
    )

    trace_context: TraceContext | None = None

    @field_validator(
        "workflow_inputs",
        mode="before",
    )
    @classmethod
    def _validate_workflow_inputs(
        cls,
        value: Any,
    ) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, Mapping):
            return deepcopy(dict(value))
        raise TypeError("workflow_inputs must be a mapping or None.")

    @field_validator(
        "trace_context",
        mode="before",
    )
    @classmethod
    def _validate_trace_context(
        cls,
        value: Any,
    ) -> TraceContext | None:
        if value is None or isinstance(value, TraceContext):
            return value

        if isinstance(value, dict):
            return TraceContext.from_dict(
                value,
            )

        raise TypeError("trace_context must be a TraceContext, dictionary, or None.")

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RuntimeContext:
        """Restore a persisted context only when its schema is explicitly supported."""

        schema_version = payload.get("schema_version")
        if schema_version != RUNTIME_CONTEXT_SCHEMA_VERSION:
            raise UnsupportedRuntimeContextSchemaError(
                "Unsupported RuntimeContext schema version: "
                f"expected {RUNTIME_CONTEXT_SCHEMA_VERSION}, got "
                f"{schema_version!r}. Historical local checkpoints must be "
                "regenerated; completed PostgreSQL runs must be migrated."
            )

        model_payload = dict(payload)
        model_payload.pop("schema_version", None)
        return cls.model_validate(model_payload)

    def with_trace_context(
        self,
        trace_context: TraceContext,
    ) -> RuntimeContext:
        return self.model_copy(
            update={
                "trace_context": trace_context,
            },
            deep=True,
        )

    def add_artifact(
        self,
        key: str,
        artifact_ref: Any,
    ) -> RuntimeContext:
        if not key.strip():
            raise ValueError("artifact key cannot be empty.")

        new_refs = deepcopy(
            self.artifact_refs,
        )

        new_refs[key] = deepcopy(
            artifact_ref,
        )

        return self.model_copy(
            update={
                "artifact_refs": new_refs,
                "context_version": self.context_version + 1,
            },
            deep=True,
        )

    def add_node_output(
        self,
        node_name: str,
        output: dict[str, Any],
    ) -> RuntimeContext:
        if not node_name.strip():
            raise ValueError("node_name cannot be empty.")

        node_outputs = dict(
            self.node_outputs,
        )

        node_outputs[node_name] = deepcopy(
            output,
        )

        return self.model_copy(
            update={
                "node_outputs": node_outputs,
                "context_version": self.context_version + 1,
            },
            deep=True,
        )

    def add_error(
        self,
        error: dict[str, Any],
    ) -> RuntimeContext:
        errors = list(
            self.errors,
        )

        errors.append(
            deepcopy(error),
        )

        return self.model_copy(
            update={
                "errors": errors,
                "context_version": self.context_version + 1,
            },
            deep=True,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": RUNTIME_CONTEXT_SCHEMA_VERSION,
            "runtime_id": self.runtime_id,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "mode": self.mode,
            "created_at": self.created_at.isoformat(),
            "simulation_time": (
                self.simulation_time.isoformat() if self.simulation_time else None
            ),
            "context_version": self.context_version,
            "workflow_inputs": deepcopy(self.workflow_inputs),
            "artifact_refs": deepcopy(self.artifact_refs),
            "node_outputs": deepcopy(self.node_outputs),
            "errors": deepcopy(self.errors),
            "trace_context": (
                self.trace_context.to_dict() if self.trace_context is not None else None
            ),
        }
