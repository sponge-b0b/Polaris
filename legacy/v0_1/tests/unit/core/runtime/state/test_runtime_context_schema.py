from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import (
    RUNTIME_CONTEXT_SCHEMA_VERSION,
    RuntimeContext,
    UnsupportedRuntimeContextSchemaError,
)


def test_runtime_context_round_trips_canonical_schema() -> None:
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        mode="simulation",
        workflow_inputs={"symbol": "SPY", "nested": {"days": 30}},
    ).add_node_output(
        "technical",
        {"success": True, "outputs": {"score": 0.12345678901234568}},
    )

    payload = context.to_dict()
    restored = RuntimeContext.from_dict(payload)

    assert payload["schema_version"] == RUNTIME_CONTEXT_SCHEMA_VERSION
    assert "state" not in payload
    assert "state_version" not in payload
    assert restored == context
    assert restored.context_version == 1
    assert restored.workflow_inputs == {"symbol": "SPY", "nested": {"days": 30}}


@pytest.mark.parametrize("schema_version", [None, 1, 3, "2"])
def test_runtime_context_rejects_unsupported_persisted_schema(
    schema_version: object,
) -> None:
    payload: dict[str, object] = {
        "runtime_id": "runtime-1",
        "workflow_id": "morning_report",
        "execution_id": "execution-1",
    }
    if schema_version is not None:
        payload["schema_version"] = schema_version

    with pytest.raises(
        UnsupportedRuntimeContextSchemaError,
        match="Unsupported RuntimeContext schema version",
    ):
        RuntimeContext.from_dict(payload)
