from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/route_return.py"
SPEC = importlib.util.spec_from_file_location("implement_ticket_route_return", SCRIPT)
assert SPEC and SPEC.loader
ROUTE_RETURN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ROUTE_RETURN
SPEC.loader.exec_module(ROUTE_RETURN)

HASH = "a" * 64
FAILED = "b" * 64
VERIFIER = "c" * 64
TRIAGE = "d" * 64
ROUTE_RESULT = "e" * 64


def _artifact() -> dict[str, object]:
    return {
        "schema": ROUTE_RETURN.SCHEMA,
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH,
        "failed_candidate_state": FAILED,
        "verifier_result_sha256": VERIFIER,
        "finding_id": "F-465-1",
        "triage_artifact_sha256": TRIAGE,
        "route": "$architecture-remediation",
        "route_result_source": "https://github.com/sponge-b0b/Polaris/issues/465",
        "route_result_sha256": ROUTE_RESULT,
        "resolution": "EXISTING_AUTHORITY_IMPLEMENTATION_RETURN",
        "returned_owner": "$implement-ticket",
        "contract_changed": False,
        "prior_post_route_attempts": 0,
        "evidence_sources": ["architecture-result", "verifier-triage"],
        "basis": ["architecture-result", "verifier-triage"],
        "status": "READY",
        "result_verifier_sha256": None,
    }


def test_existing_authority_return_creates_one_new_bounded_epoch() -> None:
    receipt = ROUTE_RETURN.validate_route_return(_artifact())
    assert receipt.status == "READY"
    assert receipt.prior_post_route_attempts == 0


def test_second_post_route_attempt_is_rejected() -> None:
    value = _artifact()
    value["prior_post_route_attempts"] = 1
    with pytest.raises(
        ROUTE_RETURN.RouteReturnError,
        match="only one post-route corrective attempt",
    ):
        ROUTE_RETURN.validate_route_return(value)


def test_changed_contract_cannot_use_route_return_epoch() -> None:
    value = _artifact()
    value["contract_changed"] = True
    with pytest.raises(
        ROUTE_RETURN.RouteReturnError,
        match="changed contract requires normal contract/feasibility reconstruction",
    ):
        ROUTE_RETURN.validate_route_return(value)


def test_route_must_return_to_implement_ticket() -> None:
    value = _artifact()
    value["returned_owner"] = "$wayfinder"
    with pytest.raises(
        ROUTE_RETURN.RouteReturnError,
        match="returned owner must be \\$implement-ticket",
    ):
        ROUTE_RETURN.validate_route_return(value)


def test_consumed_record_requires_fresh_verifier_result() -> None:
    value = _artifact()
    value["status"] = "CONSUMED"
    with pytest.raises(
        ROUTE_RETURN.RouteReturnError,
        match="invalid result verifier SHA-256",
    ):
        ROUTE_RETURN.validate_route_return(value)

    value["result_verifier_sha256"] = "f" * 64
    assert ROUTE_RETURN.validate_route_return(value).status == "CONSUMED"


def test_route_return_transition_is_monotonic() -> None:
    ready = _artifact()
    active = dict(ready)
    active["status"] = "IN_PROGRESS"
    assert ROUTE_RETURN.validate_transition(ready, active).status == "IN_PROGRESS"

    consumed = dict(active)
    consumed["status"] = "CONSUMED"
    consumed["result_verifier_sha256"] = "f" * 64
    assert ROUTE_RETURN.validate_transition(active, consumed).status == "CONSUMED"

    with pytest.raises(
        ROUTE_RETURN.RouteReturnError,
        match="status must move READY -> IN_PROGRESS -> CONSUMED",
    ):
        ROUTE_RETURN.validate_transition(consumed, ready)


def test_route_return_transition_cannot_change_identity() -> None:
    ready = _artifact()
    active = dict(ready)
    active["status"] = "IN_PROGRESS"
    active["route_result_sha256"] = "f" * 64
    with pytest.raises(
        ROUTE_RETURN.RouteReturnError,
        match="immutable field changed: route_result_sha256",
    ):
        ROUTE_RETURN.validate_transition(ready, active)


def test_control_plane_wires_post_route_return_and_machine_validator() -> None:
    control = (
        ROOT / ".agents/skills/implement-ticket/CONTROL_PLANE.md"
    ).read_text(encoding="utf-8")
    skill = (ROOT / ".agents/skills/implement-ticket/SKILL.md").read_text(
        encoding="utf-8"
    )
    gate = (
        ROOT / ".agents/skills/implement-ticket/scripts/attention_gate.py"
    ).read_text(encoding="utf-8")

    assert "POST_ROUTE_RETURN.md" in control
    assert "POST_ROUTE_RETURN.md" in skill
    assert "candidate_guard.py" in control
    assert "--route-return" in gate
    assert "validate_route_return" in gate
