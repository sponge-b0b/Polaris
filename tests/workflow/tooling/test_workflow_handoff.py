from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts/workflow_handoff.py"
spec = importlib.util.spec_from_file_location("workflow_handoff", MODULE_PATH)
assert spec is not None and spec.loader is not None
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


def manifest() -> dict:
    return {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "durability": {
            "verified": True,
            "sources": ["https://github.com/sponge-b0b/Polaris/issues/348"],
        },
        "handoffs": [
            {
                "destination": "$to-specs",
                "artifact": {
                    "title": "Wayfinder: R3 first coherent human decision slice",
                    "url": "https://github.com/sponge-b0b/Polaris/issues/348",
                },
            }
        ],
    }


def test_render_artifact_line_is_exact_canonical_format() -> None:
    assert handoff.render_artifact_line(
        "$to-tickets",
        "Spec: Example",
        "https://github.com/sponge-b0b/Polaris/issues/358",
    ) == "$to-tickets - Spec: Example (https://github.com/sponge-b0b/Polaris/issues/358)"


def test_generate_binds_exact_handoff_and_durability() -> None:
    rendered = handoff.render_manifest(manifest())
    lines = rendered.splitlines()
    assert lines[0] == "WORKFLOW HANDOFF: READY"
    assert lines[1] == (
        "$to-specs - Wayfinder: R3 first coherent human decision slice "
        "(https://github.com/sponge-b0b/Polaris/issues/348)"
    )
    assert lines[2] == "Fresh-session durability: VERIFIED"
    assert lines[3] == "Durability sources: 1"
    assert lines[4].startswith("Handoff manifest SHA-256: ")


@pytest.mark.parametrize(
    ("outcome", "ready_line"),
    [
        ("success", "✅ WORKFLOW HANDOFF: READY"),
        ("warning", "⚠️ WORKFLOW HANDOFF: READY"),
    ],
)
def test_outcome_renders_canonical_status_emoji(outcome: str, ready_line: str) -> None:
    candidate = manifest()
    candidate["outcome"] = outcome
    lines = handoff.render_manifest(candidate).splitlines()
    assert lines[0] == ready_line
    assert lines[1] == (
        "$to-specs - Wayfinder: R3 first coherent human decision slice "
        "(https://github.com/sponge-b0b/Polaris/issues/348)"
    )
    assert lines[2] == "Fresh-session durability: VERIFIED"
    assert lines[3] == "Durability sources: 1"
    assert lines[4].startswith("Handoff manifest SHA-256: ")


def test_multiple_artifacts_preserve_manifest_order() -> None:
    value = manifest()
    value["handoffs"] = [
        {
            "destination": "$to-tickets",
            "artifact": {
                "title": "Spec: A",
                "url": "https://github.com/sponge-b0b/Polaris/issues/358",
            },
        },
        {
            "destination": "$to-tickets",
            "artifact": {
                "title": "Spec: B",
                "url": "https://github.com/sponge-b0b/Polaris/issues/359",
            },
        },
    ]
    lines = handoff.render_manifest(value).splitlines()
    assert lines[1:3] == [
        "$to-tickets - Spec: A (https://github.com/sponge-b0b/Polaris/issues/358)",
        "$to-tickets - Spec: B (https://github.com/sponge-b0b/Polaris/issues/359)",
    ]


def test_subcommand_destination_is_supported() -> None:
    assert handoff.render_artifact_line(
        "$contract-ledger owner-decision",
        "Decision source",
        "https://github.com/sponge-b0b/Polaris/issues/401",
    ) == (
        "$contract-ledger owner-decision - Decision source "
        "(https://github.com/sponge-b0b/Polaris/issues/401)"
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("boundary",), "internal-composition"),
        (("outcome",), "failure"),
        (("outcome",), 1),
        (("durability", "verified"), False),
        (("durability", "sources"), []),
        (("handoffs", 0, "destination"), "to-specs"),
        (("handoffs", 0, "artifact", "title"), "bad\ntitle"),
        (("handoffs", 0, "artifact", "url"), "https://example.com/issues/1"),
    ],
)
def test_invalid_manifest_fails_closed(path: tuple, value: object) -> None:
    candidate = copy.deepcopy(manifest())
    cursor = candidate
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value
    with pytest.raises(handoff.HandoffError):
        handoff.render_manifest(candidate)


def test_duplicate_handoff_is_rejected() -> None:
    candidate = manifest()
    candidate["handoffs"].append(copy.deepcopy(candidate["handoffs"][0]))
    with pytest.raises(handoff.HandoffError, match="duplicate handoff"):
        handoff.render_manifest(candidate)


def test_validate_output_is_byte_exact_after_trim() -> None:
    candidate = manifest()
    rendered = handoff.render_manifest(candidate)
    assert handoff.validate_output(candidate, rendered + "\n") == "WORKFLOW HANDOFF: VALID"
    with pytest.raises(handoff.HandoffError, match="does not match"):
        handoff.validate_output(candidate, rendered.replace("$to-specs", "$to-tickets", 1))
