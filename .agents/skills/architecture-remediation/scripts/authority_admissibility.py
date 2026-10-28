from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "polaris.architecture-authority-disposition/v1"
RELATIONS = {
    "FORBIDS_STATE",
    "FIXES_BEHAVIOR",
    "DOES_NOT_RESOLVE_COORDINATE",
    "CONFLICTS",
}
DISPOSITIONS = {
    "FORBIDDEN_BY_EXISTING_AUTHORITY",
    "FIXED_BY_EXISTING_AUTHORITY",
    "UNRESOLVED_MATERIAL_CHOICE",
    "SOURCE_CONFLICT",
}


class AuthorityAdmissibilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuthorityAdmissibilityReceipt:
    source_workflow: str
    disposition: str
    decision_creation_allowed: bool
    sources_checked: int


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise AuthorityAdmissibilityError(message)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _nonempty(value: Any, field: str) -> str:
    _need(
        isinstance(value, str) and value.strip(),
        f"architecture authority: {field} required",
    )
    return value


def _str_list(value: Any, field: str) -> list[str]:
    _need(
        isinstance(value, list),
        f"architecture authority: {field} must be a list",
    )
    _need(
        bool(value)
        and all(isinstance(item, str) and item.strip() for item in value),
        f"architecture authority: {field} contains invalid item",
    )
    _need(
        value == sorted(set(value)),
        f"architecture authority: {field} must be sorted and unique",
    )
    return value


def validate_disposition(
    artifact: dict[str, Any],
) -> AuthorityAdmissibilityReceipt:
    _need(
        artifact.get("schema") == SCHEMA,
        f"architecture authority: schema must be {SCHEMA}",
    )
    _need(
        set(artifact)
        == {
            "schema",
            "source_workflow",
            "source_artifact",
            "observed_state",
            "governing_sources_checked",
            "findings",
            "material_coordinate",
            "disposition",
            "decision_creation_allowed",
        },
        "architecture authority: unsupported top-level fields",
    )
    source_workflow = _nonempty(
        artifact.get("source_workflow"), "source_workflow"
    )
    _nonempty(artifact.get("source_artifact"), "source_artifact")
    _nonempty(artifact.get("observed_state"), "observed_state")
    sources = _str_list(
        artifact.get("governing_sources_checked"),
        "governing_sources_checked",
    )
    source_set = set(sources)

    findings = artifact.get("findings")
    _need(
        isinstance(findings, list) and findings,
        "architecture authority: findings must be a non-empty list",
    )
    seen_sources: set[str] = set()
    relations: set[str] = set()
    for index, finding in enumerate(findings):
        _need(
            isinstance(finding, dict)
            and set(finding) == {"source", "relation", "basis"},
            f"architecture authority: findings[{index}] has invalid shape",
        )
        source = _nonempty(finding.get("source"), f"findings[{index}].source")
        relation = finding.get("relation")
        basis = _nonempty(finding.get("basis"), f"findings[{index}].basis")
        _need(
            source in source_set,
            f"architecture authority: findings[{index}] source was not checked",
        )
        _need(
            relation in RELATIONS,
            f"architecture authority: findings[{index}] invalid relation",
        )
        _need(bool(basis.strip()), "architecture authority: basis required")
        seen_sources.add(source)
        relations.add(relation)

    _need(
        seen_sources == source_set,
        "architecture authority: every governing source needs a finding",
    )

    disposition = artifact.get("disposition")
    _need(
        disposition in DISPOSITIONS,
        "architecture authority: invalid disposition",
    )
    allowed = artifact.get("decision_creation_allowed")
    _need(
        isinstance(allowed, bool),
        "architecture authority: decision_creation_allowed must be boolean",
    )
    coordinate = artifact.get("material_coordinate")
    _need(
        coordinate is None
        or (isinstance(coordinate, str) and coordinate.strip()),
        "architecture authority: material_coordinate must be null or non-empty",
    )

    has_conflict = "CONFLICTS" in relations
    has_forbidden = "FORBIDS_STATE" in relations
    has_fixed = "FIXES_BEHAVIOR" in relations
    has_unresolved = "DOES_NOT_RESOLVE_COORDINATE" in relations

    if has_conflict:
        expected = "SOURCE_CONFLICT"
    elif has_forbidden:
        expected = "FORBIDDEN_BY_EXISTING_AUTHORITY"
    elif has_fixed:
        expected = "FIXED_BY_EXISTING_AUTHORITY"
    else:
        _need(
            has_unresolved,
            "architecture authority: no authority disposition evidence",
        )
        expected = "UNRESOLVED_MATERIAL_CHOICE"

    _need(
        disposition == expected,
        "architecture authority: disposition contradicts governing authority; "
        f"expected {expected}",
    )

    if disposition == "UNRESOLVED_MATERIAL_CHOICE":
        _need(
            isinstance(coordinate, str) and coordinate.strip(),
            "architecture authority: unresolved choice requires material_coordinate",
        )
        _need(
            allowed,
            "architecture authority: unresolved material choice may create decision work",
        )
    else:
        _need(
            coordinate is None,
            "architecture authority: resolved/forbidden/conflict state cannot invent a coordinate",
        )
        _need(
            not allowed,
            "architecture authority: decision creation forbidden by current disposition",
        )

    return AuthorityAdmissibilityReceipt(
        source_workflow=source_workflow,
        disposition=disposition,
        decision_creation_allowed=allowed,
        sources_checked=len(sources),
    )


def _print(receipt: AuthorityAdmissibilityReceipt) -> None:
    print("ARCHITECTURE AUTHORITY DISPOSITION: VALID")
    print(f"Source workflow: {receipt.source_workflow}")
    print(f"Disposition: {receipt.disposition}")
    print(
        "Decision creation allowed: "
        f"{'YES' if receipt.decision_creation_allowed else 'NO'}"
    )
    print(f"Governing sources checked: {receipt.sources_checked}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    try:
        receipt = validate_disposition(_read(args.artifact))
    except (
        AuthorityAdmissibilityError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        parser.error(str(exc))
    _print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
