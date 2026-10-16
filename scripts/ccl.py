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
_OPERATIONS = {"create", "revise", "retire"}
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


def _keys(
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
    _need(isinstance(value, str) and bool(value.strip()), f"{where}: expected text")
    return value


def _texts(value: Any, where: str) -> list[str]:
    _need(isinstance(value, list), f"{where}: expected list")
    result = [_text(item, f"{where}[{index}]") for index, item in enumerate(value)]
    _need(len(result) == len(set(result)), f"{where}: duplicates are not allowed")
    return result


def _display(value: Any, where: str) -> None:
    obj = _keys(value, set(), {"title", "summary", "description"}, where)
    for key, item in obj.items():
        _text(item, f"{where}.{key}")


def _constraint(kind: str, value: Any, where: str) -> None:
    obj = _keys(value, set(), {
        "mode", "target", "relation", "presence", "minimum", "maximum",
        "name", "value_type", "closure", "members", "surface",
        "disposition", "modality", "expression",
    }, where)

    def exactly(*names: str) -> None:
        _need(set(obj) == set(names), f"{where}: {kind} requires {sorted(names)}")

    if kind == "persistence":
        exactly("mode")
        _need(obj["mode"] in {"durable", "derived", "transient"}, f"{where}.mode")
    elif kind == "distinctness":
        exactly("target")
        _text(obj["target"], f"{where}.target")
    elif kind == "relationship":
        required = {"relation", "target", "presence"}
        _need(required <= set(obj) <= required | {"minimum", "maximum"}, f"{where}: invalid relationship fields")
        _text(obj["relation"], f"{where}.relation")
        _text(obj["target"], f"{where}.target")
        _need(obj["presence"] in {"required", "optional", "forbidden"}, f"{where}.presence")
        if "minimum" in obj:
            _need(isinstance(obj["minimum"], int) and obj["minimum"] >= 0, f"{where}.minimum")
        if "maximum" in obj:
            _need(obj["maximum"] is None or isinstance(obj["maximum"], int) and obj["maximum"] >= 0, f"{where}.maximum")
        if isinstance(obj.get("maximum"), int) and "minimum" in obj:
            _need(obj["minimum"] <= obj["maximum"], f"{where}: minimum exceeds maximum")
    elif kind == "property":
        required = {"name", "presence"}
        _need(required <= set(obj) <= required | {"value_type"}, f"{where}: invalid property fields")
        _text(obj["name"], f"{where}.name")
        _need(obj["presence"] in {"required", "optional", "forbidden"}, f"{where}.presence")
        if "value_type" in obj:
            _text(obj["value_type"], f"{where}.value_type")
    elif kind == "vocabulary":
        exactly("name", "closure", "members")
        _text(obj["name"], f"{where}.name")
        _need(obj["closure"] in {"open", "closed", "reserved"}, f"{where}.closure")
        members = _texts(obj["members"], f"{where}.members")
        _need(obj["closure"] != "reserved" or not members, f"{where}: reserved vocabulary cannot define members")
    elif kind == "history":
        exactly("mode")
        _need(obj["mode"] in {"append-only", "mutable", "replaceable"}, f"{where}.mode")
    elif kind == "boundary":
        exactly("surface", "disposition")
        _text(obj["surface"], f"{where}.surface")
        _need(obj["disposition"] in {"reserved", "forbidden", "implementation-freedom"}, f"{where}.disposition")
    elif kind == "invariant":
        exactly("modality", "expression")
        _need(obj["modality"] in {"required", "forbidden"}, f"{where}.modality")
        _text(obj["expression"], f"{where}.expression")
    else:
        raise CclValidationError(f"{where}: unsupported kind {kind!r}")


def _origin(value: Any) -> tuple[str, dict[str, str]]:
    obj = _keys(value, {"mode", "sources"}, {"wayfinder"}, "origin")
    mode = obj["mode"]
    _need(mode in _MODES, "origin.mode: unsupported mode")
    _need(isinstance(obj["sources"], list) and obj["sources"], "origin.sources: expected non-empty list")
    roles: dict[str, str] = {}
    for index, source in enumerate(obj["sources"]):
        where = f"origin.sources[{index}]"
        source = _keys(source, {"source_id", "kind", "role", "ref", "content_sha256"}, where=where)
        source_id = _text(source["source_id"], f"{where}.source_id")
        _need(source_id not in roles, f"{where}.source_id: duplicate")
        _text(source["kind"], f"{where}.kind")
        _need(source["role"] in _SOURCE_ROLES, f"{where}.role")
        _text(source["ref"], f"{where}.ref")
        _need(re.fullmatch(r"[0-9a-f]{64}", source["content_sha256"]) is not None, f"{where}.content_sha256")
        roles[source_id] = source["role"]
    if mode == "wayfinder-decision":
        wf = _keys(obj.get("wayfinder"), {"map", "decision"}, where="origin.wayfinder")
        _need(all(isinstance(wf[key], int) and wf[key] > 0 for key in ("map", "decision")), "origin.wayfinder: positive integers required")
    else:
        _need("wayfinder" not in obj, "origin.wayfinder: only legal for wayfinder-decision")
    return mode, roles


def _assertion(value: Any, where: str, roles: dict[str, str], mode: str) -> str:
    obj = _keys(value, {"assertion_id", "kind", "subject", "constraint", "authority"}, {"display"}, where)
    assertion_id = _text(obj["assertion_id"], f"{where}.assertion_id")
    _need(_ID.fullmatch(assertion_id) is not None, f"{where}.assertion_id: invalid")
    _need(obj["kind"] in _KINDS, f"{where}.kind: unsupported")
    _text(obj["subject"], f"{where}.subject")
    _constraint(obj["kind"], obj["constraint"], f"{where}.constraint")
    authority = _keys(obj["authority"], {"source_ids"}, where=f"{where}.authority")
    source_ids = _texts(authority["source_ids"], f"{where}.authority.source_ids")
    _need(set(source_ids) <= set(roles), f"{where}.authority: unknown source")
    if mode == "existing-authority":
        _need(
            any(roles[source] in _SEMANTIC_ROLES for source in source_ids),
            f"{where}.authority: existing-authority requires governing/constraint support",
        )
    if "display" in obj:
        _display(obj["display"], f"{where}.display")
    return assertion_id


def _revision(value: Any, where: str, roles: dict[str, str], mode: str) -> tuple[str, int]:
    obj = _keys(
        value,
        {"contract_id", "revision", "operation", "supersedes_revision", "owner", "scope", "assertions"},
        {"display", "annotations"},
        where,
    )
    contract_id = _text(obj["contract_id"], f"{where}.contract_id")
    _need(_ID.fullmatch(contract_id) is not None, f"{where}.contract_id: invalid")
    revision = obj["revision"]
    _need(isinstance(revision, int) and revision > 0, f"{where}.revision")
    _need(obj["operation"] in _OPERATIONS, f"{where}.operation")
    supersedes = obj["supersedes_revision"]
    if obj["operation"] == "create":
        _need(revision == 1 and supersedes is None, f"{where}: create must be revision 1")
    else:
        _need(isinstance(supersedes, int) and revision == supersedes + 1, f"{where}: revision must immediately supersede prior revision")
    _text(obj["owner"], f"{where}.owner")
    scope = _keys(obj["scope"], set(), {"release", "applies_to"}, f"{where}.scope")
    for key, item in scope.items():
        _texts(item, f"{where}.scope.{key}")
    assertions = obj["assertions"]
    _need(isinstance(assertions, list), f"{where}.assertions")
    _need((obj["operation"] == "retire") == (not assertions), f"{where}: retire iff assertions are empty")
    ids = [_assertion(item, f"{where}.assertions[{i}]", roles, mode) for i, item in enumerate(assertions)]
    _need(len(ids) == len(set(ids)), f"{where}.assertions: duplicate assertion_id")
    if "display" in obj:
        _display(obj["display"], f"{where}.display")
    if "annotations" in obj:
        annotations = _keys(obj["annotations"], set(), {"notes", "examples"}, f"{where}.annotations")
        for key, item in annotations.items():
            _texts(item, f"{where}.annotations.{key}")
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
    for revision in sorted(transaction["revisions"], key=lambda item: (item["contract_id"], item["revision"])):
        revisions.append({
            "contract_id": revision["contract_id"],
            "revision": revision["revision"],
            "operation": revision["operation"],
            "supersedes_revision": revision["supersedes_revision"],
            "owner": revision["owner"],
            "scope": copy.deepcopy(revision["scope"]),
            "assertions": [
                _semantic_assertion(item)
                for item in sorted(revision["assertions"], key=lambda item: item["assertion_id"])
            ],
        })
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
    obj = _keys(transaction, {"schema", "proposal_hash", "origin", "acceptance", "revisions"}, where="transaction")
    _need(obj["schema"] == SCHEMA, f"schema: expected {SCHEMA}")
    _need(isinstance(obj["proposal_hash"], str) and _SHA.fullmatch(obj["proposal_hash"]) is not None, "proposal_hash: invalid")
    mode, roles = _origin(obj["origin"])
    _need(isinstance(obj["revisions"], list) and obj["revisions"], "revisions: expected non-empty list")
    identities = [_revision(item, f"revisions[{i}]", roles, mode) for i, item in enumerate(obj["revisions"])]
    _need(len(identities) == len(set(identities)), "revisions: duplicate contract revision")
    expected = proposal_hash(obj)
    _need(obj["proposal_hash"] == expected, f"proposal_hash: expected {expected}")
    if mode == "existing-authority":
        _need(obj["acceptance"] is None, "acceptance: must be null for existing-authority")
    else:
        acceptance = _keys(obj["acceptance"], {"proposal_hash", "artifact"}, where="acceptance")
        _need(acceptance["proposal_hash"] == obj["proposal_hash"], "acceptance.proposal_hash: mismatch")
        artifact = _keys(acceptance["artifact"], {"kind", "ref"}, where="acceptance.artifact")
        _text(artifact["kind"], "acceptance.artifact.kind")
        _text(artifact["ref"], "acceptance.artifact.ref")


def assertion_index(transactions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index exact contract@revision#assertion addresses."""
    result: dict[str, dict[str, Any]] = {}
    for transaction in transactions:
        validate_transaction(transaction)
        for revision in transaction["revisions"]:
            prefix = f"{revision['contract_id']}@{revision['revision']}"
            for assertion in revision["assertions"]:
                address = f"{prefix}#{assertion['assertion_id']}"
                _need(address not in result, f"ledger: duplicate assertion {address}")
                result[address] = _semantic_assertion(assertion)
    return result


def validate_projection(projection: dict[str, Any], transactions: list[dict[str, Any]]) -> None:
    """Require each downstream semantic claim to equal an exact CCL assertion."""
    obj = _keys(projection, {"schema", "claims"}, where="projection")
    _need(obj["schema"] == PROJECTION_SCHEMA, f"projection.schema: expected {PROJECTION_SCHEMA}")
    _need(isinstance(obj["claims"], list) and obj["claims"], "projection.claims: expected non-empty list")
    index = assertion_index(transactions)
    for i, claim in enumerate(obj["claims"]):
        where = f"projection.claims[{i}]"
        claim = _keys(claim, {"reference", "asserted"}, where=where)
        reference = _text(claim["reference"], f"{where}.reference")
        _need(reference in index, f"{where}.reference: unknown CCL assertion {reference}")
        asserted = _keys(claim["asserted"], {"kind", "subject", "constraint"}, where=f"{where}.asserted")
        expected = index[reference]
        actual = {"assertion_id": expected["assertion_id"], **asserted}
        _need(actual == expected, f"{where}.asserted: semantic strengthening/drift from {reference}")


def authority_conflicts(check: dict[str, Any]) -> list[str]:
    """Return conflicts among governing/constraint normalized source claims."""
    obj = _keys(check, {"schema", "contract_id", "assertion_id", "source_claims"}, where="authority check")
    _need(obj["schema"] == AUTHORITY_SCHEMA, f"authority check.schema: expected {AUTHORITY_SCHEMA}")
    _need(_ID.fullmatch(obj["contract_id"]) is not None, "authority check.contract_id: invalid")
    _need(_ID.fullmatch(obj["assertion_id"]) is not None, "authority check.assertion_id: invalid")
    _need(isinstance(obj["source_claims"], list) and obj["source_claims"], "authority check.source_claims: expected non-empty list")
    semantic: list[tuple[str, dict[str, Any]]] = []
    for i, claim in enumerate(obj["source_claims"]):
        where = f"authority check.source_claims[{i}]"
        claim = _keys(claim, {"source_id", "role", "normalized"}, where=where)
        source_id = _text(claim["source_id"], f"{where}.source_id")
        _need(claim["role"] in _SOURCE_ROLES, f"{where}.role")
        normalized = _keys(claim["normalized"], {"kind", "subject", "constraint"}, where=f"{where}.normalized")
        _need(normalized["kind"] in _KINDS, f"{where}.normalized.kind")
        _text(normalized["subject"], f"{where}.normalized.subject")
        _constraint(normalized["kind"], normalized["constraint"], f"{where}.normalized.constraint")
        if claim["role"] in _SEMANTIC_ROLES:
            semantic.append((source_id, normalized))
    if len(semantic) < 2:
        return []
    first_source, first = semantic[0]
    return [
        f"{obj['contract_id']}#{obj['assertion_id']}: {first_source} != {source_id}"
        for source_id, normalized in semantic[1:]
        if normalized != first
    ]


def _render(assertion: dict[str, Any]) -> str:
    subject, kind, c = assertion["subject"], assertion["kind"], assertion["constraint"]
    if kind == "persistence":
        return f"{subject}: persistence is {c['mode']}."
    if kind == "distinctness":
        return f"{subject}: semantically distinct from {c['target']}."
    if kind == "relationship":
        return f"{subject}: {c['relation']} -> {c['target']} ({c['presence']})."
    if kind == "vocabulary":
        return f"{subject}.{c['name']}: vocabulary is {c['closure']}; members: {', '.join(c['members']) or 'none'}."
    if kind == "history":
        return f"{subject}: history is {c['mode']}."
    if kind == "boundary":
        return f"{subject}.{c['surface']}: {c['disposition']}."
    if kind == "invariant":
        return f"{subject}: {c['modality']} invariant — {c['expression']}"
    return f"{subject}: {kind} {json.dumps(c, sort_keys=True)}"


def render_transaction(transaction: dict[str, Any]) -> str:
    """Render typed semantics plus clearly non-authoritative summary prose."""
    validate_transaction(transaction)
    lines: list[str] = []
    for revision in sorted(transaction["revisions"], key=lambda item: (item["contract_id"], item["revision"])):
        display = revision.get("display", {})
        lines += [
            f"# {display.get('title', revision['contract_id'])}",
            "",
            f"Contract: {revision['contract_id']}@{revision['revision']}",
            f"Owner: {revision['owner']}",
            f"Operation: {revision['operation']}",
        ]
        if display.get("summary"):
            lines += ["", "Summary (non-authoritative)", "", display["summary"]]
        lines += ["", "Typed contract", ""]
        lines += [
            f"- `{item['assertion_id']}` — {_render(item)}"
            for item in sorted(revision["assertions"], key=lambda item: item["assertion_id"])
        ] or ["- No active assertions (retired contract revision)."]
        lines += ["", f"Semantic proposal hash: {transaction['proposal_hash']}", ""]
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
