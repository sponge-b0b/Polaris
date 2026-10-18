from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

IMPLEMENT = (ROOT / ".agents/skills/implement-ticket/SKILL.md").read_text(
    encoding="utf-8"
)
DEDUP = (ROOT / ".agents/skills/deduplicate-code/SKILL.md").read_text(
    encoding="utf-8"
)
VERIFY = (ROOT / ".agents/skills/verify-ticket-closure/SKILL.md").read_text(
    encoding="utf-8"
)
GUARD = (ROOT / "scripts/workflow_candidate_guard.py").read_text(encoding="utf-8")


def test_ordinary_implement_ticket_cannot_mutate_control_plane() -> None:
    assert "zero authority" in IMPLEMENT
    assert "workflow/control-plane" in IMPLEMENT
    assert "There is deliberately **no `$implement-ticket` bypass flag**" in IMPLEMENT
    assert "restore-protected" in IMPLEMENT
    assert "scripts.workflow_candidate_guard check" in IMPLEMENT


def test_deduplicate_ticket_differential_uses_execution_anchor() -> None:
    assert "EXECUTION_ANCHOR is the comparison base" in DEDUP
    assert "`TICKET_BASELINE` is not the scanner/differential baseline" in DEDUP
    assert "fixed Spec baseline behavior" in DEDUP
    assert "Protected control-plane boundary" in DEDUP
    assert "zero authority" in DEDUP


def test_independent_verifier_rejects_control_plane_candidate() -> None:
    assert "scripts.workflow_candidate_guard check" in VERIFY
    assert "protected control-plane candidate" in VERIFY
    assert "emit neither PASS nor FAIL" in VERIFY


def test_machine_guard_has_no_authorization_bypass() -> None:
    assert "PROTECTED_PREFIXES" in GUARD
    assert '".agents/"' in GUARD
    assert '"tests/workflow/"' in GUARD
    assert '"contracts/ccl/"' in GUARD
    assert '"docs/adr/"' in GUARD
    assert 'normalized.startswith("scripts/workflow_")' in GUARD
    assert "--allow" not in GUARD
