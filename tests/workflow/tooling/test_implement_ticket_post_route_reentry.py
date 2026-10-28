from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
REENTRY_SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/post_route_reentry.py"
ATTENTION_SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/attention_gate.py"

REENTRY_SPEC = importlib.util.spec_from_file_location(
    "implement_ticket_post_route_reentry",
    REENTRY_SCRIPT,
)
assert REENTRY_SPEC and REENTRY_SPEC.loader
REENTRY = importlib.util.module_from_spec(REENTRY_SPEC)
sys.modules[REENTRY_SPEC.name] = REENTRY
REENTRY_SPEC.loader.exec_module(REENTRY)

ATTENTION_SPEC = importlib.util.spec_from_file_location(
    "implement_ticket_attention_post_route",
    ATTENTION_SCRIPT,
)
assert ATTENTION_SPEC and ATTENTION_SPEC.loader
ATTENTION = importlib.util.module_from_spec(ATTENTION_SPEC)
sys.modules[ATTENTION_SPEC.name] = ATTENTION
ATTENTION_SPEC.loader.exec_module(ATTENTION)

CONTRACT_HASH = "a" * 64
ATTENTION_HASH = "b" * 64


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def _setup_repo(tmp_path: Path) -> tuple[Path, str, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "init", "-b", "spec-1"],
        check=True,
        capture_output=True,
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    product = repo / "src/product.py"
    product.parent.mkdir(parents=True)
    product.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    anchor = _git(repo, "rev-parse", "HEAD")

    contract = repo / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "schema": "polaris.review-remediation-contract/v1",
                "remediation_contract_hash": CONTRACT_HASH,
            }
        ),
        encoding="utf-8",
    )
    return repo, anchor, product, contract


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


def _args(repo: Path, anchor: str, contract: Path) -> argparse.Namespace:
    return argparse.Namespace(
        ticket=465,
        contract=contract,
        baseline=anchor,
        branch="spec-1",
        execution_anchor=anchor,
        remote="origin",
        default_branch="main",
        receipt=repo / "attention-receipt.json",
        attention_result=repo / "attention-result.json",
        feasibility=repo / "feasibility.json",
        route_return=repo / "route-return.json",
    )


def test_dirty_exact_failed_candidate_can_pass_post_route_reentry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, anchor, product, contract = _setup_repo(tmp_path)
    product.write_text("VALUE = 2\n", encoding="utf-8")

    with _Chdir(repo):
        failed_state = REENTRY._impl.candidate_state(anchor)
        monkeypatch.setattr(
            REENTRY._impl,
            "_fetch_remote_branch",
            lambda _remote, _branch: anchor,
        )
        monkeypatch.setattr(REENTRY, "_validate_feasibility", lambda *a, **k: None)
        monkeypatch.setattr(
            REENTRY,
            "_validate_route_return",
            lambda *a, **k: {"failed_candidate_state": failed_state},
        )
        monkeypatch.setattr(
            REENTRY._impl,
            "_attention_result",
            lambda _path, _checkpoint: ("PASS", ATTENTION_HASH),
        )

        receipt = REENTRY.record_post_route_reentry(_args(repo, anchor, contract))

        assert receipt["pre_mutation"]["candidate_state"] == failed_state
        assert receipt["pre_mutation"]["attention_status"] == "PASS"
        assert product.read_text(encoding="utf-8") == "VALUE = 2\n"
        assert _git(repo, "status", "--porcelain") != ""


def test_post_route_reentry_rejects_candidate_state_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, anchor, product, contract = _setup_repo(tmp_path)
    product.write_text("VALUE = 2\n", encoding="utf-8")

    with _Chdir(repo):
        monkeypatch.setattr(
            REENTRY._impl,
            "_fetch_remote_branch",
            lambda _remote, _branch: anchor,
        )
        monkeypatch.setattr(REENTRY, "_validate_feasibility", lambda *a, **k: None)
        monkeypatch.setattr(
            REENTRY,
            "_validate_route_return",
            lambda *a, **k: {"failed_candidate_state": "f" * 64},
        )

        with pytest.raises(
            REENTRY.PostRouteReentryError,
            match="candidate state differs from returned failed candidate",
        ):
            REENTRY.record_post_route_reentry(_args(repo, anchor, contract))


def test_ordinary_pre_mutation_remains_clean_only(tmp_path: Path) -> None:
    repo, anchor, product, contract = _setup_repo(tmp_path)
    product.write_text("VALUE = 2\n", encoding="utf-8")
    args = argparse.Namespace(
        ticket=465,
        contract=contract,
        baseline=anchor,
        branch="spec-1",
        remote="origin",
    )

    with _Chdir(repo), pytest.raises(
        REENTRY._impl.AttentionGateError,
        match="pre-mutation gate requires a clean worktree",
    ):
        REENTRY._impl.record_pre_mutation(args)


def test_obsolete_pre_mutation_route_return_path_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        ATTENTION,
        "_validate_pre_mutation_feasibility",
        lambda _path, _argv: None,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "attention_gate.py",
            "pre-mutation",
            "--feasibility",
            "feasibility.json",
            "--route-return",
            "route-return.json",
        ],
    )

    assert ATTENTION.main() == 2
    output = capsys.readouterr().out
    assert "ordinary pre-mutation --route-return is not a post-route entry path" in output
    assert "post_route_reentry.py" in output


def test_policy_requires_reentry_before_ready_consumption() -> None:
    policy = (ROOT / ".agents/skills/implement-ticket/POST_ROUTE_RETURN.md").read_text(
        encoding="utf-8"
    )
    assert "Post-route re-entry is distinct from ordinary pre-mutation" in policy
    assert "Consume READY only after re-entry succeeds" in policy
    assert "POST-ROUTE REENTRY VALID" in policy
    mandatory = policy.split("The order is mandatory:", 1)[1]
    assert mandatory.index("POST-ROUTE REENTRY VALID") < mandatory.index(
        "READY -> IN_PROGRESS"
    )
