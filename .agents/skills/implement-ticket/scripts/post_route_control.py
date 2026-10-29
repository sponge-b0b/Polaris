from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from feasibility_authority import (  # noqa: E402
    FeasibilityError,
    validate_feasibility,
)
from route_return import RouteReturnError, validate_route_return  # noqa: E402
from scripts.workflow_hashing import sha256_canonical_json  # noqa: E402

CONTEXT_SCHEMA = "polaris.implement-post-route-context/v1"
REROUTE_SCHEMA = "polaris.implement-post-route-reroute/v1"
TERMINAL_SCHEMA = "polaris.implement-route-terminal/v1"
_HASH = re.compile(r"^[0-9a-f]{64}$")
ROUTING_CLASSIFICATIONS = {
    "cell-routing-defect",
    "planning-cell-gap",
    "contract-authority-gap",
    "hard-blocker",
}
TERMINAL_DISPOSITIONS = {
    "WORKFLOW_DEFECT_NO_MUTATION",
    "PRE_VERIFIER_ROUTE",
    "PRE_VERIFIER_HARD_BLOCKER",
}


class PostRouteControlError(RuntimeError):
    pass


@dataclass(frozen=True)
class PostRouteContextReceipt:
    ticket: int
    finding_id: str
    feasibility_sha256: str
    route_return_sha256: str
    artifact_sha256: str


@dataclass(frozen=True)
class PostRouteRerouteReceipt:
    ticket: int
    returned_finding_id: str
    new_finding_id: str
    classification: str
    artifact_sha256: str


@dataclass(frozen=True)
class RouteTerminalReceipt:
    ticket: int
    disposition: str
    mutation_started: bool
    attempt_consumed: bool
    artifact_sha256: str


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise PostRouteControlError(message)


def _digest(value: Any, field: str) -> str:
    _need(
        isinstance(value, str) and _HASH.fullmatch(value) is not None,
        f"post-route control: invalid {field}",
    )
    return value


def _text(value: Any, field: str) -> str:
    _need(
        isinstance(value, str) and value.strip(),
        f"post-route control: {field} must be a non-empty string",
    )
    return value


def _str_list(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    _need(isinstance(value, list), f"post-route control: {field} must be a list")
    _need(
        all(isinstance(item, str) and item.strip() for item in value),
        f"post-route control: {field} contains invalid item",
    )
    _need(
        value == sorted(set(value)),
        f"post-route control: {field} must be sorted and unique",
    )
    if nonempty:
        _need(bool(value), f"post-route control: {field} must not be empty")
    return value


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _prior_finding(feasibility: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    for row in feasibility.get("prior_findings", []):
        if isinstance(row, dict) and row.get("finding_id") == finding_id:
            return row
    return None


def validate_context(
    value: dict[str, Any],
    feasibility: dict[str, Any],
    route_return: dict[str, Any],
) -> PostRouteContextReceipt:
    _need(
        value.get("schema") == CONTEXT_SCHEMA,
        f"post-route context: schema must be {CONTEXT_SCHEMA}",
    )
    _need(
        set(value)
        == {
            "schema",
            "ticket",
            "contract_schema",
            "contract_hash",
            "finding_id",
            "verifier_result_sha256",
            "triage_artifact_sha256",
            "route_result_sha256",
            "route_return_sha256",
            "feasibility_sha256",
            "returned_disposition",
            "adjudicated_evidence_sources",
        },
        "post-route context: unsupported top-level fields",
    )
    try:
        route_receipt = validate_route_return(route_return)
    except RouteReturnError as exc:
        raise PostRouteControlError(f"route return invalid: {exc}") from exc
    try:
        feasibility_receipt = validate_feasibility(feasibility)
    except FeasibilityError as exc:
        raise PostRouteControlError(f"feasibility invalid: {exc}") from exc

    _need(
        route_receipt.status in {"READY", "IN_PROGRESS"},
        "post-route context requires an active route-return record",
    )
    _need(
        feasibility_receipt.outcome == "PASS",
        "post-route context requires feasibility PASS",
    )
    _need(value.get("ticket") == route_receipt.ticket, "post-route context: ticket mismatch")
    _need(
        value.get("ticket") == feasibility_receipt.ticket,
        "post-route context: feasibility ticket mismatch",
    )
    _need(
        value.get("contract_schema") == route_receipt.contract_schema
        == feasibility_receipt.contract_schema,
        "post-route context: contract schema mismatch",
    )
    _need(
        value.get("contract_hash") == route_receipt.contract_hash
        == feasibility_receipt.contract_hash,
        "post-route context: contract hash mismatch",
    )
    _need(value.get("finding_id") == route_receipt.finding_id, "post-route context: finding mismatch")
    _need(
        value.get("verifier_result_sha256") == route_return.get("verifier_result_sha256"),
        "post-route context: verifier-result mismatch",
    )
    _need(
        value.get("triage_artifact_sha256") == route_return.get("triage_artifact_sha256"),
        "post-route context: triage mismatch",
    )
    _need(
        value.get("route_result_sha256") == route_return.get("route_result_sha256"),
        "post-route context: route-result mismatch",
    )
    expected_route_sha = sha256_canonical_json(route_return)
    _need(
        value.get("route_return_sha256") == expected_route_sha,
        "post-route context: route-return SHA mismatch",
    )
    _need(
        value.get("feasibility_sha256") == feasibility_receipt.artifact_sha256,
        "post-route context: feasibility SHA mismatch",
    )
    _need(
        value.get("returned_disposition") == "OWNED_BY_CURRENT_TICKET",
        "post-route context: returned disposition must stay implementation-owned",
    )

    prior = _prior_finding(feasibility, route_receipt.finding_id)
    _need(prior is not None, "post-route context: returned finding missing from feasibility")
    assert prior is not None
    _need(
        prior.get("disposition") == "OWNED_BY_CURRENT_TICKET",
        "post-route context: returned finding must be OWNED_BY_CURRENT_TICKET",
    )

    feasibility_evidence = _str_list(
        feasibility.get("evidence_sources"),
        "feasibility.evidence_sources",
        nonempty=True,
    )
    route_evidence = _str_list(
        route_return.get("evidence_sources"),
        "route_return.evidence_sources",
        nonempty=True,
    )
    expected_evidence = sorted(
        set(feasibility_evidence)
        | set(route_evidence)
        | {str(route_return.get("route_result_source"))}
    )
    actual_evidence = _str_list(
        value.get("adjudicated_evidence_sources"),
        "adjudicated_evidence_sources",
        nonempty=True,
    )
    _need(
        actual_evidence == expected_evidence,
        "post-route context: adjudicated evidence must equal the exact union of current "
        "feasibility and route-return evidence",
    )

    return PostRouteContextReceipt(
        ticket=route_receipt.ticket,
        finding_id=route_receipt.finding_id,
        feasibility_sha256=feasibility_receipt.artifact_sha256,
        route_return_sha256=expected_route_sha,
        artifact_sha256=sha256_canonical_json(value),
    )


def validate_reroute(
    value: dict[str, Any],
    context: dict[str, Any],
    blocked_feasibility: dict[str, Any],
) -> PostRouteRerouteReceipt:
    _need(
        value.get("schema") == REROUTE_SCHEMA,
        f"post-route reroute: schema must be {REROUTE_SCHEMA}",
    )
    _need(
        set(value)
        == {
            "schema",
            "ticket",
            "contract_schema",
            "contract_hash",
            "context_sha256",
            "returned_finding_id",
            "new_finding_id",
            "classification",
            "new_evidence_sources",
            "new_fact",
            "first_observed_after_context",
            "blocked_feasibility_sha256",
            "route",
        },
        "post-route reroute: unsupported top-level fields",
    )
    _need(context.get("schema") == CONTEXT_SCHEMA, "post-route reroute: invalid context schema")
    try:
        blocked_receipt = validate_feasibility(blocked_feasibility)
    except FeasibilityError as exc:
        raise PostRouteControlError(f"blocked feasibility invalid: {exc}") from exc
    _need(blocked_receipt.outcome == "BLOCKED", "post-route reroute requires BLOCKED feasibility")

    _need(value.get("ticket") == context.get("ticket") == blocked_receipt.ticket, "post-route reroute: ticket mismatch")
    _need(
        value.get("contract_schema") == context.get("contract_schema")
        == blocked_receipt.contract_schema,
        "post-route reroute: contract schema mismatch",
    )
    _need(
        value.get("contract_hash") == context.get("contract_hash")
        == blocked_receipt.contract_hash,
        "post-route reroute: contract hash mismatch",
    )
    _need(
        value.get("context_sha256") == sha256_canonical_json(context),
        "post-route reroute: context SHA mismatch",
    )
    returned_finding = _text(value.get("returned_finding_id"), "returned_finding_id")
    _need(returned_finding == context.get("finding_id"), "post-route reroute: returned finding mismatch")
    new_finding = _text(value.get("new_finding_id"), "new_finding_id")
    _need(
        new_finding != returned_finding,
        "post-route reroute: the returned finding may not be relabeled as a new routing gap",
    )
    classification = value.get("classification")
    _need(
        classification in ROUTING_CLASSIFICATIONS,
        "post-route reroute: invalid classification",
    )
    blocked = blocked_feasibility.get("blocked")
    _need(isinstance(blocked, dict), "post-route reroute: missing blocked payload")
    _need(
        blocked.get("classification") == classification,
        "post-route reroute: classification differs from blocked feasibility",
    )
    _need(value.get("route") == blocked.get("route"), "post-route reroute: route mismatch")
    _need(
        value.get("blocked_feasibility_sha256") == blocked_receipt.artifact_sha256,
        "post-route reroute: blocked feasibility SHA mismatch",
    )

    returned_row = _prior_finding(blocked_feasibility, returned_finding)
    _need(returned_row is not None, "post-route reroute: returned finding missing from blocked feasibility")
    assert returned_row is not None
    _need(
        returned_row.get("disposition") == "OWNED_BY_CURRENT_TICKET",
        "post-route reroute: returned finding must remain implementation-owned",
    )
    new_row = _prior_finding(blocked_feasibility, new_finding)
    _need(new_row is not None, "post-route reroute: new finding missing from blocked feasibility")
    assert new_row is not None
    _need(
        new_row.get("disposition") in {"ROUTING_OR_PLANNING_GAP", "AMBIGUOUS"},
        "post-route reroute: new finding is not a routing/planning gap",
    )

    new_evidence = _str_list(
        value.get("new_evidence_sources"),
        "new_evidence_sources",
        nonempty=True,
    )
    adjudicated = set(
        _str_list(
            context.get("adjudicated_evidence_sources"),
            "context.adjudicated_evidence_sources",
            nonempty=True,
        )
    )
    _need(
        not set(new_evidence).intersection(adjudicated),
        "post-route reroute: new evidence overlaps the adjudicated route frontier",
    )
    blocked_evidence = set(
        _str_list(
            blocked_feasibility.get("evidence_sources"),
            "blocked_feasibility.evidence_sources",
            nonempty=True,
        )
    )
    _need(
        set(new_evidence) <= blocked_evidence,
        "post-route reroute: new evidence missing from blocked feasibility",
    )
    _need(
        value.get("first_observed_after_context") is True,
        "post-route reroute: new evidence must be first observed after the post-route context",
    )
    _text(value.get("new_fact"), "new_fact")

    return PostRouteRerouteReceipt(
        ticket=blocked_receipt.ticket,
        returned_finding_id=returned_finding,
        new_finding_id=new_finding,
        classification=str(classification),
        artifact_sha256=sha256_canonical_json(value),
    )


def validate_terminal(
    value: dict[str, Any],
    route_return: dict[str, Any],
) -> RouteTerminalReceipt:
    _need(
        value.get("schema") == TERMINAL_SCHEMA,
        f"route terminal: schema must be {TERMINAL_SCHEMA}",
    )
    _need(
        set(value)
        == {
            "schema",
            "ticket",
            "contract_schema",
            "contract_hash",
            "route_return_sha256",
            "candidate_state",
            "mutation_started",
            "attempt_consumed",
            "disposition",
            "evidence_sources",
            "basis",
            "reason",
        },
        "route terminal: unsupported top-level fields",
    )
    try:
        route_receipt = validate_route_return(route_return)
    except RouteReturnError as exc:
        raise PostRouteControlError(f"route terminal: route return invalid: {exc}") from exc
    _need(route_receipt.status == "IN_PROGRESS", "route terminal requires IN_PROGRESS route return")
    _need(value.get("ticket") == route_receipt.ticket, "route terminal: ticket mismatch")
    _need(
        value.get("contract_schema") == route_receipt.contract_schema,
        "route terminal: contract schema mismatch",
    )
    _need(
        value.get("contract_hash") == route_receipt.contract_hash,
        "route terminal: contract hash mismatch",
    )
    _need(
        value.get("route_return_sha256") == sha256_canonical_json(route_return),
        "route terminal: route-return SHA mismatch",
    )
    candidate_state = _digest(value.get("candidate_state"), "candidate_state")
    mutation_started = value.get("mutation_started")
    attempt_consumed = value.get("attempt_consumed")
    _need(isinstance(mutation_started, bool), "route terminal: mutation_started must be boolean")
    _need(isinstance(attempt_consumed, bool), "route terminal: attempt_consumed must be boolean")
    _need(
        attempt_consumed is mutation_started,
        "route terminal: pre-verifier attempt is consumed iff corrective mutation started",
    )
    if not mutation_started:
        _need(
            candidate_state == route_return.get("failed_candidate_state"),
            "route terminal: no-mutation stop must preserve the exact failed candidate state",
        )
    disposition = value.get("disposition")
    _need(disposition in TERMINAL_DISPOSITIONS, "route terminal: invalid disposition")
    evidence = _str_list(value.get("evidence_sources"), "evidence_sources", nonempty=True)
    basis = _str_list(value.get("basis"), "basis", nonempty=True)
    _need(set(basis) <= set(evidence), "route terminal: basis missing from evidence_sources")
    _text(value.get("reason"), "reason")

    return RouteTerminalReceipt(
        ticket=route_receipt.ticket,
        disposition=str(disposition),
        mutation_started=mutation_started,
        attempt_consumed=attempt_consumed,
        artifact_sha256=sha256_canonical_json(value),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    context = sub.add_parser("context")
    context.add_argument("artifact", type=Path)
    context.add_argument("--feasibility", type=Path, required=True)
    context.add_argument("--route-return", type=Path, required=True)

    reroute = sub.add_parser("reroute")
    reroute.add_argument("artifact", type=Path)
    reroute.add_argument("--context", type=Path, required=True)
    reroute.add_argument("--feasibility", type=Path, required=True)

    terminal = sub.add_parser("terminal")
    terminal.add_argument("artifact", type=Path)
    terminal.add_argument("--route-return", type=Path, required=True)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        if args.command == "context":
            receipt = validate_context(
                _read(args.artifact),
                _read(args.feasibility),
                _read(args.route_return),
            )
            print("IMPLEMENT TICKET POST-ROUTE CONTEXT: VALID")
            print(f"Ticket: #{receipt.ticket}")
            print(f"Finding: {receipt.finding_id}")
            print(f"Feasibility SHA-256: {receipt.feasibility_sha256}")
            print(f"Route Return SHA-256: {receipt.route_return_sha256}")
            print(f"Post-Route Context SHA-256: {receipt.artifact_sha256}")
        elif args.command == "reroute":
            receipt = validate_reroute(
                _read(args.artifact),
                _read(args.context),
                _read(args.feasibility),
            )
            print("IMPLEMENT TICKET POST-ROUTE REROUTE: VALID")
            print(f"Ticket: #{receipt.ticket}")
            print(f"Returned finding: {receipt.returned_finding_id}")
            print(f"New finding: {receipt.new_finding_id}")
            print(f"Classification: {receipt.classification}")
            print(f"Post-Route Reroute SHA-256: {receipt.artifact_sha256}")
        else:
            receipt = validate_terminal(
                _read(args.artifact),
                _read(args.route_return),
            )
            print("IMPLEMENT TICKET ROUTE TERMINAL: VALID")
            print(f"Ticket: #{receipt.ticket}")
            print(f"Disposition: {receipt.disposition}")
            print(f"Mutation started: {'YES' if receipt.mutation_started else 'NO'}")
            print(f"Attempt consumed: {'YES' if receipt.attempt_consumed else 'NO'}")
            print(f"Route Terminal SHA-256: {receipt.artifact_sha256}")
    except (
        PostRouteControlError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
