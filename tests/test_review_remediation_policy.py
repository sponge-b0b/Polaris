from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REVIEW = (ROOT / ".agents/skills/review-spec/SKILL.md").read_text(encoding="utf-8")
TICKETS = (ROOT / ".agents/skills/to-tickets/SKILL.md").read_text(encoding="utf-8")
IMPLEMENT = (
    ROOT / ".agents/skills/implement-ticket/SKILL.md"
).read_text(encoding="utf-8")
CLOSURE = (
    ROOT / ".agents/skills/verify-ticket-closure/SKILL.md"
).read_text(encoding="utf-8")
TO_REMEDIATION = (
    ROOT / ".agents/skills/to-remediation-tickets/SKILL.md"
).read_text(encoding="utf-8")
REVIEW_REMEDIATION = (
    ROOT / ".agents/skills/review-spec-remediation/SKILL.md"
).read_text(encoding="utf-8")
VERIFY_ROOT = (
    ROOT / ".agents/skills/verify-root-closure/SKILL.md"
).read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
README = (ROOT / ".agents/skills/README.md").read_text(encoding="utf-8")


def test_review_uses_structured_finding_ledger_not_root_blockers() -> None:
    assert "review-spec-finding-ledger:v2" in REVIEW
    assert "polaris.review-findings/v2" in REVIEW
    assert "do not synthesize or retain Root Blockers" in REVIEW
    assert "Do **not** invoke `$review-spec-remediation`" in REVIEW


def test_to_tickets_builds_finding_backed_remediation_contract() -> None:
    assert "polaris.review-remediation-contract/v1" in TICKETS
    assert "python -m scripts.review_remediation build" in TICKETS
    assert "Review Remediation Contract Hash" in TICKETS
    assert (
        "A historical Root Blocker ledger/ticket is migration history only"
        in TICKETS
    )


def test_implementation_and_closure_consume_exact_remediation_contract() -> None:
    for text in (IMPLEMENT, CLOSURE):
        assert "polaris.review-remediation-contract/v1" in text
    assert "**Review Remediation Contract Hash:**" in IMPLEMENT
    assert "**Review findings:**" in IMPLEMENT
    assert "**Root/Finding:**" not in IMPLEMENT
    assert "Do not synthesize a Root Blocker" in CLOSURE


def test_old_root_skills_are_compatibility_routes_only() -> None:
    assert "no longer a semantic decomposition owner" in TO_REMEDIATION
    assert "no longer owns a Root Blocker ledger" in REVIEW_REMEDIATION
    assert "not a certification authority" in VERIFY_ROOT


def test_repository_governance_names_current_remediation_contract() -> None:
    for text in (AGENTS, README):
        assert "review-spec-finding-ledger:v2" in text
        assert "review-remediation-contract/v1" in text
