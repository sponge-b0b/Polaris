from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

import pytest

from application.governance.governed_workflow_execution import (
    GovernedWorkflowExecutionService,
)


@pytest.mark.asyncio
async def test_governed_workflow_execution_reports_platform_correlation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    observed_started_ids: list[str] = []

    class FakeWorkflowFacade:
        policy_engine = object()
        governance_engine = None

        async def run_workflow(
            self,
            *,
            workflow_name: str,
            execution_id: str | None = None,
            mode: str = "live",
            workflow_inputs: Mapping[str, Any] | None = None,
            simulation_time: datetime | None = None,
            archive_on_completion: bool = True,
            checkpoint_on_completion: bool = False,
            metadata: dict[str, Any] | None = None,
            execution_audit_capability: object | None = None,
        ) -> dict[str, Any]:
            captured.update(
                {
                    "workflow_name": workflow_name,
                    "execution_id": execution_id,
                    "mode": mode,
                    "workflow_inputs": workflow_inputs,
                    "simulation_time": simulation_time,
                    "archive_on_completion": archive_on_completion,
                    "checkpoint_on_completion": checkpoint_on_completion,
                    "metadata": metadata,
                    "execution_audit_capability": execution_audit_capability,
                }
            )
            return {
                "success": True,
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "execution_result": {
                    "success": True,
                    "final_context": {},
                },
            }

    service = GovernedWorkflowExecutionService(
        workflow_facade=cast(Any, FakeWorkflowFacade()),
        automated_decision_audit_service=cast(Any, object()),
        decision_evidence_packet_persistence_service=cast(Any, object()),
    )

    async def fake_audit_capability_for_run(
        *,
        workflow_name: str,
        execution_id: str | None,
        prepare_evidence: bool = True,
    ) -> None:
        assert workflow_name == "morning_report"
        assert execution_id is not None
        assert prepare_evidence is True
        return None

    monkeypatch.setattr(
        service,
        "_audit_capability_for_run",
        fake_audit_capability_for_run,
    )

    result = cast(
        dict[str, Any],
        await service.run_workflow(
            workflow_name="morning_report",
            execution_started_handler=observed_started_ids.append,
        ),
    )

    assert result["success"] is True
    assert observed_started_ids == [captured["execution_id"]]
    assert captured["execution_id"].startswith("governed-")
