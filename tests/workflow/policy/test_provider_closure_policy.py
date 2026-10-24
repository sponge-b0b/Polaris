from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_to_specs_requires_provider_closure_before_ticketing() -> None:
    skill = (ROOT / ".agents/skills/to-specs/SKILL.md").read_text(encoding="utf-8")
    policy = (ROOT / ".agents/skills/to-specs/PROVIDER_CLOSURE.md").read_text(
        encoding="utf-8"
    )

    assert ".agents/skills/to-specs/PROVIDER_CLOSURE.md" in skill
    assert "TO-SPECS PROVIDER CLOSURE: VALID" in skill
    assert "ownership-homogeneous material cells" in policy.lower()
    assert "deferred-composition" in policy
    assert "composition Spec" in policy


def test_implement_ticket_distinguishes_deferred_composition() -> None:
    policy = (
        ROOT / ".agents/skills/implement-ticket/PRE_IMPLEMENTATION_FEASIBILITY.md"
    ).read_text(encoding="utf-8")
    routing = (
        ROOT / ".agents/skills/implement-ticket/ROUTING_CONTROL_PLANE.md"
    ).read_text(encoding="utf-8")

    assert "DEFERRED_COMPOSITION" in policy
    assert "Composition owner:" in policy
    assert "does **not** claim production composition" in policy
    assert "Deferred composition:" in policy
    assert "DEFERRED_COMPOSITION" in routing
    assert "deliberately downstream composition root" in routing
