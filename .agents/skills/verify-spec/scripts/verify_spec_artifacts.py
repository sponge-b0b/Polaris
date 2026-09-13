#!/usr/bin/env python3
"""Hardened contract/receipt boundary for Polaris ``$verify-spec`` artifacts."""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

BASE_PATH = Path(__file__).with_name("verify_spec_artifacts_base.py")
RECEIPT_FORMAT = "manifest-table-v2"
CELL_RE = re.compile(r"^(?:US|ID|TD|OOS|NORM)-\d+(?:\.[A-Za-z0-9_-]+)?$")
SOURCE_UNIT_RE = re.compile(r"^SU-\d{4,}$")
SOURCE_UNIT_STATES = {"normative-new", "normative-represented", "non-normative"}
CONTRACT_HANDOFF_KEYS = {
    "spec_issue",
    "head",
    "baseline",
    "branch",
    "spec_body_hash",
    "spec_contract_hash",
    "default_branch",
    "default_head",
    "source_counts",
    "manifest",
    "contract_identity",
}


def _load_base() -> Any:
    spec = importlib.util.spec_from_file_location("_polaris_verify_spec_artifacts_base", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("verify-spec base artifact utility could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_base = _load_base()
ValidationError = _base.ValidationError


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _digest_text(value: Any, label: str) -> str:
    return _base._digest_text(value, label)


def _table(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return html.escape(value, quote=False).replace("|", "&#124;").replace("\n", "<br>")


def _review_manifest_parser(receipt: str) -> list[dict[str, str]]:
    review_path = (
        Path(__file__).resolve().parents[2]
        / "review-spec"
        / "scripts"
        / "review_spec_artifacts.py"
    )
    _require(review_path.is_file(), "review-spec artifact parser is missing")
    spec = importlib.util.spec_from_file_location(
        "_polaris_review_spec_artifacts",
        review_path,
    )
    _require(
        spec is not None and spec.loader is not None,
        "review-spec artifact parser could not be loaded",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        parsed = module.parse_verification_manifest(receipt)
    except Exception as exc:  # downstream compatibility boundary
        raise ValidationError(
            f"rendered receipt is not consumable by $review-spec: {exc}"
        ) from exc
    _require(isinstance(parsed, list), "review-spec manifest parser returned invalid data")
    return parsed


def _validate_receipt_round_trip(receipt: str, state: dict[str, Any]) -> None:
    _require(
        _review_manifest_parser(receipt) == state["manifest"],
        "rendered receipt manifest does not round-trip exactly through $review-spec",
    )


def _require_contract_digest(path: str | Path, expected: str) -> None:
    expected_digest = _digest_text(expected, "contract handoff digest")
    actual_digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    _require(
        actual_digest == expected_digest,
        "contract handoff digest mismatch; rebuild via $spec-contract and recertify",
    )


def _validate_contract_identity(contract: dict[str, Any]) -> None:
    identity = contract.get("contract_identity")
    _require(isinstance(identity, dict), "contract_identity must be an object")
    _require(
        set(identity) == {"source_units", "manifest"},
        "contract_identity keys must be source_units and manifest",
    )
    source_rows = identity["source_units"]
    manifest_rows = identity["manifest"]
    _require(
        isinstance(source_rows, list) and bool(source_rows),
        "contract identity source units missing",
    )
    _require(
        isinstance(manifest_rows, list) and bool(manifest_rows),
        "contract identity manifest missing",
    )
    body_hash = _digest_text(contract.get("spec_body_hash"), "spec_body_hash")
    expected_hash = _digest_text(contract.get("spec_contract_hash"), "spec_contract_hash")

    source_ids: list[str] = []
    reverse: dict[str, list[str]] = {}
    for row in source_rows:
        _require(isinstance(row, list) and len(row) == 4, "invalid source-unit identity row")
        source_id, text_hash, classification, mapped_cells = row
        _require(
            isinstance(source_id, str) and SOURCE_UNIT_RE.fullmatch(source_id) is not None,
            "invalid source-unit ID",
        )
        _require(source_id not in source_ids, f"duplicate source-unit ID: {source_id}")
        source_ids.append(source_id)
        _digest_text(text_hash, f"{source_id} text hash")
        _require(classification in SOURCE_UNIT_STATES, f"invalid {source_id} classification")
        if mapped_cells is None:
            cells: list[str] = []
        else:
            _require(
                isinstance(mapped_cells, list),
                f"{source_id} manifest cells must be a list or null",
            )
            cells = mapped_cells
        _require(len(cells) == len(set(cells)), f"{source_id} duplicates manifest cells")
        if classification == "non-normative":
            _require(not cells, f"non-normative {source_id} must not map manifest cells")
        else:
            _require(bool(cells), f"normative {source_id} must map manifest cells")
        for cell in cells:
            _require(
                isinstance(cell, str) and CELL_RE.fullmatch(cell) is not None,
                f"invalid mapped cell in {source_id}",
            )
            reverse.setdefault(cell, []).append(source_id)

    display_manifest, _ = _base._manifest(contract.get("manifest"))
    display_cells = [row["cell"] for row in display_manifest]
    identity_cells: list[str] = []
    for row in manifest_rows:
        _require(isinstance(row, list) and len(row) == 2, "invalid manifest identity row")
        cell, row_source_ids = row
        _require(
            isinstance(cell, str) and CELL_RE.fullmatch(cell) is not None,
            "invalid manifest identity cell",
        )
        _require(cell not in identity_cells, f"duplicate manifest identity cell: {cell}")
        _require(
            isinstance(row_source_ids, list) and bool(row_source_ids),
            f"manifest identity {cell} has no source units",
        )
        _require(
            len(row_source_ids) == len(set(row_source_ids)),
            f"manifest identity {cell} duplicates source units",
        )
        _require(
            all(source_id in source_ids for source_id in row_source_ids),
            f"manifest identity {cell} references unknown source unit",
        )
        _require(
            reverse.get(cell, []) == row_source_ids,
            f"manifest identity {cell} disagrees with source-unit reverse mapping",
        )
        identity_cells.append(cell)

    _require(
        identity_cells == display_cells,
        "contract identity/display manifest cell order mismatch",
    )
    _require(
        set(reverse) == set(identity_cells),
        "source-unit identity maps cells outside the manifest identity",
    )

    payload = (
        "SPEC-CONTRACT-V2\n"
        + body_hash
        + "\n--SOURCE-UNITS--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in source_rows
        )
        + "\n--MANIFEST--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in manifest_rows
        )
        + "\n"
    )
    actual_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    _require(
        actual_hash == expected_hash,
        "contract handoff structural identity does not reproduce SPEC_CONTRACT_HASH",
    )


def finalize_parts(
    contract: Any,
    proofs: Any,
    gates: Any,
    *,
    mode: str,
    prior_checkpoint: str | None,
    repairs: list[str],
    inherited_findings: list[str],
) -> dict[str, Any]:
    _require(isinstance(contract, dict), "contract handoff must be an object")
    keys = set(contract)
    _require(
        keys == CONTRACT_HANDOFF_KEYS,
        "contract handoff keys mismatch: "
        f"missing={sorted(CONTRACT_HANDOFF_KEYS - keys)}, "
        f"extra={sorted(keys - CONTRACT_HANDOFF_KEYS)}",
    )
    _validate_contract_identity(contract)
    finalizer_contract = {
        key: value for key, value in contract.items() if key != "contract_identity"
    }
    return _base.finalize(
        {
            **finalizer_contract,
            "mode": mode,
            "prior_checkpoint": prior_checkpoint,
            "proofs": proofs,
            "gates": gates,
            "repairs": repairs,
            "unrelated_inherited_findings": inherited_findings,
        }
    )


def render_receipt(state: dict[str, Any]) -> str:
    original_table = _base._table
    _base._table = _table
    try:
        receipt = _base.render_receipt(state)
    finally:
        _base._table = original_table
    marker = "**Status:** passed\n"
    _require(marker in receipt, "base receipt status marker is missing")
    return receipt.replace(
        marker,
        marker + f"**Receipt format:** {RECEIPT_FORMAT}\n",
        1,
    )


def _emit_finalization(state: dict[str, Any], receipt_output: str) -> None:
    receipt = render_receipt(state)
    _validate_receipt_round_trip(receipt, state)
    Path(receipt_output).write_text(receipt, encoding="utf-8")
    print(
        json.dumps(
            {
                **state["summary"],
                "verification_hash": state["verification_hash"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _test_contract() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]]]:
    source_identity = [
        ["SU-0001", "1" * 64, "normative-new", ["US-1"]],
        ["SU-0002", "2" * 64, "normative-new", ["US-2"]],
        ["SU-0003", "3" * 64, "normative-new", ["OOS-1"]],
    ]
    manifest_identity = [
        ["US-1", ["SU-0001"]],
        ["US-2", ["SU-0002"]],
        ["OOS-1", ["SU-0003"]],
    ]
    body_hash = "c" * 64
    payload = (
        "SPEC-CONTRACT-V2\n"
        + body_hash
        + "\n--SOURCE-UNITS--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in source_identity
        )
        + "\n--MANIFEST--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in manifest_identity
        )
        + "\n"
    )
    contract_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    contract = {
        "spec_issue": 1,
        "head": "a" * 40,
        "baseline": "b" * 40,
        "branch": "spec-1",
        "spec_body_hash": body_hash,
        "spec_contract_hash": contract_hash,
        "default_branch": "main",
        "default_head": "e" * 40,
        "source_counts": {"user_stories": 2, "out_of_scope": 1},
        "manifest": [
            {
                "cell": "US-1",
                "source": "User Stories | 1",
                "requirement": r"NO_CANDIDATES | EXPLICIT_CREATE_NEW \ literal",
            },
            {
                "cell": "US-2",
                "source": "User Stories 2",
                "requirement": "line one\nline two <br> & markup",
            },
            {
                "cell": "OOS-1",
                "source": "Out of Scope 1",
                "requirement": r"literal \| stays literal",
            },
        ],
        "contract_identity": {
            "source_units": source_identity,
            "manifest": manifest_identity,
        },
    }
    proofs = [
        {
            "cells": ["US-1", "US-2"],
            "state": "proven",
            "evidence": ["application/x.py:1-20", "test_x::test_behavior"],
        },
        {
            "cells": ["OOS-1"],
            "state": "not-applicable",
            "reason": "Originating Spec excludes this surface.",
        },
    ]
    gates = [{"name": "Ruff lint", "status": "PASS", "evidence": "clean"}]
    return contract, proofs, gates


def self_test() -> None:
    _base.self_test()
    contract, proofs, gates = _test_contract()
    state = finalize_parts(
        contract,
        proofs,
        gates,
        mode="full",
        prior_checkpoint=None,
        repairs=[],
        inherited_findings=[],
    )
    receipt = render_receipt(state)
    assert f"**Receipt format:** {RECEIPT_FORMAT}" in receipt
    assert "&#124;" in receipt
    assert "&lt;br&gt;" in receipt
    _validate_receipt_round_trip(receipt, state)

    with tempfile.TemporaryDirectory() as temp_dir:
        contract_path = Path(temp_dir) / "contract.json"
        contract_path.write_text(
            json.dumps(contract, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        digest = hashlib.sha256(contract_path.read_bytes()).hexdigest()
        _require_contract_digest(contract_path, digest)
        try:
            _require_contract_digest(contract_path, "0" * 64)
        except ValidationError:
            pass
        else:
            raise AssertionError("invalid contract handoff digest was accepted")

    tampered = json.loads(json.dumps(contract))
    tampered["contract_identity"]["source_units"][0][1] = "9" * 64
    try:
        _validate_contract_identity(tampered)
    except ValidationError:
        pass
    else:
        raise AssertionError("tampered structural contract identity was accepted")


def _parts_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-input", required=True)
    parser.add_argument("--contract-digest", required=True)
    parser.add_argument("--proofs-input", required=True)
    parser.add_argument("--gates-input", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--prior-checkpoint")
    parser.add_argument("--repair", action="append", default=[])
    parser.add_argument("--inherited-finding", action="append", default=[])
    parser.add_argument("--receipt-output", required=True)
    return parser.parse_args(argv)


def main() -> int:
    if len(sys.argv) <= 1:
        return _base.main()
    command = sys.argv[1]
    try:
        if command == "finalize-parts":
            args = _parts_args(sys.argv[2:])
            _require_contract_digest(args.contract_input, args.contract_digest)
            _emit_finalization(
                finalize_parts(
                    _base._read_json(args.contract_input),
                    _base._read_json(args.proofs_input),
                    _base._read_json(args.gates_input),
                    mode=args.mode,
                    prior_checkpoint=args.prior_checkpoint,
                    repairs=args.repair,
                    inherited_findings=args.inherited_finding,
                ),
                args.receipt_output,
            )
            return 0
        if command == "finalize":
            raise ValidationError(
                "direct finalize is disabled; use finalize-parts with the exact "
                "$spec-contract handoff and certifier-bound digest"
            )
        if command == "self-test":
            self_test()
            print("VERIFY-SPEC ARTIFACT SELF-TEST: PASS")
            return 0
        return _base.main()
    except (OSError, json.JSONDecodeError, ValidationError, AssertionError, RuntimeError) as exc:
        print(f"VERIFY-SPEC ARTIFACT ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
