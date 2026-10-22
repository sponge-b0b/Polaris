from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "polaris.verify-spec-attribution/v1"


class AttributionError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise AttributionError(message)


def _git(repo: Path, *args: str, allow_failure: bool = False) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if allow_failure:
            return None
        detail = result.stderr.strip() or result.stdout.strip()
        raise AttributionError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def _resolve(repo: Path, ref: str) -> str:
    value = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    assert value is not None
    return value


def _blob(repo: Path, commit: str, path: str) -> str | None:
    return _git(repo, "rev-parse", "--verify", f"{commit}:{path}", allow_failure=True)


def _canonical_payload(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_manifest(repo: Path, default_ref: str, candidate_ref: str) -> dict[str, Any]:
    repo = repo.resolve()
    _git(repo, "rev-parse", "--git-dir")

    default_head = _resolve(repo, default_ref)
    candidate_head = _resolve(repo, candidate_ref)
    merge_base = _git(repo, "merge-base", default_head, candidate_head)
    _need(merge_base is not None and merge_base != "", "git: no merge base")

    raw_paths = _git(
        repo,
        "diff",
        "--name-only",
        "--diff-filter=ACMRD",
        f"{merge_base}..{candidate_head}",
    )
    assert raw_paths is not None
    branch_side_paths = sorted({line for line in raw_paths.splitlines() if line})

    attributable: list[str] = []
    inherited: list[str] = []
    for path in branch_side_paths:
        candidate_blob = _blob(repo, candidate_head, path)
        default_blob = _blob(repo, default_head, path)
        if candidate_blob == default_blob:
            inherited.append(path)
        else:
            attributable.append(path)

    return {
        "schema": SCHEMA,
        "default_ref": default_ref,
        "default_head": default_head,
        "candidate_ref": candidate_ref,
        "candidate_head": candidate_head,
        "merge_base": merge_base,
        "branch_side_paths": branch_side_paths,
        "candidate_attributable_paths": attributable,
        "inherited_default_equivalent_paths": inherited,
    }


def write_manifest(manifest: dict[str, Any], output: Path) -> str:
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    output.write_text(payload, encoding="utf-8")
    return hashlib.sha256(_canonical_payload(manifest).encode("utf-8")).hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("--repo", type=Path, default=Path("."))
    build.add_argument("--default-ref", required=True)
    build.add_argument("--candidate-ref", default="HEAD")
    build.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command != "build":
            raise AttributionError(f"unsupported command: {args.command}")
        manifest = build_manifest(args.repo, args.default_ref, args.candidate_ref)
        digest = write_manifest(manifest, args.output)
        print("VERIFY-SPEC ATTRIBUTION: VALID")
        print(f"Default branch head: {manifest['default_head']}")
        print(f"Candidate head: {manifest['candidate_head']}")
        print(f"Merge base: {manifest['merge_base']}")
        print(f"Branch-side paths: {len(manifest['branch_side_paths'])}")
        print(
            "Candidate-attributable paths: "
            f"{len(manifest['candidate_attributable_paths'])}"
        )
        print(
            "Inherited default-equivalent paths: "
            f"{len(manifest['inherited_default_equivalent_paths'])}"
        )
        print(f"Attribution Manifest SHA-256: {digest}")
        return 0
    except (AttributionError, OSError) as exc:
        print(f"VERIFY-SPEC ATTRIBUTION: INVALID\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
