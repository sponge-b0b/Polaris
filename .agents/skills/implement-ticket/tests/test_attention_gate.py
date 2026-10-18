from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "attention_gate.py"
SPEC = importlib.util.spec_from_file_location("implement_ticket_attention_gate", SCRIPT)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def _setup_repo(tmp_path: Path) -> tuple[Path, str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "init", "-b", "main"],
        check=True,
        capture_output=True,
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "product.txt").write_text("base\n", encoding="utf-8")
    skill = repo / ".agents/skills/implement-ticket/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("v1\n", encoding="utf-8")
    contract = repo / "ticket.json"
    contract.write_text(
        json.dumps(
            {
                "schema": "polaris.ticket-contract/v1",
                "ticket_contract_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    baseline = _git(repo, "rev-parse", "HEAD")
    _git(repo, "branch", "spec-1")
    return repo, baseline, contract


def _args(
    repo: Path,
    baseline: str,
    contract: Path,
    checkpoint: str,
    receipt: Path,
) -> argparse.Namespace:
    attention = repo.parent / f"{checkpoint}.txt"
    attention.write_text(
        "ATTENTION: CLEAR\n"
        f"Checkpoint: $implement-ticket {checkpoint}\n"
        "Material concerns: 0\n",
        encoding="utf-8",
    )
    return argparse.Namespace(
        ticket=1,
        contract=contract,
        baseline=baseline,
        branch="spec-1",
        receipt=receipt,
        attention_result=attention,
        default_ref="main",
    )


class _Chdir:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous: str | None = None

    def __enter__(self) -> None:
        self.previous = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, *_: object) -> None:
        assert self.previous is not None
        os.chdir(self.previous)


def test_pre_mutation_rejects_product_delta(tmp_path: Path) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    args = _args(repo, baseline, contract, "pre-mutation", repo / ".git/receipt.json")
    (repo / "product.txt").write_text("changed\n", encoding="utf-8")
    with _Chdir(repo), pytest.raises(GATE.AttentionGateError, match="clean worktree"):
        GATE.record_pre_mutation(args)


def test_preclosure_binds_exact_candidate_and_stales_after_mutation(
    tmp_path: Path,
) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    receipt = repo / ".git/receipt.json"
    pre = _args(repo, baseline, contract, "pre-mutation", receipt)
    with _Chdir(repo):
        GATE.record_pre_mutation(pre)
    (repo / "product.txt").write_text("implemented\n", encoding="utf-8")
    close = _args(repo, baseline, contract, "pre-closure", receipt)
    with _Chdir(repo):
        closed = GATE.record_pre_closure(close)
        close.expected_receipt_hash = GATE.receipt_hash(closed)
        GATE.verify(close)
    (repo / "product.txt").write_text("mutated-after-attention\n", encoding="utf-8")
    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="candidate state is stale",
    ):
        GATE.verify(close)


def test_policy_only_committed_sync_is_admissible(tmp_path: Path) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    skill = repo / ".agents/skills/implement-ticket/SKILL.md"
    skill.write_text("v2\n", encoding="utf-8")
    _git(repo, "add", str(skill.relative_to(repo)))
    _git(repo, "commit", "-m", "policy")
    main_tip = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "spec-1")
    _git(repo, "merge", "--no-ff", "main", "-m", "sync")
    receipt = repo / ".git/receipt.json"
    pre = _args(repo, baseline, contract, "pre-mutation", receipt)
    pre.default_ref = main_tip
    with _Chdir(repo):
        result = GATE.record_pre_mutation(pre)
    assert result["pre_mutation"]["head"] == _git(repo, "rev-parse", "HEAD")


def test_pre_mutation_rejects_non_policy_committed_delta(tmp_path: Path) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    (repo / "product.txt").write_text("main product change\n", encoding="utf-8")
    _git(repo, "add", "product.txt")
    _git(repo, "commit", "-m", "product")
    main_tip = _git(repo, "rev-parse", "HEAD")
    _git(repo, "switch", "spec-1")
    _git(repo, "merge", "--no-ff", "main", "-m", "sync")
    pre = _args(repo, baseline, contract, "pre-mutation", repo / ".git/receipt.json")
    pre.default_ref = main_tip
    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="not an admissible",
    ):
        GATE.record_pre_mutation(pre)


def test_wrong_attention_checkpoint_is_rejected(tmp_path: Path) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    pre = _args(repo, baseline, contract, "pre-mutation", repo / ".git/receipt.json")
    pre.attention_result.write_text(
        "ATTENTION: CLEAR\n"
        "Checkpoint: $implement-ticket during implementation\n"
        "Material concerns: 0\n",
        encoding="utf-8",
    )
    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="formal receipt",
    ):
        GATE.record_pre_mutation(pre)


def test_nonblocking_findings_are_bindable_but_blocking_findings_are_not(
    tmp_path: Path,
) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    pre = _args(repo, baseline, contract, "pre-mutation", repo / ".git/receipt.json")
    pre.attention_result.write_text(
        "ATTENTION: FINDINGS\n"
        "Checkpoint: $implement-ticket pre-mutation\n\n"
        "1. Separate drift\n"
        "   Observation: Something worth preserving.\n"
        "   Why it matters: Future maintainability.\n"
        "   Authority: resolved.\n"
        "   Recommendation/routing: defer.\n"
        "   Blocking basis: none\n",
        encoding="utf-8",
    )
    with _Chdir(repo):
        result = GATE.record_pre_mutation(pre)
    assert result["pre_mutation"]["attention_status"] == "findings-nonblocking"

    pre.attention_result.write_text(
        "ATTENTION: FINDINGS\n"
        "Checkpoint: $implement-ticket pre-mutation\n\n"
        "1. Blocking gap\n"
        "   Blocking basis: existing workflow rule\n",
        encoding="utf-8",
    )
    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="unresolved blocking",
    ):
        GATE.record_pre_mutation(pre)


def test_remediation_contract_identity_is_supported(tmp_path: Path) -> None:
    contract = tmp_path / "remediation.json"
    contract.write_text(
        json.dumps(
            {
                "schema": "polaris.review-remediation-contract/v1",
                "remediation_contract_hash": "b" * 64,
            }
        ),
        encoding="utf-8",
    )
    assert GATE._contract_identity(contract) == (
        "polaris.review-remediation-contract/v1",
        "b" * 64,
    )


def test_verify_rejects_wrong_frozen_receipt_hash(tmp_path: Path) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    receipt = repo / ".git/receipt.json"
    pre = _args(repo, baseline, contract, "pre-mutation", receipt)
    with _Chdir(repo):
        GATE.record_pre_mutation(pre)
    (repo / "product.txt").write_text("implemented\n", encoding="utf-8")
    close = _args(repo, baseline, contract, "pre-closure", receipt)
    close.expected_receipt_hash = "0" * 64
    with _Chdir(repo):
        GATE.record_pre_closure(close)
        with pytest.raises(GATE.AttentionGateError, match="hash mismatch"):
            GATE.verify(close)


def test_preclosure_rejects_commit_after_pre_mutation_gate(tmp_path: Path) -> None:
    repo, baseline, contract = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    receipt = repo / ".git/receipt.json"
    pre = _args(repo, baseline, contract, "pre-mutation", receipt)
    with _Chdir(repo):
        GATE.record_pre_mutation(pre)
    (repo / "product.txt").write_text("implemented\n", encoding="utf-8")
    _git(repo, "add", "product.txt")
    _git(repo, "commit", "-m", "premature product commit")
    close = _args(repo, baseline, contract, "pre-closure", receipt)
    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="HEAD changed after pre-mutation",
    ):
        GATE.record_pre_closure(close)
