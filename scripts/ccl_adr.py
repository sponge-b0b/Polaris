"""Render and verify CCL-backed ADR Decision sections."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scripts.ccl import CclValidationError, render_transaction, validate_transaction
from scripts.ccl_ledger import transaction_filename

_START = "<!-- ccl-decision:v1 -->"
_END = "<!-- /ccl-decision:v1 -->"


def transaction_path(transaction: dict[str, Any]) -> str:
    """Return the canonical ledger path for an accepted transaction."""
    return f"contracts/ccl/transactions/{transaction_filename(transaction)}"


def decision_block(transaction: dict[str, Any]) -> str:
    """Render the exact machine-managed ADR Decision block."""
    validate_transaction(transaction)
    path = transaction_path(transaction)
    rendered = render_transaction(transaction).rstrip()
    return (
        f"{_START}\n"
        "The normative semantic contract for this ADR is the typed CCL "
        "projection below.\n"
        "Display summaries are explanatory and non-authoritative.\n\n"
        f"CCL transaction: `{path}`\n\n"
        f"{rendered}\n"
        f"{_END}"
    )


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        raise CclValidationError("ADR: missing frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise CclValidationError("ADR: unterminated frontmatter")
    return text[4:end]


def _decision_section(text: str) -> str:
    match = re.search(r"(?m)^## Decision\s*$", text)
    if match is None:
        raise CclValidationError("ADR: missing Decision section")
    start = match.end()
    next_section = re.search(r"(?m)^##\s+", text[start:])
    end = start + next_section.start() if next_section else len(text)
    return text[start:end].strip()


def validate_adr(text: str, transaction: dict[str, Any]) -> None:
    """Require an accepted ADR to project exactly one accepted CCL transaction."""
    validate_transaction(transaction)
    path = transaction_path(transaction)
    frontmatter = _frontmatter(text)
    required_lines = {
        "status: accepted",
        f"ccl_proposal: {transaction['proposal_hash']}",
        f"ccl_transaction: {path}",
    }
    actual_lines = {line.strip() for line in frontmatter.splitlines()}
    missing = sorted(required_lines - actual_lines)
    if missing:
        raise CclValidationError(f"ADR frontmatter: missing {missing}")

    expected = decision_block(transaction).strip()
    actual = _decision_section(text)
    if actual != expected:
        raise CclValidationError("ADR Decision section: CCL projection drift")


def _load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CclValidationError(f"{path}: expected top-level object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    render = commands.add_parser("render-decision")
    render.add_argument("transaction")

    check = commands.add_parser("check-adr")
    check.add_argument("adr")
    check.add_argument("transaction")

    args = parser.parse_args()
    try:
        transaction = _load(args.transaction)
        if args.command == "render-decision":
            print(decision_block(transaction))
        else:
            text = Path(args.adr).read_text(encoding="utf-8")
            validate_adr(text, transaction)
            print("CCL ADR PROJECTION VALID")
    except (CclValidationError, json.JSONDecodeError, OSError) as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
