from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/workflow_state_ownership.py"
SPEC = importlib.util.spec_from_file_location("workflow_state_ownership", SCRIPT)
assert SPEC and SPEC.loader
STATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STATE)


def _manifest() -> dict:
    return {
        "schema": "polaris.workflow-capabilities/v1",
        "state_machines": {
            "example:v1": {
                "states": ["open", "routed", "closed"],
                "terminal_states": ["closed"],
                "owner_skills": {
                    "router": ".agents/skills/router/SKILL.md",
                    "closer": ".agents/skills/closer/SKILL.md",
                },
                "transitions": [
                    {"from": "open", "to": "routed", "owner": "router", "guard": "route exists"},
                    {"from": "routed", "to": "closed", "owner": "closer", "guard": "authority accepted"},
                ],
                "consumers": {
                    "downstream": {
                        "path": ".agents/skills/downstream/SKILL.md",
                        "admissible_states": ["closed"],
                    }
                },
            }
        },
    }


def test_valid_state_machine_has_owned_nonterminal_transitions() -> None:
    result = STATE.validate_manifest(_manifest())
    assert result == {
        "machine_count": 1,
        "state_count": 3,
        "transition_count": 2,
        "missing_owner_states": 0,
    }


def test_nonterminal_state_without_transition_owner_fails() -> None:
    manifest = _manifest()
    manifest["state_machines"]["example:v1"]["transitions"] = [
        {"from": "open", "to": "closed", "owner": "closer", "guard": "authority accepted"}
    ]
    with pytest.raises(STATE.StateOwnershipError, match="routed"):
        STATE.validate_manifest(manifest)


def test_transition_owner_must_be_declared() -> None:
    manifest = _manifest()
    manifest["state_machines"]["example:v1"]["transitions"][1]["owner"] = "missing"
    with pytest.raises(STATE.StateOwnershipError, match="undeclared"):
        STATE.validate_manifest(manifest)


def test_transition_states_must_exist() -> None:
    manifest = _manifest()
    manifest["state_machines"]["example:v1"]["transitions"][1]["to"] = "ghost"
    with pytest.raises(STATE.StateOwnershipError, match="unknown destination"):
        STATE.validate_manifest(manifest)


def test_terminal_state_cannot_have_outbound_transition() -> None:
    manifest = _manifest()
    manifest["state_machines"]["example:v1"]["transitions"].append(
        {"from": "closed", "to": "open", "owner": "router", "guard": "reopen"}
    )
    with pytest.raises(STATE.StateOwnershipError, match="terminal state"):
        STATE.validate_manifest(manifest)


def test_consumer_cannot_admit_unknown_state() -> None:
    manifest = _manifest()
    manifest["state_machines"]["example:v1"]["consumers"]["downstream"]["admissible_states"] = ["ghost"]
    with pytest.raises(STATE.StateOwnershipError, match="admits unknown state"):
        STATE.validate_manifest(manifest)
