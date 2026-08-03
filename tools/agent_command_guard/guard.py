"""Fail-closed guard for accidental broad verification commands.

This module is intentionally small and dependency-free so it can be used by PATH
shims before handing off to the real ``uv``, ``pytest``, ``mypy``, or ``ruff``
binaries. It is an accident-prevention layer for Codex ticket work, not a
security sandbox.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

GUARD_BIN_PART = f"{os.sep}.agents{os.sep}command-guard{os.sep}bin"
BROAD_VERIFY_ENV = "POLARIS_BROAD_VERIFY_AUTHORIZED"

UV_RUN_OPTIONS_WITH_VALUE = frozenset(
    {
        "--allow-insecure-host",
        "--config-file",
        "--default-index",
        "--directory",
        "--env-file",
        "--exclude-newer",
        "--exclude-newer-package",
        "--extra",
        "--extra-index-url",
        "--find-links",
        "--group",
        "--index",
        "--index-url",
        "--link-mode",
        "--no-extra",
        "--no-group",
        "--only-group",
        "--package",
        "--project",
        "--prerelease",
        "--python",
        "--python-platform",
        "--refresh-package",
        "--reinstall-package",
        "--resolution",
        "--upgrade-package",
        "--with",
        "--with-editable",
        "--with-requirements",
    }
)

PYTEST_OPTIONS_WITH_VALUE = frozenset(
    {
        "--basetemp",
        "--cache-clear",
        "--capture",
        "--confcutdir",
        "--durations",
        "--ignore",
        "--ignore-glob",
        "--import-mode",
        "--junit-prefix",
        "--junit-xml",
        "--lfnf",
        "--log-cli-level",
        "--log-file",
        "--log-file-level",
        "--maxfail",
        "--override-ini",
        "--rootdir",
        "--tb",
        "--verbosity",
        "-c",
        "-k",
        "-m",
        "-n",
        "-o",
    }
)

RUFF_OPTIONS_WITH_VALUE = frozenset(
    {
        "--config",
        "--diff",
        "--exclude",
        "--extend-exclude",
        "--fix-only",
        "--ignore",
        "--line-length",
        "--output-file",
        "--output-format",
        "--preview",
        "--select",
        "--target-version",
    }
)

MYPY_OPTIONS_WITH_VALUE = frozenset(
    {
        "--cache-dir",
        "--config-file",
        "--custom-typeshed-dir",
        "--exclude",
        "--follow-imports",
        "--install-types",
        "--junit-format",
        "--junit-xml",
        "--module",
        "--package",
        "--python-executable",
        "--python-version",
        "-m",
        "-p",
    }
)

BROAD_PYTEST_TARGETS = frozenset(
    {
        ".",
        "./",
        "tests",
        "tests/",
        "./tests",
        "./tests/",
        "tests/unit",
        "tests/unit/",
        "./tests/unit",
        "./tests/unit/",
        "tests/integration",
        "tests/integration/",
        "./tests/integration",
        "./tests/integration/",
        "tests/database",
        "tests/database/",
        "./tests/database",
        "./tests/database/",
    }
)

BROAD_STATIC_TARGETS = frozenset({".", "./"})


@dataclass(frozen=True, slots=True)
class GuardDecision:
    """Decision returned by the command classifier."""

    allowed: bool
    reason: str
    command_kind: str = "pass-through"


def repo_root() -> Path:
    """Return the Polaris repository root derived from this file location."""

    return Path(__file__).resolve().parents[2]


def cwd_is_inside_repo(cwd: Path | None = None) -> bool:
    """Return whether the current working directory is inside this repository."""

    current = (cwd or Path.cwd()).resolve()
    try:
        current.relative_to(repo_root())
    except ValueError:
        return False
    return True


def classify_command(
    argv: Sequence[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> GuardDecision:
    """Classify an intercepted command and decide whether it may run."""

    effective_env = env if env is not None else os.environ
    if not argv:
        return GuardDecision(allowed=True, reason="empty command")
    if not _guard_enabled(effective_env):
        return GuardDecision(allowed=True, reason="outside Codex agent environment")
    if not cwd_is_inside_repo(cwd):
        return GuardDecision(allowed=True, reason="outside Polaris repository")

    verification_command = _intercepted_verification_command(argv)
    if verification_command is None:
        return GuardDecision(allowed=True, reason="non-verification command")

    command, executable_args = verification_command
    decision = _classify_verification_command(command, executable_args)

    if decision.allowed or effective_env.get(BROAD_VERIFY_ENV):
        if decision.allowed:
            return decision
        return GuardDecision(
            allowed=True,
            reason=f"broad verification authorized by {BROAD_VERIFY_ENV}",
            command_kind=decision.command_kind,
        )
    return decision


def _intercepted_verification_command(
    argv: Sequence[str],
) -> tuple[str, list[str]] | None:
    command = Path(argv[0]).name
    executable_args = list(argv[1:])
    if command == "uv":
        extracted = _extract_uv_run_command(executable_args)
        if extracted is None:
            return None
        command, executable_args = extracted

    if command not in {"pytest", "mypy", "ruff"}:
        return None
    return command, executable_args


def _classify_verification_command(
    command: str, executable_args: Sequence[str]
) -> GuardDecision:
    if command == "pytest":
        return _classify_pytest(executable_args)
    if command == "mypy":
        return _classify_static_tool("mypy", executable_args, MYPY_OPTIONS_WITH_VALUE)
    return _classify_ruff(executable_args)


def _guard_enabled(env: Mapping[str, str]) -> bool:
    return bool(
        env.get("CODEX_THREAD_ID")
        or env.get("CODEX_CI")
        or env.get("POLARIS_COMMAND_GUARD")
        or env.get(BROAD_VERIFY_ENV)
    )


def find_real_executable(command_name: str, env: dict[str, str] | None = None) -> str:
    """Find the real executable, excluding the command-guard shim directory."""

    effective_env = env if env is not None else os.environ
    override = effective_env.get(
        f"POLARIS_REAL_{command_name.upper().replace('-', '_')}"
    )
    if override:
        return override

    for directory in effective_env.get("PATH", "").split(os.pathsep):
        if not directory or GUARD_BIN_PART in directory:
            continue
        candidate = Path(directory) / command_name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    raise FileNotFoundError(f"Could not locate real executable for {command_name!r}")


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint for command-guard shims."""

    intercepted = list(argv if argv is not None else sys.argv[1:])
    if not intercepted:
        print("agent-command-guard: missing command name", file=sys.stderr)
        return 127

    decision = classify_command(intercepted)
    if not decision.allowed:
        _print_block_message(intercepted, decision)
        return 126

    command_name = Path(intercepted[0]).name
    real_executable = find_real_executable(command_name)
    os.execv(real_executable, [real_executable, *intercepted[1:]])
    return 127


def _extract_uv_run_command(args: Sequence[str]) -> tuple[str, list[str]] | None:
    if not args or args[0] != "run":
        return None

    index = 1
    while index < len(args):
        token = args[index]
        if token == "--":
            index += 1
            break
        if not token.startswith("-"):
            break
        option_name = token.split("=", maxsplit=1)[0]
        index += 1
        if (
            "=" not in token
            and option_name in UV_RUN_OPTIONS_WITH_VALUE
            and index < len(args)
        ):
            index += 1

    if index >= len(args):
        return None

    command = Path(args[index]).name
    command_args = list(args[index + 1 :])
    if command in {"python", "python3"}:
        python_module = _extract_python_module_command(command_args)
        if python_module is not None:
            return python_module
    return command, command_args


def _extract_python_module_command(args: Sequence[str]) -> tuple[str, list[str]] | None:
    index = 0
    while index < len(args):
        token = args[index]
        if token == "-m" and index + 1 < len(args):
            module_name = args[index + 1]
            command = module_name.rsplit(".", maxsplit=1)[-1]
            return command, list(args[index + 2 :])
        if token == "--":
            return None
        index += 1
    return None


def _classify_pytest(args: Sequence[str]) -> GuardDecision:
    if _contains_coverage_flag(args):
        return GuardDecision(
            allowed=False,
            reason=(
                "pytest coverage runs are broad verification and require "
                "owner authorization"
            ),
            command_kind="pytest",
        )

    positional = _positionals(args, PYTEST_OPTIONS_WITH_VALUE)
    if not positional:
        return GuardDecision(
            allowed=False,
            reason=(
                "pytest without explicit test targets would run the broad default suite"
            ),
            command_kind="pytest",
        )

    broad_targets = [target for target in positional if _is_broad_pytest_target(target)]
    if broad_targets:
        return GuardDecision(
            allowed=False,
            reason=f"pytest target is too broad: {', '.join(broad_targets)}",
            command_kind="pytest",
        )

    return GuardDecision(
        allowed=True, reason="pytest target is scoped", command_kind="pytest"
    )


def _classify_static_tool(
    tool_name: str,
    args: Sequence[str],
    options_with_value: Iterable[str],
) -> GuardDecision:
    positional = _positionals(args, frozenset(options_with_value))
    if not positional:
        return GuardDecision(
            allowed=False,
            reason=(
                f"{tool_name} without explicit file targets would run "
                "broad verification"
            ),
            command_kind=tool_name,
        )

    broad_targets = [target for target in positional if _is_broad_static_target(target)]
    if broad_targets:
        return GuardDecision(
            allowed=False,
            reason=f"{tool_name} target is too broad: {', '.join(broad_targets)}",
            command_kind=tool_name,
        )

    return GuardDecision(
        allowed=True, reason=f"{tool_name} targets are scoped", command_kind=tool_name
    )


def _classify_ruff(args: Sequence[str]) -> GuardDecision:
    if not args:
        return GuardDecision(
            allowed=False,
            reason="ruff without explicit file targets would run broad verification",
            command_kind="ruff",
        )

    subcommand = args[0]
    if subcommand not in {"check", "format"}:
        return GuardDecision(
            allowed=True, reason="ruff command is not a verification command"
        )

    decision = _classify_static_tool("ruff", args[1:], RUFF_OPTIONS_WITH_VALUE)
    return GuardDecision(
        allowed=decision.allowed,
        reason=decision.reason,
        command_kind="ruff",
    )


def _contains_coverage_flag(args: Sequence[str]) -> bool:
    return any(
        arg == "--cov" or arg.startswith("--cov=") or arg.startswith("--cov-report")
        for arg in args
    )


def _positionals(args: Sequence[str], options_with_value: frozenset[str]) -> list[str]:
    positionals: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            positionals.extend(args[index + 1 :])
            break
        if token.startswith("-"):
            option_name = token.split("=", maxsplit=1)[0]
            index += 1
            if (
                "=" not in token
                and option_name in options_with_value
                and index < len(args)
            ):
                index += 1
            continue
        positionals.append(token)
        index += 1
    return positionals


def _is_broad_pytest_target(target: str) -> bool:
    normalized = _normalize_target(target)
    if normalized in BROAD_PYTEST_TARGETS:
        return True
    if normalized.startswith("tests/"):
        parts = [part for part in normalized.split("/") if part]
        return (
            len(parts) <= 3
            and "::" not in normalized
            and not normalized.endswith(".py")
        )
    return False


def _is_broad_static_target(target: str) -> bool:
    normalized = _normalize_target(target)
    if normalized in BROAD_STATIC_TARGETS:
        return True
    if normalized.endswith("/"):
        return True
    if "/" not in normalized and not Path(normalized).suffix:
        return True
    return Path(normalized).suffix == ""


def _normalize_target(target: str) -> str:
    return target.strip().removeprefix("./").rstrip("/") or "."


def _print_block_message(command: Sequence[str], decision: GuardDecision) -> None:
    command_text = " ".join(command)
    print(
        "\n".join(
            [
                "❌ Polaris agent command guard blocked broad verification.",
                "",
                "Blocked command:",
                f"  {command_text}",
                "",
                "Reason:",
                f"  {decision.reason}.",
                "",
                "For individual ticket work, run targeted checks only. If broader ",
                "verification is needed, ask the owner first and rerun with:",
                f"  {BROAD_VERIFY_ENV}=<owner-authorization-for-current-task> "
                f"{command_text}",
            ]
        ),
        file=sys.stderr,
    )


if __name__ == "__main__":
    raise SystemExit(main())
