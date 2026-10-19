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
    title: str,
    *,
    blocked_by: list[int],
    units: list[str],
    state: str = "OPEN",
    depends_on: dict[str, list[str]] | None = None,
) -> None:
    depends_on = depends_on or {}
    topology = {
        "schema": "polaris.spec-execution-topology/v1",
        "units": [
            {
                "unit_id": unit,
                "cells": [f"OBL-{index:03d}"],
                "depends_on": depends_on.get(unit, []),
            }
            for index, unit in enumerate(units, 1)
        ],
    }
    body = "<!-- spec-execution-topology:v1\n" + json.dumps(topology) + "\n-->"
    path.write_text(
        json.dumps(
            {
                "number": number,
                "title": title,
                "url": f"https://github.com/sponge-b0b/Polaris/issues/{number}",
                "state": state,
                "body": body,
                "blockedBy": {"nodes": [{"number": value} for value in blocked_by]},
            }
        ),
        encoding="utf-8",
    )


def _analysis(
    unit: str,
    providers: list[int],
    local_providers: list[str] | None = None,
) -> dict[str, object]:
    local_providers = local_providers or []
    value: dict[str, object] = {
        "unit_id": unit,
        "completion_basis": ["evidence.r3-current-basis@1#basis.complete"],
        "provider_requirements": [
            {
                "provider_spec": provider,
                "reason": "authoritative production owner required before consumer proof",
                "basis": [f"https://github.com/sponge-b0b/Polaris/issues/{provider}"],
            }
            for provider in providers
        ],
        "local_provider_requirements": [
            {
                "provider_unit": provider_unit,
                "reason": "same-Spec producer required before consumer proof",
                "basis": [f"execution-topology:{provider_unit}"],
            }
            for provider_unit in local_providers
        ],
    }
    if not providers and not local_providers:
        value["local_completion_attestation"] = {
            "result": True,
            "reason": "unit is locally completable",
            "basis": ["https://github.com/sponge-b0b/Polaris/issues/348"],
        }
    return value


def _manifest(tmp_path: Path, *, blocked_358: list[int]) -> Path:
    _issue(
        tmp_path / "358.json",
        358,
        "Spec: Intelligence",
        blocked_by=blocked_358,
        units=["EU-001", "EU-002"],
    )
    _issue(tmp_path / "359.json", 359, "Spec: Portfolio", blocked_by=[], units=["EU-001"])
    _issue(tmp_path / "360.json", 360, "Spec: Authority", blocked_by=[], units=["EU-001"])
    _issue(tmp_path / "361.json", 361, "Spec: Learning", blocked_by=[], units=["EU-001"])
    data = {
        "schema": workflow_to_specs.SCHEMA,
        "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
        "spec_order": [358, 359, 360, 361],
        "specs": [
            {
                "issue_json": "358.json",
                "unit_analysis": [
                    _analysis("EU-001", []),
                    _analysis("EU-002", [359, 360, 361]),
                ],
            },
            {"issue_json": "359.json", "unit_analysis": [_analysis("EU-001", [])]},
            {"issue_json": "360.json", "unit_analysis": [_analysis("EU-001", [])]},
            {"issue_json": "361.json", "unit_analysis": [_analysis("EU-001", [])]},
        ],
    }
    path = tmp_path / "feasibility.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_f399_shape_fails_when_open_providers_are_not_native_prerequisites(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path, blocked_358=[])
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected feasibility failure")
    assert "open provider #359 is required for completion but no native prerequisite path" in text
    assert "open provider #360 is required for completion but no native prerequisite path" in text
    assert "open provider #361 is required for completion but no native prerequisite path" in text


def test_f399_shape_passes_when_native_prerequisites_protect_consumer(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path, blocked_358=[359, 360, 361])
    output = workflow_to_specs.check_feasibility(manifest)
    assert output.startswith("SPEC EXECUTION FEASIBILITY: VALID")
    assert "Unprotected pending provider requirements: 0" in output
    assert "Unprotected downstream local provider requirements: 0" in output
    assert "Actionable frontier: #359, #360, #361" in output


def test_every_actual_execution_unit_requires_explicit_analysis(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, blocked_358=[359, 360, 361])
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["specs"][0]["unit_analysis"] = [_analysis("EU-001", [])]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        assert "must exactly cover current topology" in str(exc)
    else:
        raise AssertionError("expected missing-unit failure")


def test_empty_provider_lists_require_positive_local_attestation(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, blocked_358=[359, 360, 361])
    data = json.loads(manifest.read_text(encoding="utf-8"))
    del data["specs"][1]["unit_analysis"][0]["local_completion_attestation"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        assert "require explicit local_completion_attestation" in str(exc)
    else:
        raise AssertionError("expected local-attestation failure")


def test_local_provider_requirements_list_is_mandatory(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, blocked_358=[359, 360, 361])
    data = json.loads(manifest.read_text(encoding="utf-8"))
    del data["specs"][1]["unit_analysis"][0]["local_provider_requirements"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        assert "local_provider_requirements list required" in str(exc)
    else:
        raise AssertionError("expected local-provider-list failure")


def test_local_downstream_provider_requirement_is_rejected(tmp_path: Path) -> None:
    _issue(
        tmp_path / "359.json",
        359,
        "Spec: Portfolio",
        blocked_by=[],
        units=["EU-001", "EU-002", "EU-003"],
        depends_on={"EU-002": ["EU-001"], "EU-003": ["EU-002"]},
    )
    manifest = tmp_path / "feasibility.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": workflow_to_specs.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [359],
                "specs": [
                    {
                        "issue_json": "359.json",
                        "unit_analysis": [
                            _analysis("EU-001", [], ["EU-002", "EU-003"]),
                            _analysis("EU-002", []),
                            _analysis("EU-003", []),
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected downstream-local-provider failure")
    assert (
        "spec #359 EU-001: local provider EU-002 is required for completion but is not "
        "a transitive prerequisite of the consumer"
    ) in text
    assert (
        "spec #359 EU-001: local provider EU-003 is required for completion but is not "
        "a transitive prerequisite of the consumer"
    ) in text


def test_local_transitive_upstream_provider_requirement_is_valid(tmp_path: Path) -> None:
    _issue(
        tmp_path / "359.json",
        359,
        "Spec: Portfolio",
        blocked_by=[],
        units=["EU-001", "EU-002", "EU-003"],
        depends_on={"EU-002": ["EU-001"], "EU-003": ["EU-002"]},
    )
    manifest = tmp_path / "feasibility.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": workflow_to_specs.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [359],
                "specs": [
                    {
                        "issue_json": "359.json",
                        "unit_analysis": [
                            _analysis("EU-001", []),
                            _analysis("EU-002", [], ["EU-001"]),
                            _analysis("EU-003", [], ["EU-001"]),
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = workflow_to_specs.check_feasibility(manifest)
    assert "Unprotected downstream local provider requirements: 0" in output
    assert "Actionable frontier: #359" in output


def test_local_provider_must_name_current_execution_unit(tmp_path: Path) -> None:
    _issue(
        tmp_path / "359.json",
        359,
        "Spec: Portfolio",
        blocked_by=[],
        units=["EU-001"],
    )
    manifest = tmp_path / "feasibility.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": workflow_to_specs.SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [359],
                "specs": [
                    {
                        "issue_json": "359.json",
                        "unit_analysis": [
                            _analysis("EU-001", [], ["EU-999"]),
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        workflow_to_specs.validate_manifest(manifest)
    except workflow_to_specs.ToSpecsError as exc:
        assert "local provider EU-999 is not a current execution unit" in str(exc)
    else:
        raise AssertionError("expected unknown-local-provider failure")


def test_handoff_manifest_uses_exact_snapshot_titles_urls_and_frontier_order(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path, blocked_358=[359, 360, 361])
    output_path = tmp_path / "handoff.json"
    assert (
        workflow_to_specs.build_handoff_manifest(manifest, output_path)
        == "TO-SPECS HANDOFF MANIFEST: VALID"
    )
    handoff = json.loads(output_path.read_text(encoding="utf-8"))
    assert [item["artifact"]["title"] for item in handoff["handoffs"]] == [
        "Spec: Portfolio",
        "Spec: Authority",
        "Spec: Learning",
    ]
    assert [item["artifact"]["url"] for item in handoff["handoffs"]] == [
        "https://github.com/sponge-b0b/Polaris/issues/359",
        "https://github.com/sponge-b0b/Polaris/issues/360",
        "https://github.com/sponge-b0b/Polaris/issues/361",
    ]
    assert all(item["destination"] == "$to-tickets" for item in handoff["handoffs"])
