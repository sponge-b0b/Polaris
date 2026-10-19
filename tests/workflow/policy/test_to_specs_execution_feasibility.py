from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = ROOT / ".agents/skills/to-specs/SKILL.md"
PROCEDURE_PATH = ROOT / ".agents/skills/to-specs/PROCEDURE.md"
CAPABILITIES_PATH = ROOT / ".agents/skills/workflow-capabilities.json"
SCRIPT_PATH = ROOT / "scripts/workflow_to_specs.py"


def test_to_specs_entrypoint_binds_machine_feasibility_and_shared_handoff() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    capabilities = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))

    assert PROCEDURE_PATH.is_file()
    assert SCRIPT_PATH.is_file()
    assert "to-specs" in capabilities["human_handoff"]["required_by"]
    for phrase in (
        "TO-SPECS PREFLIGHT: VALID",
        "SPEC EXECUTION FEASIBILITY: VALID",
        "Unprotected pending provider requirements: 0",
        "Local structural success is **not** sufficient",
        "production success and proof path",
        "local_completion_attestation",
        "python -m scripts.workflow_to_specs build-handoff",
        "WORKFLOW HANDOFF: VALID",
        "byte-for-byte",
        "$to-tickets - <exact current Spec title> (<exact canonical Spec URL>)",
    ):
        assert phrase in skill


def test_retained_procedure_still_contains_cross_spec_ownership_rule() -> None:
    procedure = PROCEDURE_PATH.read_text(encoding="utf-8")
    assert "## Cross-Spec ownership integrity" in procedure
    assert (
        "an upstream Spec requires completion-time proof of behavior that can only be implemented"
        in procedure
    )
    assert "## Human handoff" in procedure
