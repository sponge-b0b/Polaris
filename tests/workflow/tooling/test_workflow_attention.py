from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.workflow_attention import AttentionProtocolError, validate_text  # noqa: E402

CHECKPOINT = "$to-tickets pre-publication"


def test_clear_exact_form_is_valid() -> None:
    receipt = validate_text(
        "\n".join(
            (
                "ATTENTION: CLEAR",
                f"Checkpoint: {CHECKPOINT}",
                "Material concerns: 0",
            )
        ),
        checkpoint=CHECKPOINT,
        require_nonblocking=True,
    )
    assert receipt.status == "clear"
    assert receipt.finding_count == 0


def test_complete_is_not_a_formal_attention_result() -> None:
    with pytest.raises(AttentionProtocolError, match="unsupported formal result header"):
        validate_text(
            "ATTENTION: COMPLETE",
            checkpoint=CHECKPOINT,
            require_nonblocking=True,
        )


def test_nonblocking_findings_require_complete_shape() -> None:
    receipt = validate_text(
        """ATTENTION: FINDINGS
Checkpoint: $to-tickets pre-publication

1. Stale routed blocker.
   Observation: The ticket still records a routed blocker.
   Why it matters: The ticket is not implementation-actionable yet.
   Authority: Resolved by current accepted authority.
   Recommendation/routing: Reconcile blocker state before implementation handoff.
   Blocking basis: none
""",
        checkpoint=CHECKPOINT,
        require_nonblocking=True,
    )
    assert receipt.status == "findings-nonblocking"
    assert receipt.finding_count == 1


@pytest.mark.parametrize(
    "field",
    [
        "Observation",
        "Why it matters",
        "Authority",
        "Recommendation/routing",
        "Blocking basis",
    ],
)
def test_findings_missing_required_field_are_rejected(field: str) -> None:
    fields = {
        "Observation": "The ticket still records a routed blocker.",
        "Why it matters": "The ticket is not implementation-actionable yet.",
        "Authority": "Resolved by current accepted authority.",
        "Recommendation/routing": "Reconcile blocker state before implementation handoff.",
        "Blocking basis": "none",
    }
    del fields[field]
    body = [
        "ATTENTION: FINDINGS",
        f"Checkpoint: {CHECKPOINT}",
        "",
        "1. Stale routed blocker.",
    ]
    body.extend(f"   {name}: {value}" for name, value in fields.items())
    with pytest.raises(AttentionProtocolError, match=f"missing {field}"):
        validate_text(
            "\n".join(body),
            checkpoint=CHECKPOINT,
            require_nonblocking=True,
        )


def test_blocking_finding_fails_nonblocking_gate() -> None:
    with pytest.raises(AttentionProtocolError, match="unresolved blocking finding"):
        validate_text(
            """ATTENTION: FINDINGS
Checkpoint: $to-tickets pre-publication

1. Material design gap.
   Observation: A public contract is unresolved.
   Why it matters: Ticketing would delegate design to implementation.
   Authority: unresolved
   Recommendation/routing: Return to the owning planning workflow.
   Blocking basis: Design-to-Implementation Boundary
""",
            checkpoint=CHECKPOINT,
            require_nonblocking=True,
        )


def test_checkpoint_mismatch_is_rejected() -> None:
    with pytest.raises(AttentionProtocolError, match="expected formal FINDINGS receipt"):
        validate_text(
            """ATTENTION: FINDINGS
Checkpoint: $to-specs frontier handoff

1. Concern.
   Observation: x
   Why it matters: y
   Authority: z
   Recommendation/routing: q
   Blocking basis: none
""",
            checkpoint=CHECKPOINT,
            require_nonblocking=True,
        )


def test_cli_emits_machine_receipt_for_nonblocking_result(tmp_path: Path) -> None:
    result_path = tmp_path / "attention.txt"
    result_path.write_text(
        "\n".join(
            (
                "ATTENTION: CLEAR",
                f"Checkpoint: {CHECKPOINT}",
                "Material concerns: 0",
            )
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.workflow_attention",
            "validate",
            "--result",
            str(result_path),
            "--checkpoint",
            CHECKPOINT,
            "--require-nonblocking",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    lines = completed.stdout.splitlines()
    assert lines[0] == "ATTENTION PROTOCOL: VALID"
    assert lines[1] == f"Checkpoint: {CHECKPOINT}"
    assert lines[2] == "Status: clear"
    assert lines[3] == "Finding count: 0"
    assert lines[4].startswith("Attention Result SHA-256: ")
