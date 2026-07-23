from __future__ import annotations

import hashlib
from collections.abc import Mapping
from collections.abc import Mapping as MappingABC
from collections.abc import Sequence as SequenceABC
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast

from core.database.models.completed_runs import (
    CompletedRunArtifactModel,
    CompletedWorkflowNodeOutputModel,
    CompletedWorkflowRunModel,
)
from core.runtime.state.runtime_context import RUNTIME_CONTEXT_SCHEMA_VERSION
from core.security.sensitive_data import sanitize_sensitive_value
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArtifactRecord,
    CompletedRunBundle,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    JsonArray,
    JsonObject,
    JsonValue,
    coerce_completed_run_execution_mode,
)


class CompletedRunPersistenceSerializer:
    """
    Serializer for completed workflow archival persistence.

    JSON dictionaries are introduced here because this module is the PostgreSQL
    JSONB persistence boundary. Runtime code should continue to work with
    ``RuntimeContext`` and typed completed-run records.
    """

    @staticmethod
    def bundle_from_context_payload(
        context_payload: Mapping[str, Any],
        *,
        workflow_name: str | None = None,
        status: str | None = None,
        success: bool | None = None,
        completed_at: datetime | None = None,
    ) -> CompletedRunBundle:
        sanitized_context = _json_object(
            context_payload,
        )
        raw_context = dict(
            deepcopy(context_payload),
        )
        resolved_workflow_name = workflow_name or str(
            raw_context.get("workflow_id") or "unknown_workflow",
        )
        execution_id = str(
            raw_context.get("execution_id") or "unknown_execution",
        )
        run_id = _stable_id(
            "completed_run",
            resolved_workflow_name,
            execution_id,
        )
        node_output_payloads = _mapping_value(
            raw_context.get("node_outputs"),
        )
        artifact_ref_payloads = _mapping_value(
            raw_context.get("artifact_refs"),
        )
        error_payloads = _json_array(
            raw_context.get("errors", []),
        )
        started_at = _parse_datetime(
            raw_context.get("created_at"),
        )
        resolved_completed_at = completed_at or _parse_datetime(
            raw_context.get("completed_at"),
        )
        resolved_success = _resolve_success(
            success=success,
            errors=error_payloads,
            node_outputs=node_output_payloads,
        )
        resolved_status = status or _status_from_success(
            resolved_success,
        )

        node_records = tuple(
            _node_output_record(
                run_id=run_id,
                workflow_name=resolved_workflow_name,
                execution_id=execution_id,
                node_name=node_name,
                node_payload=node_payload,
            )
            for node_name, node_payload in node_output_payloads.items()
        )
        artifact_records = tuple(
            _artifact_record(
                run_id=run_id,
                workflow_name=resolved_workflow_name,
                execution_id=execution_id,
                artifact_name=artifact_name,
                artifact_payload=artifact_payload,
            )
            for artifact_name, artifact_payload in artifact_ref_payloads.items()
        )
        completed_node_count = sum(
            1 for node_record in node_records if node_record.success is True
        )
        failed_node_count = sum(
            1 for node_record in node_records if node_record.success is False
        )

        run_record = CompletedRunRecord(
            run_id=run_id,
            workflow_name=resolved_workflow_name,
            workflow_id=_optional_string(
                raw_context.get("workflow_id"),
            ),
            execution_id=execution_id,
            runtime_id=_optional_string(
                raw_context.get("runtime_id"),
            ),
            status=resolved_status,
            success=resolved_success,
            context_json=sanitized_context,
            inputs_json=_json_object(
                raw_context.get("workflow_inputs", {}),
            ),
            outputs_json=_json_object(
                raw_context.get("outputs", node_output_payloads),
            ),
            metadata=_run_metadata(
                context_payload=raw_context,
                node_output_count=len(node_records),
                artifact_ref_count=len(artifact_records),
            ),
            errors_json=error_payloads,
            started_at=started_at,
            completed_at=resolved_completed_at,
            duration_seconds=_duration_seconds(
                started_at=started_at,
                completed_at=resolved_completed_at,
                explicit_duration=raw_context.get("duration_seconds"),
            ),
            node_count=len(node_records),
            completed_node_count=completed_node_count,
            failed_node_count=failed_node_count,
            schema_version=RUNTIME_CONTEXT_SCHEMA_VERSION,
            execution_mode=_execution_mode_from_context(raw_context),
        )

        return CompletedRunBundle(
            run=run_record,
            node_outputs=node_records,
            artifacts=artifact_records,
        )

    @staticmethod
    def context_payload_from_bundle(
        bundle: CompletedRunBundle,
    ) -> JsonObject:
        return bundle.run.context_json


JsonSerializableModel = Any


def sanitize_json_value(
    value: Any,
) -> JsonValue:
    return cast(
        JsonValue,
        sanitize_sensitive_value(_json_safe_value(value)),
    )


def _json_safe_value(
    value: Any,
) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Enum):
        return _json_safe_value(
            value.value,
        )

    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe_value(
            asdict(value),
        )

    if hasattr(value, "model_dump"):
        return _json_safe_value(
            _model_dump(value),
        )

    if isinstance(value, MappingABC):
        return {
            str(key): _json_safe_value(
                item,
            )
            for key, item in value.items()
        }

    if isinstance(value, set | frozenset):
        return [
            _json_safe_value(
                item,
            )
            for item in sorted(
                value,
                key=repr,
            )
        ]

    if isinstance(value, bytes | bytearray):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    if isinstance(value, SequenceABC) and not isinstance(
        value, str | bytes | bytearray
    ):
        return [
            _json_safe_value(
                item,
            )
            for item in value
        ]

    return str(
        value,
    )


def _node_output_record(
    *,
    run_id: str,
    workflow_name: str,
    execution_id: str,
    node_name: str,
    node_payload: Any,
) -> CompletedNodeOutputRecord:
    node_mapping = _mapping_value(
        node_payload,
    )
    execution_metadata = _mapping_value(
        node_mapping.get("execution_metadata"),
    )
    success = _optional_bool(
        node_mapping.get("success"),
    )
    skipped = node_mapping.get("skipped") is True
    return CompletedNodeOutputRecord(
        node_output_id=_stable_id(
            "completed_node_output",
            run_id,
            node_name,
        ),
        run_id=run_id,
        workflow_name=workflow_name,
        execution_id=execution_id,
        node_name=node_name,
        node_type=_optional_string(
            execution_metadata.get("node_type"),
        ),
        output_contract=_optional_string(
            node_mapping.get("output_contract"),
        ),
        output_schema_version=_optional_int(
            node_mapping.get("output_schema_version"),
        ),
        status=_node_status(
            success=success,
            skipped=skipped,
        ),
        success=success,
        outputs=_json_object(
            node_mapping.get("outputs", {}),
        ),
        metadata=_node_metadata(
            node_payload=node_mapping,
            execution_metadata=execution_metadata,
        ),
        errors_json=_json_array(
            node_mapping.get("errors", []),
        ),
        started_at=_parse_datetime(
            execution_metadata.get("started_at"),
        ),
        completed_at=_parse_datetime(
            execution_metadata.get("completed_at"),
        ),
        duration_seconds=_optional_float(
            execution_metadata.get("duration_seconds"),
        ),
    )


def _artifact_record(
    *,
    run_id: str,
    workflow_name: str,
    execution_id: str,
    artifact_name: str,
    artifact_payload: Any,
) -> CompletedRunArtifactRecord:
    artifact_mapping = _mapping_value(
        artifact_payload,
    )
    artifact_id = _optional_string(
        artifact_mapping.get("artifact_id"),
    ) or _stable_id(
        "completed_artifact",
        run_id,
        artifact_name,
    )
    return CompletedRunArtifactRecord(
        artifact_id=artifact_id,
        run_id=run_id,
        workflow_name=workflow_name,
        execution_id=execution_id,
        artifact_type=str(
            artifact_mapping.get("kind")
            or artifact_mapping.get("artifact_type")
            or "other",
        ),
        artifact_name=str(
            artifact_mapping.get("name") or artifact_name,
        ),
        artifact_path=str(
            artifact_mapping.get("uri") or artifact_mapping.get("path") or "",
        ),
        mime_type=_optional_string(
            artifact_mapping.get("content_type") or artifact_mapping.get("mime_type"),
        ),
        size_bytes=_optional_int(
            artifact_mapping.get("size_bytes"),
        ),
        metadata=_json_object(
            {
                "artifact_ref": artifact_mapping,
                "metadata": artifact_mapping.get("metadata", {}),
            }
        ),
    )


def _execution_mode_from_context(
    context_payload: Mapping[str, Any],
) -> CompletedRunExecutionMode:
    return coerce_completed_run_execution_mode(
        context_payload.get("execution_mode") or context_payload.get("mode"),
    )


def _run_metadata(
    *,
    context_payload: Mapping[str, Any],
    node_output_count: int,
    artifact_ref_count: int,
) -> JsonObject:
    return _json_object(
        {
            "mode": context_payload.get("mode"),
            "schema_version": context_payload.get("schema_version"),
            "context_version": context_payload.get("context_version"),
            "trace_context": context_payload.get("trace_context"),
            "node_output_count": node_output_count,
            "artifact_ref_count": artifact_ref_count,
        }
    )


def _node_metadata(
    *,
    node_payload: Mapping[str, Any],
    execution_metadata: Mapping[str, Any],
) -> JsonObject:
    return _json_object(
        {
            "execution_metadata": execution_metadata,
            "artifacts": node_payload.get("artifacts", {}),
            "emitted_events": node_payload.get("emitted_events", []),
            "stop_propagation": node_payload.get("stop_propagation"),
            "skipped": node_payload.get("skipped"),
        }
    )


def _json_object(
    value: Any,
) -> JsonObject:
    sanitized = sanitize_json_value(
        value,
    )
    if isinstance(sanitized, MappingABC):
        return cast(
            JsonObject,
            sanitized,
        )

    return {}


def _json_array(
    value: Any,
) -> JsonArray:
    sanitized = sanitize_json_value(
        value,
    )
    if isinstance(sanitized, SequenceABC) and not isinstance(
        sanitized, str | bytes | bytearray
    ):
        return cast(
            JsonArray,
            sanitized,
        )

    return []


def _mapping_value(
    value: Any,
) -> dict[str, Any]:
    if isinstance(value, MappingABC):
        return dict(
            value,
        )

    return {}


def _resolve_success(
    *,
    success: bool | None,
    errors: JsonArray,
    node_outputs: Mapping[str, Any],
) -> bool:
    if success is not None:
        return success

    if errors:
        return False

    return not any(
        isinstance(output, MappingABC)
        and output.get("success") is False
        and output.get("skipped") is not True
        for output in node_outputs.values()
    )


def _status_from_success(
    success: bool,
) -> str:
    if success:
        return "succeeded"

    return "failed"


def _node_status(
    *,
    success: bool | None,
    skipped: bool,
) -> str:
    if skipped:
        return "skipped"

    if success is False:
        return "failed"

    if success is True:
        return "succeeded"

    return "unknown"


def _parse_datetime(
    value: Any,
) -> datetime | None:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
        if parsed.tzinfo is None:
            return parsed.replace(
                tzinfo=UTC,
            )

        return parsed

    return None


def _duration_seconds(
    *,
    started_at: datetime | None,
    completed_at: datetime | None,
    explicit_duration: Any,
) -> float | None:
    explicit = _optional_float(
        explicit_duration,
    )
    if explicit is not None:
        return explicit

    if started_at is None or completed_at is None:
        return None

    return (completed_at - started_at).total_seconds()


def _optional_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value,
    )
    if not text:
        return None

    return text


def _optional_bool(
    value: Any,
) -> bool | None:
    if isinstance(value, bool):
        return value

    return None


def _optional_float(
    value: Any,
) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(
            value,
        )

    return None


def _optional_int(
    value: Any,
) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value

    return None


def _stable_id(
    prefix: str,
    *parts: str,
) -> str:
    digest = hashlib.sha256(
        "\x1f".join(parts).encode("utf-8"),
    ).hexdigest()
    return f"{prefix}_{digest[:32]}"


def _model_dump(
    value: JsonSerializableModel,
) -> Any:
    return value.model_dump(
        mode="json",
    )


def _execution_mode_value(
    value: CompletedRunExecutionMode | str,
) -> str:
    return coerce_completed_run_execution_mode(value).value


class CompletedRunModelSerializer:
    """Serializer between completed-run persistence records and ORM models."""

    @staticmethod
    def run_values(
        record: CompletedRunRecord,
    ) -> dict[str, Any]:
        return {
            "run_id": record.run_id,
            "workflow_name": record.workflow_name,
            "workflow_id": record.workflow_id,
            "execution_id": record.execution_id,
            "runtime_id": record.runtime_id,
            "status": record.status,
            "success": record.success,
            "execution_mode": _execution_mode_value(record.execution_mode),
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "duration_seconds": record.duration_seconds,
            "schema_version": record.schema_version,
            "context_json": dict(record.context_json),
            "inputs_json": dict(record.inputs_json),
            "outputs_json": dict(record.outputs_json),
            "metadata_payload": dict(record.metadata),
            "errors_json": list(record.errors_json),
            "node_count": record.node_count,
            "completed_node_count": record.completed_node_count,
            "failed_node_count": record.failed_node_count,
        }

    @staticmethod
    def node_output_values(
        record: CompletedNodeOutputRecord,
    ) -> dict[str, Any]:
        return {
            "node_output_id": record.node_output_id,
            "run_id": record.run_id,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "node_name": record.node_name,
            "node_type": record.node_type,
            "output_contract": record.output_contract,
            "output_schema_version": record.output_schema_version,
            "status": record.status,
            "success": record.success,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "duration_seconds": record.duration_seconds,
            "outputs_payload": dict(record.outputs),
            "metadata_payload": dict(record.metadata),
            "errors_json": list(record.errors_json),
        }

    @staticmethod
    def artifact_values(
        record: CompletedRunArtifactRecord,
    ) -> dict[str, Any]:
        return {
            "artifact_id": record.artifact_id,
            "run_id": record.run_id,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "artifact_type": record.artifact_type,
            "artifact_name": record.artifact_name,
            "artifact_path": record.artifact_path,
            "mime_type": record.mime_type,
            "size_bytes": record.size_bytes,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def run_from_model(
        model: CompletedWorkflowRunModel,
    ) -> CompletedRunRecord:
        return CompletedRunRecord(
            run_id=model.run_id,
            workflow_name=model.workflow_name,
            workflow_id=model.workflow_id,
            execution_id=model.execution_id,
            runtime_id=model.runtime_id,
            status=model.status,
            success=model.success,
            context_json=cast(
                JsonObject,
                model.context_json,
            ),
            inputs_json=cast(
                JsonObject,
                model.inputs_json,
            ),
            outputs_json=cast(
                JsonObject,
                model.outputs_json,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
            errors_json=cast(
                JsonArray,
                model.errors_json,
            ),
            started_at=model.started_at,
            completed_at=model.completed_at,
            duration_seconds=model.duration_seconds,
            node_count=model.node_count,
            completed_node_count=model.completed_node_count,
            failed_node_count=model.failed_node_count,
            schema_version=model.schema_version,
            execution_mode=model.execution_mode,
        )

    @staticmethod
    def node_output_from_model(
        model: CompletedWorkflowNodeOutputModel,
    ) -> CompletedNodeOutputRecord:
        return CompletedNodeOutputRecord(
            node_output_id=model.node_output_id,
            run_id=model.run_id,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            node_name=model.node_name,
            node_type=model.node_type,
            output_contract=model.output_contract,
            output_schema_version=model.output_schema_version,
            status=model.status,
            success=model.success,
            outputs=cast(
                JsonObject,
                model.outputs_payload,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
            errors_json=cast(
                JsonArray,
                model.errors_json,
            ),
            started_at=model.started_at,
            completed_at=model.completed_at,
            duration_seconds=model.duration_seconds,
        )

    @staticmethod
    def artifact_from_model(
        model: CompletedRunArtifactModel,
    ) -> CompletedRunArtifactRecord:
        return CompletedRunArtifactRecord(
            artifact_id=model.artifact_id,
            run_id=model.run_id,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            artifact_type=model.artifact_type,
            artifact_name=model.artifact_name,
            artifact_path=model.artifact_path,
            mime_type=model.mime_type,
            size_bytes=model.size_bytes,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )
