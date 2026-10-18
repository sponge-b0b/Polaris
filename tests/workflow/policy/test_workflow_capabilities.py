from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = ROOT / ".agents/skills/workflow-capabilities.json"
README_PATH = ROOT / ".agents/skills/README.md"
ATTENTION_SKILL_PATH = ROOT / ".agents/skills/attention/SKILL.md"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_migration_capability_ledger_has_no_unresolved_items() -> None:
    data = _manifest()
    assert data["schema"] == "polaris.workflow-capabilities/v1"
    assert data["migration_baseline"] == "1aef553b36f2907dbe7d811de4d6d5456b243952"
    assert len(data["capabilities"]) >= 31

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
    handoff_losses = (
        "human-handoff-boundary-classification",
        "canonical-artifact-human-handoff-format",
        "fresh-session-handoff-durability",
    )
    for capability_id in handoff_losses:
        row = rows[capability_id]
        assert row["status"] == "LOST / DEFECT"
        assert row["resolution"] == "RESTORED_BY_THIS_CHANGE"
        assert "scripts/workflow_handoff.py" in row["owner"]

    attention = rows["attention-producer-consumer-protocol-compatibility"]
    assert attention["status"] == "LOST / DEFECT"
    assert attention["resolution"] == "RESTORED_BY_THIS_CHANGE"
    assert "scripts/workflow_attention.py" in attention["owner"]


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


def test_attention_protocol_manifest_matches_producer_contract() -> None:
    data = _manifest()["attention_protocol"]
    assert data["producer"] == ".agents/skills/attention/SKILL.md"
    assert data["shared_validator"] == "scripts/workflow_attention.py"
    assert data["formal_headers"] == ["ATTENTION: CLEAR", "ATTENTION: FINDINGS"]
    assert set(data["checkpoint_consumers"]) == {
        "wayfinder",
        "to-specs",
        "to-tickets",
        "architecture-remediation",
        "implement-ticket",
        "verify-ticket-closure",
        "verify-spec",
        "review-spec",
    }

    producer = ATTENTION_SKILL_PATH.read_text(encoding="utf-8")
    for header in data["formal_headers"]:
        assert header in producer


def test_no_skill_invents_an_attention_result_header() -> None:
    allowed = set(_manifest()["attention_protocol"]["formal_headers"])
    header = re.compile(r"(?m)^\s*(ATTENTION:\s+[A-Z-]+)\s*$")
    invented: list[str] = []
    for path in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        for match in header.finditer(text):
            if match.group(1) not in allowed:
                invented.append(f"{path.relative_to(ROOT)}: {match.group(1)}")
    assert invented == []


def test_machine_attention_consumers_use_shared_validator() -> None:
    consumers = _manifest()["attention_protocol"]["machine_consumers"]
    expected = {
        "wayfinder": ".agents/skills/wayfinder/scripts/route_handoff.py",
        "to-tickets": ".agents/skills/to-tickets/SKILL.md",
        "implement-ticket": ".agents/skills/implement-ticket/scripts/attention_gate.py",
    }
    assert consumers == expected

    for consumer, relative in consumers.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        if consumer == "to-tickets":
            assert "python -m scripts.workflow_attention validate" in text
            assert "--require-nonblocking" in text
        else:
            assert "scripts.workflow_attention" in text
