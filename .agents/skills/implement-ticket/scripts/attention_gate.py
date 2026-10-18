from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
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
    return _impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
