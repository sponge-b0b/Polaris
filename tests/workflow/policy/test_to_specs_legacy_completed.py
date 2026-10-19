from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = ROOT / ".agents/skills/to-specs/SKILL.md"
SCRIPT_PATH = ROOT / "scripts/workflow_to_specs.py"


def test_to_specs_legacy_completed_compatibility_is_asymmetric() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    for phrase in (
        "### Immutable legacy-completed Specs",
        "A CLOSED Spec that predates `spec-execution-topology:v1` is immutable delivery history.",
        "legacy_completed.result",
        "legacy_completed.completion_basis",
        "does not create retroactive execution-unit authority",
        "Every OPEN Spec must contain a current `spec-execution-topology:v1` marker",
        "must still use normal `unit_analysis`",
    ):
        assert phrase in skill

    for phrase in (
        "def _validate_legacy_completed",
        "open spec missing spec-execution-topology:v1",
        "legacy_completed is allowed only for a CLOSED",
        "invent unit_analysis",
        "Legacy completed Specs:",
    ):
        assert phrase in script
