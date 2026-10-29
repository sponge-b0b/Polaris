from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VERIFY_SKILL = ROOT / ".agents/skills/verify-ticket-closure/SKILL.md"
VERIFY_POLICY = ROOT / ".agents/skills/verify-ticket-closure/POLICY_SYNC_ADMISSION.md"
IMPLEMENT_SKILL = ROOT / ".agents/skills/implement-ticket/SKILL.md"
EXECUTION_ANCHOR = ROOT / ".agents/skills/implement-ticket/EXECUTION_ANCHOR.md"
CONTROL_PLANE = ROOT / ".agents/skills/implement-ticket/CONTROL_PLANE.md"
ROUTING_CONTROL_PLANE = ROOT / ".agents/skills/implement-ticket/ROUTING_CONTROL_PLANE.md"

POLICY_GUARD = (
    "python .agents/skills/implement-ticket/scripts/candidate_guard.py check"
)
ROOT_GUARD = "python -m scripts.workflow_candidate_guard check"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_verify_ticket_closure_uses_policy_sync_aware_candidate_guard() -> None:
    skill = _text(VERIFY_SKILL)
    policy = _text(VERIFY_POLICY)

    assert "POLICY_SYNC_ADMISSION.md" in skill
    assert POLICY_GUARD in skill
    assert POLICY_GUARD in policy
    assert ROOT_GUARD not in skill
    assert "--remote origin" in skill
    assert "--default-branch main" in skill


def test_verifier_binds_execution_anchor_at_admission_and_terminal_recheck() -> None:
    skill = _text(VERIFY_SKILL)
    policy = _text(VERIFY_POLICY)

    assert "--execution-anchor <execution-anchor>" in skill
    assert "--execution-anchor <execution-anchor>" in policy
    assert "Immediately before emitting either terminal" in policy
    assert "rerun the exact policy-aware candidate guard" in policy
    assert "rerun `attention_gate.py verify`" in policy
    assert "same Execution Anchor" in policy


def test_policy_sync_is_delivery_tip_history_not_candidate_mutation() -> None:
    policy = _text(VERIFY_POLICY)
    anchor = _text(EXECUTION_ANCHOR)
    control = _text(CONTROL_PLANE)

    assert "Authorized policy-only delivery-tip movement is **not** candidate mutation" in policy
    assert "policy-sync-aware candidate universe" in anchor
    assert "Current `HEAD` need not equal the Execution Anchor" in anchor
    assert "Authorized committed policy synchronization is upstream history" in control

    stale_phrases = (
        "HEAD may not change after the pre-mutation gate until certification/persistence",
        "rejects any committed HEAD movement after the Execution Anchor",
        "while HEAD still equals the Execution Anchor",
    )
    for phrase in stale_phrases:
        assert phrase not in anchor


def test_retained_root_guard_wording_cannot_override_current_entrypoint() -> None:
    implement_skill = _text(IMPLEMENT_SKILL)
    routing = _text(ROUTING_CONTROL_PLANE)

    # The retained routing layer still contains historical root-guard wording, but the
    # current authoritative entrypoint must explicitly supersede that invocation so it
    # cannot become a source-conflict at closure time.
    assert "scripts.workflow_candidate_guard check" in routing
    assert "older direct" in implement_skill
    assert "scripts.workflow_candidate_guard check" in implement_skill
    assert "superseded by the\npolicy-sync-aware wrapper" in implement_skill


def test_verifier_policy_explicitly_supersedes_stale_retained_examples() -> None:
    policy = _text(VERIFY_POLICY)

    assert "Any retained procedure example that omits `--execution-anchor`" in policy
    assert "computes candidate identity\nfrom Ticket baseline" in policy
    assert "treats every `HEAD != Execution Anchor` state as invalid" in policy
