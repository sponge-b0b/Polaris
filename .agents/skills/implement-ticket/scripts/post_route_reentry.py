from __future__ import annotations

import argparse
import json
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
from candidate_guard import CandidateGuardError, validate_candidate  # noqa: E402
from feasibility_authority import FeasibilityError, validate_feasibility  # noqa: E402
from route_return import RouteReturnError, validate_route_return  # noqa: E402


class PostRouteReentryError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise PostRouteReentryError(message)


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PostRouteReentryError(f"{label} artifact invalid: {exc}") from exc
    _need(isinstance(value, dict), f"{label} artifact: expected JSON object")
    return value


def _validate_feasibility(
    path: Path,
    *,
    ticket: int,
    contract_schema: str,
    contract_hash: str,
    branch: str,
    head: str,
) -> None:
    value = _read_json_object(path, "feasibility")
    try:
        receipt = validate_feasibility(value)
    except FeasibilityError as exc:
        raise PostRouteReentryError(f"feasibility artifact invalid: {exc}") from exc

    _need(
        receipt.outcome == "PASS",
        "post-route re-entry requires IMPLEMENT TICKET FEASIBILITY: PASS",
    )
    _need(receipt.ticket == ticket, "feasibility artifact: ticket mismatch")
    _need(
        receipt.contract_schema == contract_schema,
        "feasibility artifact: contract schema mismatch",
    )
    _need(
        receipt.contract_hash == contract_hash,
        "feasibility artifact: contract hash mismatch",
    )
    _need(value.get("branch") == branch, "feasibility artifact: branch mismatch")
    _need(
        value.get("execution_head") == head,
        "feasibility artifact: execution HEAD is stale; "
        "rerun feasibility on current HEAD",
    )


def _validate_route_return(
    path: Path,
    *,
    ticket: int,
    contract_schema: str,
    contract_hash: str,
) -> dict[str, Any]:
    value = _read_json_object(path, "route return")
    try:
        receipt = validate_route_return(value)
    except RouteReturnError as exc:
        raise PostRouteReentryError(f"route-return artifact invalid: {exc}") from exc

    _need(
        receipt.status == "READY",
        "post-route re-entry requires route-return READY",
    )
    _need(receipt.ticket == ticket, "route-return artifact: ticket mismatch")
    _need(
        receipt.contract_schema == contract_schema,
        "route-return artifact: contract schema mismatch",
    )
    _need(
        receipt.contract_hash == contract_hash,
        "route-return artifact: contract hash mismatch",
    )
    return value


def record_post_route_reentry(args: argparse.Namespace) -> dict[str, Any]:
    # Refresh both authoritative remote refs without requiring a clean worktree.
    _impl._fetch_remote_branch(args.remote, args.default_branch)
    remote_anchor = _impl._fetch_remote_branch(args.remote, args.branch)
    _need(
        remote_anchor == args.execution_anchor,
        "post-route re-entry execution anchor does not equal fetched remote branch tip",
    )

    contract_schema, contract_hash, head = _impl._common(
        ticket=args.ticket,
        contract=args.contract,
        baseline=args.baseline,
        branch=args.branch,
        execution_anchor=args.execution_anchor,
    )
    _need(
        head == args.execution_anchor,
        "post-route re-entry requires current HEAD to equal the fetched execution anchor",
    )

    _validate_feasibility(
        args.feasibility,
        ticket=args.ticket,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
        branch=args.branch,
        head=head,
    )
    route_return = _validate_route_return(
        args.route_return,
        ticket=args.ticket,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
    )

    try:
        validate_candidate(
            args.execution_anchor,
            remote=args.remote,
            default_branch=args.default_branch,
        )
    except CandidateGuardError as exc:
        raise PostRouteReentryError(str(exc)) from exc

    current_state = _impl.candidate_state(args.execution_anchor)
    _need(
        route_return.get("failed_candidate_state") == current_state,
        "route-return artifact: candidate state differs from returned failed candidate",
    )

    attention_status, attention_hash = _impl._attention_result(
        args.attention_result,
        "$implement-ticket pre-mutation",
    )
    receipt = {
        "schema": _impl.SCHEMA,
        "ticket": args.ticket,
        "branch": args.branch,
        "baseline": args.baseline,
        "execution_anchor": args.execution_anchor,
        "remote": args.remote,
        "contract_schema": contract_schema,
        "contract_hash": contract_hash,
        "pre_mutation": {
            "head": head,
            "candidate_state": current_state,
            "attention_status": attention_status,
            "attention_result_sha256": attention_hash,
        },
        "pre_closure": None,
    }
    _impl._write_receipt(args.receipt, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticket", type=int, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--execution-anchor", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--default-branch", default="main")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--attention-result", type=Path, required=True)
    parser.add_argument("--feasibility", type=Path, required=True)
    parser.add_argument("--route-return", type=Path, required=True)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if args.receipt is None:
        args.receipt = _impl.default_receipt_path(args.ticket)
    try:
        receipt = record_post_route_reentry(args)
        _impl._print("IMPLEMENT TICKET ATTENTION: POST-ROUTE REENTRY VALID", receipt)
    except (
        PostRouteReentryError,
        _impl.AttentionGateError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
