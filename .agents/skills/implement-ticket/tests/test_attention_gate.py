from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
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


def _setup_repo(tmp_path: Path) -> tuple[Path, str, Path, Path]:
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )
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
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "main", "spec-1")
    return repo, baseline, contract, remote


def _attention(tmp_path: Path, checkpoint: str) -> Path:
    path = tmp_path / f"{checkpoint}.txt"
    path.write_text(
        "ATTENTION: CLEAR\n"
        f"Checkpoint: $implement-ticket {checkpoint}\n"
        "Material concerns: 0\n",
        encoding="utf-8",
    )
    return path


def _pre_args(
    repo: Path,
    baseline: str,
    contract: Path,
    tmp_path: Path,
) -> argparse.Namespace:
    return argparse.Namespace(
        ticket=1,
        contract=contract,
        baseline=baseline,
        branch="spec-1",
        receipt=repo / ".git/receipt.json",
        attention_result=_attention(tmp_path, "pre-mutation"),
        remote="origin",
    )


def _close_args(
    repo: Path,
    baseline: str,
    contract: Path,
    tmp_path: Path,
    execution_anchor: str,
) -> argparse.Namespace:
    return argparse.Namespace(
        ticket=1,
        contract=contract,
        baseline=baseline,
        branch="spec-1",
        receipt=repo / ".git/receipt.json",
        attention_result=_attention(tmp_path, "pre-closure"),
        execution_anchor=execution_anchor,
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


def test_pre_mutation_rejects_dirty_candidate(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    args = _pre_args(repo, baseline, contract, tmp_path)
    (repo / "product.txt").write_text("changed\n", encoding="utf-8")
    with _Chdir(repo), pytest.raises(GATE.AttentionGateError, match="clean worktree"):
        GATE.record_pre_mutation(args)


def test_committed_shared_branch_advancement_after_baseline_is_admissible(
    tmp_path: Path,
) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    (repo / "accepted-authority.txt").write_text("accepted\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "accepted upstream authority")
    _git(repo, "push")
    with _Chdir(repo):
        receipt = GATE.record_pre_mutation(_pre_args(repo, baseline, contract, tmp_path))
    assert receipt["schema"] == "polaris.implement-ticket-attention/v2"
    assert receipt["baseline"] == baseline
    assert receipt["execution_anchor"] == _git(repo, "rev-parse", "HEAD")


def test_pre_mutation_fetches_and_rejects_stale_local_head(tmp_path: Path) -> None:
    repo, baseline, contract, remote = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")

    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", str(remote), str(other)],
        check=True,
        capture_output=True,
    )
    _git(other, "config", "user.email", "test@example.com")
    _git(other, "config", "user.name", "Test")
    _git(other, "switch", "spec-1")
    (other / "upstream.txt").write_text("new remote state\n", encoding="utf-8")
    _git(other, "add", ".")
    _git(other, "commit", "-m", "remote advancement")
    _git(other, "push")

    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="does not equal fetched remote branch tip",
    ):
        GATE.record_pre_mutation(_pre_args(repo, baseline, contract, tmp_path))


def test_pre_mutation_rejects_unpushed_local_commit(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    (repo / "local-only.txt").write_text("not durable\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "local ahead")
    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="does not equal fetched remote branch tip",
    ):
        GATE.record_pre_mutation(_pre_args(repo, baseline, contract, tmp_path))


def test_candidate_state_is_relative_to_execution_anchor(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    (repo / "upstream.txt").write_text("already durable\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "upstream")
    _git(repo, "push")

    with _Chdir(repo):
        pre = GATE.record_pre_mutation(_pre_args(repo, baseline, contract, tmp_path))
    anchor = pre["execution_anchor"]
    (repo / "product.txt").write_text("ticket candidate\n", encoding="utf-8")
    close = _close_args(repo, baseline, contract, tmp_path, anchor)
    with _Chdir(repo):
        closed = GATE.record_pre_closure(close)
        assert closed["pre_closure"]["candidate_state"] == GATE.candidate_state(anchor)
        assert GATE.candidate_state(anchor) != GATE.candidate_state(baseline)


def test_preclosure_binds_exact_candidate_and_stales_after_mutation(
    tmp_path: Path,
) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    with _Chdir(repo):
        pre = GATE.record_pre_mutation(_pre_args(repo, baseline, contract, tmp_path))
    anchor = pre["execution_anchor"]
    (repo / "product.txt").write_text("implemented\n", encoding="utf-8")
    close = _close_args(repo, baseline, contract, tmp_path, anchor)
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


def test_preclosure_rejects_commit_after_pre_mutation_gate(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    with _Chdir(repo):
        pre = GATE.record_pre_mutation(_pre_args(repo, baseline, contract, tmp_path))
    anchor = pre["execution_anchor"]
    (repo / "product.txt").write_text("implemented\n", encoding="utf-8")
    _git(repo, "add", "product.txt")
    _git(repo, "commit", "-m", "premature product commit")
    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="HEAD changed after pre-mutation",
    ):
        GATE.record_pre_closure(_close_args(repo, baseline, contract, tmp_path, anchor))


def test_wrong_attention_checkpoint_is_rejected(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    pre = _pre_args(repo, baseline, contract, tmp_path)
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


def test_nonblocking_findings_bind_but_blocking_findings_do_not(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    pre = _pre_args(repo, baseline, contract, tmp_path)
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


def test_verify_rejects_wrong_execution_anchor_and_receipt_hash(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    (repo / "upstream.txt").write_text("durable before ticket\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "upstream")
    _git(repo, "push")
    with _Chdir(repo):
        pre = GATE.record_pre_mutation(_pre_args(repo, baseline, contract, tmp_path))
    anchor = pre["execution_anchor"]
    (repo / "product.txt").write_text("implemented\n", encoding="utf-8")
    close = _close_args(repo, baseline, contract, tmp_path, anchor)
    with _Chdir(repo):
        closed = GATE.record_pre_closure(close)
        close.expected_receipt_hash = "0" * 64
        with pytest.raises(GATE.AttentionGateError, match="hash mismatch"):
            GATE.verify(close)
        close.expected_receipt_hash = GATE.receipt_hash(closed)
        close.execution_anchor = baseline
        with pytest.raises(GATE.AttentionGateError, match="execution anchor mismatch"):
            GATE.verify(close)


def test_direct_cli_invocation_needs_no_pythonpath(tmp_path: Path) -> None:
    repo, baseline, contract, _ = _setup_repo(tmp_path)
    _git(repo, "switch", "spec-1")
    attention = _attention(tmp_path, "pre-mutation")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "pre-mutation",
            "--ticket",
            "1",
            "--contract",
            str(contract),
            "--baseline",
            baseline,
            "--branch",
            "spec-1",
            "--attention-result",
            str(attention),
            "--receipt",
            str(repo / ".git/direct.json"),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "IMPLEMENT TICKET ATTENTION: PRE-MUTATION VALID" in result.stdout
    assert "Execution Anchor:" in result.stdout
