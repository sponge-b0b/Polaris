from __future__ import annotations

import argparse
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
SHARED_HANDOFF_PATH = ROOT / "scripts/workflow_handoff.py"
VALID = "WORKFLOW HANDOFF: VALID"
INVALID = "WORKFLOW HANDOFF: INVALID"


def _shared_handoff() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_polaris_shared_workflow_handoff",
        SHARED_HANDOFF_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("shared workflow handoff gate could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("manifest: expected JSON object")
    return value


def finalize(manifest_path: Path, output_path: Path) -> str:
    """Render, verify, and atomically publish one validated Human Handoff file."""

    output_path.unlink(missing_ok=True)
    shared = _shared_handoff()
    manifest = _read_manifest(manifest_path)
    rendered = shared.render_manifest(manifest)
    receipt = shared.validate_output(manifest, rendered)
    if receipt != VALID:
        raise RuntimeError(f"shared validator returned unexpected receipt: {receipt}")

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
        receipt = shared.validate_output(
            manifest,
            temporary_path.read_text(encoding="utf-8"),
        )
        if receipt != VALID:
            raise RuntimeError(f"shared validator returned unexpected receipt: {receipt}")
        os.replace(temporary_path, output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        raise

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
