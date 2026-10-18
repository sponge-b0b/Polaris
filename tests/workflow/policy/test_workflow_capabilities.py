from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / ".agents/skills/workflow-capabilities.json"
README_PATH = ROOT / ".agents/skills/README.md"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_migration_capability_ledger_has_no_unresolved_items() -> None:
    data = _manifest()
    assert data["schema"] == "polaris.workflow-capabilities/v1"
    assert data["migration_baseline"] == "1aef553b36f2907dbe7d811de4d6d5456b243952"
    assert len(data["capabilities"]) >= 30

    ambiguous = [row["id"] for row in data["capabilities"] if row["status"] == "AMBIGUOUS"]
    unresolved_losses = [
        row["id"]
        for row in data["capabilities"]
        if row["status"] == "LOST / DEFECT"
        and row.get("resolution") != "RESTORED_BY_THIS_CHANGE"
    ]
    assert ambiguous == []
    assert unresolved_losses == []


def test_known_migration_losses_are_explicitly_restored() -> None:
    rows = {row["id"]: row for row in _manifest()["capabilities"]}
    for capability_id in (
        "human-handoff-boundary-classification",
        "canonical-artifact-human-handoff-format",
        "fresh-session-handoff-durability",
    ):
        row = rows[capability_id]
        assert row["status"] == "LOST / DEFECT"
        assert row["resolution"] == "RESTORED_BY_THIS_CHANGE"
        assert "scripts/workflow_handoff.py" in row["owner"]


def test_shared_handoff_gate_covers_all_lifecycle_producers() -> None:
    data = _manifest()
    assert data["human_handoff"]["shared_gate"] == "scripts/workflow_handoff.py"
    assert set(data["human_handoff"]["required_by"]) == {
        "wayfinder",
        "to-specs",
        "to-tickets",
        "implement-ticket",
        "verify-spec",
        "review-spec",
        "architecture-remediation",
        "spec-merge-cleanup",
    }


def test_every_declared_current_owner_exists() -> None:
    data = _manifest()
    for row in data["capabilities"]:
        for owner in row.get("owner", []):
            if owner.startswith("$") or "/" not in owner and not owner.endswith(".md"):
                continue
            assert (ROOT / owner).exists(), f"missing capability owner: {owner}"


def test_cross_skill_policy_requires_the_shared_gate() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    for phrase in (
        "## Human Handoff boundary",
        "Internal composition",
        "Ordinary return",
        "In-skill HITL",
        "Lifecycle / user-control boundary",
        "$<skill-name> - <Artifact Title> (<Artifact URL>)",
        "python -m scripts.workflow_handoff generate",
        "Fresh-session durability",
        "byte-for-byte",
    ):
        assert phrase in text
