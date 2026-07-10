from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Mapping

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
    output_contract: str | None = None
    output_schema_version: int | None = None

    def __post_init__(
        self,
    ) -> None:
        if self.success and self.skipped:
            raise ValueError("RuntimeNodeOutput cannot be both success and skipped.")

        if self.output_contract is not None and not self.output_contract.strip():
            raise ValueError("output_contract cannot be empty when provided.")

        if self.output_schema_version is not None and self.output_schema_version <= 0:
            raise ValueError("output_schema_version must be positive when provided.")

        if self.output_contract is not None and self.output_schema_version is None:
            raise ValueError(
                "output_schema_version is required when output_contract is provided."
            )

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
            "output_contract": self.output_contract,
            "output_schema_version": self.output_schema_version,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> RuntimeNodeOutput:
        return cls(
            success=bool(payload.get("success", True)),
            skipped=payload.get("skipped") is True,
            stop_propagation=payload.get("stop_propagation") is True,
            outputs=deepcopy(_mapping_value(payload.get("outputs"))),
            artifacts=deepcopy(_mapping_value(payload.get("artifacts"))),
            emitted_events=[],
            errors=deepcopy(_list_value(payload.get("errors"))),
            execution_metadata=deepcopy(
                _mapping_value(payload.get("execution_metadata")),
            ),
            output_contract=_optional_string(payload.get("output_contract")),
            output_schema_version=_optional_int(
                payload.get("output_schema_version"),
            ),
        )

    @classmethod
    def success_output(
        cls,
        outputs: dict[str, Any] | None = None,
        execution_metadata: dict[str, Any] | None = None,
        output_contract: str | None = None,
        output_schema_version: int | None = None,
    ) -> RuntimeNodeOutput:
        return cls(
            success=True,
            outputs=outputs or {},
            execution_metadata=execution_metadata or {},
            output_contract=output_contract,
            output_schema_version=output_schema_version,
        )

    @classmethod
    def failure_output(
        cls,
        errors: list[dict[str, Any]],
        execution_metadata: dict[str, Any] | None = None,
        stop_propagation: bool = False,
        output_contract: str | None = None,
        output_schema_version: int | None = None,
    ) -> RuntimeNodeOutput:
        return cls(
            success=False,
            errors=errors,
            stop_propagation=stop_propagation,
            execution_metadata=execution_metadata or {},
            output_contract=output_contract,
            output_schema_version=output_schema_version,
        )

    @classmethod
    def skipped_output(
        cls,
        reason: str,
        execution_metadata: dict[str, Any] | None = None,
        output_contract: str | None = None,
        output_schema_version: int | None = None,
    ) -> RuntimeNodeOutput:
        metadata = dict(execution_metadata or {})
        metadata["skip_reason"] = reason
        return cls(
            success=False,
            skipped=True,
            execution_metadata=metadata,
            output_contract=output_contract,
            output_schema_version=output_schema_version,
        )


def _mapping_value(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)

    return {}


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value

    return []


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    return text


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value

    return None
