from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/workflow_reslice_recovery.py"

spec = importlib.util.spec_from_file_location("workflow_reslice_recovery", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
HASH_A = "d" * 64
HASH_B = "e" * 64


def record(
    *,
    status: str = "pending-prerequisite",
    order: str = "#404 → #405 → #406",
    explicit_order: str | None = "source-first",
    source_completion: str = "Pending",
    destination_baseline: str = "Pending",
    destination_completion: str = "Pending",
) -> str:
    execution_line = (
        f"**Execution order:** {explicit_order}\n" if explicit_order is not None else ""
    )
    return f"""<!-- ticket-reslice-recovery:v1 -->
## Ticket Reslice Recovery

**Status:** {status}
**Parent Spec:** #359
**Source ticket:** #404
**Destination ticket:** #406
**Shared branch:** spec-359
**Source ticket baseline:** {SHA_A}
**Reslice branch anchor:** {SHA_B}
**Recovery mode:** isolated-worktree
**Native execution order:** {order}
{execution_line}**Protected donor checkout:** /tmp/donor
**Protected donor HEAD / Execution Anchor:** {SHA_A}
**Protected donor candidate state:** {HASH_A}
**Protected donor Attention receipt file SHA-256:** {HASH_B}
**Source completion commit:** {source_completion}
**Destination baseline:** {destination_baseline}
**Destination completion commit:** {destination_completion}

### Exact donor attribution at capture

| Donor path | Current hunk(s) or untracked SHA-256 | Attribution | Disposition |
| --- | --- | --- | --- |
| `src/example.py` | +1 | source | Preserve source |
"""


def test_source_first_pending_is_valid() -> None:
    parsed = module.parse_record(record())
    assert parsed.execution_order == "source-first"
    assert parsed.status == "pending-prerequisite"


def test_legacy_missing_execution_order_is_derived() -> None:
    parsed = module.parse_record(record(explicit_order=None))
    assert parsed.execution_order == "source-first"
    assert parsed.execution_order_source == "derived-legacy"


def test_source_first_source_complete_is_valid() -> None:
    parsed = module.parse_record(
        record(status="source-complete", source_completion=SHA_C)
    )
    assert parsed.source_completion == SHA_C


def test_destination_first_prerequisite_complete_is_valid() -> None:
    parsed = module.parse_record(
        record(
            status="prerequisite-complete",
            order="#406 → #404",
            explicit_order="destination-first",
            destination_baseline=SHA_B,
            destination_completion=SHA_C,
        )
    )
    assert parsed.execution_order == "destination-first"


def test_source_first_cannot_use_prerequisite_complete() -> None:
    try:
        module.parse_record(
            record(
                status="prerequisite-complete",
                destination_baseline=SHA_B,
                destination_completion=SHA_C,
            )
        )
    except module.RecoveryError as exc:
        assert "destination-first" in str(exc)
    else:
        raise AssertionError(
            "expected invalid source-first prerequisite-complete state"
        )


def test_terminal_requires_both_completion_commits() -> None:
    try:
        module.parse_record(record(status="source-reconciled", source_completion=SHA_C))
    except module.RecoveryError as exc:
        assert "both exact completion" in str(exc)
    else:
        raise AssertionError("expected incomplete terminal state to fail")


def test_terminal_source_first_is_valid() -> None:
    parsed = module.parse_record(
        record(
            status="source-reconciled",
            source_completion=SHA_A,
            destination_baseline=SHA_B,
            destination_completion=SHA_C,
        )
    )
    assert parsed.status == "source-reconciled"
