from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
FEASIBILITY_PATH = (
    ROOT / ".agents/skills/implement-ticket/scripts/feasibility_authority.py"
)
SCHEMA = "polaris.architecture-route-request/v1"


class ArchitectureRouteError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArchitectureRouteReceipt:
    ticket: int
    contract_hash: str
    feasibility_outcome: str
    new_evidence_count: int


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ArchitectureRouteError(message)


def _load_feasibility() -> Any:
    script_dir = str(FEASIBILITY_PATH.parent)
    inserted = script_dir not in sys.path
    if inserted:
        sys.path.insert(0, script_dir)
    try:
        spec = importlib.util.spec_from_file_location(
            "_polaris_feasibility_authority", FEASIBILITY_PATH
        )
        if spec is None or spec.loader is None:
            raise ArchitectureRouteError(
                "architecture route: feasibility validator unavailable"
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted:
            sys.path.remove(script_dir)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _str_list(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    _need(isinstance(value, list), f"architecture route: {field} must be a list")
    _need(
        all(isinstance(item, str) and item.strip() for item in value),
        f"architecture route: {field} contains invalid item",
    )
    _need(
        value == sorted(set(value)),
        f"architecture route: {field} must be sorted and unique",
    )
    if nonempty:
        _need(bool(value), f"architecture route: {field} must not be empty")
    return value


def validate_route(
    feasibility: dict[str, Any], request: dict[str, Any]
) -> ArchitectureRouteReceipt:
    module = _load_feasibility()
    f_receipt = module.validate_feasibility(feasibility)
    _need(
        request.get("schema") == SCHEMA,
        f"architecture route: schema must be {SCHEMA}",
    )
    _need(
        set(request)
        == {
            "schema",
            "ticket",
            "contract_hash",
            "question_kind",
            "authority_coordinate",
            "governing_sources_checked",
            "basis",
            "post_feasibility_evidence",
        },
        "architecture route: unsupported top-level fields",
    )
    _need(
        request.get("ticket") == f_receipt.ticket,
        "architecture route: ticket differs from feasibility artifact",
    )
    _need(
        request.get("contract_hash") == f_receipt.contract_hash,
        "architecture route: contract differs from feasibility artifact",
    )
    _need(
        request.get("question_kind") == "semantic-authority-gap",
        "architecture route: implementation difficulty is not an architecture question",
    )
    coordinate = request.get("authority_coordinate")
    _need(
        isinstance(coordinate, str) and coordinate.strip(),
        "architecture route: authority_coordinate required",
    )
    sources_checked = _str_list(
        request.get("governing_sources_checked"),
        "governing_sources_checked",
        nonempty=True,
    )
    basis = _str_list(request.get("basis"), "basis", nonempty=True)
    post = _str_list(
        request.get("post_feasibility_evidence"), "post_feasibility_evidence"
    )
    basis_set = set(basis)
    _need(
        set(sources_checked) <= basis_set,
        "architecture route: governing sources must be included in basis",
    )
    _need(
        set(post) <= basis_set,
        "architecture route: post-feasibility evidence must be included in basis",
    )

    previous = set(feasibility["evidence_sources"])
    new_evidence = set(post) - previous
    _need(
        len(new_evidence) == len(post),
        "architecture route: post-feasibility evidence must be genuinely new",
    )

    if f_receipt.outcome == "PASS":
        _need(
            bool(post),
            "architecture route: feasibility PASS cannot be invalidated by pre-existing evidence; correct the feasibility result instead",
        )
    else:
        blocked = feasibility.get("blocked") or {}
        _need(
            blocked.get("classification") == "contract-authority-gap",
            "architecture route: only contract-authority-gap feasibility BLOCKED may route to architecture",
        )

    return ArchitectureRouteReceipt(
        ticket=f_receipt.ticket,
        contract_hash=f_receipt.contract_hash,
        feasibility_outcome=f_receipt.outcome,
        new_evidence_count=len(new_evidence),
    )


def _print(receipt: ArchitectureRouteReceipt) -> None:
    print("ARCHITECTURE ROUTE: VALID")
    print(f"Ticket: #{receipt.ticket}")
    print(f"Contract Hash: {receipt.contract_hash}")
    print(f"Feasibility outcome: {receipt.feasibility_outcome}")
    print(f"New post-feasibility evidence: {receipt.new_evidence_count}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feasibility", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = validate_route(
            _read(args.feasibility),
            _read(args.request),
        )
    except (
        ArchitectureRouteError,
        json.JSONDecodeError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        parser.error(str(exc))
    _print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
