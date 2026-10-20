from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHARED = ROOT / ".agents/skills/WORKFLOW_INVOCATION_JOURNAL.md"
IMPLEMENT = ROOT / ".agents/skills/implement-ticket/WORKFLOW_INVOCATION_JOURNAL.md"
SKILL = ROOT / ".agents/skills/implement-ticket/SKILL.md"
CAPABILITIES = ROOT / ".agents/skills/workflow-capabilities.json"


def test_shared_contract_is_non_authoritative_and_non_blocking() -> None:
    text = SHARED.read_text(encoding="utf-8")

    assert "WIJ failure is never a workflow failure" in text
    assert "not semantic, contract, dependency, candidate, closure" in text
    assert "Current repository/tracker authority always wins" in text
    assert "git rev-parse --absolute-git-dir" in text
    assert "Single-writer invariant" in text
    assert "Path-aware selective invalidation is explicitly deferred beyond V1" in text


def test_implement_ticket_contract_requires_current_authority() -> None:
    text = IMPLEMENT.read_text(encoding="utf-8")

    assert "Only an explicit `resume $implement-ticket" in text
    assert "Steps 1-3" in text
    assert "Always-refresh/live checks" in text
    assert "current candidate guard" in text
    assert "attention_gate.py verify" in text
    assert "cannot salvage or certify the verdict" in text
    assert "v3" in text


def test_implement_ticket_skill_composes_journal_contracts() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert ".agents/skills/WORKFLOW_INVOCATION_JOURNAL.md" in text
    assert ".agents/skills/implement-ticket/WORKFLOW_INVOCATION_JOURNAL.md" in text
    assert "journal failure" in text.lower()


def test_capability_manifest_registers_workflow_invocation_resumability() -> None:
    payload = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    matches = [
        item
        for item in payload["capabilities"]
        if item["id"] == "workflow-invocation-resumability"
    ]

    assert len(matches) == 1
    assert matches[0]["status"] == "PRESERVED"
    assert ".agents/skills/WORKFLOW_INVOCATION_JOURNAL.md" in matches[0]["owner"]
    assert "scripts/workflow_journal.py" in matches[0]["owner"]
