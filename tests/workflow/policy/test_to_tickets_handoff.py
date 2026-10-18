from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = ROOT / ".agents/skills/to-tickets/SKILL.md"
CAPABILITIES_PATH = ROOT / ".agents/skills/workflow-capabilities.json"
HANDOFF_MODULE_PATH = ROOT / "scripts/workflow_handoff.py"

spec = importlib.util.spec_from_file_location("workflow_handoff", HANDOFF_MODULE_PATH)
assert spec is not None and spec.loader is not None
workflow_handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow_handoff)


def test_to_tickets_frontier_is_bound_to_shared_handoff_gate() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    capabilities = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))

    assert "to-tickets" in capabilities["human_handoff"]["required_by"]
    for phrase in (
        "complete actionable frontier",
        "Do not stop after the first actionable ticket",
        "python -m scripts.workflow_handoff generate",
        "python -m scripts.workflow_handoff verify",
        "WORKFLOW HANDOFF: VALID",
        "byte-for-byte",
        "Do not emit a bare `$implement-ticket` line",
    ):
        assert phrase in skill


def test_to_tickets_frontier_manifest_contains_every_actionable_ticket() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    assert "one handoff entry for every actionable ticket" in skill
    assert "`$implement-ticket`" in skill
    assert "ordinary destination/topology order" in skill
    assert "review-remediation proposal alias order" in skill


def test_shared_gate_renders_multiple_implementation_handoffs_in_order() -> None:
    manifest = {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "durability": {
            "verified": True,
            "sources": [
                "https://github.com/sponge-b0b/Polaris/issues/358",
                "https://github.com/sponge-b0b/Polaris/issues/402",
                "https://github.com/sponge-b0b/Polaris/issues/404",
            ],
        },
        "handoffs": [
            {
                "destination": "$implement-ticket",
                "artifact": {
                    "title": "Validate foundational Investment Intelligence judgments against current CCL",
                    "url": "https://github.com/sponge-b0b/Polaris/issues/402",
                },
            },
            {
                "destination": "$implement-ticket",
                "artifact": {
                    "title": "Independent parallel implementation slice",
                    "url": "https://github.com/sponge-b0b/Polaris/issues/404",
                },
            },
        ],
    }

    lines = workflow_handoff.render_manifest(manifest).splitlines()
    assert lines[0] == "WORKFLOW HANDOFF: READY"
    assert lines[1:3] == [
        "$implement-ticket - Validate foundational Investment Intelligence judgments against current CCL (https://github.com/sponge-b0b/Polaris/issues/402)",
        "$implement-ticket - Independent parallel implementation slice (https://github.com/sponge-b0b/Polaris/issues/404)",
    ]
    assert lines[3] == "Fresh-session durability: VERIFIED"
    assert lines[4] == "Durability sources: 3"
    assert lines[5].startswith("Handoff manifest SHA-256: ")
