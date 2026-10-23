from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = ROOT / ".agents/skills/to-specs/SKILL.md"
SCRIPT_PATH = ROOT / "scripts/workflow_to_specs.py"


def test_to_specs_requires_intra_spec_completion_feasibility() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    for phrase in (
        "The same fail-closed rule applies **inside one Spec**.",
        "`local_provider_requirements`",
        "must be reachable through the consumer unit's transitive `depends_on` prerequisites",
        "downstream or unrelated local execution unit",
        "Unprotected downstream local provider requirements: 0",
    ):
        assert phrase in skill

    for phrase in (
        "def _validate_local_provider_requirements",
        "local_provider_requirements list required",
        "provider_unit cannot be self",
        "is not a transitive prerequisite of the consumer",
        "Unprotected downstream local provider requirements: 0",
    ):
        assert phrase in script
