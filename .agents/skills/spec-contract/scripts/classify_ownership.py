#!/usr/bin/env python3
"""Deterministically classify Spec-owned versus inherited repository changes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


class OwnershipError(RuntimeError):
    pass


def _run(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        args,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise OwnershipError(f"{' '.join(args)}: {detail}")
    return result.stdout.strip()


def _require_commit(value: str, label: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{value}^{{commit}}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise OwnershipError(f"{label} is not a resolvable commit: {value}")


def _changed_files(base: str, head: str) -> set[str]:
    output = _run("git", "diff", "--name-only", f"{base}...{head}")
    return {line for line in output.splitlines() if line}


def _default_head(repo: str) -> tuple[str, str]:
    default_branch = _run("gh", "api", f"repos/{repo}", "--jq", ".default_branch")
    if not default_branch:
        raise OwnershipError("repository default branch is empty")
    default_head = _run(
        "gh",
        "api",
        f"repos/{repo}/commits/{default_branch}",
        "--jq",
        ".sha",
    )
    if not default_head:
        raise OwnershipError("repository default HEAD is empty")

    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{default_head}^{{commit}}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if probe.returncode != 0:
        _run(
            "git",
            "fetch",
            "--quiet",
            f"https://github.com/{repo}.git",
            f"refs/heads/{default_branch}",
        )
        fetched = _run("git", "rev-parse", "FETCH_HEAD")
        if fetched != default_head:
            raise OwnershipError(
                "default branch advanced while ownership head was being pinned"
            )

    _require_commit(default_head, "default HEAD")
    return default_branch, default_head


def classify(baseline: str, branch: str, head: str) -> dict[str, object]:
    _require_commit(baseline, "baseline")
    _require_commit(head, "HEAD")
    current_branch = _run("git", "branch", "--show-current")
    if current_branch != branch:
        raise OwnershipError(
            f"current branch {current_branch!r} does not match expected {branch!r}"
        )
    if _run("git", "rev-parse", "HEAD") != head:
        raise OwnershipError("working HEAD does not match requested HEAD")

    repo = _run(
        "gh",
        "repo",
        "view",
        "--json",
        "nameWithOwner",
        "--jq",
        ".nameWithOwner",
    )
    if not repo:
        raise OwnershipError("repository identity could not be resolved")

    default_branch, default_head = _default_head(repo)
    integration = _changed_files(baseline, head)
    owned_delta = _changed_files(default_head, head)
    inherited_delta = _changed_files(baseline, default_head)

    mixed = owned_delta & inherited_delta
    spec_owned = owned_delta - mixed
    inherited_only = integration - owned_delta
    commits = [
        line
        for line in _run(
            "git", "rev-list", "--reverse", head, "--not", default_head
        ).splitlines()
        if line
    ]

    return {
        "repository": repo,
        "baseline": baseline,
        "branch": branch,
        "head": head,
        "default_branch": default_branch,
        "default_head": default_head,
        "spec_owned_commits": commits,
        "spec_owned_surfaces": sorted(spec_owned),
        "mixed_surfaces": sorted(mixed),
        "inherited_only_surfaces": sorted(inherited_only),
    }


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--head", required=True)
    return parser.parse_args()


def main() -> int:
    args = _args()
    try:
        result = classify(args.baseline, args.branch, args.head)
    except OwnershipError as exc:
        print(f"SPEC OWNERSHIP: AMBIGUOUS\nReason: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
