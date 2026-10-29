from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/bounded_execution.py"
SPEC = importlib.util.spec_from_file_location(
    "implement_ticket_bounded_execution", SCRIPT
)
assert SPEC and SPEC.loader
BOUNDED = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BOUNDED
SPEC.loader.exec_module(BOUNDED)

HASH = "a" * 64
STATE = "b" * 64


def _concerns() -> dict[str, object]:
    return {
        "schema": BOUNDED.CONCERN_SCHEMA,
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH,
        "candidate_state": STATE,
        "evidence_sources": ["candidate-test", "review-rf7"],
        "concerns": [],
    }


def _triage() -> dict[str, object]:
    return {
        "schema": BOUNDED.TRIAGE_SCHEMA,
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH,
        "failed_candidate_state": STATE,
        "verifier_result_sha256": "c" * 64,
        "finding_id": "F-465-1",
        "evidence_sources": ["verifier-fail"],
        "classification": "IMPLEMENTATION_LOCAL",
        "prior_local_attempts": 0,
        "boundary_changes": {
            "new_runtime_dependency": False,
            "new_deployment_or_config_requirement": False,
            "new_retention_or_recovery_lifecycle": False,
            "new_operational_responsibility": False,
            "new_material_semantic_choice": False,
            "new_planning_or_ownership_change": False,
        },
        "basis": ["verifier-fail"],
        "route": None,
    }


def _continuation() -> dict[str, object]:
    return {
        "schema": BOUNDED.CONTINUATION_SCHEMA,
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH,
        "branch": "spec-358",
        "execution_anchor": "d" * 40,
        "candidate_state": STATE,
        "phase": "post-verifier-triage",
        "completed": ["feasibility", "verifier-fail"],
        "pending": ["architecture-route"],
        "next_action": "persist exact architecture route",
        "reason": "context-compaction",
        "verifier_state": {
            "attempt": 1,
            "result": "FAIL",
            "result_sha256": "c" * 64,
        },
        "stale_evidence": ["attention-pre-closure"],
    }


def test_contract_touching_concern_cannot_be_deferred() -> None:
    value = _concerns()
    value["concerns"] = [
        {
            "concern_id": "C-1",
            "summary": "owner commit can outlive publication timestamp",
            "assigned_cells": ["OBL-010"],
            "guardrails": [],
            "falsifiers": ["RF-7"],
            "disposition": "DEFERRED_OUTSIDE_CONTRACT",
            "basis": ["review-rf7"],
            "disproof_evidence": [],
        }
    ]

    with pytest.raises(
        BOUNDED.BoundedExecutionError,
        match="touches assigned cells/falsifiers/guardrails and cannot be deferred",
    ):
        BOUNDED.validate_concerns(value)


def test_contract_touching_concern_requires_positive_disproof() -> None:
    value = _concerns()
    value["concerns"] = [
        {
            "concern_id": "C-1",
            "summary": "owner commit can outlive publication timestamp",
            "assigned_cells": ["OBL-010"],
            "guardrails": [],
            "falsifiers": ["RF-7"],
            "disposition": "DISPROVEN",
            "basis": ["review-rf7"],
            "disproof_evidence": [],
        }
    ]

    with pytest.raises(
        BOUNDED.BoundedExecutionError,
        match="requires positive disproof_evidence",
    ):
        BOUNDED.validate_concerns(value)

    value["concerns"][0]["disproof_evidence"] = ["candidate-test"]
    assert BOUNDED.validate_concerns(value).outcome == "PASS"


def test_blocking_concern_prevents_preclosure_pass() -> None:
    value = _concerns()
    value["concerns"] = [
        {
            "concern_id": "C-1",
            "summary": "crash window remains unproved",
            "assigned_cells": ["OBL-010"],
            "guardrails": [],
            "falsifiers": ["RF-7"],
            "disposition": "BLOCKING",
            "basis": ["review-rf7"],
            "disproof_evidence": [],
        }
    ]
    receipt = BOUNDED.validate_concerns(value)
    assert receipt.outcome == "BLOCKED"
    assert receipt.blocking_count == 1


def test_verifier_local_retry_is_single_and_boundary_free() -> None:
    value = _triage()
    receipt = BOUNDED.validate_triage(value)
    assert receipt.classification == "IMPLEMENTATION_LOCAL"

    value["prior_local_attempts"] = 1
    with pytest.raises(
        BOUNDED.BoundedExecutionError,
        match="only one local corrective attempt",
    ):
        BOUNDED.validate_triage(value)


def test_verifier_local_retry_rejects_new_runtime_or_operational_boundary() -> None:
    value = _triage()
    value["boundary_changes"]["new_deployment_or_config_requirement"] = True

    with pytest.raises(
        BOUNDED.BoundedExecutionError,
        match=(
            "cannot introduce material runtime/operational/semantic/planning "
            "boundaries"
        ),
    ):
        BOUNDED.validate_triage(value)


def test_verifier_route_requires_material_boundary_and_owner() -> None:
    value = _triage()
    value["classification"] = "ROUTE_REQUIRED"
    value["boundary_changes"]["new_retention_or_recovery_lifecycle"] = True
    value["route"] = "$architecture-remediation"
    assert BOUNDED.validate_triage(value).classification == "ROUTE_REQUIRED"


def test_continuation_distinguishes_checkpoint_from_actual_execution_boundary() -> None:
    value = _continuation()
    assert BOUNDED.validate_continuation(value).durable_continuation is False

    value["reason"] = "stage-checkpoint"
    assert BOUNDED.validate_continuation(value).durable_continuation is False

    value["reason"] = "usage-boundary"
    assert BOUNDED.validate_continuation(value).durable_continuation is True

    value["reason"] = "tool-boundary"
    assert BOUNDED.validate_continuation(value).durable_continuation is True


def test_candidate_created_compaction_with_verification_pending_must_continue() -> None:
    value = _continuation()
    value["phase"] = "candidate-created"
    value["completed"] = ["candidate-created", "feasibility", "post-route-reentry"]
    value["pending"] = [
        "architecture-check",
        "duplicate-code-check",
        "independent-closure-verification",
        "pre-closure-attention",
        "technical-checks",
    ]
    value["next_action"] = "run final verification stages"
    value["reason"] = "context-compaction"
    value["verifier_state"] = {
        "attempt": 0,
        "result": "none",
        "result_sha256": None,
    }
    value["stale_evidence"] = []

    receipt = BOUNDED.validate_continuation(value)
    assert receipt.phase == "candidate-created"
    assert receipt.reason == "context-compaction"
    assert receipt.durable_continuation is False


def test_policy_requires_all_three_bounded_execution_invariants() -> None:
    policy = (ROOT / ".agents/skills/implement-ticket/BOUNDED_EXECUTION.md").read_text(
        encoding="utf-8"
    )
    skill = (ROOT / ".agents/skills/implement-ticket/SKILL.md").read_text(
        encoding="utf-8"
    )
    gate_path = ROOT / ".agents/skills/implement-ticket/scripts/attention_gate.py"
    gate = gate_path.read_text(encoding="utf-8")

    assert "Pre-closure concern admission is fail-closed" in policy
    assert "Verifier FAIL requires triage before mutation" in policy
    assert "Mandatory stage checkpoints" in policy
    assert "Durable Continuation" in policy
    assert "actual execution boundary" in policy
    assert "Context compaction is a checkpoint trigger, not a lifecycle transition" in policy
    assert "BOUNDED_EXECUTION.md" in skill
    assert "--concerns" in gate
    assert "validate_concerns" in gate
