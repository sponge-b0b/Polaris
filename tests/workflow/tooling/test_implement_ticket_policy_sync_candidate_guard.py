from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/candidate_guard.py"
SPEC = importlib.util.spec_from_file_location(
    "implement_ticket_policy_sync_candidate_guard",
    SCRIPT,
)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GUARD
SPEC.loader.exec_module(GUARD)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def _setup(tmp_path: Path) -> tuple[Path, str, Path, Path]:
    repo = tmp_path / "repo"
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


def test_authorized_committed_policy_sync_is_not_ticket_candidate(
    tmp_path: Path,
) -> None:
    repo, anchor, policy, product = _setup(tmp_path)
    product.write_text("VALUE = 2\n", encoding="utf-8")

    with _Chdir(repo):
        assert GUARD.authorized_policy_sync_paths(anchor) == (
            str(policy.relative_to(repo)),
        )
        assert GUARD.validate_delivery_tip(anchor) == (
            str(policy.relative_to(repo)),
        )
        assert GUARD.validate_candidate(anchor) == (str(product.relative_to(repo)),)


def test_delivery_tip_rejects_committed_product_advance(tmp_path: Path) -> None:
    repo, anchor, _policy, product = _setup(tmp_path)
    product.write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", str(product.relative_to(repo)))
    _git(repo, "commit", "-m", "committed product change")

    with _Chdir(repo), pytest.raises(
        GUARD.CandidateGuardError,
        match="not authorized policy synchronization",
    ):
        GUARD.validate_delivery_tip(anchor)


def test_local_edit_to_synced_policy_is_still_rejected(tmp_path: Path) -> None:
    repo, anchor, policy, _product = _setup(tmp_path)
    policy.write_text("ticket-local-policy-edit\n", encoding="utf-8")

    with _Chdir(repo), pytest.raises(
        GUARD.CandidateGuardError,
        match="protected workflow/control-plane path",
    ):
        GUARD.validate_candidate(anchor)


def test_policy_blob_must_match_current_default_branch(tmp_path: Path) -> None:
    repo, anchor, policy, _product = _setup(tmp_path)
    policy.write_text("different-policy\n", encoding="utf-8")
    _git(repo, "add", str(policy.relative_to(repo)))
    _git(repo, "commit", "-m", "different sync")

    with _Chdir(repo), pytest.raises(
        GUARD.CandidateGuardError,
        match="protected workflow/control-plane path",
    ):
        GUARD.validate_candidate(anchor)


def test_policy_touching_commit_cannot_smuggle_product_change(tmp_path: Path) -> None:
    repo, anchor, policy, product = _setup(tmp_path)
    _git(repo, "reset", "--hard", anchor)
    policy.write_text("policy-v2\n", encoding="utf-8")
    product.write_text("VALUE = 99\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "mixed policy and product")

    with _Chdir(repo), pytest.raises(
        GUARD.CandidateGuardError,
        match="protected workflow/control-plane path",
    ):
        GUARD.validate_candidate(anchor)


def test_restore_preserves_committed_policy_sync(tmp_path: Path) -> None:
    repo, anchor, policy, _product = _setup(tmp_path)
    policy.write_text("dirty-policy\n", encoding="utf-8")

    with _Chdir(repo):
        assert GUARD.restore_protected(anchor) == (str(policy.relative_to(repo)),)
        assert policy.read_text(encoding="utf-8") == "policy-v2\n"
        assert GUARD.validate_candidate(anchor) == ()


def test_documented_candidate_guard_runs_without_pythonpath(tmp_path: Path) -> None:
    repo, anchor, _policy, product = _setup(tmp_path)
    product.write_text("VALUE = 2\n", encoding="utf-8")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "check",
            "--anchor",
            anchor,
            "--remote",
            "origin",
            "--default-branch",
            "main",
        ],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "WORKFLOW CANDIDATE GUARD: VALID" in result.stdout
    assert "Protected control-plane paths: 0" in result.stdout
