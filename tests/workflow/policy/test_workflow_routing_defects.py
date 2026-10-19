from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TO_SPECS = ROOT / ".agents/skills/to-specs/SKILL.md"
TO_SPECS_BASE = ROOT / ".agents/skills/to-specs/CONTROL_PLANE.md"
IMPLEMENT = ROOT / ".agents/skills/implement-ticket/SKILL.md"
IMPLEMENT_BASE = ROOT / ".agents/skills/implement-ticket/CONTROL_PLANE.md"
SCRIPT = ROOT / "scripts/workflow_routing_defects.py"


def test_to_specs_requires_machine_routing_defect_inventory() -> None:
    skill = TO_SPECS.read_text(encoding="utf-8")
    assert TO_SPECS_BASE.is_file()
    assert SCRIPT.is_file()
    for phrase in (
        "TO-SPECS ROUTING DEFECT PREFLIGHT: VALID",
        "TO-SPECS ROUTING DEFECT INVENTORY: VALID",
        "TO-SPECS ROUTING DEFECT COVERAGE: VALID",
        "Unprotected routing defect requirements: 0",
        "workflow-routing-defect:v1",
        "required_local_provider_cells",
        "actor omitted the provider from `unit_analysis`",
    ):
        assert phrase in skill


def test_implement_ticket_persists_machine_routing_defect_marker() -> None:
    skill = IMPLEMENT.read_text(encoding="utf-8")
    assert IMPLEMENT_BASE.is_file()
    for phrase in (
        "WORKFLOW ROUTING DEFECT MARKER: VALID",
        "workflow-routing-defect:v1",
        "required_local_provider_cells",
        "Include that exact comment URL in the outbound shared-handoff durability sources.",
        "cell-routing-defect -> $to-tickets",
    ):
        assert phrase in skill
