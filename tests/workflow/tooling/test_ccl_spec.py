from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.ccl import CclValidationError
from scripts.ccl_spec import manifest_comment, render_section, validate_spec_body

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ccl"


def _transaction() -> dict:
    return json.loads(
        (FIXTURES / "demo-recording.json").read_text(encoding="utf-8")
    )


def _manifest() -> dict:
    return {
        "schema": "polaris.spec-ccl/v1",
        "obligations": [
            {
                "obligation_id": "OBL-001",
                "source_ref": "Decision #102",
                "ccl": [
                    "workflow-demo.recording@1#record.persistence",
                    "workflow-demo.recording@1#record.not-command",
                ],
            }
        ],
    }


def _body(manifest: dict, transaction: dict) -> str:
    return (
        manifest_comment(manifest, [transaction])
        + "\n## Problem Statement\n\nNeed durable workflow-record behavior.\n\n"
        + render_section(manifest, [transaction])
        + "\n## Implementation Decisions\n\nImplement OBL-001.\n"
    )


def test_valid_manifest_and_generated_section_are_accepted() -> None:
    transaction = _transaction()
    manifest = _manifest()

    validate_spec_body(_body(manifest, transaction), [transaction])


def test_unknown_taxonomy_cannot_be_added_as_spec_contract() -> None:
    transaction = _transaction()
    manifest = _manifest()
    manifest["obligations"][0]["ccl"].append(
        "workflow-demo.recording@1#record.reason-taxonomy"
    )

    with pytest.raises(CclValidationError, match="unknown CCL assertion"):
        render_section(manifest, [transaction])


def test_projection_drift_is_rejected() -> None:
    transaction = _transaction()
    manifest = _manifest()
    body = _body(manifest, transaction)
    body = body.replace("persistence is `durable`", "persistence is `derived`")

    with pytest.raises(CclValidationError, match="projection drift"):
        validate_spec_body(body, [transaction])


def test_manifest_requires_unique_stable_obligation_ids() -> None:
    transaction = _transaction()
    manifest = _manifest()
    duplicate = copy.deepcopy(manifest["obligations"][0])
    manifest["obligations"].append(duplicate)

    with pytest.raises(CclValidationError, match="duplicate"):
        render_section(manifest, [transaction])


def test_ccl_annotations_do_not_appear_in_spec_projection() -> None:
    transaction = _transaction()
    rendered = render_section(_manifest(), [transaction])

    assert "sample-only explanation" not in rendered
    assert "add no contract semantics" not in rendered


def test_manifest_is_machine_managed_provenance_comment() -> None:
    transaction = _transaction()
    rendered = manifest_comment(_manifest(), [transaction])

    assert rendered.startswith("<!-- spec-contract-ccl:v1\n")
    assert rendered.endswith("-->\n")
