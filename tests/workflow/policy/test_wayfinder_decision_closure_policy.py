from pathlib import Path

ROOT = Path(__file__).parents[3]
WAYFINDER = (ROOT / ".agents/skills/wayfinder/SKILL.md").read_text(encoding="utf-8")
SCRIPT = ROOT / ".agents/skills/wayfinder/scripts/decision_closure.py"


def test_wayfinder_requires_machine_decision_closure_gate() -> None:
    assert SCRIPT.is_file()
    assert "decision_closure.py" in WAYFINDER
    assert "WAYFINDER DECISION CLOSURE: ALLOWED" in WAYFINDER
    assert "polaris.wayfinder-decision-closure/v1" in WAYFINDER
    assert '"affected_knowledge_routing"' in WAYFINDER
    assert "complete Affected Knowledge" in WAYFINDER
    assert "Routing Record required by its own workflow" in WAYFINDER


def test_wayfinder_cannot_close_before_wiki_sync_receipt() -> None:
    assert "A failed or missing closure gate means the decision remains open" in WAYFINDER
    assert "close the decision" in WAYFINDER
    assert "mutate the map frontier" in WAYFINDER
    assert "NO_DURABLE_KNOWLEDGE_CHANGED" in WAYFINDER
    assert "CCL-backed" in WAYFINDER
    assert "$wiki-sync" in WAYFINDER
