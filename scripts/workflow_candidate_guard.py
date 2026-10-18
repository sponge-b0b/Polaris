from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


class CandidateGuardError(RuntimeError):
    pass


PROTECTED_PREFIXES = (
    ".agents/",
    ".github/",
    "contracts/ccl/",
    "docs/adr/",
    "docs/process/",
    "tests/workflow/",
)

PROTECTED_EXACT = frozenset(
    {
        "AGENTS.md",
        "scripts/ccl.py",
        "scripts/ccl_adr.py",
        "scripts/ccl_ledger.py",
        "scripts/ccl_spec.py",
        "scripts/install_codex_command_guard.sh",
        "scripts/project_delivery.py",
        "scripts/review_remediation.py",
        "scripts/spec_contract.py",
    }
)


def _run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        raise CandidateGuardError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result


def _verify_anchor(anchor: str) -> None:
    _run_git("rev-parse", "--verify", f"{anchor}^{{commit}}")


def _git_paths(*args: str) -> set[str]:
    result = subprocess.run(
        ["git", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise CandidateGuardError(
            f"git {' '.join(args)} failed: "
            f"{result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return {
        os.fsdecode(item)
        for item in result.stdout.split(b"\0")
        if item
    }


def candidate_paths(anchor: str) -> tuple[str, ...]:
    _verify_anchor(anchor)
    changed = _git_paths(
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        anchor,
        "--",
    )
    untracked = _git_paths(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
    )
    return tuple(sorted(changed | untracked))


def protection_reason(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    if normalized in PROTECTED_EXACT:
        return "workflow/control-plane authority file"
    if normalized.startswith("scripts/workflow_") and normalized.endswith(".py"):
        return "workflow/control-plane tooling"
    for prefix in PROTECTED_PREFIXES:
        if normalized.startswith(prefix):
            return f"protected control-plane namespace {prefix}"
    return None


def protected_candidate_paths(anchor: str) -> tuple[tuple[str, str], ...]:
    return tuple(
        (path, reason)
        for path in candidate_paths(anchor)
        if (reason := protection_reason(path)) is not None
    )


def validate_candidate(anchor: str) -> tuple[str, ...]:
    violations = protected_candidate_paths(anchor)
    if violations:
        detail = "; ".join(f"{path} ({reason})" for path, reason in violations)
        raise CandidateGuardError(
            "ordinary $implement-ticket candidate modifies protected "
            f"workflow/control-plane path(s): {detail}"
        )
    return candidate_paths(anchor)


def _is_untracked(path: str) -> bool:
    return path in _git_paths(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
        path,
    )


def restore_protected(anchor: str) -> tuple[str, ...]:
    """Restore only protected candidate paths to exact Execution Anchor state."""

    violations = protected_candidate_paths(anchor)
    restored: list[str] = []
    for path, _reason in violations:
        result = _run_git(
            "restore",
            "--source",
            anchor,
            "--staged",
            "--worktree",
            "--",
            path,
            check=False,
        )
        if result.returncode == 0:
            restored.append(path)
            continue

        if _is_untracked(path):
            target = Path(path)
            if target.is_symlink() or target.is_file():
                target.unlink()
                restored.append(path)
                continue
            raise CandidateGuardError(
                f"refusing to remove non-file untracked protected path: {path}"
            )

        raise CandidateGuardError(
            f"could not restore protected path {path}: {result.stderr.strip()}"
        )

    remaining = protected_candidate_paths(anchor)
    if remaining:
        detail = "; ".join(path for path, _reason in remaining)
        raise CandidateGuardError(
            f"protected paths remain after restoration: {detail}"
        )
    return tuple(restored)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--anchor", required=True)

    restore = sub.add_parser("restore-protected")
    restore.add_argument("--anchor", required=True)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        if args.command == "check":
            paths = validate_candidate(args.anchor)
            print("WORKFLOW CANDIDATE GUARD: VALID")
            print(f"Execution Anchor: {args.anchor}")
            print(f"Candidate paths: {len(paths)}")
            print("Protected control-plane paths: 0")
        else:
            restored = restore_protected(args.anchor)
            print("WORKFLOW CANDIDATE RESTORE: COMPLETE")
            print(f"Execution Anchor: {args.anchor}")
            print(f"Restored protected paths: {len(restored)}")
            for path in restored:
                print(f"- {path}")
    except CandidateGuardError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
