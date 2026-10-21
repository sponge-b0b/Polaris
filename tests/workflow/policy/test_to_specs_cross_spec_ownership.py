from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / ".agents/skills/to-specs/SKILL.md"
RETAINED = ROOT / ".agents/skills/to-specs/RETAINED_SKILL.md"
SCRIPT = ROOT / "scripts/workflow_spec_ownership.py"


def test_to_specs_entrypoint_requires_machine_cross_spec_ownership_gate() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    retained = RETAINED.read_text(encoding="utf-8")

    assert SCRIPT.is_file()
    assert "Durable routing-defect inventory gate" in retained
    for phrase in (
        "TO-SPECS OWNERSHIP PREFLIGHT: VALID",
        "TO-SPECS CROSS-SPEC OWNERSHIP: VALID",
        "Unprotected consumed-boundary requirements: 0",
        "Execution units without local material ownership: 0",
        "ownership_analysis",
        "provider_spec",
        "provider_cells",
        "planning cell may not exist solely to",
    ):
        assert phrase in skill
