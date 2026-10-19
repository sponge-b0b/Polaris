from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = ROOT / ".agents/skills/implement-ticket/SKILL.md"
CAPABILITIES_PATH = ROOT / ".agents/skills/workflow-capabilities.json"
HANDOFF_MODULE_PATH = ROOT / "scripts/workflow_handoff.py"

spec = importlib.util.spec_from_file_location("workflow_handoff", HANDOFF_MODULE_PATH)
assert spec is not None and spec.loader is not None
workflow_handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow_handoff)


def test_implement_ticket_is_bound_to_shared_handoff_gate() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    capabilities = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))

    assert "implement-ticket" in capabilities["human_handoff"]["required_by"]
    for phrase in (
        "Every terminal **Human Handoff** from `$implement-ticket`",
        "verifier `cell-routing-defect` -> `$to-tickets`",
        "verifier `planning-cell-gap` -> `$to-specs`",
        "contract-authority-gap",
        "python -m scripts.workflow_handoff generate",
        "python -m scripts.workflow_handoff verify",
        "WORKFLOW HANDOFF: VALID",
        "byte-for-byte",
        "A recommendation, prose instruction, or bare downstream skill command is **not** a Human",
        "Do not emit a bare `$to-specs`, `$to-tickets`, `$architecture-remediation`,",
    ):
        assert phrase in skill


def test_implement_ticket_routes_to_exact_downstream_artifacts() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")

    assert "$to-tickets` receives the exact current Parent Spec issue" in skill
    assert (
        "$to-specs` receives the exact current planning source for the Parent Spec"
        in skill
    )
    assert (
        "A current Spec issue is a durability source, not a substitute planning source."
        in skill
    )
    assert "$implement-ticket` receives each exact current actionable ticket issue" in skill
    assert "$verify-spec` receives the exact current Parent Spec issue" in skill


def test_planning_gap_handoff_renders_canonical_to_specs_block() -> None:
    manifest = {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "durability": {
            "verified": True,
            "sources": [
                "https://github.com/sponge-b0b/Polaris/issues/399",
                "https://github.com/sponge-b0b/Polaris/issues/358",
                "https://github.com/sponge-b0b/Polaris/issues/348",
            ],
        },
        "handoffs": [
            {
                "destination": "$to-specs",
                "artifact": {
                    "title": "Wayfinder: R3 Investment Decision workflow",
                    "url": "https://github.com/sponge-b0b/Polaris/issues/348",
                },
            }
        ],
    }

    output = workflow_handoff.render_manifest(manifest)
    lines = output.splitlines()
    assert lines[0] == "WORKFLOW HANDOFF: READY"
    assert lines[1] == (
        "$to-specs - Wayfinder: R3 Investment Decision workflow "
        "(https://github.com/sponge-b0b/Polaris/issues/348)"
    )
    assert lines[2] == "Fresh-session durability: VERIFIED"
    assert lines[3] == "Durability sources: 3"
    assert lines[4].startswith("Handoff manifest SHA-256: ")
    assert workflow_handoff.validate_output(manifest, output) == "WORKFLOW HANDOFF: VALID"


def test_post_closure_frontier_requires_every_actionable_ticket() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "complete current actionable ticket" in skill
    assert "Do not stop after the first actionable ticket" in skill
    assert "one manifest handoff entry" in skill

    manifest = {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "durability": {
            "verified": True,
            "sources": [
                "https://github.com/sponge-b0b/Polaris/issues/358",
                "https://github.com/sponge-b0b/Polaris/issues/403",
                "https://github.com/sponge-b0b/Polaris/issues/400",
            ],
        },
        "handoffs": [
            {
                "destination": "$implement-ticket",
                "artifact": {
                    "title": "Resolve overlapping Intelligence corrections and prove temporal basis",
                    "url": "https://github.com/sponge-b0b/Polaris/issues/403",
                },
            },
            {
                "destination": "$implement-ticket",
                "artifact": {
                    "title": "Implement Recommendation and withholding formation with Portfolio/Risk consequences",
                    "url": "https://github.com/sponge-b0b/Polaris/issues/400",
                },
            },
        ],
    }

    lines = workflow_handoff.render_manifest(manifest).splitlines()
    assert lines[1:3] == [
        "$implement-ticket - Resolve overlapping Intelligence corrections and prove temporal basis (https://github.com/sponge-b0b/Polaris/issues/403)",
        "$implement-ticket - Implement Recommendation and withholding formation with Portfolio/Risk consequences (https://github.com/sponge-b0b/Polaris/issues/400)",
    ]


def test_completed_ticket_can_render_verify_spec_handoff() -> None:
    manifest = {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "durability": {
            "verified": True,
            "sources": ["https://github.com/sponge-b0b/Polaris/issues/358"],
        },
        "handoffs": [
            {
                "destination": "$verify-spec",
                "artifact": {
                    "title": "Spec: Implement R3 Investment Intelligence and Recommendation",
                    "url": "https://github.com/sponge-b0b/Polaris/issues/358",
                },
            }
        ],
    }

    output = workflow_handoff.render_manifest(manifest)
    assert (
        "$verify-spec - Spec: Implement R3 Investment Intelligence and Recommendation "
        "(https://github.com/sponge-b0b/Polaris/issues/358)"
    ) in output
    assert workflow_handoff.validate_output(manifest, output) == "WORKFLOW HANDOFF: VALID"
