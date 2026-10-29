from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "polaris.implement-route-return/v1"
TERMINAL_SCHEMA = "polaris.implement-route-terminal/v1"
CONTRACT_SCHEMAS = {
    "polaris.ticket-contract/v1",
    "polaris.review-remediation-contract/v1",
}
ROUTES = {"$architecture-remediation", "$to-specs", "$to-tickets"}
STATUSES = {"READY", "IN_PROGRESS", "CONSUMED"}
RESOLUTION = "EXISTING_AUTHORITY_IMPLEMENTATION_RETURN"
TERMINAL_DISPOSITIONS = {
    "WORKFLOW_DEFECT_NO_MUTATION",
    "PRE_VERIFIER_ROUTE",
    "PRE_VERIFIER_HARD_BLOCKER",
}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class RouteReturnError(RuntimeError):
    pass


@dataclass(frozen=True)
class RouteReturnReceipt:
    ticket: int
    contract_schema: str
    contract_hash: str
    finding_id: str
    route: str
    status: str
    prior_post_route_attempts: int
    artifact_sha256: str


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise RouteReturnError(message)


def _sha(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _digest(value: Any, field: str) -> str:
    _need(
        isinstance(value, str) and _HEX64.fullmatch(value) is not None,
        f"route return: invalid {field}",
    )
    return value


def _text(value: Any, field: str) -> str:
    _need(
        isinstance(value, str) and value.strip(),
        f"route return: {field} must be a non-empty string",
    )
    return value


def _str_list(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    _need(isinstance(value, list), f"route return: {field} must be a list")
    _need(
        all(isinstance(item, str) and item.strip() for item in value),
        f"route return: {field} contains invalid item",
    )
    _need(
        value == sorted(set(value)),
        f"route return: {field} must be sorted and unique",
    )
    if nonempty:
        _need(bool(value), f"route return: {field} must not be empty")
    return value


def validate_route_return(value: dict[str, Any]) -> RouteReturnReceipt:
    _need(
        value.get("schema") == SCHEMA,
        f"route return: schema must be {SCHEMA}",
    )
    _need(
        set(value)
        == {
            "schema",
            "ticket",
            "contract_schema",
            "contract_hash",
            "failed_candidate_state",
            "verifier_result_sha256",
            "finding_id",
            "triage_artifact_sha256",
            "route",
            "route_result_source",
            "route_result_sha256",
            "resolution",
            "returned_owner",
            "contract_changed",
            "prior_post_route_attempts",
            "evidence_sources",
            "basis",
            "status",
            "result_verifier_sha256",
        },
        "route return: unsupported top-level fields",
    )

    ticket = value.get("ticket")
    _need(isinstance(ticket, int) and ticket > 0, "route return: invalid ticket")
    contract_schema = value.get("contract_schema")
    _need(
        contract_schema in CONTRACT_SCHEMAS,
        "route return: unsupported contract schema",
    )
    assert isinstance(contract_schema, str)
    contract_hash = _digest(value.get("contract_hash"), "contract hash")
    _digest(value.get("failed_candidate_state"), "failed candidate state")
    _digest(value.get("verifier_result_sha256"), "verifier result SHA-256")
    finding_id = _text(value.get("finding_id"), "finding_id")
    _digest(value.get("triage_artifact_sha256"), "triage artifact SHA-256")

    route = value.get("route")
    _need(route in ROUTES, "route return: invalid original route")
    assert isinstance(route, str)
    _text(value.get("route_result_source"), "route_result_source")
    _digest(value.get("route_result_sha256"), "route result SHA-256")
    _need(
        value.get("resolution") == RESOLUTION,
        "route return: route must resolve by existing authority back to implementation",
    )
    _need(
        value.get("returned_owner") == "$implement-ticket",
        "route return: returned owner must be $implement-ticket",
    )
    _need(
        value.get("contract_changed") is False,
        "route return: changed contract requires normal contract/feasibility "
        "reconstruction",
    )

    prior = value.get("prior_post_route_attempts")
    _need(
        isinstance(prior, int) and prior >= 0,
        "route return: invalid prior_post_route_attempts",
    )
    _need(
        prior == 0,
        "route return: only one post-route corrective attempt is allowed "
        "for one triage/route-result pair",
    )

    evidence = _str_list(
        value.get("evidence_sources"),
        "evidence_sources",
        nonempty=True,
    )
    basis = _str_list(value.get("basis"), "basis", nonempty=True)
    _need(
        set(basis) <= set(evidence),
        "route return: basis missing from evidence_sources",
    )

    status = value.get("status")
    _need(status in STATUSES, "route return: invalid status")
    assert isinstance(status, str)
    result_sha = value.get("result_verifier_sha256")
    if status in {"READY", "IN_PROGRESS"}:
        _need(
            result_sha is None,
            "route return: active attempt must not already name a terminal result",
        )
    else:
        _digest(result_sha, "terminal result SHA-256")

    return RouteReturnReceipt(
        ticket=ticket,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
        finding_id=finding_id,
        route=route,
        status=status,
        prior_post_route_attempts=prior,
        artifact_sha256=_sha(value),
    )


_IDENTITY_FIELDS = {
    "schema",
    "ticket",
    "contract_schema",
    "contract_hash",
    "failed_candidate_state",
    "verifier_result_sha256",
    "finding_id",
    "triage_artifact_sha256",
    "route",
    "route_result_source",
    "route_result_sha256",
    "resolution",
    "returned_owner",
    "contract_changed",
    "prior_post_route_attempts",
    "evidence_sources",
    "basis",
}


def _validate_terminal_artifact(
    terminal: dict[str, Any],
    previous: dict[str, Any],
) -> tuple[bool, str]:
    _need(
        terminal.get("schema") == TERMINAL_SCHEMA,
        f"route return transition: terminal schema must be {TERMINAL_SCHEMA}",
    )
    _need(
        set(terminal)
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
        "route return transition: unsupported terminal fields",
    )
    _need(terminal.get("ticket") == previous.get("ticket"), "route return transition: terminal ticket mismatch")
    _need(
        terminal.get("contract_schema") == previous.get("contract_schema"),
        "route return transition: terminal contract schema mismatch",
    )
    _need(
        terminal.get("contract_hash") == previous.get("contract_hash"),
        "route return transition: terminal contract hash mismatch",
    )
    _need(
        terminal.get("route_return_sha256") == _sha(previous),
        "route return transition: terminal route-return SHA mismatch",
    )
    candidate_state = _digest(terminal.get("candidate_state"), "terminal candidate state")
    mutation_started = terminal.get("mutation_started")
    attempt_consumed = terminal.get("attempt_consumed")
    _need(isinstance(mutation_started, bool), "route return transition: terminal mutation_started must be boolean")
    _need(isinstance(attempt_consumed, bool), "route return transition: terminal attempt_consumed must be boolean")
    _need(
        attempt_consumed is mutation_started,
        "route return transition: terminal attempt is consumed iff corrective mutation started",
    )
    _need(
        terminal.get("disposition") in TERMINAL_DISPOSITIONS,
        "route return transition: invalid terminal disposition",
    )
    evidence = _str_list(terminal.get("evidence_sources"), "terminal evidence_sources", nonempty=True)
    basis = _str_list(terminal.get("basis"), "terminal basis", nonempty=True)
    _need(set(basis) <= set(evidence), "route return transition: terminal basis missing from evidence_sources")
    _text(terminal.get("reason"), "terminal reason")
    if not mutation_started:
        _need(
            candidate_state == previous.get("failed_candidate_state"),
            "route return transition: no-mutation terminal must preserve failed candidate state",
        )
    return mutation_started, _sha(terminal)


def validate_transition(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    terminal: dict[str, Any] | None = None,
) -> RouteReturnReceipt:
    old = validate_route_return(previous)
    new = validate_route_return(current)
    for field in _IDENTITY_FIELDS:
        _need(
            previous.get(field) == current.get(field),
            f"route return transition: immutable field changed: {field}",
        )

    if (old.status, new.status) == ("READY", "IN_PROGRESS"):
        _need(terminal is None, "route return transition: READY -> IN_PROGRESS does not take a terminal artifact")
        return new

    if old.status == "IN_PROGRESS" and terminal is not None:
        mutation_started, terminal_sha = _validate_terminal_artifact(terminal, previous)
        if mutation_started:
            _need(new.status == "CONSUMED", "route return transition: mutated pre-verifier stop must consume the attempt")
            _need(
                current.get("result_verifier_sha256") == terminal_sha,
                "route return transition: CONSUMED result must equal route-terminal artifact SHA",
            )
        else:
            _need(new.status == "READY", "route return transition: no-mutation terminal must restore READY")
            _need(
                current.get("result_verifier_sha256") is None,
                "route return transition: restored READY must not carry a terminal result",
            )
        return new

    _need(
        (old.status, new.status) == ("IN_PROGRESS", "CONSUMED"),
        "route return transition: status must move READY -> IN_PROGRESS, or "
        "IN_PROGRESS -> CONSUMED/READY through a valid terminal artifact",
    )
    _need(
        terminal is None,
        "route return transition: unexpected terminal artifact",
    )
    # Legacy/fresh-verifier path: the CONSUMED artifact's terminal-result digest is
    # the fresh verifier-result SHA supplied by the owning closure procedure.
    _digest(current.get("result_verifier_sha256"), "result verifier SHA-256")
    return new


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--terminal", type=Path)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    try:
        current = _read(args.artifact)
        if args.previous is None:
            _need(args.terminal is None, "route return: --terminal requires --previous")
            receipt = validate_route_return(current)
        else:
            terminal = _read(args.terminal) if args.terminal is not None else None
            receipt = validate_transition(
                _read(args.previous),
                current,
                terminal=terminal,
            )
    except (RouteReturnError, OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    print("IMPLEMENT TICKET ROUTE RETURN: VALID")
    print(f"Ticket: #{receipt.ticket}")
    print(f"Finding: {receipt.finding_id}")
    print(f"Route: {receipt.route}")
    print(f"Status: {receipt.status}")
    print(f"Prior post-route attempts: {receipt.prior_post_route_attempts}")
    print(f"Route Return Artifact SHA-256: {receipt.artifact_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
