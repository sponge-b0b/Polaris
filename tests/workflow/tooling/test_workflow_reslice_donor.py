from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from scripts.workflow_reslice_donor import DonorValidationError, live_candidate_state
from scripts.workflow_reslice_donor import validate_live_donor
from scripts.workflow_reslice_recovery import parse_record

ROOT = Path(__file__).resolve().parents[3]
ATTENTION_SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/attention_gate.py"
ATTENTION_SPEC = importlib.util.spec_from_file_location(
    "implement_ticket_attention_for_reslice_test",
    ATTENTION_SCRIPT,
)
assert ATTENTION_SPEC and ATTENTION_SPEC.loader
ATTENTION_GATE = importlib.util.module_from_spec(ATTENTION_SPEC)
ATTENTION_SPEC.loader.exec_module(ATTENTION_GATE)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _receipt_path(repo: Path, ticket: int) -> Path:
    value = Path(
        _git(
            repo,
            "rev-parse",
            "--git-path",
            f"polaris/implement-ticket-attention/ticket-{ticket}.json",
        )
    )
    return value if value.is_absolute() else repo / value


def _write_canonical_receipt(repo: Path, ticket: int) -> str:
    value: dict[str, object] = {
        "schema": "polaris.implement-ticket-attention/v2",
        "ticket": ticket,
        "branch": "spec-359",
        "baseline": "a" * 40,
        "execution_anchor": "a" * 40,
        "remote": "origin",
        "contract_schema": "polaris.ticket-contract/v1",
        "contract_hash": "b" * 64,
        "pre_mutation": {
            "head": "a" * 40,
            "candidate_state": "c" * 64,
            "attention_status": "clear",
            "attention_result_sha256": "d" * 64,
        },
        "pre_closure": {
            "head": "a" * 40,
            "candidate_state": "e" * 64,
            "attention_status": "clear",
            "attention_result_sha256": "f" * 64,
        },
    }
    receipt = _receipt_path(repo, ticket)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    receipt.write_text(canonical + "\n", encoding="utf-8")
    return ATTENTION_GATE.receipt_hash(value)


def _make_donor(tmp_path: Path) -> tuple[Path, str, str, str]:
    repo = tmp_path / "donor"
    repo.mkdir()
    _git(repo, "init", "-b", "spec-359")
    _git(repo, "config", "user.name", "Workflow Test")
    _git(repo, "config", "user.email", "workflow@example.invalid")
    tracked = repo / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "base")
    head = _git(repo, "rev-parse", "HEAD")

    tracked.write_text("changed\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("preserved\n", encoding="utf-8")
    state = live_candidate_state(repo, head)

    receipt = _receipt_path(repo, 409)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_bytes(b'{"schema":"test-recovery-receipt"}\n')
    receipt_hash = hashlib.sha256(receipt.read_bytes()).hexdigest()
    return repo, head, state, receipt_hash


def _record(repo: Path, head: str, state: str, receipt_hash: str) -> str:
    return f"""<!-- ticket-reslice-recovery:v1 -->
## Ticket Reslice Recovery

**Status:** source-retired
**Parent Spec:** #359
**Destination Parent Spec:** #358
**Source ticket:** #409
**Destination ticket:** #399
**Source disposition:** retire
**Source branch:** spec-359
**Destination branch:** spec-358
**Source ticket baseline:** {head}
**Reslice branch anchor:** {head}
**Recovery mode:** isolated-worktree
**Native execution order:** #399
**Execution order:** destination-only
**Protected donor checkout:** {repo}
**Protected donor HEAD / Execution Anchor:** {head}
**Protected donor candidate state:** {state}
**Protected donor Attention receipt file SHA-256:** {receipt_hash}
**Source completion commit:** Not applicable
**Source retirement:** closed-not-planned
**Destination baseline:** Pending
**Destination completion commit:** Pending

### Exact donor attribution at capture

| Donor path | Current hunk(s) or untracked SHA-256 | Attribution | Disposition |
| --- | --- | --- | --- |
| `tracked.txt` | changed | destination ticket | transplant later |
| `untracked.txt` | untracked | destination ticket | transplant later |
"""


def test_live_donor_accepts_exact_branch_head_state_and_legacy_file_hash(
    tmp_path: Path,
) -> None:
    repo, head, state, receipt_hash = _make_donor(tmp_path)
    record = parse_record(_record(repo, head, state, receipt_hash))

    branch, observed_head, observed_state, observed_receipt = validate_live_donor(record)

    assert branch == "spec-359"
    assert observed_head == head
    assert observed_state == state
    assert observed_receipt == receipt_hash


def test_live_donor_accepts_canonical_attention_receipt_hash(tmp_path: Path) -> None:
    repo, head, state, _legacy_hash = _make_donor(tmp_path)
    receipt_hash = _write_canonical_receipt(repo, 409)
    record = parse_record(_record(repo, head, state, receipt_hash))

    _branch, _head, _state, observed_receipt = validate_live_donor(record)

    assert observed_receipt == receipt_hash
    assert hashlib.sha256(_receipt_path(repo, 409).read_bytes()).hexdigest() != receipt_hash


def test_live_donor_accepts_durable_receipt_identity_when_git_metadata_is_missing(
    tmp_path: Path,
) -> None:
    repo, head, state, receipt_hash = _make_donor(tmp_path)
    record = parse_record(_record(repo, head, state, receipt_hash))
    _receipt_path(repo, 409).unlink()

    _branch, _head, _state, observed_receipt = validate_live_donor(record)

    assert observed_receipt == receipt_hash


def test_live_donor_rejects_detached_checkout_even_when_bytes_match(tmp_path: Path) -> None:
    repo, head, state, receipt_hash = _make_donor(tmp_path)
    record = parse_record(_record(repo, head, state, receipt_hash))
    _git(repo, "checkout", "--detach", head)

    with pytest.raises(DonorValidationError, match="branch mismatch"):
        validate_live_donor(record)


def test_live_donor_rejects_changed_candidate_bytes(tmp_path: Path) -> None:
    repo, head, state, receipt_hash = _make_donor(tmp_path)
    record = parse_record(_record(repo, head, state, receipt_hash))
    (repo / "tracked.txt").write_text("different\n", encoding="utf-8")

    with pytest.raises(DonorValidationError, match="candidate state mismatch"):
        validate_live_donor(record)


def test_live_donor_rejects_changed_attention_receipt(tmp_path: Path) -> None:
    repo, head, state, receipt_hash = _make_donor(tmp_path)
    record = parse_record(_record(repo, head, state, receipt_hash))
    _receipt_path(repo, 409).write_text('{"schema":"changed"}\n', encoding="utf-8")

    with pytest.raises(DonorValidationError, match="Attention receipt mismatch"):
        validate_live_donor(record)
