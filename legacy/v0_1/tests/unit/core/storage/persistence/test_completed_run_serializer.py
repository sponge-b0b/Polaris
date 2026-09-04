from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from pydantic import BaseModel

from core.security.sensitive_data import REDACTED_VALUE
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.serializers.completed_run_serializer import (
    CompletedRunModelSerializer,
    CompletedRunPersistenceSerializer,
    sanitize_json_value,
)


@dataclass(frozen=True, slots=True)
class ExampleDataclass:
    value: float


class ExampleModel(BaseModel):
    value: float


def _context_payload() -> dict[str, object]:
    return {
        "schema_version": 2,
        "runtime_id": "runtime-1",
        "workflow_id": "morning_report",
        "execution_id": "exec-1",
        "mode": "live",
        "created_at": "2026-06-21T12:00:00+00:00",
        "simulation_time": None,
        "context_version": 7,
        "workflow_inputs": {
            "symbol": "SPY",
            "request_metadata": {
                "unserializable": ExampleDataclass(0.12345678901234568),
            },
        },
        "artifact_refs": {
            "technical_report": {
                "artifact_id": "artifact-1",
                "kind": "markdown",
                "uri": "reports/technical.md",
                "name": "technical.md",
                "content_type": "text/markdown",
                "size_bytes": 2048,
                "metadata": {"confidence": 0.9876543210987654},
            }
        },
        "node_outputs": {
            "technical_analysis": {
                "success": True,
                "skipped": False,
                "stop_propagation": False,
                "outputs": {"technical_score": 0.12345678901234568},
                "artifacts": {
                    "technical_report": {
                        "artifact_id": "artifact-1",
                        "uri": "reports/technical.md",
                    }
                },
                "emitted_events": [],
                "errors": [],
                "output_contract": "polaris.market.technical_analysis",
                "output_schema_version": 1,
                "execution_metadata": {
                    "node_name": "technical_analysis",
                    "node_type": "runtime",
                    "started_at": "2026-06-21T12:00:01+00:00",
                    "completed_at": "2026-06-21T12:00:03+00:00",
                    "duration_seconds": 2.1234567890123457,
                },
            },
            "risk_analysis": {
                "success": False,
                "skipped": False,
                "outputs": {},
                "errors": [{"message": "risk failed"}],
                "execution_metadata": {
                    "node_name": "risk_analysis",
                    "node_type": "runtime",
                },
            },
        },
        "errors": [{"message": "risk failed"}],
        "trace_context": {"trace_id": "trace-1"},
    }


def test_serializer_builds_completed_run_bundle_without_mutating_source() -> None:
    payload = _context_payload()
    original = deepcopy(payload)

    bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
        payload,
        completed_at=datetime(2026, 6, 21, 12, 5, tzinfo=UTC),
    )

    assert payload == original
    assert bundle.run.workflow_name == "morning_report"
    assert bundle.run.workflow_id == "morning_report"
    assert bundle.run.execution_id == "exec-1"
    assert bundle.run.runtime_id == "runtime-1"
    assert bundle.run.status == "failed"
    assert bundle.run.success is False
    assert bundle.run.node_count == 2
    assert bundle.run.completed_node_count == 1
    assert bundle.run.failed_node_count == 1
    assert len(bundle.node_outputs) == 2
    assert len(bundle.artifacts) == 1
    assert bundle.run.schema_version == 2
    assert bundle.run.inputs_json["symbol"] == "SPY"
    assert bundle.run.metadata["schema_version"] == 2
    assert bundle.run.metadata["context_version"] == 7


def test_serializer_preserves_numeric_precision_in_payloads() -> None:
    bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
        _context_payload(),
        success=True,
        status="succeeded",
        completed_at=datetime(2026, 6, 21, 12, 5, tzinfo=UTC),
    )

    technical_node = next(
        node for node in bundle.node_outputs if node.node_name == "technical_analysis"
    )
    artifact = bundle.artifacts[0]

    assert bundle.run.context_json["node_outputs"] == _context_payload()["node_outputs"]
    assert technical_node.output_contract == "polaris.market.technical_analysis"
    assert technical_node.output_schema_version == 1
    assert technical_node.outputs["technical_score"] == 0.12345678901234568
    assert technical_node.duration_seconds == 2.1234567890123457
    assert artifact.metadata["metadata"] == {"confidence": 0.9876543210987654}


def test_serializer_loads_legacy_node_output_without_contract_identity() -> None:
    payload = _context_payload()
    node_outputs = cast(dict[str, object], payload["node_outputs"])
    technical = cast(dict[str, object], node_outputs["technical_analysis"])
    technical.pop("output_contract", None)
    technical.pop("output_schema_version", None)

    bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
        payload,
        completed_at=datetime(2026, 6, 21, 12, 5, tzinfo=UTC),
    )

    technical_node = next(
        node for node in bundle.node_outputs if node.node_name == "technical_analysis"
    )

    assert technical_node.output_contract is None
    assert technical_node.output_schema_version is None


def test_serializer_sanitizes_json_boundary_values() -> None:
    sanitized_value = sanitize_json_value(
        {
            "dataclass": ExampleDataclass(0.12345678901234568),
            "model": ExampleModel(value=0.8765432109876543),
            "set": {"b", "a"},
            "bytes": b"hello",
            "object": object(),
        }
    )

    sanitized = cast(
        Mapping[str, object],
        sanitized_value,
    )

    assert sanitized["dataclass"] == {"value": 0.12345678901234568}
    assert sanitized["model"] == {"value": 0.8765432109876543}
    assert sanitized["set"] == ["a", "b"]
    assert sanitized["bytes"] == "hello"
    assert isinstance(sanitized["object"], str)


def test_serializer_returns_context_payload_from_bundle() -> None:
    payload = _context_payload()
    bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
        payload,
        completed_at=datetime(2026, 6, 21, 12, 5, tzinfo=UTC),
    )

    assert CompletedRunPersistenceSerializer.context_payload_from_bundle(bundle) == (
        bundle.run.context_json
    )


def test_serializer_redacts_secrets_from_all_persisted_run_boundaries() -> None:
    payload = _context_payload()
    database_url = "".join(
        (
            "postgresql+asyncpg://polaris:",
            "db-secret",
            "@localhost:5432/polaris",
        )
    )
    payload["workflow_inputs"] = {
        "api_key": "input-secret",
        "database_url": database_url,
    }
    node_outputs = cast(dict[str, object], payload["node_outputs"])
    technical = cast(dict[str, object], node_outputs["technical_analysis"])
    technical["outputs"] = {
        "authorization": "Bearer output-secret",
        "safe": "visible",
    }
    technical["errors"] = [{"message": "password=node-secret"}]
    payload["errors"] = [{"message": "token=run-secret"}]
    original = deepcopy(payload)

    bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
        payload,
        completed_at=datetime(2026, 6, 21, 12, 5, tzinfo=UTC),
    )

    assert payload == original
    assert bundle.run.inputs_json["api_key"] == REDACTED_VALUE
    assert "db-secret" not in str(bundle.run.inputs_json)
    assert "run-secret" not in str(bundle.run.errors_json)
    assert "input-secret" not in str(bundle.run.context_json)
    technical_record = next(
        node for node in bundle.node_outputs if node.node_name == "technical_analysis"
    )
    assert technical_record.outputs == {
        "authorization": REDACTED_VALUE,
        "safe": "visible",
    }
    assert "node-secret" not in str(technical_record.errors_json)


def test_serializer_promotes_runtime_mode_to_first_class_execution_mode() -> None:
    payload = _context_payload()
    payload["mode"] = "backtest"

    bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
        payload,
        completed_at=datetime(2026, 6, 21, 12, 5, tzinfo=UTC),
    )

    assert bundle.run.execution_mode is CompletedRunExecutionMode.BACKTEST
    assert bundle.run.metadata["mode"] == "backtest"
    assert CompletedRunModelSerializer.run_values(bundle.run)["execution_mode"] == (
        "backtest"
    )


def test_serializer_prefers_first_class_execution_mode_over_runtime_mode() -> None:
    payload = _context_payload()
    payload["mode"] = "live"
    payload["execution_mode"] = "simulated"

    bundle = CompletedRunPersistenceSerializer.bundle_from_context_payload(
        payload,
        completed_at=datetime(2026, 6, 21, 12, 5, tzinfo=UTC),
    )

    assert bundle.run.execution_mode is CompletedRunExecutionMode.SIMULATED
