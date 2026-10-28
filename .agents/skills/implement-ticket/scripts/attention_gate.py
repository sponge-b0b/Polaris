from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
FEASIBILITY_PATH = SCRIPT_DIR / "feasibility_authority.py"
BOUNDED_EXECUTION_PATH = SCRIPT_DIR / "bounded_execution.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import attention_gate_impl as _impl  # noqa: E402
from scripts.workflow_candidate_guard import (  # noqa: E402
    CandidateGuardError,
    validate_candidate,
)

AttentionGateError = _impl.AttentionGateError
SCHEMA = _impl.SCHEMA
CONTRACT_HASH_FIELDS = _impl.CONTRACT_HASH_FIELDS

# Re-export the helpers used by the focused gate tests and current workflow.
candidate_state = _impl.candidate_state
default_receipt_path = _impl.default_receipt_path
receipt_hash = _impl.receipt_hash
record_pre_mutation = _impl.record_pre_mutation
_contract_identity = _impl._contract_identity

_original_record_pre_closure = _impl.record_pre_closure
_original_verify = _impl.verify


def _load_module(path: Path, module_name: str, label: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AttentionGateError(f"{label} validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_feasibility_module() -> Any:
    return _load_module(
        FEASIBILITY_PATH,
        "_polaris_implement_feasibility_authority",
        "implement-ticket feasibility",
    )


def _load_bounded_execution_module() -> Any:
    return _load_module(
        BOUNDED_EXECUTION_PATH,
        "_polaris_implement_bounded_execution",
        "implement-ticket bounded-execution",
    )


def _extract_required_custom_arg(
    argv: list[str],
    *,
    command: str,
    flag: str,
    guidance: str,
) -> Path | None:
    if len(argv) < 2 or argv[1] != command or "--help" in argv or "-h" in argv:
        return None
    try:
        index = argv.index(flag)
    except ValueError as exc:
        raise AttentionGateError(f"{command} requires {flag} {guidance}") from exc
    if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
        raise AttentionGateError(f"{flag} requires a JSON artifact path")
    value = Path(argv[index + 1])
    del argv[index : index + 2]
    return value


def _extract_feasibility_arg(argv: list[str]) -> Path | None:
    return _extract_required_custom_arg(
        argv,
        command="pre-mutation",
        flag="--feasibility",
        guidance=(
            "<polaris.implement-feasibility/v1 JSON>; read "
            ".agents/skills/implement-ticket/PRE_IMPLEMENTATION_FEASIBILITY.md"
        ),
    )


def _extract_concerns_arg(argv: list[str]) -> Path | None:
    return _extract_required_custom_arg(
        argv,
        command="pre-closure",
        flag="--concerns",
        guidance=(
            "<polaris.implement-preclosure-concerns/v1 JSON>; read "
            ".agents/skills/implement-ticket/BOUNDED_EXECUTION.md"
        ),
    )


def _arg_value(argv: list[str], name: str) -> str:
    try:
        index = argv.index(name)
    except ValueError as exc:
        raise AttentionGateError(f"missing required {name}") from exc
    if index + 1 >= len(argv):
        raise AttentionGateError(f"missing value for {name}")
    return argv[index + 1]


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise AttentionGateError(f"{label} artifact invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise AttentionGateError(f"{label} artifact: expected JSON object")
    return value


def _validate_pre_mutation_feasibility(path: Path, argv: list[str]) -> None:
    module = _load_feasibility_module()
    value = _read_json_object(path, "feasibility")
    try:
        receipt = module.validate_feasibility(value)
    except RuntimeError as exc:
        raise AttentionGateError(f"feasibility artifact invalid: {exc}") from exc

    ticket = int(_arg_value(argv, "--ticket"))
    contract_path = Path(_arg_value(argv, "--contract"))
    branch = _arg_value(argv, "--branch")
    contract_schema, contract_hash = _contract_identity(contract_path)
    head = str(_impl._run_git("rev-parse", "HEAD")).strip()

    if receipt.outcome != "PASS":
        raise AttentionGateError(
            "pre-mutation requires IMPLEMENT TICKET FEASIBILITY: PASS; "
            f"artifact outcome is {receipt.outcome}"
        )
    if receipt.ticket != ticket:
        raise AttentionGateError("feasibility artifact: ticket mismatch")
    if receipt.contract_schema != contract_schema:
        raise AttentionGateError("feasibility artifact: contract schema mismatch")
    if receipt.contract_hash != contract_hash:
        raise AttentionGateError("feasibility artifact: contract hash mismatch")
    if value.get("branch") != branch:
        raise AttentionGateError("feasibility artifact: branch mismatch")
    if value.get("execution_head") != head:
        raise AttentionGateError(
            "feasibility artifact: execution HEAD is stale; rerun feasibility on current HEAD"
        )


def _validate_pre_closure_concerns(path: Path, argv: list[str]) -> None:
    module = _load_bounded_execution_module()
    value = _read_json_object(path, "pre-closure concerns")
    try:
        receipt = module.validate_concerns(value)
    except RuntimeError as exc:
        raise AttentionGateError(f"pre-closure concerns artifact invalid: {exc}") from exc

    ticket = int(_arg_value(argv, "--ticket"))
    contract_path = Path(_arg_value(argv, "--contract"))
    execution_anchor = _arg_value(argv, "--execution-anchor")
    contract_schema, contract_hash = _contract_identity(contract_path)
    current_state = candidate_state(execution_anchor)

    if receipt.outcome != "PASS":
        raise AttentionGateError(
            "pre-closure requires PRE-CLOSURE CONCERNS: PASS; "
            f"artifact outcome is {receipt.outcome}"
        )
    if receipt.ticket != ticket:
        raise AttentionGateError("pre-closure concerns artifact: ticket mismatch")
    if receipt.contract_schema != contract_schema:
        raise AttentionGateError("pre-closure concerns artifact: contract schema mismatch")
    if receipt.contract_hash != contract_hash:
        raise AttentionGateError("pre-closure concerns artifact: contract hash mismatch")
    if receipt.candidate_state != current_state:
        raise AttentionGateError(
            "pre-closure concerns artifact: candidate state is stale; rebuild concern disposition"
        )


def _require_admissible_candidate(execution_anchor: str) -> None:
    try:
        validate_candidate(execution_anchor)
    except CandidateGuardError as exc:
        raise AttentionGateError(str(exc)) from exc


def record_pre_closure(args: Any) -> dict[str, Any]:
    _require_admissible_candidate(args.execution_anchor)
    return _original_record_pre_closure(args)


def verify(args: Any) -> dict[str, Any]:
    _require_admissible_candidate(args.execution_anchor)
    return _original_verify(args)


# The retained implementation's CLI resolves these globals from its own module.
# Patch only the two terminal candidate-admission functions so direct execution
# is machine-enforced even when an agent skipped the standalone guard command.
_impl.record_pre_closure = record_pre_closure
_impl.verify = verify


def main() -> int:
    argv = list(sys.argv)
    try:
        feasibility = _extract_feasibility_arg(argv)
        if feasibility is not None:
            _validate_pre_mutation_feasibility(feasibility, argv)
        concerns = _extract_concerns_arg(argv)
        if concerns is not None:
            _validate_pre_closure_concerns(concerns, argv)
    except AttentionGateError as exc:
        print(f"IMPLEMENT TICKET ATTENTION: INVALID\nReason: {exc}")
        return 2
    sys.argv[:] = argv
    return _impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
