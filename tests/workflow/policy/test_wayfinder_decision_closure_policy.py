from pathlib import Path

ROOT = Path(__file__).parents[3]
WAYFINDER = (ROOT / ".agents/skills/wayfinder/SKILL.md").read_text(encoding="utf-8")
SCRIPT = ROOT / ".agents/skills/wayfinder/scripts/decision_closure.py"


def test_wayfinder_requires_machine_decision_closure_gate() -> None:
    assert SCRIPT.is_file()
    assert "decision_closure.py" in WAYFINDER
    assert "WAYFINDER DECISION CLOSURE: ALLOWED" in WAYFINDER
    assert "polaris.wayfinder-decision-closure/v1" in WAYFINDER
    assert "Affected Knowledge Routing Record" in WAYFINDER


def test_wayfinder_cannot_close_before_wiki_sync_receipt() -> None:
    assert "Do not post final resolution, close the decision, or mutate the map frontier" in WAYFINDER
    assert "NO_DURABLE_KNOWLEDGE_CHANGED" in WAYFINDER
    assert "CCL-backed" in WAYFINDER
    assert "$wiki-sync" in WAYFINDER
