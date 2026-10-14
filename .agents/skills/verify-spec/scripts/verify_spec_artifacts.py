#!/usr/bin/env python3
"""Stable front-end for ``$verify-spec`` artifact bookkeeping.

The implementation remains in ``verify_spec_artifacts_impl.py``. This front-end
owns the durable Spec-contract identity boundary so verification cannot regress
to model-authored source-unit mappings as hash input.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

_IMPL_PATH = Path(__file__).with_name("verify_spec_artifacts_impl.py")
_IMPL_SPEC = importlib.util.spec_from_file_location(
    "_polaris_verify_spec_artifacts_impl",
    _IMPL_PATH,
)
if _IMPL_SPEC is None or _IMPL_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("verify-spec artifact implementation could not be loaded")
_impl = importlib.util.module_from_spec(_IMPL_SPEC)
_IMPL_SPEC.loader.exec_module(_impl)

_legacy_validate_contract_identity = _impl._validate_contract_identity
_legacy_contract_coherence = _impl.contract_coherence
_legacy_self_test = _impl.self_test

_TCM_SPEC_COVERAGE_HEADER = "### Spec Obligation Coverage"
_TCM_CELL_RE = re.compile(
    r"^(?P<cell>(?:US|ID|TD|OOS|NORM)-\d+(?:\.[A-Za-z0-9_-]+)?)\s+→\s+"
)


def _contract_hash_module() -> Any:
    path = (
        Path(__file__).resolve().parents[2]
        / "spec-contract"
        / "scripts"
        / "extract_source_units.py"
    )
    module_spec = importlib.util.spec_from_file_location(
        "_polaris_spec_contract_source_extractor",
        path,
    )
    _impl._require(
        module_spec is not None and module_spec.loader is not None,
        "spec-contract source extractor could not be loaded",
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _stable_contract_hash(body_hash: str) -> str:
    module = _contract_hash_module()
    try:
        value = module.spec_contract_hash_from_body_hash(body_hash)
    except (AttributeError, ValueError) as exc:
        raise _impl.ValidationError(
            f"spec-contract hash helper failed: {exc}"
        ) from exc
    return _impl._digest_text(value, "mechanical spec contract hash")


def _old_structural_hash(contract: dict[str, Any]) -> str:
    body_hash = _impl._digest_text(contract.get("spec_body_hash"), "spec_body_hash")
    identity = contract.get("contract_identity")
    _impl._require(isinstance(identity, dict), "contract_identity must be an object")
    source_rows = identity.get("source_units")
    manifest_rows = identity.get("manifest")
    _impl._require(isinstance(source_rows, list), "contract identity source units missing")
    _impl._require(isinstance(manifest_rows, list), "contract identity manifest missing")
    payload = (
        "SPEC-CONTRACT\n"
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
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_contract_identity(contract: dict[str, Any]) -> None:
    """Validate semantic evidence, then validate only mechanical durable identity."""

    structural = copy.deepcopy(contract)
    structural["spec_contract_hash"] = _old_structural_hash(structural)
    _legacy_validate_contract_identity(structural)

    body_hash = _impl._digest_text(contract.get("spec_body_hash"), "spec_body_hash")
    expected_hash = _impl._digest_text(
        contract.get("spec_contract_hash"),
        "spec_contract_hash",
    )
    actual_hash = _stable_contract_hash(body_hash)
    _impl._require(
        actual_hash == expected_hash,
        "SPEC_CONTRACT_HASH does not match the mechanical Spec-body identity",
    )


def _tcm_spec_cells(lines: list[str]) -> list[str]:
    _impl._require(
        _TCM_SPEC_COVERAGE_HEADER in lines,
        "Ticket Coverage Manifest missing Spec Obligation Coverage",
    )
    start = lines.index(_TCM_SPEC_COVERAGE_HEADER) + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("### "):
            end = index
            break

    cells: list[str] = []
    for line in lines[start:end]:
        match = _TCM_CELL_RE.match(line)
        if match is None:
            continue
        cell = match.group("cell")
        _impl._require(cell not in cells, f"duplicate TCM Spec cell: {cell}")
        cells.append(cell)
    _impl._require(bool(cells), "Ticket Coverage Manifest has no Spec-cell rows")
    return cells


def contract_coherence(summary: Any, contract: Any) -> dict[str, str]:
    result = _legacy_contract_coherence(summary, contract)

    tcm = summary.get("ticket_coverage_manifest")
    _impl._require(isinstance(tcm, dict), "current Ticket Coverage Manifest is missing")
    tcm_body = _impl._text(tcm.get("body"), "Ticket Coverage Manifest body")
    tcm_cells = _tcm_spec_cells(tcm_body.splitlines())
    _, contract_cells = _impl._manifest(contract.get("manifest"))

    _impl._require(
        len(tcm_cells) == len(contract_cells) and set(tcm_cells) == set(contract_cells),
        "TCM Spec-cell set does not match the fresh Spec contract manifest",
    )
    return result


def self_test() -> None:
    # Retain the complete legacy bookkeeping self-test under its historical
    # structural-hash implementation, then test the new durable identity seam.
    current_validator = _impl._validate_contract_identity
    current_coherence = _impl.contract_coherence
    try:
        _impl._validate_contract_identity = _legacy_validate_contract_identity
        _impl.contract_coherence = _legacy_contract_coherence
        _legacy_self_test()
    finally:
        _impl._validate_contract_identity = current_validator
        _impl.contract_coherence = current_coherence

    body_hash = "b" * 64
    stable_hash = _stable_contract_hash(body_hash)
    source_rows = [
        ["SU-0001", "1" * 64, "normative-new", ["US-1"]],
        ["SU-0002", "2" * 64, "normative-represented", ["US-1"]],
    ]
    manifest_rows = [["US-1", ["SU-0001", "SU-0002"]]]
    contract = {
        "spec_issue": 1,
        "head": "a" * 40,
        "baseline": "c" * 40,
        "branch": "spec-1",
        "spec_body_hash": body_hash,
        "spec_contract_hash": stable_hash,
        "default_branch": "main",
        "default_head": "d" * 40,
        "source_counts": {
            "user_stories": 1,
            "implementation_decisions": 0,
            "testing_decisions": 0,
            "out_of_scope": 0,
            "other_normative": 0,
        },
        "manifest": [
            {"cell": "US-1", "source": "User Stories 1", "requirement": "one"}
        ],
        "contract_identity": {
            "source_units": source_rows,
            "manifest": manifest_rows,
        },
    }
    _validate_contract_identity(contract)

    # Different represented-summary mapping evidence over the exact same Spec
    # body must not perturb the durable contract hash.
    alternate = copy.deepcopy(contract)
    alternate["contract_identity"]["source_units"] = [
        ["SU-0001", "1" * 64, "normative-new", ["US-1"]],
        ["SU-0002", "2" * 64, "non-normative", None],
    ]
    alternate["contract_identity"]["manifest"] = [["US-1", ["SU-0001"]]]
    _validate_contract_identity(alternate)
    assert alternate["spec_contract_hash"] == contract["spec_contract_hash"]

    summary = {
        "ticket_coverage_manifest_count": 1,
        "ticket_coverage_manifest": {
            "id": 9,
            "body": (
                "## Ticket Coverage Manifest\n"
                f"Spec Body Hash: {body_hash}\n"
                f"Spec Contract Hash: {stable_hash}\n"
                "\n### Spec Obligation Coverage\n\n"
                "US-1 → #1\n"
            ),
        },
    }
    coherent = contract_coherence(summary, contract)
    assert coherent["status"] == "PASS"

    mismatched = copy.deepcopy(summary)
    mismatched["ticket_coverage_manifest"]["body"] = (
        mismatched["ticket_coverage_manifest"]["body"].replace("US-1 → #1", "US-2 → #1")
    )
    try:
        contract_coherence(mismatched, contract)
    except _impl.ValidationError:
        pass
    else:  # pragma: no cover
        raise AssertionError("TCM Spec-cell mismatch was accepted")


_impl._validate_contract_identity = _validate_contract_identity
_impl.contract_coherence = contract_coherence
_impl.self_test = self_test

# Re-export the implementation API for callers that import this script.
for _name, _value in vars(_impl).items():
    if _name.startswith("__"):
        continue
    globals().setdefault(_name, _value)
globals()["_validate_contract_identity"] = _validate_contract_identity
globals()["contract_coherence"] = contract_coherence
globals()["self_test"] = self_test


if __name__ == "__main__":
    raise SystemExit(_impl.main())
