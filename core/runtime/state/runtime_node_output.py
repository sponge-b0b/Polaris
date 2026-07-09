from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from core.runtime.events.runtime_events import RuntimeEvent


@dataclass(frozen=True, slots=True)
class RuntimeNodeOutput:
    """Canonical serialized output emitted by one runtime node execution."""

    success: bool = True
    skipped: bool = False
    stop_propagation: bool = False
    outputs: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    emitted_events: list[RuntimeEvent] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    execution_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        if self.success and self.skipped:
            raise ValueError("RuntimeNodeOutput cannot be both success and skipped.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "success": self.success,
            "skipped": self.skipped,
            "stop_propagation": self.stop_propagation,
            "outputs": deepcopy(self.outputs),
            "artifacts": deepcopy(self.artifacts),
            "emitted_events": [event.to_dict() for event in self.emitted_events],
            "errors": deepcopy(self.errors),
            "execution_metadata": deepcopy(self.execution_metadata),
        }

    @classmethod
    def success_output(
        cls,
        outputs: dict[str, Any] | None = None,
        execution_metadata: dict[str, Any] | None = None,
    ) -> RuntimeNodeOutput:
        return cls(
            success=True,
            outputs=outputs or {},
            execution_metadata=execution_metadata or {},
        )

    @classmethod
    def failure_output(
        cls,
        errors: list[dict[str, Any]],
        execution_metadata: dict[str, Any] | None = None,
        stop_propagation: bool = False,
    ) -> RuntimeNodeOutput:
        return cls(
            success=False,
            errors=errors,
            stop_propagation=stop_propagation,
            execution_metadata=execution_metadata or {},
        )

    @classmethod
    def skipped_output(
        cls,
        reason: str,
        execution_metadata: dict[str, Any] | None = None,
    ) -> RuntimeNodeOutput:
        metadata = dict(execution_metadata or {})
        metadata["skip_reason"] = reason
        return cls(
            success=False,
            skipped=True,
            execution_metadata=metadata,
        )
