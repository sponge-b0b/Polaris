from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENT = (
    ROOT / ".agents/skills/implement-ticket/SKILL.md"
).read_text(encoding="utf-8")
VERIFY = (
    ROOT / ".agents/skills/verify-ticket-closure/SKILL.md"
).read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
README = (ROOT / ".agents/skills/README.md").read_text(encoding="utf-8")


def test_ticket_contract_is_deterministic_boundary() -> None:
    for text in (IMPLEMENT, VERIFY):
        assert "polaris.ticket-contract/v1" in text
        assert "Ticket Contract Hash" in text
    assert "build-ticket" in IMPLEMENT
    assert "ticket-coverage-manifest:v2" in IMPLEMENT


def test_implementation_does_not_self_certify_semantics() -> None:
    assert "Implementation Evidence Index" in IMPLEMENT
    assert "does **not** build a Ticket Acceptance Universe" in IMPLEMENT
    assert "fresh non-mutating `$verify-ticket-closure`" in IMPLEMENT
    assert "proof independence" in VERIFY


def test_verifier_cannot_reconstruct_broader_semantic_universe() -> None:
    for phrase in (
        "add/remove a cell",
        "build Source Unit or `ARCHSRC-*` inventories",
        "reopen ADR/wiki/Decision prose",
    ):
        assert phrase in VERIFY
    assert "contract-authority-gap" in VERIFY
    assert "cell-routing-defect" in VERIFY


def test_parent_exclusions_are_deterministic_guardrails() -> None:
    assert "every current parent `EXC-*` as a guardrail" in IMPLEMENT
    assert "every current parent EXC-* cell" in VERIFY
    assert "exclusion guardrails unresolved: 0" in VERIFY


def test_current_attempts_use_only_v3_checkpoint() -> None:
    assert "implement-ticket-closure-checkpoint:v3" in IMPLEMENT
    assert "Legacy checkpoint migration" not in IMPLEMENT
    assert "v2/root checkpoints" not in IMPLEMENT


def test_repository_governance_requires_frozen_ticket_contract() -> None:
    assert "$verify-ticket-closure" in AGENTS
    assert "proof independence" in AGENTS
    assert "$implement-ticket" in README
    assert "Independence means proof" in README


def test_gap_routing_is_owned_upstream() -> None:
    for text in (IMPLEMENT, VERIFY):
        assert "planning-cell-gap" in text
        assert "contract-authority-gap" in text
        assert "$to-specs" in text
        assert "$to-tickets" in text
