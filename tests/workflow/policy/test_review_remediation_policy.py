from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

REVIEW = (ROOT / ".agents/skills/review-spec/SKILL.md").read_text(encoding="utf-8")
TICKETS = (ROOT / ".agents/skills/to-tickets/SKILL.md").read_text(encoding="utf-8")
IMPLEMENT = (
    ROOT / ".agents/skills/implement-ticket/SKILL.md"
).read_text(encoding="utf-8")
CLOSURE = (
    ROOT / ".agents/skills/verify-ticket-closure/SKILL.md"
).read_text(encoding="utf-8")
CLEANUP = (
    ROOT / ".agents/skills/spec-merge-cleanup/SKILL.md"
).read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
README = (ROOT / ".agents/skills/README.md").read_text(encoding="utf-8")


def test_review_uses_v2_finding_ledger_without_legacy_transport_fields() -> None:
    assert "review-spec-finding-ledger:v2" in REVIEW
    assert "polaris.review-findings/v2" in REVIEW
    assert "review-spec-finding-ledger:v1" not in REVIEW
    assert "**Root blockers:**" not in REVIEW
    assert "**Candidate new roots:**" not in REVIEW


def test_to_tickets_builds_finding_backed_remediation_contract() -> None:
    assert "polaris.review-remediation-contract/v1" in TICKETS
    assert "python -m scripts.review_remediation build" in TICKETS
    assert "Review Remediation Contract Hash" in TICKETS


def test_implementation_and_closure_consume_exact_remediation_contract() -> None:
    for text in (IMPLEMENT, CLOSURE):
        assert "polaris.review-remediation-contract/v1" in text
    assert "**Review Remediation Contract Hash:**" in IMPLEMENT
    assert "**Review findings:**" in IMPLEMENT
    assert "**Root/Finding:**" not in IMPLEMENT


def test_cleanup_consumes_v2_review_state_only() -> None:
    assert "review-spec-finding-ledger:v2" in CLEANUP
    assert "review-spec-finding-ledger:v1" not in CLEANUP
    assert "**Root blockers:**" not in CLEANUP
    assert "**Candidate new roots:**" not in CLEANUP
    assert "REVIEW FINDING LEDGER: VALID" in CLEANUP


def test_retired_root_compatibility_skills_are_absent() -> None:
    for skill in (
        "to-remediation-tickets",
        "review-spec-remediation",
        "verify-root-closure",
    ):
        assert not (ROOT / ".agents/skills" / skill / "SKILL.md").exists()
        assert not (ROOT / ".agents/skills" / skill / "agents/openai.yaml").exists()


def test_repository_governance_names_current_remediation_contract() -> None:
    for text in (AGENTS, README):
        assert "review-spec-finding-ledger:v2" in text
        assert "review-remediation-contract/v1" in text
    assert "$to-remediation-tickets" not in README
    assert "$review-spec-remediation" not in README
    assert "$verify-root-closure" not in README
