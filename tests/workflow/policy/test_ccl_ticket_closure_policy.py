from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


COMPOSED_AUTHORITY_FILES = (
    "SKILL.md",
    "PROCEDURE.md",
    "EXECUTION_ANCHOR.md",
    "CONTROL_PLANE.md",
    "ROUTING_CONTROL_PLANE.md",
)


def _composed_skill(relative: str) -> str:
    root = ROOT / relative
    parts = [
        (root / name).read_text(encoding="utf-8")
        for name in COMPOSED_AUTHORITY_FILES
        if (root / name).exists()
    ]
    return "\n".join(parts)


IMPLEMENT = _composed_skill(".agents/skills/implement-ticket")
VERIFY = _composed_skill(".agents/skills/verify-ticket-closure")
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


def test_implement_ticket_attention_checkpoints_are_auditable() -> None:
    assert "does **not** satisfy this checkpoint" in IMPLEMENT
    assert "Checkpoint: $implement-ticket pre-mutation" in IMPLEMENT
    assert "No substantive mutation is allowed until" in IMPLEMENT
    assert "Checkpoint: $implement-ticket pre-closure" in IMPLEMENT
    assert "Do not write the v3" in IMPLEMENT
    assert (
        "`awaiting-closure-verification` checkpoint until this verification succeeds"
        in IMPLEMENT
    )


def test_execution_anchor_separates_lineage_from_candidate_identity() -> None:
    for text in (IMPLEMENT, VERIFY):
        assert "Ticket baseline" in text
        assert "Execution Anchor" in text
    assert "immutable per-ticket historical / lineage anchor" in IMPLEMENT
    assert "exact fetched remote shared-Spec-branch commit" in IMPLEMENT
    assert "diff base `TICKET_BASELINE` with `EXECUTION_ANCHOR`" in IMPLEMENT
    assert "Candidate state: <hash relative to Execution Anchor>" in VERIFY


def test_attention_gate_is_directly_executable_and_anchor_bound() -> None:
    assert "no `PYTHONPATH` workaround is required" in IMPLEMENT
    assert "--remote origin" in IMPLEMENT
    assert "--execution-anchor <execution-anchor>" in IMPLEMENT
    assert "polaris.implement-ticket-attention/v2" in IMPLEMENT
    assert "v1 Attention receipt" in VERIFY


def test_build_ticket_uses_published_coverage_destination() -> None:
    assert "exact coverage `destination`" in IMPLEMENT
    assert "for example `T1`" in IMPLEMENT
    assert '"<ticket-destination>"' in IMPLEMENT
    assert '"#<ticket-number>"' not in IMPLEMENT


def test_verifier_result_finalization_is_same_context_and_non_appealable() -> None:
    assert "result-finalization handshake" in IMPLEMENT
    assert "result-finalization handshake" in VERIFY
    assert "TICKET CLOSURE RESULT: CONFIRMED" in IMPLEMENT
    assert "TICKET CLOSURE RESULT: CONFIRMED" in VERIFY
    assert "TICKET CLOSURE: INVALID" in IMPLEMENT
    assert "TICKET CLOSURE: INVALID" in VERIFY
    assert "self-contradictory-verdict" in IMPLEMENT
    assert "self-contradictory-verdict" in VERIFY
    assert "same-context post-result interaction" in IMPLEMENT
    assert "same verifier context" in VERIFY
    assert "may not create an INVALID payload" in IMPLEMENT
    assert "Free-form follow-up" in IMPLEMENT
    assert "Retracted result SHA-256" in VERIFY


def test_verifier_failure_saturates_bounded_counterexample_classes() -> None:
    assert "Bounded counterexample-class saturation" in VERIFY
    assert "counterexample-class-complete" in VERIFY
    assert "at least one representative falsifier" in VERIFY
    assert "does **not**\n   require exhaustive bug search" in VERIFY
    assert "migration/DDL mechanics" in VERIFY
    assert "executed durable schema" in VERIFY
    assert "Any unchecked applicable counterexample class" in VERIFY
    assert "Counterexample-class saturation: complete" in VERIFY
    assert "counterexample classes and their dispositions" in VERIFY
