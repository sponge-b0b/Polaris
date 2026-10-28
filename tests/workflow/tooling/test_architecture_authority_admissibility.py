from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GUARD = (
    ROOT
    / ".agents/skills/architecture-remediation/scripts/authority_admissibility.py"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


A = _load("test_architecture_authority_admissibility_module", GUARD)


def _artifact(
    *,
    relations: tuple[str, ...],
    disposition: str,
    allowed: bool,
    coordinate: str | None = None,
):
    sources = [f"source:{index}" for index in range(len(relations))]
    findings = [
        {
            "source": source,
            "relation": relation,
            "basis": f"basis for {relation}",
        }
        for source, relation in zip(sources, relations, strict=True)
    ]
    return {
        "schema": "polaris.architecture-authority-disposition/v1",
        "source_workflow": "$implement-ticket",
        "source_artifact": "https://github.com/sponge-b0b/Polaris/issues/465",
        "observed_state": (
            "business fact committed before required historical knowledge boundary "
            "is durably recoverable"
        ),
        "governing_sources_checked": sources,
        "findings": findings,
        "material_coordinate": coordinate,
        "disposition": disposition,
        "decision_creation_allowed": allowed,
    }


def test_forbidden_state_resolves_without_decision_creation():
    receipt = A.validate_disposition(
        _artifact(
            relations=("FORBIDS_STATE",),
            disposition="FORBIDDEN_BY_EXISTING_AUTHORITY",
            allowed=False,
        )
    )
    assert receipt.disposition == "FORBIDDEN_BY_EXISTING_AUTHORITY"
    assert receipt.decision_creation_allowed is False


def test_narrow_missing_sentence_cannot_override_stronger_forbidden_state():
    with pytest.raises(
        A.AuthorityAdmissibilityError,
        match="expected FORBIDDEN_BY_EXISTING_AUTHORITY",
    ):
        A.validate_disposition(
            _artifact(
                relations=(
                    "DOES_NOT_RESOLVE_COORDINATE",
                    "FORBIDS_STATE",
                ),
                disposition="UNRESOLVED_MATERIAL_CHOICE",
                allowed=True,
                coordinate="receipt behavior in the invalid interval",
            )
        )


def test_unresolved_admissible_state_may_create_decision_work():
    receipt = A.validate_disposition(
        _artifact(
            relations=("DOES_NOT_RESOLVE_COORDINATE",),
            disposition="UNRESOLVED_MATERIAL_CHOICE",
            allowed=True,
            coordinate="admissible publication behavior",
        )
    )
    assert receipt.disposition == "UNRESOLVED_MATERIAL_CHOICE"
    assert receipt.decision_creation_allowed is True


def test_fixed_existing_authority_forbids_new_decision_work():
    receipt = A.validate_disposition(
        _artifact(
            relations=("FIXES_BEHAVIOR",),
            disposition="FIXED_BY_EXISTING_AUTHORITY",
            allowed=False,
        )
    )
    assert receipt.decision_creation_allowed is False


def test_source_conflict_has_precedence_over_other_relations():
    receipt = A.validate_disposition(
        _artifact(
            relations=("CONFLICTS", "FORBIDS_STATE"),
            disposition="SOURCE_CONFLICT",
            allowed=False,
        )
    )
    assert receipt.disposition == "SOURCE_CONFLICT"


def test_every_checked_source_requires_an_explicit_finding():
    artifact = _artifact(
        relations=("FORBIDS_STATE",),
        disposition="FORBIDDEN_BY_EXISTING_AUTHORITY",
        allowed=False,
    )
    artifact["governing_sources_checked"].append("source:missing")
    with pytest.raises(
        A.AuthorityAdmissibilityError,
        match="every governing source needs a finding",
    ):
        A.validate_disposition(artifact)


def test_policy_requires_admissibility_before_wayfinder_routing():
    policy = (
        ROOT / ".agents/skills/architecture-remediation/SKILL.md"
    ).read_text(encoding="utf-8")
    authority = (
        ROOT / ".agents/skills/architecture-remediation/AUTHORITY_ADMISSIBILITY.md"
    ).read_text(encoding="utf-8")
    assert "AUTHORITY_ADMISSIBILITY.md" in policy
    assert "FORBIDDEN_BY_EXISTING_AUTHORITY" in policy
    assert (
        "only after the authority-admissibility gate permits decision creation"
        in policy
    )
    assert "implementation-created invalid state" in authority
    assert "Never reverse steps 2 and 3" in authority
    assert "decision_creation_allowed=true" in authority
