from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode


@dataclass(frozen=True, slots=True)
class WorkflowNodeDefinition:
    """
    Immutable orchestration-level node definition.

    Defines how a RuntimeNode participates in workflow topology.
    """

    # ============================================================
    # NODE IDENTITY
    # ============================================================

    name: str

    node_type: type[RuntimeNode]

    # ============================================================
    # DAG DEPENDENCIES
    # ============================================================

    dependencies: tuple[str, ...] = ()

    # ============================================================
    # ORCHESTRATION POLICY
    # ============================================================

    enabled: bool = True

    max_retries: int = 2

    retry_backoff_seconds: float = 0.0

    fail_fast: bool = False

    timeout_seconds: float | None = None

    # ============================================================
    # EXECUTION TAGGING
    # ============================================================

    tags: tuple[str, ...] = ()

    # ============================================================
    # METADATA
    # ============================================================

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    # ============================================================
    # VALIDATION
    # ============================================================

    def validate(
        self,
    ) -> None:
        if not self.name.strip():
            raise ValueError("Workflow node name cannot be empty.")

        if not issubclass(
            self.node_type,
            RuntimeNode,
        ):
            raise TypeError(f"{self.node_type} must inherit RuntimeNode.")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative.")

        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative.")

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0 when provided.")

        if self.name in self.dependencies:
            raise ValueError(f"Node '{self.name}' cannot depend on itself.")

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "node_type": self.node_type.__name__,
            "dependencies": list(self.dependencies),
            "enabled": self.enabled,
            "max_retries": self.max_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "fail_fast": self.fail_fast,
            "timeout_seconds": self.timeout_seconds,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }
