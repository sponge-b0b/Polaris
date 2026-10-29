from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/attention_gate.py"
SPEC = importlib.util.spec_from_file_location("implement_ticket_attention_guarded", SCRIPT)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def _setup_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "init", "-b", "spec-1"],
        check=True,
        capture_output=True,
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    protected = repo / ".agents/skills/example/SKILL.md"
    protected.parent.mkdir(parents=True)
    protected.write_text("base\n", encoding="utf-8")
    product = repo / "src/product.py"
    product.parent.mkdir(parents=True)
    product.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo, _git(repo, "rev-parse", "HEAD")


def _setup_policy_sync_repo(tmp_path: Path) -> tuple[Path, str, Path, Path]:
    repo = tmp_path / "policy-repo"
    repo.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "init", "-b", "main"],
        check=True,
        capture_output=True,
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")

    policy = repo / ".agents/skills/example/SKILL.md"
    policy.parent.mkdir(parents=True)
    policy.write_text("policy-v1\n", encoding="utf-8")
    product = repo / "src/product.py"
    product.parent.mkdir(parents=True)
    product.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    anchor = _git(repo, "rev-parse", "HEAD")

    policy.write_text("policy-v2\n", encoding="utf-8")
    _git(repo, "add", str(policy.relative_to(repo)))
    _git(repo, "commit", "-m", "default policy")
    default_head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", default_head)

    _git(repo, "checkout", "-b", "spec-1", anchor)
    policy.write_text("policy-v2\n", encoding="utf-8")
    _git(repo, "add", str(policy.relative_to(repo)))
    _git(repo, "commit", "-m", "sync policy")
    product.write_text("VALUE = 2\n", encoding="utf-8")
    return repo, anchor, policy, product


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


def test_preclosure_machine_gate_rejects_protected_candidate(
    tmp_path: Path,
) -> None:
    repo, anchor = _setup_repo(tmp_path)
    (repo / ".agents/skills/example/SKILL.md").write_text(
        "unauthorized\n", encoding="utf-8"
    )
    args = argparse.Namespace(execution_anchor=anchor)

    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="protected workflow/control-plane path",
    ):
        GATE.record_pre_closure(args)


def test_preclosure_wrapper_allows_product_candidate_to_reach_retained_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor = _setup_repo(tmp_path)
    (repo / "src/product.py").write_text("VALUE = 2\n", encoding="utf-8")
    sentinel = {"ok": True}
    monkeypatch.setattr(GATE, "_original_record_pre_closure", lambda _args: sentinel)
    args = argparse.Namespace(execution_anchor=anchor)

    with _Chdir(repo):
        assert GATE.record_pre_closure(args) is sentinel


def test_preclosure_and_verify_allow_exact_main_policy_sync_after_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor, _policy, product = _setup_policy_sync_repo(tmp_path)
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "schema": "polaris.ticket-contract/v1",
                "ticket_contract_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    receipt_path = tmp_path / "attention-receipt.json"
    attention_path = tmp_path / "attention.txt"
    receipt_path.write_text(
        json.dumps(
            {
                "schema": GATE.SCHEMA,
                "ticket": 1,
                "branch": "spec-1",
                "baseline": anchor,
                "execution_anchor": anchor,
                "remote": "origin",
                "contract_schema": "polaris.ticket-contract/v1",
                "contract_hash": "a" * 64,
                "pre_mutation": {
                    "head": anchor,
                    "candidate_state": "0" * 64,
                    "attention_status": "NONBLOCKING",
                    "attention_result_sha256": "b" * 64,
                },
                "pre_closure": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        GATE._impl,
        "_attention_result",
        lambda _path, _checkpoint: ("NONBLOCKING", "c" * 64),
    )
    args = argparse.Namespace(
        ticket=1,
        contract=contract,
        baseline=anchor,
        branch="spec-1",
        execution_anchor=anchor,
        receipt=receipt_path,
        attention_result=attention_path,
    )

    with _Chdir(repo):
        expected_state = GATE.candidate_state(anchor)
        preclosure = GATE.record_pre_closure(args)
        assert preclosure["pre_closure"]["head"] != anchor
        assert preclosure["pre_closure"]["candidate_state"] == expected_state
        assert expected_state == GATE.candidate_state(anchor)
        assert GATE._impl._candidate_paths(anchor) == [os.fsencode(product.relative_to(repo))]

        verify_args = argparse.Namespace(
            ticket=1,
            contract=contract,
            baseline=anchor,
            branch="spec-1",
            execution_anchor=anchor,
            receipt=receipt_path,
            expected_receipt_hash=GATE.receipt_hash(preclosure),
        )
        assert GATE.verify(verify_args)["pre_closure"]["candidate_state"] == expected_state


def test_preclosure_rejects_committed_product_advance_after_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor, _policy, product = _setup_policy_sync_repo(tmp_path)
    _git(repo, "add", str(product.relative_to(repo)))
    _git(repo, "commit", "-m", "commit product")
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "schema": "polaris.ticket-contract/v1",
                "ticket_contract_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    receipt_path = tmp_path / "attention-receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema": GATE.SCHEMA,
                "ticket": 1,
                "branch": "spec-1",
                "baseline": anchor,
                "execution_anchor": anchor,
                "remote": "origin",
                "contract_schema": "polaris.ticket-contract/v1",
                "contract_hash": "a" * 64,
                "pre_mutation": {
                    "head": anchor,
                    "candidate_state": "0" * 64,
                    "attention_status": "NONBLOCKING",
                    "attention_result_sha256": "b" * 64,
                },
                "pre_closure": None,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        GATE._impl,
        "_attention_result",
        lambda _path, _checkpoint: ("NONBLOCKING", "c" * 64),
    )
    args = argparse.Namespace(
        ticket=1,
        contract=contract,
        baseline=anchor,
        branch="spec-1",
        execution_anchor=anchor,
        receipt=receipt_path,
        attention_result=tmp_path / "attention.txt",
    )

    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="not authorized policy synchronization",
    ):
        GATE.record_pre_closure(args)
