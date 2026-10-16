"""Render and validate CCL-backed Spec contract projections."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scripts.ccl import CclValidationError, assertion_index
from scripts.ccl_ledger import load_ledger

SCHEMA = "polaris.spec-ccl/v1"
_MARKER = "spec-contract-ccl:v1"
_SECTION = "Canonical Contract Obligations"
_OBLIGATION_ID = re.compile(r"^OBL-[0-9]{3,}$")


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise CclValidationError(message)


def _text(value: Any, where: str) -> str:
    _need(isinstance(value, str) and value.strip() != "", f"{where}: expected text")
    return value


def validate_manifest(
    manifest: dict[str, Any],
    transactions: list[dict[str, Any]],
) -> None:
    """Validate one Spec-to-CCL obligation manifest."""
    _need(isinstance(manifest, dict), "manifest: expected object")
    _need(set(manifest) == {"schema", "obligations"}, "manifest: unsupported shape")
    _need(manifest["schema"] == SCHEMA, f"manifest.schema: expected {SCHEMA}")
    obligations = manifest["obligations"]
    _need(isinstance(obligations, list) and obligations, "manifest.obligations: empty")

    index = assertion_index(transactions)
    obligation_ids: set[str] = set()
    for i, obligation in enumerate(obligations):
        where = f"manifest.obligations[{i}]"
        _need(isinstance(obligation, dict), f"{where}: expected object")
        _need(
            set(obligation) == {"obligation_id", "source_ref", "ccl"},
            f"{where}: unsupported shape",
        )
        obligation_id = _text(obligation["obligation_id"], f"{where}.obligation_id")
        _need(
            _OBLIGATION_ID.fullmatch(obligation_id) is not None,
            f"{where}.obligation_id: invalid",
        )
        _need(obligation_id not in obligation_ids, f"{where}.obligation_id: duplicate")
        obligation_ids.add(obligation_id)
        _text(obligation["source_ref"], f"{where}.source_ref")

        refs = obligation["ccl"]
        _need(isinstance(refs, list) and refs, f"{where}.ccl: expected non-empty list")
        _need(len(refs) == len(set(refs)), f"{where}.ccl: duplicate reference")
        for j, ref in enumerate(refs):
            ref = _text(ref, f"{where}.ccl[{j}]")
            _need(ref in index, f"{where}.ccl[{j}]: unknown CCL assertion {ref}")


def _manifest_comment(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    return f"<!-- {_MARKER}\n{payload}\n-->"


def _render_assertion(assertion: dict[str, Any]) -> str:
    kind = assertion["kind"]
    subject = assertion["subject"]
    value = assertion["constraint"]

    if kind == "persistence":
        return f"{subject}: persistence is `{value['mode']}`."
    if kind == "distinctness":
        return f"{subject}: semantically distinct from `{value['target']}`."
    if kind == "relationship":
        cardinality = ""
        if "minimum" in value or "maximum" in value:
            cardinality = (
                f"; minimum={value.get('minimum', 'unspecified')}, "
                f"maximum={value.get('maximum', 'unspecified')}"
            )
        return (
            f"{subject}: `{value['relation']}` -> `{value['target']}` "
            f"is `{value['presence']}`{cardinality}."
        )
    if kind == "property":
        value_type = f"; type={value['value_type']}" if "value_type" in value else ""
        return (
            f"{subject}: property `{value['name']}` is `{value['presence']}`"
            f"{value_type}."
        )
    if kind == "vocabulary":
        members = ", ".join(f"`{item}`" for item in value["members"]) or "none"
        return (
            f"{subject}.{value['name']}: vocabulary is `{value['closure']}`; "
            f"members: {members}."
        )
    if kind == "history":
        return f"{subject}: history is `{value['mode']}`."
    if kind == "boundary":
        return f"{subject}.{value['surface']}: `{value['disposition']}`."
    if kind == "invariant":
        return f"{subject}: `{value['modality']}` invariant — {value['expression']}"
    raise CclValidationError(f"unsupported CCL assertion kind {kind!r}")


def render_section(
    manifest: dict[str, Any],
    transactions: list[dict[str, Any]],
) -> str:
    """Render the exact authoritative material-semantic Spec section."""
    validate_manifest(manifest, transactions)
    index = assertion_index(transactions)
    lines = [
        f"## {_SECTION}",
        "",
        (
            "Material semantics below are exact CCL projections. Other Spec prose "
            "may explain or plan work but does not strengthen these contracts."
        ),
    ]

    for obligation in manifest["obligations"]:
        lines.extend(
            [
                "",
                f"### {obligation['obligation_id']}",
                "",
                f"Planning source: `{obligation['source_ref']}`",
            ]
        )
        for ref in obligation["ccl"]:
            assertion = index[ref]
            lines.append(f"- `{ref}` — {_render_assertion(assertion)}")
    return "\n".join(lines).rstrip() + "\n"


def manifest_comment(
    manifest: dict[str, Any],
    transactions: list[dict[str, Any]],
) -> str:
    """Return the exact machine-managed manifest comment after validation."""
    validate_manifest(manifest, transactions)
    return _manifest_comment(manifest) + "\n"


def _extract_manifest(body: str) -> dict[str, Any]:
    pattern = re.compile(
        rf"<!--\s*{re.escape(_MARKER)}\s*\n(?P<payload>.*?)\n-->",
        re.DOTALL,
    )
    matches = list(pattern.finditer(body))
    _need(len(matches) == 1, f"Spec: expected exactly one {_MARKER} manifest")
    try:
        value = json.loads(matches[0].group("payload"))
    except json.JSONDecodeError as exc:
        raise CclValidationError(f"Spec CCL manifest: invalid JSON: {exc}") from exc
    _need(isinstance(value, dict), "Spec CCL manifest: expected object")
    return value


def _extract_section(body: str) -> str:
    heading = re.search(rf"(?m)^##\s+{re.escape(_SECTION)}\s*$", body)
    _need(heading is not None, f"Spec: missing ## {_SECTION}")
    start = heading.start()
    tail = body[heading.end() :]
    next_heading = re.search(r"(?m)^##\s+", tail)
    end = heading.end() + (next_heading.start() if next_heading else len(tail))
    return body[start:end].strip() + "\n"


def validate_spec_body(
    body: str,
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate the manifest and exact generated CCL section in one Spec body."""
    manifest = _extract_manifest(body)
    validate_manifest(manifest, transactions)
    expected = render_section(manifest, transactions)
    actual = _extract_section(body)
    _need(actual == expected, "Spec Canonical Contract Obligations: projection drift")
    return manifest


def _load_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected top-level object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("render", "comment"):
        child = commands.add_parser(name)
        child.add_argument("manifest")
        child.add_argument("ledger")

    check = commands.add_parser("check")
    check.add_argument("spec_body")
    check.add_argument("ledger")

    args = parser.parse_args()
    try:
        transactions = load_ledger(Path(args.ledger))
        if args.command == "check":
            body = Path(args.spec_body).read_text(encoding="utf-8")
            validate_spec_body(body, transactions)
            print("CCL SPEC PROJECTION VALID")
        else:
            manifest = _load_json(args.manifest)
            if args.command == "render":
                print(render_section(manifest, transactions), end="")
            else:
                print(manifest_comment(manifest, transactions), end="")
    except (CclValidationError, json.JSONDecodeError, OSError) as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
