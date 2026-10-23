from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/workflow_to_specs.py"
spec = importlib.util.spec_from_file_location("workflow_to_specs", MODULE_PATH)
assert spec is not None and spec.loader is not None
workflow_to_specs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = workflow_to_specs
spec.loader.exec_module(workflow_to_specs)


def _issue(
    path: Path,
    number: int,
    *,
    state: str,
    units: list[str] | None,
) -> None:
    if units is None:
        body = "legacy completed spec without topology"
    else:
        topology = {
            "schema": "polaris.spec-execution-topology/v1",
            "units": [
                {"unit_id": unit, "cells": ["OBL-001"], "depends_on": []}
                for unit in units
            ],
        }
        body = "<!-- spec-execution-topology:v1\n" + json.dumps(topology) + "\n-->"
    path.write_text(
        json.dumps(
            {
                "number": number,
                "title": f"Spec: {number}",
                "url": f"https://github.com/sponge-b0b/Polaris/issues/{number}",
                "state": state,
                "body": body,
                "blockedBy": {"nodes": []},
            }
        ),
        encoding="utf-8",
    )


def _analysis(unit: str, providers: list[int]) -> dict[str, object]:
    return {
        "unit_id": unit,
        "completion_basis": ["evidence.r3-current-basis@1#basis.complete"],
        "provider_requirements": [
            {
                "provider_spec": provider,
                "reason": "production provider required",
                "basis": [f"https://github.com/sponge-b0b/Polaris/issues/{provider}"],
            }
            for provider in providers
        ],
        "local_provider_requirements": [],
        **(
            {}
            if providers
            else {
                "local_completion_attestation": {
                    "result": True,
                    "reason": "locally completable",
                    "basis": ["https://github.com/sponge-b0b/Polaris/issues/348"],
                }
            }
        ),
    }


def _legacy_entry() -> dict[str, object]:
    return {
        "issue_json": "357.json",
        "legacy_completed": {
            "result": True,
            "reason": "completed before execution-topology manifests existed",
            "completion_basis": [
                "https://github.com/sponge-b0b/Polaris/issues/357",
                "https://github.com/sponge-b0b/Polaris/issues/357#issuecomment-verification",
            ],
        },
    }


def test_closed_legacy_spec_without_topology_can_serve_as_durable_provider(
    tmp_path: Path,
) -> None:
    _issue(tmp_path / "357.json", 357, state="CLOSED", units=None)
    _issue(tmp_path / "358.json", 358, state="OPEN", units=["EU-001"])
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": workflow_to_specs.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [357, 358],
                "specs": [
                    _legacy_entry(),
                    {
                        "issue_json": "358.json",
                        "unit_analysis": [_analysis("EU-001", [357])],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    output = workflow_to_specs.check_feasibility(manifest)
    assert "Legacy completed Specs: 1" in output
    assert "Unprotected pending provider requirements: 0" in output
    assert "Actionable frontier: #358" in output


def test_closed_legacy_spec_requires_explicit_completion_attestation(
    tmp_path: Path,
) -> None:
    _issue(tmp_path / "357.json", 357, state="CLOSED", units=None)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": workflow_to_specs.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [357],
                "specs": [{"issue_json": "357.json"}],
            }
        ),
        encoding="utf-8",
    )
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        assert "requires legacy_completed attestation" in str(exc)
    else:
        raise AssertionError("expected legacy-attestation failure")


def test_open_topologyless_spec_cannot_use_legacy_compatibility(tmp_path: Path) -> None:
    _issue(tmp_path / "358.json", 358, state="OPEN", units=None)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": workflow_to_specs.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [358],
                "specs": [
                    {
                        "issue_json": "358.json",
                        "legacy_completed": {
                            "result": True,
                            "reason": "not actually legacy",
                            "completion_basis": [
                                "https://github.com/sponge-b0b/Polaris/issues/358"
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        assert "open spec missing spec-execution-topology:v1" in str(exc)
    else:
        raise AssertionError("expected open-topology failure")


def test_closed_topology_bearing_spec_cannot_use_legacy_shortcut(tmp_path: Path) -> None:
    _issue(tmp_path / "357.json", 357, state="CLOSED", units=["EU-001"])
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": workflow_to_specs.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [357],
                "specs": [_legacy_entry()],
            }
        ),
        encoding="utf-8",
    )
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        assert "legacy_completed is allowed only for a CLOSED spec that lacks" in str(exc)
    else:
        raise AssertionError("expected topology-bearing bypass failure")
