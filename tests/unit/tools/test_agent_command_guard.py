from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tools.agent_command_guard.guard import BROAD_VERIFY_ENV, classify_command

REPO_ROOT = Path(__file__).resolve().parents[3]
CODEX_ENV = {"CODEX_CI": "1"}


def unauthorized_codex_subprocess_env(**overrides: str) -> dict[str, str]:
    env = {**os.environ, "CODEX_CI": "1", **overrides}
    env.pop(BROAD_VERIFY_ENV, None)
    return env


def test_blocks_full_uv_pytest_suite() -> None:
    decision = classify_command(
        ["uv", "run", "pytest", "-q"], cwd=REPO_ROOT, env=CODEX_ENV
    )

    assert not decision.allowed
    assert "broad default suite" in decision.reason


@pytest.mark.parametrize(
    "command",
    [
        ["uv", "run", "pytest"],
        ["uv", "run", "pytest", "tests"],
        ["uv", "run", "pytest", "tests/unit"],
        ["uv", "run", "pytest", "tests/integration"],
        ["uv", "run", "--frozen", "pytest", "-q"],
        ["uv", "run", "python", "-m", "pytest", "-q"],
        ["pytest", "--cov"],
        ["pytest", "--cov=application", "tests/unit/foo/test_bar.py"],
    ],
)
def test_blocks_broad_pytest_shapes(command: list[str]) -> None:
    decision = classify_command(command, cwd=REPO_ROOT, env=CODEX_ENV)

    assert not decision.allowed


@pytest.mark.parametrize(
    "command",
    [
        ["uv", "run", "pytest", "-q", "tests/unit/foo/test_bar.py"],
        ["uv", "run", "--frozen", "pytest", "-q", "tests/unit/foo/test_bar.py"],
        ["uv", "run", "python", "-m", "pytest", "-q", "tests/unit/foo/test_bar.py"],
        ["uv", "run", "pytest", "-q", "tests/unit/foo/test_bar.py::test_case"],
        ["pytest", "tests/unit/application/governance"],
        ["pytest", "tests/integration/core/storage/test_repo.py"],
    ],
)
def test_allows_targeted_pytest_shapes(command: list[str]) -> None:
    decision = classify_command(command, cwd=REPO_ROOT, env=CODEX_ENV)

    assert decision.allowed


@pytest.mark.parametrize(
    "command",
    [
        ["uv", "run", "mypy", "."],
        ["uv", "run", "mypy"],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "ruff", "format", "."],
        ["ruff", "check"],
    ],
)
def test_blocks_broad_static_verification(command: list[str]) -> None:
    decision = classify_command(command, cwd=REPO_ROOT, env=CODEX_ENV)

    assert not decision.allowed


@pytest.mark.parametrize(
    "command",
    [
        ["uv", "run", "mypy", "application/foo.py", "tests/unit/test_foo.py"],
        ["uv", "run", "ruff", "check", "application/foo.py"],
        ["uv", "run", "ruff", "format", "--check", "application/foo.py"],
        ["mypy", "--explicit-package-bases", "tools/agent_command_guard/guard.py"],
        ["ruff", "check", "tools/agent_command_guard/guard.py"],
    ],
)
def test_allows_targeted_static_verification(command: list[str]) -> None:
    decision = classify_command(command, cwd=REPO_ROOT, env=CODEX_ENV)

    assert decision.allowed


def test_authorization_env_allows_otherwise_broad_command() -> None:
    decision = classify_command(
        ["uv", "run", "pytest", "-q"],
        cwd=REPO_ROOT,
        env={BROAD_VERIFY_ENV: "owner-approved-for-current-task"},
    )

    assert decision.allowed
    assert BROAD_VERIFY_ENV in decision.reason


def test_outside_repo_passes_through_broad_command(tmp_path: Path) -> None:
    decision = classify_command(
        ["uv", "run", "pytest", "-q"], cwd=tmp_path, env=CODEX_ENV
    )

    assert decision.allowed
    assert decision.reason == "outside Polaris repository"


def test_without_codex_agent_env_passes_through_broad_command() -> None:
    decision = classify_command(["uv", "run", "pytest", "-q"], cwd=REPO_ROOT, env={})

    assert decision.allowed
    assert decision.reason == "outside Codex agent environment"


def test_uv_shim_blocks_before_real_executable(tmp_path: Path) -> None:
    fake_uv = tmp_path / "fake-uv"
    fake_uv.write_text("#!/usr/bin/env bash\necho should-not-run\n")
    fake_uv.chmod(0o755)

    result = subprocess.run(
        [str(REPO_ROOT / ".agents/command-guard/bin/uv"), "run", "pytest", "-q"],
        cwd=REPO_ROOT,
        env=unauthorized_codex_subprocess_env(POLARIS_REAL_UV=str(fake_uv)),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 126
    assert "blocked broad verification" in result.stderr
    assert "should-not-run" not in result.stdout


def test_uv_shim_execs_allowed_targeted_command(tmp_path: Path) -> None:
    fake_uv = tmp_path / "fake-uv"
    fake_uv.write_text('#!/usr/bin/env bash\necho real-uv "$@"\n')
    fake_uv.chmod(0o755)

    result = subprocess.run(
        [
            str(REPO_ROOT / ".agents/command-guard/bin/uv"),
            "run",
            "pytest",
            "-q",
            "tests/unit/foo/test_bar.py",
        ],
        cwd=REPO_ROOT,
        env=unauthorized_codex_subprocess_env(POLARIS_REAL_UV=str(fake_uv)),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "real-uv run pytest -q tests/unit/foo/test_bar.py" in result.stdout


def test_installer_is_shell_syntax_valid() -> None:
    result = subprocess.run(
        ["bash", "-n", str(REPO_ROOT / "scripts/install_codex_command_guard.sh")],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
