from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
CONTROL_PATH = ROOT / ".agents/skills/implement-ticket/scripts/post_route_control.py"
RETURN_PATH = ROOT / ".agents/skills/implement-ticket/scripts/route_return.py"

RETURN_SPEC = importlib.util.spec_from_file_location("post_route_return_convergence", RETURN_PATH)
assert RETURN_SPEC and RETURN_SPEC.loader
RETURN = importlib.util.module_from_spec(RETURN_SPEC)
sys.modules[RETURN_SPEC.name] = RETURN
RETURN_SPEC.loader.exec_module(RETURN)

CONTROL_SPEC = importlib.util.spec_from_file_location("post_route_control_convergence", CONTROL_PATH)
assert CONTROL_SPEC and CONTROL_SPEC.loader
CONTROL = importlib.util.module_from_spec(CONTROL_SPEC)
sys.modules[CONTROL_SPEC.name] = CONTROL
CONTROL_SPEC.loader.exec_module(CONTROL)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64
HEAD = "1" * 40


def _route(status: str = "READY") -> dict[str, object]:
    return {
        "schema": "polaris.implement-route-return/v1",
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH_A,
        "failed_candidate_state": HASH_B,
        "verifier_result_sha256": HASH_C,
        "finding_id": "F-465-1",
        "triage_artifact_sha256": HASH_D,
        "route": "$architecture-remediation",
        "route_result_source": "https://example.test/route-result",
        "route_result_sha256": "e" * 64,
        "resolution": "EXISTING_AUTHORITY_IMPLEMENTATION_RETURN",
        "returned_owner": "$implement-ticket",
        "contract_changed": False,
        "prior_post_route_attempts": 0,
        "evidence_sources": [
            "https://example.test/triage",
            "https://example.test/route-result",
        ],
        "basis": ["https://example.test/route-result"],
        "status": status,
        "result_verifier_sha256": None,
    }


def _feasibility(*, outcome: str = "PASS", new_finding: bool = False) -> dict[str, object]:
    evidence = [
        "docs/current/platform-architecture-0.2.0.md",
        "https://example.test/route-result",
        "https://example.test/triage",
        "src/polaris/infrastructure/persistence/postgresql/investment_intelligence.py",
    ]
    prior: list[dict[str, object]] = [
        {
            "finding_id": "F-465-1",
            "disposition": "OWNED_BY_CURRENT_TICKET",
            "basis": ["https://example.test/route-result"],
        }
    ]
    blocked = None
    seams: list[dict[str, object]] = [
        {
            "seam_id": "owner-history",
            "required_cells": ["OBL-007"],
            "ownership_status": "OWNED_BY_CURRENT_TICKET",
            "authority_status": "FIXED_IMPLEMENTATION_LOCAL",
            "authority_basis": ["docs/current/platform-architecture-0.2.0.md"],
            "realization_basis": [
                "src/polaris/infrastructure/persistence/postgresql/investment_intelligence.py"
            ],
        }
    ]
    if outcome == "BLOCKED":
        assert new_finding
        evidence.append("https://example.test/new-evidence")
        evidence.sort()
        prior.append(
            {
                "finding_id": "F-465-2",
                "disposition": "ROUTING_OR_PLANNING_GAP",
                "basis": ["https://example.test/new-evidence"],
            }
        )
        blocked = {
            "classification": "planning-cell-gap",
            "seam_id": "owner-history",
            "required_cells": ["OBL-007"],
            "durable_owner": "new planning owner required",
            "reason": "new materially distinct fact",
            "route": "$to-specs",
        }
    return {
        "schema": "polaris.implement-feasibility/v1",
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH_A,
        "branch": "spec-358",
        "execution_head": HEAD,
        "evidence_sources": evidence,
        "seams": seams,
        "prior_findings": prior,
        "outcome": outcome,
        "blocked": blocked,
    }


def _context(feasibility: dict[str, object], route: dict[str, object]) -> dict[str, object]:
    evidence = sorted(
        set(feasibility["evidence_sources"])
        | set(route["evidence_sources"])
        | {str(route["route_result_source"])}
    )
    return {
        "schema": "polaris.implement-post-route-context/v1",
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH_A,
        "finding_id": "F-465-1",
        "verifier_result_sha256": HASH_C,
        "triage_artifact_sha256": HASH_D,
        "route_result_sha256": "e" * 64,
        "route_return_sha256": CONTROL.sha256_canonical_json(route),
        "feasibility_sha256": CONTROL.sha256_canonical_json(feasibility),
        "returned_disposition": "OWNED_BY_CURRENT_TICKET",
        "adjudicated_evidence_sources": evidence,
    }


def test_context_requires_returned_finding_to_stay_implementation_owned() -> None:
    feasibility = _feasibility()
    route = _route()
    context = _context(feasibility, route)
    receipt = CONTROL.validate_context(context, feasibility, route)
    assert receipt.finding_id == "F-465-1"

    feasibility["prior_findings"] = []
    context["feasibility_sha256"] = CONTROL.sha256_canonical_json(feasibility)
    with pytest.raises(CONTROL.PostRouteControlError, match="returned finding missing"):
        CONTROL.validate_context(context, feasibility, route)


def test_same_returned_finding_cannot_be_relabeled_for_reroute() -> None:
    pass_feasibility = _feasibility()
    route = _route()
    context = _context(pass_feasibility, route)
    blocked = _feasibility(outcome="BLOCKED", new_finding=True)
    reroute = {
        "schema": "polaris.implement-post-route-reroute/v1",
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH_A,
        "context_sha256": CONTROL.sha256_canonical_json(context),
        "returned_finding_id": "F-465-1",
        "new_finding_id": "F-465-1",
        "classification": "planning-cell-gap",
        "new_evidence_sources": ["https://example.test/new-evidence"],
        "new_fact": "new fact",
        "first_observed_after_context": True,
        "blocked_feasibility_sha256": CONTROL.sha256_canonical_json(blocked),
        "route": "$to-specs",
    }
    with pytest.raises(CONTROL.PostRouteControlError, match="may not be relabeled"):
        CONTROL.validate_reroute(reroute, context, blocked)


def test_materially_distinct_new_finding_can_reroute_with_new_evidence() -> None:
    pass_feasibility = _feasibility()
    route = _route()
    context = _context(pass_feasibility, route)
    blocked = _feasibility(outcome="BLOCKED", new_finding=True)
    reroute = {
        "schema": "polaris.implement-post-route-reroute/v1",
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH_A,
        "context_sha256": CONTROL.sha256_canonical_json(context),
        "returned_finding_id": "F-465-1",
        "new_finding_id": "F-465-2",
        "classification": "planning-cell-gap",
        "new_evidence_sources": ["https://example.test/new-evidence"],
        "new_fact": "new fact first observed after re-entry context",
        "first_observed_after_context": True,
        "blocked_feasibility_sha256": CONTROL.sha256_canonical_json(blocked),
        "route": "$to-specs",
    }
    receipt = CONTROL.validate_reroute(reroute, context, blocked)
    assert receipt.new_finding_id == "F-465-2"


def _terminal(route: dict[str, object], *, mutation_started: bool) -> dict[str, object]:
    return {
        "schema": "polaris.implement-route-terminal/v1",
        "ticket": 465,
        "contract_schema": "polaris.review-remediation-contract/v1",
        "contract_hash": HASH_A,
        "route_return_sha256": RETURN._sha(route),
        "candidate_state": HASH_B if not mutation_started else "f" * 64,
        "mutation_started": mutation_started,
        "attempt_consumed": mutation_started,
        "disposition": (
            "WORKFLOW_DEFECT_NO_MUTATION"
            if not mutation_started
            else "PRE_VERIFIER_HARD_BLOCKER"
        ),
        "evidence_sources": ["https://example.test/blocker"],
        "basis": ["https://example.test/blocker"],
        "reason": "terminal before verifier",
    }


def test_no_mutation_terminal_can_restore_ready_without_consuming_attempt() -> None:
    previous = _route("IN_PROGRESS")
    current = _route("READY")
    terminal = _terminal(previous, mutation_started=False)
    receipt = RETURN.validate_transition(previous, current, terminal=terminal)
    assert receipt.status == "READY"

    with pytest.raises(RETURN.RouteReturnError):
        RETURN.validate_transition(previous, current)


def test_mutated_pre_verifier_terminal_consumes_with_terminal_artifact_sha() -> None:
    previous = _route("IN_PROGRESS")
    terminal = _terminal(previous, mutation_started=True)
    current = _route("CONSUMED")
    current["result_verifier_sha256"] = RETURN._sha(terminal)
    receipt = RETURN.validate_transition(previous, current, terminal=terminal)
    assert receipt.status == "CONSUMED"
