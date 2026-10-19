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
    "source-reconciled",
}


class RecoveryError(ValueError):
    pass


@dataclass(frozen=True)
class RecoveryRecord:
    status: str
    parent_spec: int
    source_ticket: int
    destination_ticket: int
    shared_branch: str
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


def _required(fields: dict[str, str], key: str) -> str:
    value = fields.get(key)
    if not value:
        raise RecoveryError(f"missing field: {key}")
    return value


def parse_record(text: str) -> RecoveryRecord:
    if not text.startswith(MARKER):
        raise RecoveryError("missing ticket-reslice-recovery:v1 marker at start")

    fields = _fields(text)
    status = _required(fields, "Status")
    if status not in VALID_STATUSES:
        raise RecoveryError(f"unsupported Status: {status}")

    parent_spec = _issue(_required(fields, "Parent Spec"), "Parent Spec")
    source_ticket = _issue(_required(fields, "Source ticket"), "Source ticket")
    destination_ticket = _issue(
        _required(fields, "Destination ticket"), "Destination ticket"
    )
    if source_ticket == destination_ticket:
        raise RecoveryError("Source ticket and Destination ticket must differ")

    shared_branch = _required(fields, "Shared branch")
    source_baseline = _required(fields, "Source ticket baseline")
    reslice_anchor = _required(fields, "Reslice branch anchor")
    donor_head = _required(fields, "Protected donor HEAD / Execution Anchor")
    candidate_state = _required(fields, "Protected donor candidate state")
    attention_hash = _required(
        fields, "Protected donor Attention receipt file SHA-256"
    )
    for value, name in (
        (source_baseline, "Source ticket baseline"),
        (reslice_anchor, "Reslice branch anchor"),
        (donor_head, "Protected donor HEAD / Execution Anchor"),
    ):
        if not HEX40.fullmatch(value):
            raise RecoveryError(f"{name} must be 40-hex SHA")
    for value, name in (
        (candidate_state, "Protected donor candidate state"),
        (attention_hash, "Protected donor Attention receipt file SHA-256"),
    ):
        if not HEX64.fullmatch(value):
            raise RecoveryError(f"{name} must be 64-hex hash")

    if _required(fields, "Recovery mode") != "isolated-worktree":
        raise RecoveryError("Recovery mode must be isolated-worktree")

    order_text = _required(fields, "Native execution order")
    native_order = tuple(int(value) for value in ISSUE_RE.findall(order_text))
    if len(native_order) < 2 or len(set(native_order)) != len(native_order):
        raise RecoveryError("Native execution order must contain unique issue numbers")
    if source_ticket not in native_order or destination_ticket not in native_order:
        raise RecoveryError("Native execution order must contain Source and Destination")
    source_index = native_order.index(source_ticket)
    destination_index = native_order.index(destination_ticket)
    derived_order = "source-first" if source_index < destination_index else "destination-first"

    explicit_order = fields.get("Execution order")
    if explicit_order is None:
        execution_order = derived_order
        order_source = "derived-legacy"
    else:
        if explicit_order not in {"source-first", "destination-first"}:
            raise RecoveryError("Execution order must be source-first or destination-first")
        if explicit_order != derived_order:
            raise RecoveryError("Execution order contradicts Native execution order")
        execution_order = explicit_order
        order_source = "explicit"

    donor_checkout = _required(fields, "Protected donor checkout")
    source_completion = _sha_or_pending(
        _required(fields, "Source completion commit"), "Source completion commit"
    )
    destination_completion = _sha_or_pending(
        _required(fields, "Destination completion commit"),
        "Destination completion commit",
    )
    destination_baseline = _sha_or_pending(
        fields.get("Destination baseline", "Pending"), "Destination baseline"
    )

    if status == "pending-prerequisite":
        if source_completion != "Pending" or destination_completion != "Pending":
            raise RecoveryError("pending-prerequisite requires both completions Pending")
    elif status == "source-complete":
        if execution_order != "source-first":
            raise RecoveryError("source-complete is valid only for source-first recovery")
        if not HEX40.fullmatch(source_completion) or destination_completion != "Pending":
            raise RecoveryError(
                "source-complete requires Source completion SHA and Destination Pending"
            )
    elif status == "prerequisite-complete":
        if execution_order != "destination-first":
            raise RecoveryError(
                "prerequisite-complete is valid only for destination-first recovery"
            )
        if source_completion != "Pending" or not HEX40.fullmatch(destination_completion):
            raise RecoveryError(
                "prerequisite-complete requires Destination completion SHA and Source Pending"
            )
        if not HEX40.fullmatch(destination_baseline):
            raise RecoveryError(
                "prerequisite-complete requires pinned Destination baseline SHA"
            )
    elif status == "source-reconciled":
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

    if "### Exact donor attribution at capture" not in text:
        raise RecoveryError("missing Exact donor attribution at capture section")
    attribution_rows = sum(
        1
        for line in text.splitlines()
        if line.startswith("| `") and "|" in line[3:]
    )
    if attribution_rows < 1:
        raise RecoveryError("donor attribution table must contain at least one item")

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return RecoveryRecord(
        status=status,
        parent_spec=parent_spec,
        source_ticket=source_ticket,
        destination_ticket=destination_ticket,
        shared_branch=shared_branch,
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
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
