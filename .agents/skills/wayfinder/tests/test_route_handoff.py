from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "route_handoff.py"
SPEC = importlib.util.spec_from_file_location("route_handoff", SCRIPT)
assert SPEC and SPEC.loader
route_handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route_handoff)

TITLE = "Wayfinder: R3 first coherent human decision slice"
URL = "https://github.com/sponge-b0b/Polaris/issues/348"
SHA = "1f76b9f14669f1ef4c18a9b6ee39e452ea9a4b46"


def write_map(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "map.json"
    path.write_text(json.dumps({"title": TITLE, "url": URL, "body": body}), encoding="utf-8")
    return path


def write_attention(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "attention.txt"
    path.write_text(text, encoding="utf-8")
    return path


def clear_attention(tmp_path: Path) -> Path:
    return write_attention(
        tmp_path,
        "ATTENTION: CLEAR\n"
        "Checkpoint: $wayfinder route clarity\n"
        "Material concerns: 0\n",
    )


def nonblocking_findings(tmp_path: Path) -> Path:
    return write_attention(
        tmp_path,
        "ATTENTION: FINDINGS\n"
        "Checkpoint: $wayfinder route clarity\n\n"
        "1. Continuation reconciliation remains.\n"
        "   Observation: A real merge conflict exists.\n"
        "   Why it matters: The Spec branch cannot yet inherit canonical authority.\n"
        "   Authority: Resolved by Wayfinder continuation reconciliation.\n"
        "   Recommendation/routing: Hand off to $to-specs.\n"
        "   Blocking basis: none\n",
    )


def required_body(owner: str = "$to-specs", markers: int = 1) -> str:
    block = f"""<!-- continuation-reconciliation:v1 -->
## Continuation Reconciliation

**Status:** required
**Canonical authority:** {SHA}
**Continuation branch:** spec-358
**Conflict paths:** wiki/log.md
**Reconciliation owner:** {owner}
"""
    return "## Route Clarity\nRoute clear.\n\n" + (block * markers)


def test_specification_handoff_exact_without_reconciliation(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, "## Route Clarity\nRoute clear.\n")
    attention = clear_attention(tmp_path)
    output = route_handoff.specification_handoff(map_json, attention)
    lines = output.splitlines()
    assert lines[0] == "WAYFINDER HANDOFF: SPECIFICATION"
    assert lines[1] == f"$to-specs - {TITLE} ({URL})"
    assert lines[2].startswith("Route Clarity Attention SHA-256: ")


def test_required_reconciliation_emits_exact_coordinates(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, required_body())
    output = route_handoff.specification_handoff(map_json, nonblocking_findings(tmp_path))
    assert f"$to-specs - {TITLE} ({URL})" in output
    assert f"Canonical authority: {SHA}" in output
    assert "Continuation branch: spec-358" in output
    assert "Conflict paths: wiki/log.md" in output


def test_malformed_attention_header_is_rejected(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, required_body())
    attention = write_attention(
        tmp_path,
        "ATTENTION: FINDINGS — $wayfinder route clarity\n"
        "1. Something.\n",
    )
    with pytest.raises(route_handoff.HandoffError, match="invalid result header"):
        route_handoff.specification_handoff(map_json, attention)


def test_wrong_attention_checkpoint_is_rejected(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, required_body())
    attention = write_attention(
        tmp_path,
        "ATTENTION: CLEAR\nCheckpoint: $wayfinder other\nMaterial concerns: 0\n",
    )
    with pytest.raises(route_handoff.HandoffError, match="exact three-line"):
        route_handoff.specification_handoff(map_json, attention)


def test_blocking_attention_finding_is_rejected(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, required_body())
    attention = write_attention(
        tmp_path,
        "ATTENTION: FINDINGS\n"
        "Checkpoint: $wayfinder route clarity\n\n"
        "1. Design remains unresolved.\n"
        "   Observation: Semantics are ambiguous.\n"
        "   Why it matters: Two implementations differ materially.\n"
        "   Authority: unresolved\n"
        "   Recommendation/routing: Route to decision owner.\n"
        "   Blocking basis: route clarity requires zero unresolved material semantics\n",
    )
    with pytest.raises(route_handoff.HandoffError, match="blocking finding"):
        route_handoff.specification_handoff(map_json, attention)


def test_findings_require_complete_formal_fields(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, required_body())
    attention = write_attention(
        tmp_path,
        "ATTENTION: FINDINGS\n"
        "Checkpoint: $wayfinder route clarity\n\n"
        "1. Incomplete.\n"
        "   Observation: Something.\n"
        "   Blocking basis: none\n",
    )
    with pytest.raises(route_handoff.HandoffError, match="Why it matters"):
        route_handoff.specification_handoff(map_json, attention)


def test_required_reconciliation_requires_to_specs_owner(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, required_body(owner="$wayfinder"))
    with pytest.raises(route_handoff.HandoffError, match="must name \\$to-specs"):
        route_handoff.specification_handoff(map_json, clear_attention(tmp_path))


def test_multiple_continuation_blocks_are_rejected(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, required_body(markers=2))
    with pytest.raises(route_handoff.HandoffError, match="multiple"):
        route_handoff.specification_handoff(map_json, clear_attention(tmp_path))


def test_route_clarity_section_is_required(tmp_path: Path) -> None:
    map_json = write_map(tmp_path, "## Destination\nSomething\n")
    with pytest.raises(route_handoff.HandoffError, match="Route Clarity"):
        route_handoff.specification_handoff(map_json, clear_attention(tmp_path))
