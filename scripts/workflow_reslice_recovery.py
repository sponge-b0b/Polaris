from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

MARKER = "<!-- ticket-reslice-recovery:v1 -->"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FIELD_RE = re.compile(r"^\*\*(?P<key>[^*]+):\*\*\s*(?P<value>.+?)\s*$")
ISSUE_RE = re.compile(r"#(\d+)")
VALID_STATUSES = {
    "pending-prerequisite",
    "source-complete",
    "prerequisite-complete",
    "pending-source-retirement",
    "source-retired",
    "source-reconciled",
}


class RecoveryError(ValueError):
    pass


@dataclass(frozen=True)
class RecoveryRecord:
    status: str
    parent_spec: int
    destination_parent_spec: int
    source_ticket: int
    destination_ticket: int
    source_disposition: str
    shared_branch: str | None
    source_branch: str
    destination_branch: str
    source_baseline: str
    reslice_anchor: str
    native_order: tuple[int, ...]
    execution_order: str
    execution_order_source: str
    donor_checkout: str
    donor_head: str
    candidate_state: str
    attention_receipt_hash: str
    source_completion: str
    source_retirement: str | None
    destination_baseline: str
    destination_completion: str
    attribution_rows: int
    sha256: str


def _fields(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = FIELD_RE.match(line.strip())
        if match:
            key = match.group("key").strip()
            if key in result:
                raise RecoveryError(f"duplicate field: {key}")
            result[key] = match.group("value").strip()
    return result


def _issue(value: str, field: str) -> int:
    match = re.fullmatch(r"#(\d+)", value)
    if not match:
        raise RecoveryError(f"{field} must be #<number>")
    return int(match.group(1))


def _sha_or_pending(value: str, field: str) -> str:
    if value == "Pending" or HEX40.fullmatch(value):
        return value
    raise RecoveryError(f"{field} must be Pending or 40-hex SHA")


def _source_completion(value: str) -> str:
    if value in {"Pending", "Not applicable"} or HEX40.fullmatch(value):
        return value
    raise RecoveryError(
        "Source completion commit must be Pending, Not applicable, or 40-hex SHA"
    )


def _required(fields: dict[str, str], key: str) -> str:
    value = fields.get(key)
    if not value:
        raise RecoveryError(f"missing field: {key}")
    return value


def _parse_status(fields: dict[str, str]) -> str:
    status = _required(fields, "Status")
    if status not in VALID_STATUSES:
        raise RecoveryError(f"unsupported Status: {status}")
    return status


def _parse_identity(fields: dict[str, str]) -> tuple[int, int, int, str]:
    parent_spec = _issue(_required(fields, "Parent Spec"), "Parent Spec")
    source_ticket = _issue(_required(fields, "Source ticket"), "Source ticket")
    destination_ticket = _issue(
        _required(fields, "Destination ticket"), "Destination ticket"
    )
    if source_ticket == destination_ticket:
        raise RecoveryError("Source ticket and Destination ticket must differ")

    source_disposition = fields.get("Source disposition", "execute")
    if source_disposition not in {"execute", "retire"}:
        raise RecoveryError("Source disposition must be execute or retire")
    return parent_spec, source_ticket, destination_ticket, source_disposition


def _destination_parent_spec(
    fields: dict[str, str], parent_spec: int
) -> tuple[int, str | None]:
    value = fields.get("Destination Parent Spec")
    if value is None:
        return parent_spec, None
    return _issue(value, "Destination Parent Spec"), value


def _parse_execute_branches(
    fields: dict[str, str],
    *,
    parent_spec: int,
    destination_parent_spec: int,
) -> tuple[str, str, str]:
    shared_branch = fields.get("Shared branch")
    if not shared_branch:
        raise RecoveryError("execute recovery requires Shared branch")

    source_branch = fields.get("Source branch", shared_branch)
    destination_branch = fields.get("Destination branch", shared_branch)
    if source_branch != shared_branch or destination_branch != shared_branch:
        raise RecoveryError(
            "execute recovery Source/Destination branches must equal Shared branch"
        )
    if destination_parent_spec != parent_spec:
        raise RecoveryError(
            "execute recovery Destination Parent Spec must equal Parent Spec"
        )
    return shared_branch, source_branch, destination_branch


def _parse_retired_branches(
    fields: dict[str, str],
    *,
    destination_parent_text: str | None,
) -> tuple[None, str, str]:
    if fields.get("Shared branch") is not None:
        raise RecoveryError("retired-source recovery must not declare Shared branch")

    source_branch = fields.get("Source branch")
    if not source_branch:
        raise RecoveryError("retired-source recovery requires Source branch")

    destination_branch = fields.get("Destination branch")
    if not destination_branch:
        raise RecoveryError("retired-source recovery requires Destination branch")

    if destination_parent_text is None:
        raise RecoveryError("retired-source recovery requires Destination Parent Spec")
    return None, source_branch, destination_branch


def _parse_branches(
    fields: dict[str, str], *, source_disposition: str, parent_spec: int
) -> tuple[int, str | None, str, str]:
    destination_parent_spec, destination_parent_text = _destination_parent_spec(
        fields, parent_spec
    )
    if source_disposition == "execute":
        shared, source, destination = _parse_execute_branches(
            fields,
            parent_spec=parent_spec,
            destination_parent_spec=destination_parent_spec,
        )
    else:
        shared, source, destination = _parse_retired_branches(
            fields,
            destination_parent_text=destination_parent_text,
        )
    return destination_parent_spec, shared, source, destination


def _require_hex40(value: str, name: str) -> str:
    if not HEX40.fullmatch(value):
        raise RecoveryError(f"{name} must be 40-hex SHA")
    return value


def _require_hex64(value: str, name: str) -> str:
    if not HEX64.fullmatch(value):
        raise RecoveryError(f"{name} must be 64-hex hash")
    return value


def _parse_candidate_identity(
    fields: dict[str, str],
) -> tuple[str, str, str, str, str]:
    source_baseline = _require_hex40(
        _required(fields, "Source ticket baseline"),
        "Source ticket baseline",
    )
    reslice_anchor = _require_hex40(
        _required(fields, "Reslice branch anchor"),
        "Reslice branch anchor",
    )
    donor_head = _require_hex40(
        _required(fields, "Protected donor HEAD / Execution Anchor"),
        "Protected donor HEAD / Execution Anchor",
    )
    candidate_state = _require_hex64(
        _required(fields, "Protected donor candidate state"),
        "Protected donor candidate state",
    )
    attention_hash = _require_hex64(
        _required(fields, "Protected donor Attention receipt file SHA-256"),
        "Protected donor Attention receipt file SHA-256",
    )
    return source_baseline, reslice_anchor, donor_head, candidate_state, attention_hash


def _parse_native_order(fields: dict[str, str]) -> tuple[int, ...]:
    order_text = _required(fields, "Native execution order")
    native_order = tuple(int(value) for value in ISSUE_RE.findall(order_text))
    if len(native_order) != len(set(native_order)):
        raise RecoveryError("Native execution order must contain unique issue numbers")
    return native_order


def _parse_retired_order(
    fields: dict[str, str],
    *,
    native_order: tuple[int, ...],
    source_ticket: int,
    destination_ticket: int,
) -> tuple[str, str]:
    if not native_order or destination_ticket not in native_order:
        raise RecoveryError(
            "retired-source Native execution order must contain Destination"
        )
    if source_ticket in native_order:
        raise RecoveryError(
            "retired-source Native execution order must not contain retired Source"
        )
    if fields.get("Execution order") != "destination-only":
        raise RecoveryError("retired-source Execution order must be destination-only")
    return "destination-only", "explicit"


def _parse_execute_order(
    fields: dict[str, str],
    *,
    native_order: tuple[int, ...],
    source_ticket: int,
    destination_ticket: int,
) -> tuple[str, str]:
    if len(native_order) < 2:
        raise RecoveryError(
            "Native execution order must contain at least Source and Destination"
        )
    if source_ticket not in native_order or destination_ticket not in native_order:
        raise RecoveryError(
            "Native execution order must contain Source and Destination"
        )

    source_index = native_order.index(source_ticket)
    destination_index = native_order.index(destination_ticket)
    derived_order = (
        "source-first" if source_index < destination_index else "destination-first"
    )
    explicit_order = fields.get("Execution order")
    if explicit_order is None:
        return derived_order, "derived-legacy"
    if explicit_order not in {"source-first", "destination-first"}:
        raise RecoveryError("Execution order must be source-first or destination-first")
    if explicit_order != derived_order:
        raise RecoveryError("Execution order contradicts Native execution order")
    return explicit_order, "explicit"


def _parse_execution_order(
    fields: dict[str, str],
    *,
    source_disposition: str,
    source_ticket: int,
    destination_ticket: int,
) -> tuple[tuple[int, ...], str, str]:
    native_order = _parse_native_order(fields)
    if source_disposition == "retire":
        execution_order, order_source = _parse_retired_order(
            fields,
            native_order=native_order,
            source_ticket=source_ticket,
            destination_ticket=destination_ticket,
        )
    else:
        execution_order, order_source = _parse_execute_order(
            fields,
            native_order=native_order,
            source_ticket=source_ticket,
            destination_ticket=destination_ticket,
        )
    return native_order, execution_order, order_source


def _validate_retired_pending(
    source_retirement: str | None,
    _destination_baseline: str,
    destination_completion: str,
) -> None:
    if source_retirement != "Pending":
        raise RecoveryError(
            "pending-source-retirement requires Source retirement Pending"
        )
    if destination_completion != "Pending":
        raise RecoveryError(
            "pending-source-retirement requires Destination completion Pending"
        )


def _validate_source_retired(
    source_retirement: str | None,
    _destination_baseline: str,
    destination_completion: str,
) -> None:
    if source_retirement != "closed-not-planned":
        raise RecoveryError(
            "source-retired requires Source retirement closed-not-planned"
        )
    if destination_completion != "Pending":
        raise RecoveryError("source-retired requires Destination completion Pending")


def _validate_retired_reconciled(
    source_retirement: str | None,
    destination_baseline: str,
    destination_completion: str,
) -> None:
    if source_retirement != "closed-not-planned":
        raise RecoveryError(
            "retired source-reconciled requires Source retirement closed-not-planned"
        )
    if not HEX40.fullmatch(destination_completion):
        raise RecoveryError(
            "retired source-reconciled requires Destination completion SHA"
        )
    if not HEX40.fullmatch(destination_baseline):
        raise RecoveryError(
            "retired source-reconciled requires pinned Destination baseline SHA"
        )


def _validate_retired_status(
    *,
    status: str,
    source_retirement: str | None,
    destination_baseline: str,
    destination_completion: str,
) -> None:
    if source_retirement not in {"Pending", "closed-not-planned"}:
        raise RecoveryError(
            "retired-source recovery requires Source retirement: "
            "Pending or closed-not-planned"
        )

    validators = {
        "pending-source-retirement": _validate_retired_pending,
        "source-retired": _validate_source_retired,
        "source-reconciled": _validate_retired_reconciled,
    }
    validator = validators.get(status)
    if validator is None:
        raise RecoveryError(f"Status {status} is invalid for retired-source recovery")
    validator(
        source_retirement,
        destination_baseline,
        destination_completion,
    )


def _validate_pending_prerequisite(
    _execution_order: str,
    source_completion: str,
    _destination_baseline: str,
    destination_completion: str,
) -> None:
    if source_completion != "Pending" or destination_completion != "Pending":
        raise RecoveryError("pending-prerequisite requires both completions Pending")


def _validate_source_complete(
    execution_order: str,
    source_completion: str,
    _destination_baseline: str,
    destination_completion: str,
) -> None:
    if execution_order != "source-first":
        raise RecoveryError("source-complete is valid only for source-first recovery")
    if not HEX40.fullmatch(source_completion) or destination_completion != "Pending":
        raise RecoveryError(
            "source-complete requires Source completion SHA and Destination Pending"
        )


def _validate_prerequisite_complete(
    execution_order: str,
    source_completion: str,
    destination_baseline: str,
    destination_completion: str,
) -> None:
    if execution_order != "destination-first":
        raise RecoveryError(
            "prerequisite-complete is valid only for destination-first recovery"
        )
    if source_completion != "Pending" or not HEX40.fullmatch(destination_completion):
        raise RecoveryError(
            "prerequisite-complete requires Destination completion SHA "
            "and Source Pending"
        )
    if not HEX40.fullmatch(destination_baseline):
        raise RecoveryError(
            "prerequisite-complete requires pinned Destination baseline SHA"
        )


def _validate_execute_reconciled(
    _execution_order: str,
    source_completion: str,
    destination_baseline: str,
    destination_completion: str,
) -> None:
    if not HEX40.fullmatch(source_completion) or not HEX40.fullmatch(
        destination_completion
    ):
        raise RecoveryError(
            "source-reconciled requires both exact completion commit SHAs"
        )
    if not HEX40.fullmatch(destination_baseline):
        raise RecoveryError(
            "source-reconciled requires pinned Destination baseline SHA"
        )


def _validate_execute_status(
    *,
    status: str,
    execution_order: str,
    source_completion: str,
    destination_baseline: str,
    destination_completion: str,
) -> None:
    validators = {
        "pending-prerequisite": _validate_pending_prerequisite,
        "source-complete": _validate_source_complete,
        "prerequisite-complete": _validate_prerequisite_complete,
        "source-reconciled": _validate_execute_reconciled,
    }
    validator = validators.get(status)
    if validator is None:
        raise RecoveryError(f"Status {status} is invalid for execute recovery")
    validator(
        execution_order,
        source_completion,
        destination_baseline,
        destination_completion,
    )


def _parse_completion_state(
    fields: dict[str, str],
    *,
    status: str,
    source_disposition: str,
    execution_order: str,
) -> tuple[str, str | None, str, str]:
    source_completion = _source_completion(
        _required(fields, "Source completion commit")
    )
    destination_completion = _sha_or_pending(
        _required(fields, "Destination completion commit"),
        "Destination completion commit",
    )
    destination_baseline = _sha_or_pending(
        fields.get("Destination baseline", "Pending"),
        "Destination baseline",
    )
    source_retirement = fields.get("Source retirement")

    if source_disposition == "retire":
        if source_completion != "Not applicable":
            raise RecoveryError(
                "retired-source recovery requires Source completion commit: "
                "Not applicable"
            )
        _validate_retired_status(
            status=status,
            source_retirement=source_retirement,
            destination_baseline=destination_baseline,
            destination_completion=destination_completion,
        )
    else:
        if source_retirement is not None:
            raise RecoveryError("execute recovery must not declare Source retirement")
        if source_completion == "Not applicable":
            raise RecoveryError(
                "execute recovery requires Source completion commit Pending or SHA"
            )
        _validate_execute_status(
            status=status,
            execution_order=execution_order,
            source_completion=source_completion,
            destination_baseline=destination_baseline,
            destination_completion=destination_completion,
        )

    return (
        source_completion,
        source_retirement,
        destination_baseline,
        destination_completion,
    )


def _parse_attribution_rows(text: str) -> int:
    if "### Exact donor attribution at capture" not in text:
        raise RecoveryError("missing Exact donor attribution at capture section")
    rows = sum(
        1 for line in text.splitlines() if line.startswith("| `") and "|" in line[3:]
    )
    if rows < 1:
        raise RecoveryError("donor attribution table must contain at least one item")
    return rows


def parse_record(text: str) -> RecoveryRecord:
    if not text.startswith(MARKER):
        raise RecoveryError("missing ticket-reslice-recovery:v1 marker at start")

    fields = _fields(text)
    status = _parse_status(fields)
    (
        parent_spec,
        source_ticket,
        destination_ticket,
        source_disposition,
    ) = _parse_identity(fields)
    (
        destination_parent_spec,
        shared_branch,
        source_branch,
        destination_branch,
    ) = _parse_branches(
        fields,
        source_disposition=source_disposition,
        parent_spec=parent_spec,
    )
    (
        source_baseline,
        reslice_anchor,
        donor_head,
        candidate_state,
        attention_hash,
    ) = _parse_candidate_identity(fields)

    if _required(fields, "Recovery mode") != "isolated-worktree":
        raise RecoveryError("Recovery mode must be isolated-worktree")

    native_order, execution_order, order_source = _parse_execution_order(
        fields,
        source_disposition=source_disposition,
        source_ticket=source_ticket,
        destination_ticket=destination_ticket,
    )
    (
        source_completion,
        source_retirement,
        destination_baseline,
        destination_completion,
    ) = _parse_completion_state(
        fields,
        status=status,
        source_disposition=source_disposition,
        execution_order=execution_order,
    )

    donor_checkout = _required(fields, "Protected donor checkout")
    attribution_rows = _parse_attribution_rows(text)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    return RecoveryRecord(
        status=status,
        parent_spec=parent_spec,
        destination_parent_spec=destination_parent_spec,
        source_ticket=source_ticket,
        destination_ticket=destination_ticket,
        source_disposition=source_disposition,
        shared_branch=shared_branch,
        source_branch=source_branch,
        destination_branch=destination_branch,
        source_baseline=source_baseline,
        reslice_anchor=reslice_anchor,
        native_order=native_order,
        execution_order=execution_order,
        execution_order_source=order_source,
        donor_checkout=donor_checkout,
        donor_head=donor_head,
        candidate_state=candidate_state,
        attention_receipt_hash=attention_hash,
        source_completion=source_completion,
        source_retirement=source_retirement,
        destination_baseline=destination_baseline,
        destination_completion=destination_completion,
        attribution_rows=attribution_rows,
        sha256=digest,
    )


def _cmd_validate(args: argparse.Namespace) -> int:
    text = Path(args.body).read_text(encoding="utf-8")
    try:
        record = parse_record(text)
    except RecoveryError as exc:
        print("TICKET RESLICE RECOVERY: INVALID")
        print(f"Reason: {exc}")
        return 1

    print("TICKET RESLICE RECOVERY: VALID")
    print("Schema: ticket-reslice-recovery:v1")
    print(f"Status: {record.status}")
    print(f"Source disposition: {record.source_disposition}")
    print(f"Execution order: {record.execution_order}")
    print(f"Execution order source: {record.execution_order_source}")
    print(f"Source ticket: #{record.source_ticket}")
    print(f"Destination ticket: #{record.destination_ticket}")
    print(f"Attribution rows: {record.attribution_rows}")
    print(f"Recovery Record SHA-256: {record.sha256}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--body", required=True)
    validate.set_defaults(func=_cmd_validate)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        return int(args.func(args))
    except RecoveryError as exc:
        print(f"TICKET RESLICE RECOVERY: INVALID\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
