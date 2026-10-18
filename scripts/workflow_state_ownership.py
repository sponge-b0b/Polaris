from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "polaris.workflow-capabilities/v1"


class StateOwnershipError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise StateOwnershipError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), "manifest: expected JSON object")
    return value


def validate_manifest(manifest: dict[str, Any]) -> dict[str, int]:
    _need(manifest.get("schema") == SCHEMA, f"manifest: schema must be {SCHEMA}")
    machines = manifest.get("state_machines")
    _need(isinstance(machines, dict) and machines, "manifest: state_machines required")

    machine_count = 0
    state_count = 0
    transition_count = 0
    missing_owner_states: list[str] = []

    for machine_name, raw_machine in machines.items():
        _need(isinstance(machine_name, str) and machine_name, "state machine: invalid name")
        _need(isinstance(raw_machine, dict), f"{machine_name}: expected object")

        states = raw_machine.get("states")
        _need(isinstance(states, list) and states, f"{machine_name}: states required")
        _need(all(isinstance(state, str) and state for state in states), f"{machine_name}: invalid state")
        _need(len(set(states)) == len(states), f"{machine_name}: duplicate state")
        state_set = set(states)

        terminal = raw_machine.get("terminal_states")
        _need(isinstance(terminal, list), f"{machine_name}: terminal_states must be a list")
        _need(set(terminal) <= state_set, f"{machine_name}: unknown terminal state")

        owners = raw_machine.get("owner_skills")
        _need(isinstance(owners, dict) and owners, f"{machine_name}: owner_skills required")
        for owner, path in owners.items():
            _need(isinstance(owner, str) and owner, f"{machine_name}: invalid owner name")
            _need(isinstance(path, str) and path, f"{machine_name}: owner {owner} missing path")

        transitions = raw_machine.get("transitions")
        _need(isinstance(transitions, list), f"{machine_name}: transitions must be a list")
        outbound: dict[str, int] = {state: 0 for state in states}
        seen: set[tuple[str, str, str]] = set()
        for transition in transitions:
            _need(isinstance(transition, dict), f"{machine_name}: transition must be object")
            source = transition.get("from")
            destination = transition.get("to")
            owner = transition.get("owner")
            guard = transition.get("guard")
            _need(source in state_set, f"{machine_name}: transition has unknown source {source!r}")
            _need(destination in state_set, f"{machine_name}: transition has unknown destination {destination!r}")
            _need(source != destination, f"{machine_name}: self-transition {source!r} is not lifecycle progress")
            _need(owner in owners, f"{machine_name}: transition owner {owner!r} is undeclared")
            _need(isinstance(guard, str) and guard.strip(), f"{machine_name}: transition guard required")
            key = (source, destination, owner)
            _need(key not in seen, f"{machine_name}: duplicate transition {key}")
            seen.add(key)
            outbound[source] += 1
            transition_count += 1

        for state in states:
            if state not in terminal and outbound[state] == 0:
                missing_owner_states.append(f"{machine_name}:{state}")
            if state in terminal:
                _need(outbound[state] == 0, f"{machine_name}: terminal state {state!r} has outbound transition")

        consumers = raw_machine.get("consumers", {})
        _need(isinstance(consumers, dict), f"{machine_name}: consumers must be an object")
        for consumer, definition in consumers.items():
            _need(isinstance(consumer, str) and consumer, f"{machine_name}: invalid consumer")
            _need(isinstance(definition, dict), f"{machine_name}: consumer {consumer} must be object")
            path = definition.get("path")
            admitted = definition.get("admissible_states")
            _need(isinstance(path, str) and path, f"{machine_name}: consumer {consumer} missing path")
            _need(isinstance(admitted, list) and admitted, f"{machine_name}: consumer {consumer} needs admissible_states")
            _need(set(admitted) <= state_set, f"{machine_name}: consumer {consumer} admits unknown state")

        machine_count += 1
        state_count += len(states)

    _need(not missing_owner_states, "nonterminal states without transition owner: " + ", ".join(missing_owner_states))
    return {
        "machine_count": machine_count,
        "state_count": state_count,
        "transition_count": transition_count,
        "missing_owner_states": len(missing_owner_states),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "validate":
            result = validate_manifest(_read_json(args.manifest))
            print("WORKFLOW STATE OWNERSHIP: VALID")
            print(f"State machines: {result['machine_count']}")
            print(f"States: {result['state_count']}")
            print(f"Transitions: {result['transition_count']}")
            print(f"Nonterminal states without owner: {result['missing_owner_states']}")
            return 0
        raise StateOwnershipError(f"unsupported command: {args.command}")
    except (StateOwnershipError, json.JSONDecodeError, OSError) as exc:
        print(f"WORKFLOW STATE OWNERSHIP: INVALID\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
