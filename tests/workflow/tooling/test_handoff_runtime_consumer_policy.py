import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESOLVER = ".agents/skills/shared_handoff_runtime.py"


def test_direct_long_lived_branch_consumers_use_runtime_resolver() -> None:
    for relative in (
        ".agents/skills/to-tickets/SKILL.md",
        ".agents/skills/implement-ticket/SKILL.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert RESOLVER in text
        assert "python -m scripts.workflow_handoff generate" not in text
        assert "python -m scripts.workflow_handoff verify" not in text
        assert "WORKFLOW HANDOFF: VALID" in text


def test_direct_consumers_document_non_mutating_default_fallback() -> None:
    for relative in (
        ".agents/skills/to-tickets/SKILL.md",
        ".agents/skills/implement-ticket/SKILL.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        assert "fetches current `origin/main`" in normalized
        assert "without mutating the candidate branch" in normalized


def test_capability_inventory_records_runtime_contract_and_resolver() -> None:
    manifest = json.loads(
        (ROOT / ".agents/skills/workflow-capabilities.json").read_text(
            encoding="utf-8"
        )
    )
    handoff = manifest["human_handoff"]
    assert handoff["shared_gate"] == "scripts/workflow_handoff.py"
    assert handoff["runtime_contract"] == "polaris.workflow-handoff-runtime/v2"
    assert handoff["runtime_resolver"] == RESOLVER

    capability_by_id = {item["id"]: item for item in manifest["capabilities"]}
    for capability_id in (
        "human-handoff-boundary-classification",
        "canonical-artifact-human-handoff-format",
        "fresh-session-handoff-durability",
    ):
        assert RESOLVER in capability_by_id[capability_id]["owner"]
