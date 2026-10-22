from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VERIFY = (ROOT / ".agents/skills/verify-spec/SKILL.md").read_text(encoding="utf-8")
DEDUP = (ROOT / ".agents/skills/deduplicate-code/SKILL.md").read_text(encoding="utf-8")
CAPABILITIES_PATH = ROOT / ".agents/skills/workflow-capabilities.json"
HANDOFF_MODULE_PATH = ROOT / "scripts/workflow_handoff.py"
HANDOFF_FINALIZER = ".agents/skills/verify-spec/scripts/verify_spec_handoff.py"

spec = importlib.util.spec_from_file_location("workflow_handoff", HANDOFF_MODULE_PATH)
assert spec is not None and spec.loader is not None
workflow_handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow_handoff)


def test_verify_spec_uses_machine_candidate_attribution() -> None:
    helper = ".agents/skills/verify-spec/scripts/verify_spec_attribution.py"
    for phrase in (
        helper,
        "VERIFY-SPEC ATTRIBUTION: VALID",
        "candidate_attributable_paths",
        "inherited_default_equivalent_paths",
        "The fixed Spec baseline is immutable lineage/contract history",
        "unrelated failure",
    ):
        assert phrase in VERIFY

    for phrase in (
        helper,
        "Spec-differential uses the verify-spec attribution manifest",
        "upstream-inherited",
        "candidate_attributable_paths",
        "inherited_default_equivalent_paths",
        "It must never be used to turn an exact",
        "current default-branch-equivalent path into Spec-attributable duplicate debt.",
    ):
        assert phrase in DEDUP

    assert "scripts.workflow_verify_spec_attribution" not in VERIFY
    assert "scripts.workflow_verify_spec_attribution" not in DEDUP


def test_verify_spec_is_bound_to_fail_closed_shared_handoff_gate() -> None:
    capabilities = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))
    assert "verify-spec" in capabilities["human_handoff"]["required_by"]

    for phrase in (
        "Every terminal **Human Handoff** from `$verify-spec`",
        HANDOFF_FINALIZER,
        "WORKFLOW HANDOFF: VALID",
        "byte-for-byte",
        "resume $verify-spec after ...",
        "READY` output cannot be",
        "Do not manually reconstruct a handoff",
        "the lifecycle remains at `$verify-spec`",
    ):
        assert phrase in VERIFY

    assert "python -m scripts.workflow_handoff generate" not in VERIFY
    assert "python -m scripts.workflow_handoff verify" not in VERIFY


def test_verify_spec_pass_handoff_renders_review_spec() -> None:
    manifest = {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "durability": {
            "verified": True,
            "sources": ["https://github.com/sponge-b0b/Polaris/issues/359"],
        },
        "handoffs": [
            {
                "destination": "$review-spec",
                "artifact": {
                    "title": (
                        "Spec: Implement R3 Portfolio consequence and "
                        "Portfolio Risk semantics"
                    ),
                    "url": "https://github.com/sponge-b0b/Polaris/issues/359",
                },
            }
        ],
    }

    output = workflow_handoff.render_manifest(manifest)
    assert (
        "$review-spec - Spec: Implement R3 Portfolio consequence and "
        "Portfolio Risk semantics "
        "(https://github.com/sponge-b0b/Polaris/issues/359)"
    ) in output
    assert (
        workflow_handoff.validate_output(manifest, output) == "WORKFLOW HANDOFF: VALID"
    )
