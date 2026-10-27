from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FEAS = ROOT / ".agents/skills/implement-ticket/scripts/feasibility_authority.py"
ARCH = ROOT / ".agents/skills/architecture-remediation/scripts/architecture_route_guard.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


F = _load("test_feasibility_authority_module", FEAS)
A = _load("test_architecture_route_guard_module", ARCH)

HASH = "a" * 64
HEAD = "b" * 40


def _feasibility(*, outcome="PASS", authority="FIXED_IMPLEMENTATION_LOCAL"):
    blocked = None
    if outcome == "BLOCKED":
        blocked = {
            "classification": "contract-authority-gap",
            "seam_id": "history-write",
            "required_cells": ["OBL-007"],
            "durable_owner": "Wayfinder #348",
            "reason": "Current authority does not determine the publication boundary.",
            "route": "$architecture-remediation",
        }
    return {
        "schema": "polaris.implement-feasibility/v1",
        "ticket": 465,
        "contract_hash": HASH,
        "branch": "spec-358",
        "execution_head": HEAD,
        "evidence_sources": ["adr:0016", "arch:0.2.0", "source:history-store"],
        "seams": [
            {
                "seam_id": "history-write",
                "required_cells": ["OBL-007"],
                "ownership_status": "OWNED_BY_CURRENT_TICKET",
                "authority_status": authority,
                "authority_basis": ["adr:0016", "arch:0.2.0"],
                "realization_basis": ["source:history-store"],
            }
        ],
        "prior_findings": [],
        "outcome": outcome,
        "blocked": blocked,
    }


def _request(*, post=()):
    basis = ["adr:0016", "arch:0.2.0", *post]
    return {
        "schema": "polaris.architecture-route-request/v1",
        "ticket": 465,
        "contract_hash": HASH,
        "question_kind": "semantic-authority-gap",
        "authority_coordinate": "durable known-at publication boundary",
        "governing_sources_checked": ["adr:0016", "arch:0.2.0"],
        "basis": sorted(basis),
        "post_feasibility_evidence": sorted(post),
    }


def test_pass_requires_authority_closed_for_owned_seam():
    receipt = F.validate_feasibility(_feasibility())
    assert receipt.outcome == "PASS"


def test_pass_rejects_unresolved_material_choice():
    with pytest.raises(F.FeasibilityError, match="PASS forbidden"):
        F.validate_feasibility(
            _feasibility(authority="UNRESOLVED_MATERIAL_CHOICE")
        )


def test_contract_authority_gap_requires_unresolved_seam():
    with pytest.raises(
        F.FeasibilityError,
        match="requires an unresolved material authority seam",
    ):
        F.validate_feasibility(_feasibility(outcome="BLOCKED"))


def test_blocked_contract_authority_gap_with_unresolved_seam_is_valid():
    receipt = F.validate_feasibility(
        _feasibility(
            outcome="BLOCKED",
            authority="UNRESOLVED_MATERIAL_CHOICE",
        )
    )
    assert receipt.outcome == "BLOCKED"


def test_architecture_route_rejects_preexisting_evidence_after_pass():
    with pytest.raises(A.ArchitectureRouteError, match="pre-existing evidence"):
        A.validate_route(_feasibility(), _request())


def test_architecture_route_allows_genuinely_new_evidence_after_pass():
    receipt = A.validate_route(
        _feasibility(),
        _request(post=("new:accepted-source-conflict",)),
    )
    assert receipt.feasibility_outcome == "PASS"
    assert receipt.new_evidence_count == 1


def test_architecture_route_accepts_prior_contract_authority_block():
    receipt = A.validate_route(
        _feasibility(
            outcome="BLOCKED",
            authority="UNRESOLVED_MATERIAL_CHOICE",
        ),
        _request(),
    )
    assert receipt.feasibility_outcome == "BLOCKED"


def test_pre_mutation_attention_gate_requires_machine_feasibility():
    gate = (
        ROOT / ".agents/skills/implement-ticket/scripts/attention_gate.py"
    ).read_text(encoding="utf-8")
    assert "--feasibility" in gate
    assert "pre-mutation requires IMPLEMENT TICKET FEASIBILITY: PASS" in gate
    assert "execution HEAD is stale" in gate


def test_architecture_policy_requires_route_consistency_guard():
    policy = (
        ROOT / ".agents/skills/architecture-remediation/SKILL.md"
    ).read_text(encoding="utf-8")
    assert "architecture_route_guard.py" in policy
    assert "feasibility PASS cannot" not in policy  # machine message belongs in the guard
    assert "Evidence already enumerated before PASS" in policy
    assert "implementation-realization problem is not itself a semantic-authority gap" in policy
