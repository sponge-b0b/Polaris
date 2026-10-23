from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/workflow_routing_defects.py"
spec = importlib.util.spec_from_file_location("workflow_routing_defects", MODULE_PATH)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _issue(path: Path, number: int, units: list[dict[str, object]]) -> None:
    topology = {"schema": "polaris.spec-execution-topology/v1", "units": units}
    path.write_text(
        json.dumps(
            {
                "number": number,
                "title": f"Spec: {number}",
                "url": f"https://github.com/sponge-b0b/Polaris/issues/{number}",
                "state": "OPEN",
                "body": "<!-- spec-execution-topology:v1\n"
                + json.dumps(topology)
                + "\n-->",
                "blockedBy": {"nodes": []},
            }
        ),
        encoding="utf-8",
    )


def _marker(status: str = "open") -> dict[str, object]:
    return {
        "schema": mod.MARKER_SCHEMA,
        "defect_id": "ticket-404:OBL-005-history",
        "status": status,
        "classification": "cell-routing-defect",
        "source_ticket": 404,
        "parent_spec": 359,
        "affected_cells": ["OBL-005"],
        "required_local_provider_cells": ["OBL-003", "OBL-004"],
        "reason": "history cell requires projected-consequence and risk producers",
        "basis": [
            "https://github.com/sponge-b0b/Polaris/issues/404#issuecomment-6262488883"
        ],
    }


def _manifest(
    tmp_path: Path, units: list[dict[str, object]]
) -> tuple[Path, Path]:
    issue = tmp_path / "359.json"
    _issue(issue, 359, units)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": mod.FEASIBILITY_SCHEMA,
                "planning_source": "https://github.com/sponge-b0b/Polaris/issues/348",
                "spec_order": [359],
                "specs": [{"issue_json": "359.json", "unit_analysis": []}],
            }
        ),
        encoding="utf-8",
    )
    inventory = tmp_path / "routing.json"
    inventory.write_text(
        json.dumps(
            {
                "schema": mod.INVENTORY_SCHEMA,
                "repository": "sponge-b0b/Polaris",
                "specs_scanned": [359],
                "defects": [_marker()],
            }
        ),
        encoding="utf-8",
    )
    return inventory, manifest


def test_404_shape_fails_even_if_feasibility_unit_analysis_omits_local_provider_edges(
    tmp_path: Path,
) -> None:
    inventory, manifest = _manifest(
        tmp_path,
        [
            {"unit_id": "EU-001", "cells": ["OBL-005"], "depends_on": []},
            {
                "unit_id": "EU-002",
                "cells": ["OBL-003"],
                "depends_on": ["EU-001"],
            },
            {
                "unit_id": "EU-003",
                "cells": ["OBL-004"],
                "depends_on": ["EU-002"],
            },
        ],
    )
    try:
        mod.check_inventory(inventory, manifest)
    except mod.RoutingDefectError as exc:
        text = str(exc)
    else:
        raise AssertionError("expected routing-defect coverage failure")
    assert "OBL-005 in EU-001 requires provider cell OBL-003 in EU-002" in text
    assert "OBL-005 in EU-001 requires provider cell OBL-004 in EU-003" in text


def test_reconciled_topology_passes_when_provider_cells_are_self_or_upstream(
    tmp_path: Path,
) -> None:
    inventory, manifest = _manifest(
        tmp_path,
        [
            {"unit_id": "EU-001", "cells": ["OBL-003"], "depends_on": []},
            {
                "unit_id": "EU-002",
                "cells": ["OBL-004", "OBL-005"],
                "depends_on": ["EU-001"],
            },
        ],
    )
    output = mod.check_inventory(inventory, manifest)
    assert output.startswith("TO-SPECS ROUTING DEFECT COVERAGE: VALID")
    assert "Unprotected routing defect requirements: 0" in output


def test_open_marker_without_provider_cells_fails_closed(tmp_path: Path) -> None:
    inventory, manifest = _manifest(
        tmp_path,
        [{"unit_id": "EU-001", "cells": ["OBL-005"], "depends_on": []}],
    )
    data = json.loads(inventory.read_text(encoding="utf-8"))
    data["defects"][0]["required_local_provider_cells"] = []
    inventory.write_text(json.dumps(data), encoding="utf-8")
    try:
        mod.check_inventory(inventory, manifest)
    except mod.RoutingDefectError as exc:
        assert "no machine-resolvable local provider cells and remains blocking" in str(exc)
    else:
        raise AssertionError("expected unresolved marker failure")


def test_inventory_must_cover_exact_feasibility_spec_set(tmp_path: Path) -> None:
    inventory, manifest = _manifest(
        tmp_path,
        [
            {
                "unit_id": "EU-001",
                "cells": ["OBL-003", "OBL-004", "OBL-005"],
                "depends_on": [],
            }
        ],
    )
    data = json.loads(inventory.read_text(encoding="utf-8"))
    data["specs_scanned"] = [358, 359]
    inventory.write_text(json.dumps(data), encoding="utf-8")
    try:
        mod.check_inventory(inventory, manifest)
    except mod.RoutingDefectError as exc:
        assert "must scan every and only feasibility Spec" in str(exc)
    else:
        raise AssertionError("expected inventory coverage failure")


def test_collector_discovers_machine_marker_from_child_comment(
    tmp_path: Path, monkeypatch
) -> None:
    marker = _marker()
    body = "<!-- workflow-routing-defect:v1\n" + json.dumps(marker) + "\n-->"

    def fake_paged(endpoint: str):
        if endpoint.endswith("/359/sub_issues"):
            return [{"number": 404, "state": "open"}]
        if endpoint.endswith("/404/comments"):
            return [
                {
                    "id": 6262488883,
                    "html_url": marker["basis"][0],
                    "body": body,
                }
            ]
        raise AssertionError(endpoint)

    monkeypatch.setattr(mod, "_paged", fake_paged)
    output_path = tmp_path / "inventory.json"
    output = mod.collect_inventory("sponge-b0b/Polaris", [359], output_path)
    assert output.startswith("TO-SPECS ROUTING DEFECT INVENTORY: VALID")
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["specs_scanned"] == [359]
    assert data["defects"][0]["defect_id"] == marker["defect_id"]
    assert data["defects"][0]["marker_sha256"]
