from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class RuntimeNode(ABC):
    """
    Canonical runtime execution unit.

    Subclasses implement only _execute().
    RuntimeNode.run() wraps execution with:
    - context validation
    - timing metadata
    - exception normalization
    - immutable output metadata enrichment
    """

    # ============================================================
    # REQUIRED METADATA
    # ============================================================

    node_name: str = "unnamed_node"
    node_type: str = "runtime"
    node_version: str = "1.0.0"

    # ============================================================
    # EXECUTION CAPABILITIES
    # ============================================================

    retryable: bool = True
    timeout_seconds: float | None = None
    checkpoint_enabled: bool = True
    parallel_safe: bool = True

    # ============================================================
    # PUBLIC EXECUTION ENTRYPOINT
    # ============================================================

    async def run(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        started_at = datetime.now(timezone.utc)

        try:
            self.validate_context(context)

            output = await self._execute(
                context=context,
            )

            completed_at = datetime.now(timezone.utc)

            return self._with_execution_metadata(
                output=output,
                started_at=started_at,
                completed_at=completed_at,
                failed=False,
            )

        except Exception as exc:
            completed_at = datetime.now(timezone.utc)

            return RuntimeNodeOutput.failure_output(
                errors=[
                    {
                        "node_name": self.node_name,
                        "node_type": self.node_type,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                        "started_at": started_at.isoformat(),
                        "completed_at": completed_at.isoformat(),
                    }
                ],
                execution_metadata={
                    "node_name": self.node_name,
                    "node_type": self.node_type,
                    "node_version": self.node_version,
                    "started_at": started_at.isoformat(),
                    "completed_at": completed_at.isoformat(),
                    "duration_seconds": (completed_at - started_at).total_seconds(),
                    "failed": True,
                },
            )

    # ============================================================
    # INTERNAL EXECUTION
    # ============================================================

    @abstractmethod
    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        raise NotImplementedError

    # ============================================================
    # VALIDATION
    # ============================================================

    def validate_context(
        self,
        context: RuntimeContext,
    ) -> None:
        return None

    # ============================================================
    # METADATA ENRICHMENT
    # ============================================================

    def _with_execution_metadata(
        self,
        output: RuntimeNodeOutput,
        started_at: datetime,
        completed_at: datetime,
        failed: bool,
    ) -> RuntimeNodeOutput:
        metadata = {
            **dict(output.execution_metadata),
            "node_name": self.node_name,
            "node_type": self.node_type,
            "node_version": self.node_version,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": (completed_at - started_at).total_seconds(),
            "failed": failed,
        }

        return RuntimeNodeOutput(
            success=output.success,
            skipped=output.skipped,
            stop_propagation=output.stop_propagation,
            outputs=dict(output.outputs),
            artifacts=dict(output.artifacts),
            emitted_events=list(output.emitted_events),
            errors=list(output.errors),
            execution_metadata=metadata,
        )

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "node_name": self.node_name,
            "node_type": self.node_type,
            "node_version": self.node_version,
            "retryable": self.retryable,
            "timeout_seconds": self.timeout_seconds,
            "checkpoint_enabled": self.checkpoint_enabled,
            "parallel_safe": self.parallel_safe,
        }
