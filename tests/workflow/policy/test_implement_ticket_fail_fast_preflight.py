from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROUTING = ROOT / ".agents/skills/implement-ticket/ROUTING_CONTROL_PLANE.md"
FEASIBILITY = ROOT / ".agents/skills/implement-ticket/PRE_IMPLEMENTATION_FEASIBILITY.md"
DONOR = ROOT / "scripts/workflow_reslice_donor.py"


def test_routing_composes_feasibility_before_mutation() -> None:
    text = ROUTING.read_text(encoding="utf-8")
    assert "PRE_IMPLEMENTATION_FEASIBILITY.md" in text
    assert "before the retained Section 4 pre-mutation Attention checkpoint" in text
    assert "IMPLEMENT TICKET FEASIBILITY: PASS" in text
    assert "IMPLEMENT TICKET FEASIBILITY: BLOCKED" in text


def test_routing_requires_live_donor_validation_at_preflight() -> None:
    text = ROUTING.read_text(encoding="utf-8")
    assert "scripts.workflow_reslice_donor validate" in text
    assert "TICKET RESLICE DONOR: VALID" in text
    assert "a detached checkout is not equivalent" in text
    assert "Do not postpone donor fingerprint validation" in text


def test_feasibility_distinguishes_production_from_test_only_providers() -> None:
    text = FEASIBILITY.read_text(encoding="utf-8")
    assert "Test fixtures, fakes, mocks" in text
    assert "PRESENT_UPSTREAM" in text
    assert "OWNED_BY_CURRENT_TICKET" in text
    assert "MISSING_UPSTREAM" in text
    assert "AMBIGUOUS_OWNER" in text
    assert "planning-cell-gap" in text


def test_live_donor_validator_is_read_only_and_checks_recorded_identity() -> None:
    text = DONOR.read_text(encoding="utf-8")
    assert '"branch", "--show-current"' in text
    assert '"rev-parse", "HEAD"' in text
    assert "live_candidate_state" in text
    assert "attention_receipt_hash" in text
    for forbidden in ("checkout", "reset", "clean", "stash", "commit"):
        assert f'"{forbidden}"' not in text
