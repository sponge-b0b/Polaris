"""Maintain append-only Polaris Canonical Contract Ledger history."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from scripts.ccl import CclValidationError, validate_transaction

TRANSACTION_SUFFIX = ".json"


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise CclValidationError(message)


def transaction_filename(transaction: dict[str, Any]) -> str:
    """Return the only legal filename for a validated CCL transaction."""
    validate_transaction(transaction)
    digest = transaction["proposal_hash"].removeprefix("sha256:")
    return f"{digest}{TRANSACTION_SUFFIX}"


def validate_ledger(transactions: list[dict[str, Any]]) -> None:
    """Validate cross-transaction history and revision continuity."""
    proposal_hashes: set[str] = set()
    histories: dict[str, list[dict[str, Any]]] = {}

    for tx_index, transaction in enumerate(transactions):
        validate_transaction(transaction)
        proposal = transaction["proposal_hash"]
        _need(
            proposal not in proposal_hashes,
            f"ledger: duplicate proposal hash {proposal}",
        )
        proposal_hashes.add(proposal)

        contract_ids: set[str] = set()
        for revision in transaction["revisions"]:
            contract_id = revision["contract_id"]
            _need(
                contract_id not in contract_ids,
                f"ledger transaction {tx_index}: duplicate contract {contract_id}",
            )
            contract_ids.add(contract_id)
            histories.setdefault(contract_id, []).append(revision)

    for contract_id, revisions in histories.items():
        ordered = sorted(revisions, key=lambda item: item["revision"])
        expected_revision = 1
        retired = False
        for revision in ordered:
            _need(
                not retired,
                f"{contract_id}: revision after retirement is forbidden",
            )
            actual_revision = revision["revision"]
            _need(
                actual_revision == expected_revision,
                (
                    f"{contract_id}: expected revision {expected_revision}, "
                    f"found {actual_revision}"
                ),
            )
            operation = revision["operation"]
            supersedes = revision["supersedes_revision"]
            if expected_revision == 1:
                _need(operation == "create", f"{contract_id}@1: expected create")
                _need(
                    supersedes is None,
                    f"{contract_id}@1: supersedes_revision must be null",
                )
            else:
                _need(
                    operation in {"revise", "retire"},
                    f"{contract_id}@{actual_revision}: expected revise or retire",
                )
                _need(
                    supersedes == expected_revision - 1,
                    (
                        f"{contract_id}@{actual_revision}: expected "
                        f"supersedes_revision {expected_revision - 1}"
                    ),
                )
            retired = operation == "retire"
            expected_revision += 1


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected top-level object")
    return value


def load_ledger(directory: Path) -> list[dict[str, Any]]:
    """Load and validate every immutable transaction in one ledger directory."""
    if not directory.exists():
        return []
    _need(directory.is_dir(), f"{directory}: expected directory")

    transactions: list[dict[str, Any]] = []
    for path in sorted(directory.glob(f"*{TRANSACTION_SUFFIX}")):
        transaction = _load_json(path)
        expected_name = transaction_filename(transaction)
        _need(
            path.name == expected_name,
            f"{path}: expected filename {expected_name}",
        )
        transactions.append(transaction)

    validate_ledger(transactions)
    return transactions


def admission_state(
    transaction: dict[str, Any],
    existing: list[dict[str, Any]],
) -> str:
    """Return ready or already-present, rejecting illegal ledger history."""
    validate_transaction(transaction)
    validate_ledger(existing)

    proposal = transaction["proposal_hash"]
    if any(item["proposal_hash"] == proposal for item in existing):
        return "already-present"

    validate_ledger([*existing, transaction])
    return "ready"


def persist_transaction(directory: Path, transaction: dict[str, Any]) -> Path:
    """Create one transaction file without overwriting ledger history."""
    existing = load_ledger(directory)
    state = admission_state(transaction, existing)
    target = directory / transaction_filename(transaction)
    if state == "already-present":
        _need(target.exists(), f"{target}: expected idempotent transaction")
        return target

    directory.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(transaction, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o644,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
        load_ledger(directory)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def contract_history(
    transactions: list[dict[str, Any]],
    contract_id: str,
) -> list[dict[str, Any]]:
    """Return validated revisions for one contract in revision order."""
    validate_ledger(transactions)
    revisions = [
        revision
        for transaction in transactions
        for revision in transaction["revisions"]
        if revision["contract_id"] == contract_id
    ]
    _need(revisions, f"unknown CCL contract {contract_id}")
    return sorted(revisions, key=lambda item: item["revision"])


def lookup_contract(
    transactions: list[dict[str, Any]],
    contract_id: str,
    revision: int | None = None,
) -> dict[str, Any]:
    """Return an exact revision, or the latest revision when omitted."""
    history = contract_history(transactions, contract_id)
    if revision is None:
        return history[-1]
    for item in history:
        if item["revision"] == revision:
            return item
    raise CclValidationError(f"unknown CCL contract {contract_id}@{revision}")


def lookup_assertion(
    transactions: list[dict[str, Any]],
    contract_id: str,
    assertion_id: str,
    revision: int | None = None,
) -> dict[str, Any]:
    """Return one assertion from an exact or latest contract revision."""
    contract = lookup_contract(transactions, contract_id, revision)
    for assertion in contract["assertions"]:
        if assertion["assertion_id"] == assertion_id:
            return assertion
    address = f"{contract_id}@{contract['revision']}#{assertion_id}"
    raise CclValidationError(f"unknown CCL assertion {address}")


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate-ledger")
    validate.add_argument("directory")

    admit = commands.add_parser("admit")
    admit.add_argument("directory")
    admit.add_argument("transaction")

    persist = commands.add_parser("persist")
    persist.add_argument("directory")
    persist.add_argument("transaction")

    lookup = commands.add_parser("lookup")
    lookup.add_argument("directory")
    lookup.add_argument("contract_id")
    lookup.add_argument("--revision", type=int)
    lookup.add_argument("--assertion")

    args = parser.parse_args()
    try:
        directory = Path(args.directory)
        if args.command == "validate-ledger":
            transactions = load_ledger(directory)
            print(f"CCL LEDGER VALID: {len(transactions)} transaction(s)")
        elif args.command == "admit":
            state = admission_state(
                _load_json(Path(args.transaction)),
                load_ledger(directory),
            )
            print(f"CCL ADMISSION: {state.upper()}")
        elif args.command == "persist":
            target = persist_transaction(
                directory,
                _load_json(Path(args.transaction)),
            )
            print(target)
        else:
            transactions = load_ledger(directory)
            if args.assertion:
                value = lookup_assertion(
                    transactions,
                    args.contract_id,
                    args.assertion,
                    args.revision,
                )
            else:
                value = lookup_contract(
                    transactions,
                    args.contract_id,
                    args.revision,
                )
            _print_json(value)
    except (CclValidationError, json.JSONDecodeError, OSError) as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
