from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_RUNTIME_CONTRACT = "polaris.workflow-handoff-runtime/v2"
RUNTIME_FILES = (
    "scripts/workflow_handoff.py",
    "scripts/workflow_hashing.py",
)
VALID = "WORKFLOW HANDOFF: VALID"
INVALID = "WORKFLOW HANDOFF: INVALID"


class HandoffRuntimeError(RuntimeError):
    pass


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "git command failed"
        )
        raise HandoffRuntimeError(detail)
    return completed.stdout.strip()


def _fetch_default(root: Path) -> None:
    _run_git(root, "fetch", "--quiet", "origin", "main")


def _materialize_default_runtime(root: Path, target: Path) -> None:
    scripts = target / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for path in RUNTIME_FILES:
        completed = subprocess.run(
            ["git", "show", f"origin/main:{path}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise HandoffRuntimeError(
                "could not materialize current default-branch handoff runtime "
                f"{path}: {detail}"
            )
        destination = target / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(completed.stdout)


def _runtime_command(runtime_root: Path, *args: str) -> str:
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.workflow_handoff", *args],
        cwd=runtime_root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        detail = completed.stdout.strip() or completed.stderr.strip()
        raise HandoffRuntimeError(detail or "shared workflow handoff runtime failed")
    return completed.stdout.strip()


def _require_contract(runtime_root: Path) -> None:
    receipt = _runtime_command(runtime_root, "contract")
    expected = f"WORKFLOW HANDOFF RUNTIME: {REQUIRED_RUNTIME_CONTRACT}"
    if receipt != expected:
        raise HandoffRuntimeError(
            "shared workflow handoff runtime contract mismatch: "
            f"expected {expected!r}, got {receipt!r}"
        )


def _finalize_with_runtime(
    runtime_root: Path,
    manifest_path: Path,
    output_path: Path,
) -> str:
    _require_contract(runtime_root)
    rendered = _runtime_command(
        runtime_root,
        "generate",
        "--manifest",
        str(manifest_path.resolve()),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        dir=output_path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered)
            stream.write("\n")
        receipt = _runtime_command(
            runtime_root,
            "verify",
            "--manifest",
            str(manifest_path.resolve()),
            "--output",
            str(temporary_path.resolve()),
        )
        if receipt != VALID:
            raise HandoffRuntimeError(
                f"shared validator returned unexpected receipt: {receipt}"
            )
        os.replace(temporary_path, output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        raise
    return VALID


def finalize(manifest_path: Path, output_path: Path, *, repo_root: Path) -> str:
    """Finalize through a v2-compatible shared handoff runtime.

    Prefer the active checkout when it already satisfies the required runtime contract.
    Otherwise fetch current origin/main, materialize only the shared handoff runtime closure
    into a temporary directory, and execute there without mutating the candidate branch.
    """

    output_path.unlink(missing_ok=True)
    repo_root = repo_root.resolve()
    try:
        _require_contract(repo_root)
    except HandoffRuntimeError:
        _fetch_default(repo_root)
    else:
        return _finalize_with_runtime(repo_root, manifest_path, output_path)

    with tempfile.TemporaryDirectory(prefix="polaris-handoff-runtime-") as temporary:
        runtime_root = Path(temporary)
        _materialize_default_runtime(repo_root, runtime_root)
        return _finalize_with_runtime(runtime_root, manifest_path, output_path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--manifest", type=Path, required=True)
    finalize_parser.add_argument("--output", type=Path, required=True)
    finalize_parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command != "finalize":
            raise HandoffRuntimeError(f"unsupported command: {args.command}")
        print(finalize(args.manifest, args.output, repo_root=args.repo_root))
        return 0
    except (HandoffRuntimeError, OSError, ValueError) as exc:
        if getattr(args, "output", None) is not None:
            args.output.unlink(missing_ok=True)
        print(f"{INVALID}\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
