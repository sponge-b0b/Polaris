"""Validate and inspect Polaris Canonical Contract Ledger v1 artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "polaris.ccl/v1"
PROJECTION_SCHEMA = "polaris.ccl-projection/v1"
AUTHORITY_SCHEMA = "polaris.ccl-authority-check/v1"

_ID = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_ROLES = {"governing", "constraint", "rationale", "evidence"}
_SEMANTIC_ROLES = {"governing", "constraint"}
_MODES = {"existing-authority", "owner-decision", "wayfinder-decision"}
_KINDS = {
    "persistence",
    "distinctness",
    "relationship",
    "property",
    "vocabulary",
    "history",
    "boundary",
    "invariant",
}


class CclValidationError(ValueError):
    """Raised when a CCL artifact violates a deterministic v1 invariant."""


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise CclValidationError(message)


def _obj(
    value: Any,
    required: set[str],
    optional: set[str] = frozenset(),
    where: str = "object",
) -> dict[str, Any]:
    _need(isinstance(value, dict), f"{where}: expected object")
    missing = required - set(value)
    extra = set(value) - required - optional
    _need(not missing, f"{where}: missing keys {sorted(missing)}")
    _need(not extra, f"{where}: unsupported keys {sorted(extra)}")
    return value


def _text(value: Any, where: str) -> str:
    _need(isinstance(value, str) and value.strip() != "", f"{where}: expected text")
    return value


def _texts(value: Any, where: str) -> list[str]:
    _need(isinstance(value, list), f"{where}: expected list")
    result = [_text(item, f"{where}[{i}]") for i, item in enumerate(value)]
    _need(len(result) == len(set(result)), f"{where}: duplicate values")
    return result


def _enum(value: Any, allowed: set[str], where: str) -> str:
    _need(value in allowed, f"{where}: unsupported value {value!r}")
    return value


def _constraint(kind: str, value: Any, where: str) -> None:
    value = _obj(value, set(), set(value) if isinstance(value, dict) else set(), where)
    if kind == "persistence":
        _need(set(value) == {"mode"}, f"{where}: persistence shape")
        _enum(value["mode"], {"durable", "derived", "transient"}, f"{where}.mode")
    elif kind == "distinctness":
        _need(set(value) == {"target"}, f"{where}: distinctness shape")
        _text(value["target"], f"{where}.target")
    elif kind == "relationship":
        required = {"relation", "target", "presence"}
        _need(
            required <= set(value) <= required | {"minimum", "maximum"},
            f"{where}: relationship shape",
        )
        _text(value["relation"], f"{where}.relation")
        _text(value["target"], f"{where}.target")
        _enum(
            value["presence"],
            {"required", "optional", "forbidden"},
            f"{where}.presence",
        )
        for key in ("minimum", "maximum"):
            if key in value and value[key] is not None:
                _need(
                    isinstance(value[key], int) and value[key] >= 0,
                    f"{where}.{key}: expected non-negative integer",
                )
        if "minimum" in value and isinstance(value.get("maximum"), int):
            _need(value["minimum"] <= value["maximum"], f"{where}: min > max")
    elif kind == "property":
        required = {"name", "presence"}
        _need(
            required <= set(value) <= required | {"value_type"},
            f"{where}: property shape",
        )
        _text(value["name"], f"{where}.name")
        _enum(
            value["presence"],
            {"required", "optional", "forbidden"},
            f"{where}.presence",
        )
        if "value_type" in value:
            _text(value["value_type"], f"{where}.value_type")
    elif kind == "vocabulary":
        _need(
            set(value) == {"name", "closure", "members"},
            f"{where}: vocabulary shape",
        )
        _text(value["name"], f"{where}.name")
        closure = _enum(
            value["closure"],
            {"open", "closed", "reserved"},
            f"{where}.closure",
        )
        members = _texts(value["members"], f"{where}.members")
        _need(closure != "reserved" or not members, f"{where}: reserved has members")
    elif kind == "history":
        _need(set(value) == {"mode"}, f"{where}: history shape")
        _enum(
            value["mode"],
            {"append-only", "mutable", "replaceable"},
            f"{where}.mode",
        )
    elif kind == "boundary":
        _need(
            set(value) == {"surface", "disposition"},
            f"{where}: boundary shape",
        )
        _text(value["surface"], f"{where}.surface")
        _enum(
            value["disposition"],
            {"reserved", "forbidden", "implementation-freedom"},
            f"{where}.disposition",
        )
    elif kind == "invariant":
        _need(
            set(value) == {"modality", "expression"},
            f"{where}: invariant shape",
        )
        _enum(value["modality"], {"required", "forbidden"}, f"{where}.modality")
        _text(value["expression"], f"{where}.expression")
    else:
        raise CclValidationError(f"{where}: unsupported kind {kind!r}")


def _origin(value: Any) -> tuple[str, dict[str, str]]:
    value = _obj(value, {"mode", "sources"}, {"wayfinder"}, "origin")
    mode = _enum(value["mode"], _MODES, "origin.mode")
    _need(value["sources"], "origin.sources: expected non-empty list")
    roles: dict[str, str] = {}
    for i, source in enumerate(value["sources"]):
        where = f"origin.sources[{i}]"
        source = _obj(
            source,
            {"source_id", "kind", "role", "ref", "content_sha256"},
            where=where,
        )
        source_id = _text(source["source_id"], f"{where}.source_id")
        _need(source_id not in roles, f"{where}.source_id: duplicate")
        _text(source["kind"], f"{where}.kind")
        roles[source_id] = _enum(source["role"], _SOURCE_ROLES, f"{where}.role")
        _text(source["ref"], f"{where}.ref")
        _need(
            re.fullmatch(r"[0-9a-f]{64}", source["content_sha256"]) is not None,
            f"{where}.content_sha256: invalid",
        )
    if mode == "wayfinder-decision":
        wf = _obj(value.get("wayfinder"), {"map", "decision"}, where="origin.wayfinder")
        _need(
            all(isinstance(wf[key], int) and wf[key] > 0 for key in wf),
            "origin.wayfinder: positive integers required",
        )
    else:
        _need("wayfinder" not in value, "origin.wayfinder: unexpected")
    return mode, roles


def _assertion(
    value: Any,
    where: str,
    roles: dict[str, str],
    mode: str,
) -> str:
    value = _obj(
        value,
        {"assertion_id", "kind", "subject", "constraint", "authority"},
        {"display"},
        where,
    )
    assertion_id = _text(value["assertion_id"], f"{where}.assertion_id")
    _need(_ID.fullmatch(assertion_id) is not None, f"{where}.assertion_id")
    kind = _enum(value["kind"], _KINDS, f"{where}.kind")
    _text(value["subject"], f"{where}.subject")
    _constraint(kind, value["constraint"], f"{where}.constraint")
    authority = _obj(
        value["authority"],
        {"source_ids"},
        where=f"{where}.authority",
    )
    source_ids = _texts(authority["source_ids"], f"{where}.authority.source_ids")
    _need(set(source_ids) <= set(roles), f"{where}.authority: unknown source")
    if mode == "existing-authority":
        _need(
            any(roles[source] in _SEMANTIC_ROLES for source in source_ids),
            f"{where}.authority: no governing/constraint support",
        )
    return assertion_id


def _revision(
    value: Any,
    where: str,
    roles: dict[str, str],
    mode: str,
) -> tuple[str, int]:
    value = _obj(
        value,
        {
            "contract_id",
            "revision",
            "operation",
            "supersedes_revision",
            "owner",
            "scope",
            "assertions",
        },
        {"display", "annotations"},
        where,
    )
    contract_id = _text(value["contract_id"], f"{where}.contract_id")
    _need(_ID.fullmatch(contract_id) is not None, f"{where}.contract_id")
    revision = value["revision"]
    _need(isinstance(revision, int) and revision > 0, f"{where}.revision")
    operation = _enum(
        value["operation"],
        {"create", "revise", "retire"},
        f"{where}.operation",
    )
    prior = value["supersedes_revision"]
    if operation == "create":
        _need(revision == 1 and prior is None, f"{where}: invalid create")
    else:
        _need(
            isinstance(prior, int) and revision == prior + 1,
            f"{where}: invalid supersession",
        )
    _text(value["owner"], f"{where}.owner")
    scope = _obj(
        value["scope"],
        set(),
        {"release", "applies_to"},
        f"{where}.scope",
    )
    for key, item in scope.items():
        _texts(item, f"{where}.scope.{key}")
    assertions = value["assertions"]
    _need(isinstance(assertions, list), f"{where}.assertions")
    _need((operation == "retire") == (not assertions), f"{where}: retire shape")
    ids = [
        _assertion(item, f"{where}.assertions[{i}]", roles, mode)
        for i, item in enumerate(assertions)
    ]
    _need(len(ids) == len(set(ids)), f"{where}.assertions: duplicate ID")
    return contract_id, revision


def _semantic_assertion(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "assertion_id": value["assertion_id"],
        "kind": value["kind"],
        "subject": value["subject"],
        "constraint": copy.deepcopy(value["constraint"]),
    }


def semantic_payload(transaction: dict[str, Any]) -> dict[str, Any]:
    """Return the display/provenance-free semantic payload."""
    revisions = []
    for revision in sorted(
        transaction["revisions"],
        key=lambda item: (item["contract_id"], item["revision"]),
    ):
        assertions = sorted(
            revision["assertions"],
            key=lambda item: item["assertion_id"],
        )
        revisions.append(
            {
                "contract_id": revision["contract_id"],
                "revision": revision["revision"],
                "operation": revision["operation"],
                "supersedes_revision": revision["supersedes_revision"],
                "owner": revision["owner"],
                "scope": copy.deepcopy(revision["scope"]),
                "assertions": [_semantic_assertion(item) for item in assertions],
            }
        )
    return {"schema": SCHEMA, "revisions": revisions}


def proposal_hash(transaction: dict[str, Any]) -> str:
    """Return deterministic identity of material CCL semantics only."""
    encoded = json.dumps(
        semantic_payload(transaction),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def validate_transaction(transaction: dict[str, Any]) -> None:
    """Validate one complete CCL transaction."""
    value = _obj(
        transaction,
        {"schema", "proposal_hash", "origin", "acceptance", "revisions"},
        where="transaction",
    )
    _need(value["schema"] == SCHEMA, f"schema: expected {SCHEMA}")
    _need(
        isinstance(value["proposal_hash"], str)
        and _SHA.fullmatch(value["proposal_hash"]) is not None,
        "proposal_hash: invalid",
    )
    mode, roles = _origin(value["origin"])
    _need(value["revisions"], "revisions: expected non-empty list")
    identities = [
        _revision(item, f"revisions[{i}]", roles, mode)
        for i, item in enumerate(value["revisions"])
    ]
    _need(len(identities) == len(set(identities)), "revisions: duplicate")
    expected = proposal_hash(value)
    _need(value["proposal_hash"] == expected, f"proposal_hash: expected {expected}")
    if mode == "existing-authority":
        _need(value["acceptance"] is None, "acceptance: expected null")
        return
    acceptance = _obj(
        value["acceptance"],
        {"proposal_hash", "artifact"},
        where="acceptance",
    )
    _need(
        acceptance["proposal_hash"] == value["proposal_hash"],
        "acceptance.proposal_hash: mismatch",
    )
    artifact = _obj(
        acceptance["artifact"],
        {"kind", "ref"},
        where="acceptance.artifact",
    )
    _text(artifact["kind"], "acceptance.artifact.kind")
    _text(artifact["ref"], "acceptance.artifact.ref")


def assertion_index(
    transactions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Index exact contract@revision#assertion addresses."""
    result: dict[str, dict[str, Any]] = {}
    for transaction in transactions:
        validate_transaction(transaction)
        for revision in transaction["revisions"]:
            prefix = f"{revision['contract_id']}@{revision['revision']}"
            for assertion in revision["assertions"]:
                address = f"{prefix}#{assertion['assertion_id']}"
                _need(address not in result, f"duplicate assertion {address}")
                result[address] = _semantic_assertion(assertion)
    return result


def validate_projection(
    projection: dict[str, Any],
    transactions: list[dict[str, Any]],
) -> None:
    """Require each downstream semantic claim to equal one CCL assertion."""
    projection = _obj(projection, {"schema", "claims"}, where="projection")
    _need(projection["schema"] == PROJECTION_SCHEMA, "projection.schema")
    _need(projection["claims"], "projection.claims: expected non-empty list")
    index = assertion_index(transactions)
    for i, claim in enumerate(projection["claims"]):
        where = f"projection.claims[{i}]"
        claim = _obj(claim, {"reference", "asserted"}, where=where)
        reference = _text(claim["reference"], f"{where}.reference")
        _need(
            reference in index,
            f"{where}.reference: unknown CCL assertion {reference}",
        )
        asserted = _obj(
            claim["asserted"],
            {"kind", "subject", "constraint"},
            where=f"{where}.asserted",
        )
        expected = index[reference]
        actual = {"assertion_id": expected["assertion_id"], **asserted}
        _need(actual == expected, f"{where}.asserted: semantic drift")


def authority_conflicts(check: dict[str, Any]) -> list[str]:
    """Return conflicts among governing/constraint normalized source claims."""
    check = _obj(
        check,
        {"schema", "contract_id", "assertion_id", "source_claims"},
        where="authority check",
    )
    _need(check["schema"] == AUTHORITY_SCHEMA, "authority check.schema")
    _need(_ID.fullmatch(check["contract_id"]) is not None, "contract_id")
    _need(_ID.fullmatch(check["assertion_id"]) is not None, "assertion_id")
    semantic: list[tuple[str, dict[str, Any]]] = []
    for i, claim in enumerate(check["source_claims"]):
        where = f"authority check.source_claims[{i}]"
        claim = _obj(claim, {"source_id", "role", "normalized"}, where=where)
        source_id = _text(claim["source_id"], f"{where}.source_id")
        role = _enum(claim["role"], _SOURCE_ROLES, f"{where}.role")
        normalized = _obj(
            claim["normalized"],
            {"kind", "subject", "constraint"},
            where=f"{where}.normalized",
        )
        kind = _enum(normalized["kind"], _KINDS, f"{where}.normalized.kind")
        _text(normalized["subject"], f"{where}.normalized.subject")
        _constraint(kind, normalized["constraint"], f"{where}.constraint")
        if role in _SEMANTIC_ROLES:
            semantic.append((source_id, normalized))
    if len(semantic) < 2:
        return []
    first_source, first = semantic[0]
    coordinate = f"{check['contract_id']}#{check['assertion_id']}"
    return [
        f"{coordinate}: {first_source} != {source_id}"
        for source_id, normalized in semantic[1:]
        if normalized != first
    ]


def _render(assertion: dict[str, Any]) -> str:
    subject = assertion["subject"]
    kind = assertion["kind"]
    value = assertion["constraint"]
    if kind == "persistence":
        return f"{subject}: persistence is {value['mode']}."
    if kind == "distinctness":
        return f"{subject}: semantically distinct from {value['target']}."
    if kind == "relationship":
        return (
            f"{subject}: {value['relation']} -> {value['target']} "
            f"({value['presence']})."
        )
    if kind == "vocabulary":
        members = ", ".join(value["members"]) or "none"
        return (
            f"{subject}.{value['name']}: vocabulary is {value['closure']}; "
            f"members: {members}."
        )
    if kind == "history":
        return f"{subject}: history is {value['mode']}."
    if kind == "boundary":
        return f"{subject}.{value['surface']}: {value['disposition']}."
    if kind == "invariant":
        return (
            f"{subject}: {value['modality']} invariant — "
            f"{value['expression']}"
        )
    return f"{subject}: {kind} {json.dumps(value, sort_keys=True)}"


def render_transaction(transaction: dict[str, Any]) -> str:
    """Render typed semantics plus clearly non-authoritative summary prose."""
    validate_transaction(transaction)
    lines: list[str] = []
    for revision in sorted(
        transaction["revisions"],
        key=lambda item: (item["contract_id"], item["revision"]),
    ):
        display = revision.get("display", {})
        lines.extend(
            [
                f"# {display.get('title', revision['contract_id'])}",
                "",
                f"Contract: {revision['contract_id']}@{revision['revision']}",
                f"Owner: {revision['owner']}",
                f"Operation: {revision['operation']}",
            ]
        )
        if display.get("summary"):
            lines.extend(
                [
                    "",
                    "Summary (non-authoritative)",
                    "",
                    display["summary"],
                ]
            )
        lines.extend(["", "Typed contract", ""])
        assertions = sorted(
            revision["assertions"],
            key=lambda item: item["assertion_id"],
        )
        lines.extend(
            f"- `{item['assertion_id']}` — {_render(item)}"
            for item in assertions
        )
        if not assertions:
            lines.append("- No active assertions (retired contract revision).")
        lines.extend(
            [
                "",
                f"Semantic proposal hash: {transaction['proposal_hash']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected top-level object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "hash", "render", "check-authority"):
        child = commands.add_parser(name)
        child.add_argument("path")
    projection = commands.add_parser("check-projection")
    projection.add_argument("projection")
    projection.add_argument("transactions", nargs="+")

    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate_transaction(_load(args.path))
            print("CCL VALID")
        elif args.command == "hash":
            print(proposal_hash(_load(args.path)))
        elif args.command == "render":
            print(render_transaction(_load(args.path)), end="")
        elif args.command == "check-authority":
            conflicts = authority_conflicts(_load(args.path))
            _need(not conflicts, "CCL SOURCE CONFLICT: " + "; ".join(conflicts))
            print("CCL AUTHORITY CONSISTENT")
        else:
            validate_projection(
                _load(args.projection),
                [_load(path) for path in args.transactions],
            )
            print("CCL PROJECTION VALID")
    except (CclValidationError, json.JSONDecodeError) as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
