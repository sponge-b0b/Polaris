from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
SHARED_RUNTIME_PATH = ROOT / ".agents/skills/shared_handoff_runtime.py"
CONVERGENCE_PATH = ROOT / ".agents/skills/review-spec/scripts/review_convergence.py"
COVERAGE_PATH = ROOT / ".agents/skills/review-spec/scripts/review_coverage.py"
VALID = "WORKFLOW HANDOFF: VALID"
INVALID = "WORKFLOW HANDOFF: INVALID"


def _load_module(name: str, path: Path) -> Any:
    root = str(ROOT)
    inserted_root = root not in sys.path
    script_dir = str(path.parent)
    inserted_script = script_dir not in sys.path
    if inserted_root:
        sys.path.insert(0, root)
    if inserted_script:
        sys.path.insert(0, script_dir)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"could not load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted_script:
            sys.path.remove(script_dir)
        if inserted_root:
            sys.path.remove(root)


def _shared_runtime() -> Any:
    return _load_module("_polaris_shared_handoff_runtime", SHARED_RUNTIME_PATH)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _read_manifest(path: Path) -> dict[str, Any]:
    return _read_json(path)


def _validate_review_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != "polaris.workflow-handoff/v1":
        raise RuntimeError("manifest: wrong schema")
    if manifest.get("boundary") != "human-lifecycle":
        raise RuntimeError("manifest: boundary must be human-lifecycle")
    outcome = manifest.get("outcome")
    if outcome not in {"success", "warning"}:
        raise RuntimeError("manifest: review-spec outcome must be success or warning")

    durability = manifest.get("durability")
    if not isinstance(durability, dict):
        raise RuntimeError("manifest: missing durability receipt")
    sources = durability.get("sources")
    if not isinstance(sources, list) or len(sources) < 4:
        raise RuntimeError(
            "manifest: review-spec requires finding, coverage, "
            "adjudication, and session-ledger durability sources"
        )

    handoffs = manifest.get("handoffs")
    if not isinstance(handoffs, list) or len(handoffs) != 1:
        raise RuntimeError("manifest: review-spec requires exactly one handoff")
    item = handoffs[0]
    if not isinstance(item, dict):
        raise RuntimeError("manifest: invalid handoff")
    destination = item.get("destination")
    if outcome == "success":
        if destination != "$spec-merge-cleanup":
            raise RuntimeError(
                "manifest: review-spec success must hand off to $spec-merge-cleanup"
            )
    elif destination == "$spec-merge-cleanup":
        raise RuntimeError(
            "manifest: review-spec warning cannot hand off to $spec-merge-cleanup"
        )


def _validate_converged_handoff(
    manifest: dict[str, Any], coverage_path: Path, convergence_path: Path
) -> None:
    durability = manifest.get("durability")
    assert isinstance(durability, dict)
    sources = durability.get("sources")
    if not isinstance(sources, list) or len(sources) < 5:
        raise RuntimeError(
            "manifest: converged review-spec handoff requires finding, coverage, "
            "adjudication, convergence, and session-ledger durability sources"
        )

    coverage_module = _load_module("_polaris_review_coverage", COVERAGE_PATH)
    convergence_module = _load_module("_polaris_review_convergence", CONVERGENCE_PATH)
    coverage = _read_json(coverage_path)
    convergence = _read_json(convergence_path)
    convergence_receipt = convergence_module.validate_convergence(convergence)

    coverage_hash = coverage_module.sha256_canonical_json(coverage)
    rounds = convergence.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        raise RuntimeError("convergence: no final round")
    final_round = rounds[-1]
    if not isinstance(final_round, dict):
        raise RuntimeError("convergence: invalid final round")
    if final_round.get("coverage_sha256") != coverage_hash:
        raise RuntimeError(
            "convergence: final round is not bound to the final review coverage artifact"
        )
    if convergence.get("reviewed_head") != coverage.get("reviewed_head"):
        raise RuntimeError("convergence: reviewed HEAD differs from final coverage")
    if convergence.get("spec_contract_hash") != coverage.get("spec_contract_hash"):
        raise RuntimeError("convergence: Spec Contract Hash differs from final coverage")
    if convergence_receipt.rounds < 2:
        raise RuntimeError("convergence: insufficient complete challenger rounds")


def finalize(manifest_path: Path, output_path: Path) -> str:
    """Render, verify, and atomically publish one review Human Handoff."""

    output_path.unlink(missing_ok=True)
    manifest = _read_manifest(manifest_path)
    _validate_review_manifest(manifest)
    runtime = _shared_runtime()
    receipt = runtime.finalize(manifest_path, output_path, repo_root=ROOT)
    if receipt != VALID:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(f"shared runtime returned unexpected receipt: {receipt}")
    return receipt


def finalize_converged(
    manifest_path: Path,
    coverage_path: Path,
    convergence_path: Path,
    output_path: Path,
) -> str:
    """Fail closed unless review completeness reached a candidate-bound fixed point."""

    output_path.unlink(missing_ok=True)
    manifest = _read_manifest(manifest_path)
    _validate_review_manifest(manifest)
    _validate_converged_handoff(manifest, coverage_path, convergence_path)
    runtime = _shared_runtime()
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
    finalize_parser.add_argument("--coverage", type=Path, required=True)
    finalize_parser.add_argument("--convergence", type=Path, required=True)
    finalize_parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command != "finalize":
            raise RuntimeError(f"unsupported command: {args.command}")
        print(
            finalize_converged(
                args.manifest,
                args.coverage,
                args.convergence,
                args.output,
            )
        )
        return 0
    except (json.JSONDecodeError, OSError, RuntimeError, ValueError) as exc:
        if getattr(args, "output", None) is not None:
            args.output.unlink(missing_ok=True)
        print(f"{INVALID}\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
