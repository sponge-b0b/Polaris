from __future__ import annotations

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

        async def run_workflow(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {
                "success": True,
                "workflow_name": kwargs["workflow_name"],
                "execution_id": kwargs["execution_id"],
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

    async def fake_audit_capability_for_run(**_: object) -> None:
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
