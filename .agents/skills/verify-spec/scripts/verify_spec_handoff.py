from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
SHARED_RUNTIME_PATH = ROOT / ".agents/skills/shared_handoff_runtime.py"
VALID = "WORKFLOW HANDOFF: VALID"
INVALID = "WORKFLOW HANDOFF: INVALID"


def _shared_runtime() -> Any:
    root = str(ROOT)
    inserted_root = root not in sys.path
    if inserted_root:
        sys.path.insert(0, root)
    try:
        spec = importlib.util.spec_from_file_location(
            "_polaris_shared_handoff_runtime",
            SHARED_RUNTIME_PATH,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("shared handoff runtime resolver could not be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted_root:
            sys.path.remove(root)


def _read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("manifest: expected JSON object")
    return value


def finalize(manifest_path: Path, output_path: Path) -> str:
    """Render, verify, and atomically publish one validated Human Handoff file."""

    output_path.unlink(missing_ok=True)
    runtime = _shared_runtime()
    manifest = _read_manifest(manifest_path)
    outcome = manifest.get("outcome")
    if outcome not in {"success", "warning"}:
        raise RuntimeError("manifest: verify-spec outcome must be success or warning")
    receipt = runtime.finalize(manifest_path, output_path, repo_root=ROOT)
    if receipt != VALID:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(f"shared runtime returned unexpected receipt: {receipt}")
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--manifest", type=Path, required=True)
    finalize_parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command != "finalize":
            raise RuntimeError(f"unsupported command: {args.command}")
        print(finalize(args.manifest, args.output))
        return 0
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
        if getattr(args, "output", None) is not None:
            args.output.unlink(missing_ok=True)
        print(f"{INVALID}\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
