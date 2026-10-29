from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONCERN_SCHEMA = "polaris.implement-preclosure-concerns/v1"
TRIAGE_SCHEMA = "polaris.implement-verifier-failure-triage/v1"
CONTINUATION_SCHEMA = "polaris.implement-continuation/v1"
CONTRACT_SCHEMAS = {
    "polaris.ticket-contract/v1",
    "polaris.review-remediation-contract/v1",
}
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class BoundedExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConcernReceipt:
    ticket: int
    contract_schema: str
    contract_hash: str
    candidate_state: str
    outcome: str
    concern_count: int
    blocking_count: int
    artifact_sha256: str


@dataclass(frozen=True)
class TriageReceipt:
    ticket: int
    contract_schema: str
    contract_hash: str
    finding_id: str
    classification: str
    prior_local_attempts: int
    artifact_sha256: str


@dataclass(frozen=True)
class ContinuationReceipt:
    ticket: int
    contract_schema: str
    contract_hash: str
    phase: str
    reason: str
    durable_continuation: bool
    artifact_sha256: str


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise BoundedExecutionError(message)


def _sha(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _str(value: Any, field: str) -> str:
    _need(
        isinstance(value, str) and value.strip(),
        f"{field} must be a non-empty string",
    )
    return value


def _str_list(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    _need(isinstance(value, list), f"{field} must be a list")
    _need(
        all(isinstance(item, str) and item.strip() for item in value),
        f"{field} contains invalid item",
    )
    _need(value == sorted(set(value)), f"{field} must be sorted and unique")
    if nonempty:
        _need(bool(value), f"{field} must not be empty")
    return value


def _contract(value: dict[str, Any], prefix: str) -> tuple[int, str, str]:
    ticket = value.get("ticket")
    _need(isinstance(ticket, int) and ticket > 0, f"{prefix}: invalid ticket")
    schema = value.get("contract_schema")
    _need(schema in CONTRACT_SCHEMAS, f"{prefix}: unsupported contract schema")
    assert isinstance(schema, str)
    digest = value.get("contract_hash")
    _need(
        isinstance(digest, str) and _HEX64.fullmatch(digest) is not None,
        f"{prefix}: invalid contract hash",
    )
    return ticket, schema, digest


def validate_concerns(value: dict[str, Any]) -> ConcernReceipt:
    prefix = "pre-closure concerns"
    _need(
        value.get("schema") == CONCERN_SCHEMA,
        f"{prefix}: schema must be {CONCERN_SCHEMA}",
    )
    _need(
        set(value)
        == {
            "schema",
            "ticket",
            "contract_schema",
            "contract_hash",
            "candidate_state",
            "evidence_sources",
            "concerns",
        },
        f"{prefix}: unsupported top-level fields",
    )
    ticket, contract_schema, contract_hash = _contract(value, prefix)
    candidate_state = value.get("candidate_state")
    _need(
        isinstance(candidate_state, str)
        and _HEX64.fullmatch(candidate_state) is not None,
        f"{prefix}: invalid candidate state",
    )
    evidence = _str_list(value.get("evidence_sources"), f"{prefix}.evidence_sources")
    evidence_set = set(evidence)
    concerns = value.get("concerns")
    _need(isinstance(concerns, list), f"{prefix}: concerns must be a list")
    ids: set[str] = set()
    blocking = 0
    for row in concerns:
        _need(isinstance(row, dict), f"{prefix}: invalid concern row")
        _need(
            set(row)
            == {
                "concern_id",
                "summary",
                "assigned_cells",
                "guardrails",
                "falsifiers",
                "disposition",
                "basis",
                "disproof_evidence",
            },
            f"{prefix}: unsupported concern fields",
        )
        concern_id = _str(row.get("concern_id"), f"{prefix}.concern_id")
        _need(concern_id not in ids, f"{prefix}: duplicate concern_id")
        ids.add(concern_id)
        _str(row.get("summary"), f"{concern_id}.summary")
        cells = _str_list(row.get("assigned_cells"), f"{concern_id}.assigned_cells")
        guardrails = _str_list(row.get("guardrails"), f"{concern_id}.guardrails")
        falsifiers = _str_list(row.get("falsifiers"), f"{concern_id}.falsifiers")
        basis = _str_list(row.get("basis"), f"{concern_id}.basis", nonempty=True)
        disproof = _str_list(
            row.get("disproof_evidence"), f"{concern_id}.disproof_evidence"
        )
        _need(
            set(basis) <= evidence_set,
            f"{prefix}: {concern_id} basis missing from evidence_sources",
        )
        _need(
            set(disproof) <= evidence_set,
            f"{prefix}: {concern_id} disproof evidence missing from evidence_sources",
        )
        disposition = row.get("disposition")
        _need(
            disposition in {"DISPROVEN", "BLOCKING", "DEFERRED_OUTSIDE_CONTRACT"},
            f"{prefix}: {concern_id} invalid disposition",
        )
        touches_contract = bool(cells or guardrails or falsifiers)
        if disposition == "DISPROVEN":
            _need(
                bool(disproof),
                f"{prefix}: {concern_id} DISPROVEN requires positive disproof_evidence",
            )
        elif disposition == "BLOCKING":
            _need(
                not disproof,
                f"{prefix}: {concern_id} BLOCKING must not claim disproof_evidence",
            )
            blocking += 1
        else:
            _need(
                not touches_contract,
                f"{prefix}: {concern_id} touches assigned cells/falsifiers/guardrails "
                "and cannot be deferred",
            )
            _need(
                not disproof,
                f"{prefix}: {concern_id} deferred concern must not claim "
                "disproof_evidence",
            )
    outcome = "BLOCKED" if blocking else "PASS"
    return ConcernReceipt(
        ticket=ticket,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
        candidate_state=candidate_state,
        outcome=outcome,
        concern_count=len(concerns),
        blocking_count=blocking,
        artifact_sha256=_sha(value),
    )


def validate_triage(value: dict[str, Any]) -> TriageReceipt:
    prefix = "verifier-failure triage"
    _need(
        value.get("schema") == TRIAGE_SCHEMA,
        f"{prefix}: schema must be {TRIAGE_SCHEMA}",
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
            "evidence_sources",
            "classification",
            "prior_local_attempts",
            "boundary_changes",
            "basis",
            "route",
        },
        f"{prefix}: unsupported top-level fields",
    )
    ticket, contract_schema, contract_hash = _contract(value, prefix)
    failed_state = value.get("failed_candidate_state")
    _need(
        isinstance(failed_state, str) and _HEX64.fullmatch(failed_state) is not None,
        f"{prefix}: invalid failed candidate state",
    )
    result_sha = value.get("verifier_result_sha256")
    _need(
        isinstance(result_sha, str) and _HEX64.fullmatch(result_sha) is not None,
        f"{prefix}: invalid verifier result SHA-256",
    )
    finding_id = _str(value.get("finding_id"), f"{prefix}.finding_id")
    evidence = _str_list(
        value.get("evidence_sources"),
        f"{prefix}.evidence_sources",
        nonempty=True,
    )
    basis = _str_list(value.get("basis"), f"{prefix}.basis", nonempty=True)
    _need(set(basis) <= set(evidence), f"{prefix}: basis missing from evidence_sources")
    prior = value.get("prior_local_attempts")
    _need(
        isinstance(prior, int) and prior >= 0,
        f"{prefix}: invalid prior_local_attempts",
    )
    changes = value.get("boundary_changes")
    _need(isinstance(changes, dict), f"{prefix}: boundary_changes must be an object")
    expected = {
        "new_runtime_dependency",
        "new_deployment_or_config_requirement",
        "new_retention_or_recovery_lifecycle",
        "new_operational_responsibility",
        "new_material_semantic_choice",
        "new_planning_or_ownership_change",
    }
    _need(set(changes) == expected, f"{prefix}: unsupported boundary_changes fields")
    _need(
        all(isinstance(changes[key], bool) for key in expected),
        f"{prefix}: boundary changes must be boolean",
    )
    classification = value.get("classification")
    _need(
        classification in {"IMPLEMENTATION_LOCAL", "ROUTE_REQUIRED"},
        f"{prefix}: invalid classification",
    )
    route = value.get("route")
    if classification == "IMPLEMENTATION_LOCAL":
        _need(
            prior == 0,
            f"{prefix}: only one local corrective attempt is allowed per "
            "verifier finding",
        )
        _need(
            not any(changes.values()),
            f"{prefix}: implementation-local correction cannot introduce material "
            "runtime/operational/semantic/planning boundaries",
        )
        _need(
            route is None,
            f"{prefix}: implementation-local correction must not name a route",
        )
    else:
        _need(
            any(changes.values()),
            f"{prefix}: ROUTE_REQUIRED must identify at least one material "
            "boundary change",
        )
        _need(
            route in {"$architecture-remediation", "$to-specs", "$to-tickets"},
            f"{prefix}: invalid owning route",
        )
    return TriageReceipt(
        ticket=ticket,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
        finding_id=finding_id,
        classification=classification,
        prior_local_attempts=prior,
        artifact_sha256=_sha(value),
    )


def validate_continuation(value: dict[str, Any]) -> ContinuationReceipt:
    prefix = "continuation checkpoint"
    _need(
        value.get("schema") == CONTINUATION_SCHEMA,
        f"{prefix}: schema must be {CONTINUATION_SCHEMA}",
    )
    _need(
        set(value)
        == {
            "schema",
            "ticket",
            "contract_schema",
            "contract_hash",
            "branch",
            "execution_anchor",
            "candidate_state",
            "phase",
            "completed",
            "pending",
            "next_action",
            "reason",
            "verifier_state",
            "stale_evidence",
        },
        f"{prefix}: unsupported top-level fields",
    )
    ticket, contract_schema, contract_hash = _contract(value, prefix)
    _str(value.get("branch"), f"{prefix}.branch")
    anchor = value.get("execution_anchor")
    _need(
        isinstance(anchor, str) and _HEX40.fullmatch(anchor) is not None,
        f"{prefix}: invalid execution anchor",
    )
    candidate_state = value.get("candidate_state")
    _need(
        isinstance(candidate_state, str)
        and _HEX64.fullmatch(candidate_state) is not None,
        f"{prefix}: invalid candidate state",
    )
    phase = value.get("phase")
    phases = {
        "post-feasibility",
        "post-pre-mutation",
        "candidate-created",
        "technical-checks-complete",
        "post-pre-closure",
        "post-verifier-result",
        "post-verifier-triage",
        "routing-prepared",
    }
    _need(phase in phases, f"{prefix}: invalid phase")
    _str_list(value.get("completed"), f"{prefix}.completed")
    _str_list(value.get("pending"), f"{prefix}.pending", nonempty=True)
    _str(value.get("next_action"), f"{prefix}.next_action")
    reason = value.get("reason")
    _need(
        reason
        in {
            "stage-checkpoint",
            "context-compaction",
            "usage-boundary",
            "tool-boundary",
        },
        f"{prefix}: invalid reason",
    )
    verifier = value.get("verifier_state")
    _need(isinstance(verifier, dict), f"{prefix}: verifier_state must be an object")
    _need(
        set(verifier) == {"attempt", "result", "result_sha256"},
        f"{prefix}: unsupported verifier_state fields",
    )
    attempt = verifier.get("attempt")
    _need(
        isinstance(attempt, int) and attempt >= 0,
        f"{prefix}: invalid verifier attempt",
    )
    result = verifier.get("result")
    _need(
        result in {"none", "PASS", "FAIL", "invalid"},
        f"{prefix}: invalid verifier result",
    )
    result_sha = verifier.get("result_sha256")
    if result == "none":
        _need(
            result_sha is None,
            f"{prefix}: verifier result SHA must be null when result is none",
        )
    else:
        _need(
            isinstance(result_sha, str)
            and _HEX64.fullmatch(result_sha) is not None,
            f"{prefix}: invalid verifier result SHA",
        )
    _str_list(value.get("stale_evidence"), f"{prefix}.stale_evidence")
    return ContinuationReceipt(
        ticket=ticket,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
        phase=phase,
        reason=reason,
        durable_continuation=reason in {"usage-boundary", "tool-boundary"},
        artifact_sha256=_sha(value),
    )


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("concerns", "triage", "continuation"):
        item = sub.add_parser(name)
        item.add_argument("artifact", type=Path)
    args = parser.parse_args()
    try:
        value = _read(args.artifact)
        if args.command == "concerns":
            receipt = validate_concerns(value)
            print(f"PRE-CLOSURE CONCERNS: {receipt.outcome}")
            print(f"Ticket: #{receipt.ticket}")
            print(f"Contract Schema: {receipt.contract_schema}")
            print(f"Contract Hash: {receipt.contract_hash}")
            print(f"Candidate state: {receipt.candidate_state}")
            print(f"Concerns: {receipt.concern_count}")
            print(f"Blocking concerns: {receipt.blocking_count}")
            print(f"Concern Artifact SHA-256: {receipt.artifact_sha256}")
        elif args.command == "triage":
            receipt = validate_triage(value)
            print("VERIFIER FAILURE TRIAGE: VALID")
            print(f"Ticket: #{receipt.ticket}")
            print(f"Finding: {receipt.finding_id}")
            print(f"Classification: {receipt.classification}")
            print(f"Prior local attempts: {receipt.prior_local_attempts}")
            print(f"Triage Artifact SHA-256: {receipt.artifact_sha256}")
        else:
            receipt = validate_continuation(value)
            print("IMPLEMENT TICKET CONTINUATION: VALID")
            print(f"Ticket: #{receipt.ticket}")
            print(f"Phase: {receipt.phase}")
            print(f"Reason: {receipt.reason}")
            print(
                "Durable Continuation: "
                f"{'YES' if receipt.durable_continuation else 'NO'}"
            )
            print(f"Continuation Artifact SHA-256: {receipt.artifact_sha256}")
    except (BoundedExecutionError, OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
