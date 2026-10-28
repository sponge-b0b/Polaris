from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.workflow_candidate_guard import (  # noqa: E402
    CandidateGuardError,
    protection_reason,
)

POLICY_SYNC_PREFIXES = (
    ".agents/skills/",
    "docs/process/",
)
POLICY_SYNC_EXACT = frozenset({"AGENTS.md"})


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


def _verify_anchor(anchor: str) -> None:
    _run_git("rev-parse", "--verify", f"{anchor}^{{commit}}")


def _policy_sync_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized in POLICY_SYNC_EXACT:
        return True
    return any(normalized.startswith(prefix) for prefix in POLICY_SYNC_PREFIXES)


def _blob(revision: str, path: str) -> str:
    result = _run_git("rev-parse", f"{revision}:{path}", check=False)
    if result.returncode:
        raise CandidateGuardError(
            f"authorized policy sync path {path} is missing at {revision}"
        )
    return result.stdout.strip()


def _commit_paths(commit: str) -> set[str]:
    return _git_paths(
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        "-z",
        commit,
        "--",
    )


def authorized_policy_sync_paths(
    anchor: str,
    *,
    remote: str = "origin",
    default_branch: str = "main",
) -> tuple[str, ...]:
    _verify_anchor(anchor)
    head = _run_git("rev-parse", "HEAD").stdout.strip()
    if _run_git("merge-base", "--is-ancestor", anchor, head, check=False).returncode:
        return ()

    committed = _git_paths(
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        anchor,
        "HEAD",
        "--",
    )
    protected = {path for path in committed if protection_reason(path) is not None}
    if not protected:
        return ()

    if any(not _policy_sync_path(path) for path in protected):
        return ()

    commits = _run_git("rev-list", "--reverse", f"{anchor}..HEAD").stdout.splitlines()
    for commit in commits:
        paths = _commit_paths(commit)
        if not paths.intersection(protected):
            continue
        if any(not _policy_sync_path(path) for path in paths):
            return ()

    default_ref = f"{remote}/{default_branch}"
    _run_git("rev-parse", "--verify", f"{default_ref}^{{commit}}")
    for path in protected:
        if _blob("HEAD", path) != _blob(default_ref, path):
            return ()

    return tuple(sorted(protected))


def candidate_paths(
    anchor: str,
    *,
    remote: str = "origin",
    default_branch: str = "main",
) -> tuple[str, ...]:
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
    dirty = _git_paths(
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        "HEAD",
        "--",
    ) | untracked
    authorized = set(
        authorized_policy_sync_paths(
            anchor,
            remote=remote,
            default_branch=default_branch,
        )
    )
    return tuple(sorted(((changed | untracked) - authorized) | dirty))


def protected_candidate_paths(
    anchor: str,
    *,
    remote: str = "origin",
    default_branch: str = "main",
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (path, reason)
        for path in candidate_paths(
            anchor,
            remote=remote,
            default_branch=default_branch,
        )
        if (reason := protection_reason(path)) is not None
    )


def validate_candidate(
    anchor: str,
    *,
    remote: str = "origin",
    default_branch: str = "main",
) -> tuple[str, ...]:
    violations = protected_candidate_paths(
        anchor,
        remote=remote,
        default_branch=default_branch,
    )
    if violations:
        detail = "; ".join(f"{path} ({reason})" for path, reason in violations)
        raise CandidateGuardError(
            "ordinary $implement-ticket candidate modifies protected "
            f"workflow/control-plane path(s): {detail}"
        )
    return candidate_paths(
        anchor,
        remote=remote,
        default_branch=default_branch,
    )


def _is_untracked(path: str) -> bool:
    return path in _git_paths(
        "ls-files",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
        path,
    )


def restore_protected(
    anchor: str,
    *,
    remote: str = "origin",
    default_branch: str = "main",
) -> tuple[str, ...]:
    violations = protected_candidate_paths(
        anchor,
        remote=remote,
        default_branch=default_branch,
    )
    restored: list[str] = []
    for path, _reason in violations:
        result = _run_git(
            "restore",
            "--source",
            "HEAD",
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

    remaining = protected_candidate_paths(
        anchor,
        remote=remote,
        default_branch=default_branch,
    )
    if remaining:
        detail = "; ".join(path for path, _reason in remaining)
        raise CandidateGuardError(
            f"protected paths remain after restoration: {detail}"
        )
    return tuple(restored)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--default-branch", default="main")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    _add_common_args(check)

    restore = sub.add_parser("restore-protected")
    _add_common_args(restore)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        if args.command == "check":
            paths = validate_candidate(
                args.anchor,
                remote=args.remote,
                default_branch=args.default_branch,
            )
            authorized = authorized_policy_sync_paths(
                args.anchor,
                remote=args.remote,
                default_branch=args.default_branch,
            )
            print("WORKFLOW CANDIDATE GUARD: VALID")
            print(f"Execution Anchor: {args.anchor}")
            print(f"Candidate paths: {len(paths)}")
            print(f"Authorized committed policy-sync paths: {len(authorized)}")
            print("Protected control-plane paths: 0")
        else:
            restored = restore_protected(
                args.anchor,
                remote=args.remote,
                default_branch=args.default_branch,
            )
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
