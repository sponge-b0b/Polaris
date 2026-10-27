from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
FEASIBILITY_PATH = SCRIPT_DIR / "feasibility_authority.py"
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


def _load_feasibility_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_polaris_implement_feasibility_authority", FEASIBILITY_PATH
    )
    if spec is None or spec.loader is None:
        raise AttentionGateError(
            "implement-ticket feasibility validator could not be loaded"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _extract_feasibility_arg(argv: list[str]) -> Path | None:
    if len(argv) < 2 or argv[1] != "pre-mutation":
        return None
    try:
        index = argv.index("--feasibility")
    except ValueError as exc:
        raise AttentionGateError(
            "pre-mutation requires --feasibility <polaris.implement-feasibility/v1 JSON>; "
            "read .agents/skills/implement-ticket/PRE_IMPLEMENTATION_FEASIBILITY.md"
        ) from exc
    if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
        raise AttentionGateError("--feasibility requires a JSON artifact path")
    value = Path(argv[index + 1])
    del argv[index : index + 2]
    return value


def _arg_value(argv: list[str], name: str) -> str:
    try:
        index = argv.index(name)
    except ValueError as exc:
        raise AttentionGateError(f"pre-mutation missing required {name}") from exc
    if index + 1 >= len(argv):
        raise AttentionGateError(f"pre-mutation missing value for {name}")
    return argv[index + 1]


def _validate_pre_mutation_feasibility(path: Path, argv: list[str]) -> None:
    module = _load_feasibility_module()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise AttentionGateError("feasibility artifact: expected JSON object")
        receipt = module.validate_feasibility(value)
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
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
    except AttentionGateError as exc:
        print(f"IMPLEMENT TICKET ATTENTION: INVALID\nReason: {exc}")
        return 2
    sys.argv[:] = argv
    return _impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
