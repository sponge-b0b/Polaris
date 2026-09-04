from __future__ import annotations

from copy import deepcopy

from core.runtime.checkpoints.runtime_checkpoint import RuntimeCheckpoint
from core.runtime.state.runtime_context import RuntimeContext
from core.security.sensitive_data import REDACTED_VALUE


def test_runtime_checkpoint_redacts_sensitive_data_without_mutating_context() -> None:
    database_url = "".join(
        (
            "postgresql+asyncpg://polaris:",
            "db-password",
            "@localhost/polaris",
        )
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="workflow-1",
        execution_id="execution-1",
        workflow_inputs={"api_key": "input-secret"},
        node_outputs={
            "provider": {
                "outputs": {"authorization": "Bearer node-secret"},
                "errors": [{"message": "password=node-password"}],
            }
        },
        errors=[{"message": f"connection failed for {database_url}"}],
    )
    original = context.to_dict()
    metadata = {"refresh_token": "metadata-secret"}
    original_metadata = deepcopy(metadata)
    checkpoint = RuntimeCheckpoint.from_context(
        checkpoint_id="checkpoint-1",
        context=context,
        metadata=metadata,
    )

    payload = checkpoint.to_dict()

    assert context.to_dict() == original
    assert metadata == original_metadata
    assert payload["metadata"] == {"refresh_token": REDACTED_VALUE}
    runtime_context = payload["runtime_context"]
    assert isinstance(runtime_context, dict)
    assert runtime_context["workflow_inputs"] == {"api_key": REDACTED_VALUE}
    assert runtime_context["node_outputs"]["provider"]["outputs"] == {
        "authorization": REDACTED_VALUE
    }
    assert "node-password" not in str(runtime_context["node_outputs"])
    assert "db-password" not in str(runtime_context["errors"])

    restored = RuntimeCheckpoint.from_dict(payload)

    assert restored.runtime_context is not None
    assert restored.runtime_context.workflow_inputs["api_key"] == REDACTED_VALUE
