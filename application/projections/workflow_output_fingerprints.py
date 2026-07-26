from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum

from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunRecord,
)


def calculate_workflow_output_source_fingerprint(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
) -> str:
    """Calculate a deterministic fingerprint for one archived node output."""

    payload = {
        "run_id": run.run_id,
        "workflow_name": run.workflow_name,
        "execution_id": run.execution_id,
        "node_output_id": node_output.node_output_id,
        "node_name": node_output.node_name,
        "output_contract": node_output.output_contract,
        "output_schema_version": node_output.output_schema_version,
        "status": node_output.status,
        "success": node_output.success,
        "outputs": node_output.outputs,
        "metadata": node_output.metadata,
        "errors_json": node_output.errors_json,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


__all__ = ["calculate_workflow_output_source_fingerprint"]
