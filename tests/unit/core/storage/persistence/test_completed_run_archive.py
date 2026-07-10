from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from datetime import UTC
from datetime import datetime

import pytest

from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunArchive
from core.storage.persistence.completed_run_archive import CompletedRunArtifactRecord
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import JsonObject
from core.storage.persistence.completed_run_archive import (
    coerce_completed_run_execution_mode,
)


def _completed_at() -> datetime:
    return datetime(2026, 6, 21, 12, 0, 0, tzinfo=UTC)


def _run_record() -> CompletedRunRecord:
    precision_sensitive_payload: JsonObject = {
        "technical_score": 0.12345678901234568,
        "market_cap": 9123456789012345,
        "nested": {
            "breadth_score": -0.9876543210987654,
        },
    }
    return CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="workflow-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json=precision_sensitive_payload,
        inputs_json={"symbols": ["SPY", "AAPL"]},
        outputs_json={"report": "full report text"},
        metadata={"source": "runtime"},
        errors_json=[],
        started_at=_completed_at(),
        completed_at=_completed_at(),
        duration_seconds=0.12345678901234568,
        node_count=2,
        completed_node_count=2,
        failed_node_count=0,
    )


def _node_output_record() -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="technical_analysis",
        node_type="RuntimeNode",
        output_contract=None,
        output_schema_version=None,
        status="succeeded",
        success=True,
        outputs={"signal": {"confidence": 0.8765432109876543}},
        metadata={"attempt": 1},
        errors_json=[],
        started_at=_completed_at(),
        completed_at=_completed_at(),
        duration_seconds=1.2345678901234567,
    )


def _artifact_record() -> CompletedRunArtifactRecord:
    return CompletedRunArtifactRecord(
        artifact_id="artifact-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        artifact_type="markdown_report",
        artifact_name="morning_report.md",
        artifact_path="reports/morning_report.md",
        mime_type="text/markdown",
        size_bytes=4096,
        metadata={"renderer": "markdown"},
    )


def test_completed_run_contracts_are_frozen_and_slotted() -> None:
    record = _run_record()

    assert not hasattr(record, "__dict__")
    with pytest.raises(FrozenInstanceError):
        record.status = "failed"  # type: ignore[misc]


def test_completed_run_bundle_preserves_typed_child_records() -> None:
    run = _run_record()
    node_output = _node_output_record()
    artifact = _artifact_record()

    bundle = CompletedRunBundle(
        run=run,
        node_outputs=(node_output,),
        artifacts=(artifact,),
    )

    assert bundle.run is run
    assert bundle.node_outputs == (node_output,)
    assert bundle.artifacts == (artifact,)
    assert not hasattr(bundle, "__dict__")
    with pytest.raises(FrozenInstanceError):
        bundle.run = _run_record()  # type: ignore[misc]


def test_completed_run_payloads_retain_full_numeric_precision() -> None:
    record = _run_record()
    node_output = _node_output_record()

    assert record.context_json["technical_score"] == 0.12345678901234568
    assert record.context_json["market_cap"] == 9123456789012345
    assert record.duration_seconds == 0.12345678901234568
    assert node_output.outputs["signal"] == {"confidence": 0.8765432109876543}
    assert node_output.duration_seconds == 1.2345678901234567


def test_completed_run_archive_contract_is_async_and_typed() -> None:
    assert inspect.iscoroutinefunction(CompletedRunArchive.archive_run)
    assert inspect.iscoroutinefunction(CompletedRunArchive.load_archived_run)
    assert inspect.iscoroutinefunction(CompletedRunArchive.list_archived_runs)
    assert inspect.iscoroutinefunction(CompletedRunArchive.delete_archived_run)
    assert inspect.iscoroutinefunction(CompletedRunArchive.cleanup_archived_runs)

    archive_annotations = CompletedRunArchive.archive_run.__annotations__
    load_annotations = CompletedRunArchive.load_archived_run.__annotations__

    assert archive_annotations["bundle"] == "CompletedRunBundle"
    assert load_annotations["return"] == "CompletedRunBundle | None"


def test_completed_run_execution_mode_is_first_class_and_normalized() -> None:
    record = CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="workflow-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={},
        outputs_json={},
        metadata={},
        errors_json=[],
        started_at=None,
        completed_at=None,
        duration_seconds=None,
        node_count=0,
        completed_node_count=0,
        failed_node_count=0,
        execution_mode="backtest",
    )

    assert record.execution_mode is CompletedRunExecutionMode.BACKTEST
    assert (
        coerce_completed_run_execution_mode("live") is CompletedRunExecutionMode.NORMAL
    )

    with pytest.raises(ValueError):
        coerce_completed_run_execution_mode("paper")
