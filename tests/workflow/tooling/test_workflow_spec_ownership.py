from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "scripts/workflow_spec_ownership.py"
spec = importlib.util.spec_from_file_location("workflow_spec_ownership", MODULE)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _body(
    obligations: dict[str, list[str]],
    *,
    implementation: dict[str, str] | None = None,
    testing: dict[str, str] | None = None,
    units: list[dict[str, object]],
) -> str:
    ccl = {
        "schema": "polaris.spec-ccl/v1",
        "obligations": [
            {
                "obligation_id": cell,
                "source_ref": "https://github.com/sponge-b0b/Polaris/issues/348",
                "ccl": refs,
            }
            for cell, refs in obligations.items()
        ],
    }
    topology = {"schema": "polaris.spec-execution-topology/v1", "units": units}
    imp = "None." if not implementation else "\n".join(
        f"- `{cell}` — {text}" for cell, text in implementation.items()
    )
    tests = "None." if not testing else "\n".join(
        f"- `{cell}` — {text}" for cell, text in testing.items()
    )
    return (
        "<!-- spec-contract-ccl:v1\n"
        + json.dumps(ccl)
        + "\n-->\n<!-- spec-execution-topology:v1\n"
        + json.dumps(topology)
        + "\n-->\n\n## Implementation Decisions\n"
        + imp
        + "\n\n## Testing Decisions\n"
        + tests
        + "\n\n## Out of Scope\nNone.\n"
    )


def _issue(path: Path, number: int, body: str, blocked_by: list[int]) -> None:
    path.write_text(
        json.dumps(
            {
                "number": number,
                "title": f"Spec: {number}",
                "url": f"https://github.com/sponge-b0b/Polaris/issues/{number}",
                "state": "OPEN",
                "body": body,
                "blockedBy": {"nodes": [{"number": item} for item in blocked_by]},
            }
        ),
        encoding="utf-8",
    )


def _unit(unit: str, providers: list[int]) -> dict[str, object]:
    value: dict[str, object] = {
        "unit_id": unit,
        "completion_basis": ["https://github.com/sponge-b0b/Polaris/issues/348"],
        "provider_requirements": [
            {
                "provider_spec": provider,
                "reason": "provider required",
                "basis": [f"https://github.com/sponge-b0b/Polaris/issues/{provider}"],
            }
            for provider in providers
        ],
        "local_provider_requirements": [],
    }
    if not providers:
        value["local_completion_attestation"] = {
            "result": True,
            "reason": "locally completable",
            "basis": ["https://github.com/sponge-b0b/Polaris/issues/348"],
        }
    return value


def _owned(cell: str) -> dict[str, object]:
    return {
        "cell": cell,
        "disposition": "owned",
        "role": "local material outcome",
        "reason": "local owner",
        "basis": ["https://github.com/sponge-b0b/Polaris/issues/348"],
    }


def _consumed(cell: str, provider: int, provider_cell: str) -> dict[str, object]:
    return {
        "cell": cell,
        "disposition": "consumed-boundary",
        "provider_spec": provider,
        "provider_cells": [provider_cell],
        "reason": "sibling provider owns production capability",
        "basis": [f"https://github.com/sponge-b0b/Polaris/issues/{provider}"],
    }


def _planning(cell: str, supports: list[str]) -> dict[str, object]:
    return {
        "cell": cell,
        "supports": supports,
        "reason": "local implementation/proof responsibility",
        "basis": ["https://github.com/sponge-b0b/Polaris/issues/348"],
    }


def _manifest(tmp_path: Path, specs: list[dict[str, object]]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema": mod.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [item["number"] for item in specs],
                "specs": [item["entry"] for item in specs],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_409_shape_fails_when_atomic_consumer_owner_is_downstream(
    tmp_path: Path,
) -> None:
    shared = [
        "evidence.r3-current-basis@2#basis.complete",
        "evidence.r3-current-basis@2#basis.stale-vocabulary",
        "evidence.r3-current-basis@2#basis.temporal-meaning",
        "evidence.r3-current-basis@2#basis.atomic-commit",
    ]
    _issue(
        tmp_path / "359.json",
        359,
        _body(
            {"OBL-008": shared},
            implementation={"IMP-003": "Atomically validate with dependent write."},
            testing={"TEST-004": "Prove the dependent atomic write."},
            units=[
                {
                    "unit_id": "EU-006",
                    "cells": ["OBL-008", "IMP-003", "TEST-004"],
                    "depends_on": [],
                }
            ],
        ),
        [],
    )
    _issue(
        tmp_path / "358.json",
        358,
        _body(
            {"OBL-009": ["investment@2#transaction.revalidation", *shared]},
            units=[{"unit_id": "EU-002", "cells": ["OBL-009"], "depends_on": []}],
        ),
        [359],
    )
    manifest = _manifest(
        tmp_path,
        [
            {
                "number": 359,
                "entry": {
                    "issue_json": "359.json",
                    "unit_analysis": [_unit("EU-006", [358])],
                    "ownership_analysis": {
                        "material": [_consumed("OBL-008", 358, "OBL-009")],
                        "planning": [
                            _planning("IMP-003", ["OBL-008"]),
                            _planning("TEST-004", ["OBL-008"]),
                        ],
                    },
                },
            },
            {
                "number": 358,
                "entry": {
                    "issue_json": "358.json",
                    "unit_analysis": [_unit("EU-002", [])],
                    "ownership_analysis": {
                        "material": [_owned("OBL-009")],
                        "planning": [],
                    },
                },
            },
        ],
    )
    try:
        mod.validate_manifest(manifest)
    except mod.OwnershipError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected ownership failure")
    assert "open provider #358 is downstream/unrelated" in text
    assert "IMP-003: planning cell has no locally owned material outcome" in text
    assert "TEST-004: planning cell has no locally owned material outcome" in text
    assert "EU-006: execution unit has no locally owned material OBL" in text


def test_upstream_provider_with_local_material_anchor_passes(tmp_path: Path) -> None:
    shared = ["shared@1#fact"]
    _issue(
        tmp_path / "359.json",
        359,
        _body(
            {"OBL-001": shared},
            units=[{"unit_id": "EU-001", "cells": ["OBL-001"], "depends_on": []}],
        ),
        [],
    )
    _issue(
        tmp_path / "358.json",
        358,
        _body(
            {"OBL-001": ["consumer@1#outcome"], "OBL-002": shared},
            implementation={
                "IMP-001": "Consume provider while producing local outcome."
            },
            units=[
                {
                    "unit_id": "EU-001",
                    "cells": ["OBL-001", "OBL-002", "IMP-001"],
                    "depends_on": [],
                }
            ],
        ),
        [359],
    )
    manifest = _manifest(
        tmp_path,
        [
            {
                "number": 359,
                "entry": {
                    "issue_json": "359.json",
                    "unit_analysis": [_unit("EU-001", [])],
                    "ownership_analysis": {
                        "material": [_owned("OBL-001")],
                        "planning": [],
                    },
                },
            },
            {
                "number": 358,
                "entry": {
                    "issue_json": "358.json",
                    "unit_analysis": [_unit("EU-001", [359])],
                    "ownership_analysis": {
                        "material": [
                            _owned("OBL-001"),
                            _consumed("OBL-002", 359, "OBL-001"),
                        ],
                        "planning": [_planning("IMP-001", ["OBL-001", "OBL-002"])],
                    },
                },
            },
        ],
    )
    output = mod.check_ownership(manifest)
    assert output.startswith("TO-SPECS CROSS-SPEC OWNERSHIP: VALID")
    assert "Unprotected consumed-boundary requirements: 0" in output
    assert "Execution units without local material ownership: 0" in output
