---
name: to-specs
description: Project decision-complete planning into implementation Specs from exact Canonical Contract Ledger semantics while preserving Independent Specs and existing Spec identity.
disable-model-invocation: true
---

# To Specs

## Authoritative procedure composition

Before executing this skill, read all of these files in full:

1. `.agents/skills/to-specs/PROCEDURE.md`
2. `.agents/skills/to-specs/CONTROL_PLANE.md`

`PROCEDURE.md` preserves the complete established `$to-specs` lifecycle.
`CONTROL_PLANE.md` preserves the previously authoritative entrypoint through the
machine-enforced cross-Spec and intra-Spec execution-feasibility, legacy-completed
compatibility, planning-worktree, and shared Human Handoff repairs.

This `SKILL.md` is now the authoritative entrypoint and adds the machine-enforced durable
routing-defect inventory gate below. On conflict, this file wins. Failure to load either
retained file is a Hard Blocker.

All requirements in both retained files remain mandatory unless explicitly overridden here.

## Retained execution-feasibility contract

Local structural success is **not** sufficient. The production success and proof path must be traced before readiness.
Every topology-bearing unit still uses `provider_requirements`, `local_provider_requirements`, and, only when neither kind of provider is required, `local_completion_attestation`.

The same fail-closed rule applies **inside one Spec**.
A distinct local provider must be reachable through the consumer unit's transitive `depends_on` prerequisites; a downstream or unrelated local execution unit is invalid.
Successful retained feasibility still requires:

```text
SPEC EXECUTION FEASIBILITY: VALID
Unprotected pending provider requirements: 0
Unprotected downstream local provider requirements: 0
```

### Immutable legacy-completed Specs

A CLOSED Spec that predates `spec-execution-topology:v1` is immutable delivery history.
`legacy_completed.result` and `legacy_completed.completion_basis` remain required by the
retained compatibility path, which does not create retroactive execution-unit authority.
Every OPEN Spec must contain a current `spec-execution-topology:v1` marker, and a CLOSED
Spec that already contains topology must still use normal `unit_analysis`.

The retained canonical handoff mechanics also remain mandatory:

```bash
python -m scripts.workflow_to_specs build-handoff \
  --manifest <execution-feasibility.json> \
  --output <handoff-manifest.json>
```

They must still produce `WORKFLOW HANDOFF: VALID`, and the user-visible terminal block must
remain byte-for-byte machine output, including the canonical form:

```text
$to-tickets - <exact current Spec title> (<exact canonical Spec URL>)
```

## Durable routing-defect inventory gate

Execution feasibility is not allowed to depend only on provider edges that the current
`$to-specs` actor remembers to declare in `unit_analysis`. Durable downstream evidence that
already proves a ticket/Spec routing defect is part of the current planning state and must be
machine-consumed.

A model-authored statement such as "no routing defects found" is not evidence. The inventory
must be collected mechanically from the current native child tickets of every Spec supplied
to the feasibility manifest.

### Current control-plane admission

Immediately after the retained `$to-specs` preflight, require the routing-defect control
plane to be current relative to the same fetched default branch:

```bash
python -m scripts.workflow_routing_defects preflight \
  --repo . \
  --main-ref origin/main
```

Require exact:

```text
TO-SPECS ROUTING DEFECT PREFLIGHT: VALID
```

This prevents a clean planning worktree from using a stale routing-defect collector or stale
producer/consumer skill contract.

### Machine inventory collection

Before the first execution-feasibility decision and again immediately before frontier
handoff, collect the inventory from GitHub using every Spec in the bounded feasibility set:

```bash
python -m scripts.workflow_routing_defects collect \
  --repo <owner/repo> \
  --spec <spec-number> \
  [--spec <spec-number> ...] \
  --output <routing-defects.json>
```

Require exact header:

```text
TO-SPECS ROUTING DEFECT INVENTORY: VALID
```

The collector follows current native child-ticket relationships and reads their current
comments. It recognizes only machine-readable `workflow-routing-defect:v1` markers; prose,
chat memory, labels, or a hand-maintained list cannot substitute for the collector.

The exact scanned Spec set must later equal every and only Spec snapshot supplied to the
execution-feasibility manifest.

### Routing-defect marker semantics

A current cell-routing defect uses exactly one machine-readable marker shaped as:

```text
<!-- workflow-routing-defect:v1
{
  "schema": "polaris.workflow-routing-defect/v1",
  "defect_id": "<stable id>",
  "status": "open | resolved",
  "classification": "cell-routing-defect",
  "source_ticket": <ticket>,
  "parent_spec": <spec>,
  "affected_cells": ["OBL-..."],
  "required_local_provider_cells": ["OBL-..."],
  "reason": "<why the assigned cell cannot complete in the current route>",
  "basis": ["<durable source>"]
}
-->
```

The marker records cells rather than historical execution-unit IDs so a later topology
reconciliation cannot make the evidence disappear by renaming, merging, or moving units.

`required_local_provider_cells` may be empty only when the downstream workflow has proved a
cell-routing defect but cannot yet identify machine-resolvable same-Spec provider cells. Such
an OPEN marker is deliberately blocking: `$to-specs` must not claim feasibility until the
planning authority can either identify the exact provider relation or otherwise reconcile the
defect under frozen authority.

### Machine coverage against the current topology

After building the retained `polaris.to-specs-execution-feasibility/v1` manifest, validate the
fresh routing-defect inventory against that exact manifest:

```bash
python -m scripts.workflow_routing_defects check \
  --inventory <routing-defects.json> \
  --manifest <execution-feasibility.json>
```

Require exact:

```text
TO-SPECS ROUTING DEFECT COVERAGE: VALID
Unprotected routing defect requirements: 0
```

For every OPEN marker, the machine gate maps each `affected_cells` entry and each
`required_local_provider_cells` entry onto the **current** `spec-execution-topology:v1`.
For each resulting consumer/provider pair, the provider must either be in the same current
execution unit or be a transitive `depends_on` prerequisite of the consumer.

If the provider is downstream or unrelated, the plan is invalid even when:

- the local topology is acyclic;
- deterministic decomposition is valid;
- the actor omitted the provider from `unit_analysis`;
- the current ticket coverage maps every cell exactly once; or
- a prior feasibility manifest passed before the routing defect was discovered.

An affected/provider cell absent from the current topology also fails closed. An OPEN marker
with no machine-resolvable provider cells fails closed rather than disappearing from analysis.

This gate supplements, and does not replace, the retained `scripts.workflow_to_specs
check-feasibility` gate. Both must pass on the same current Spec snapshots before publication,
readiness mutation, or Human Handoff.

## Reconciliation ownership

When this gate fails, `$to-specs` owns topology reconciliation whenever accepted planning/CCL
authority already determines the lawful repair. Preserve Spec identity, frozen material
cells, closed delivery history, and live-WIP recovery handles. Do not split or weaken a
material cell merely to satisfy the gate.

After any Spec/topology mutation, rebuild the current Spec contract/decomposition,
reconstruct the complete feasibility manifest, and rerun both routing-defect collection/check
and the retained execution-feasibility gate.

## Frontier and Human Handoff override

A Spec is not actionable for `$to-tickets` merely because the retained feasibility gate says
VALID. Immediately before building the shared Human Handoff manifest, rerun the machine
routing-defect collection and coverage check from current tracker state and require both
receipts again.

Therefore a terminal `$to-tickets` handoff is legal only when all of the following are true
on one current state:

```text
TO-SPECS PREFLIGHT: VALID
TO-SPECS ROUTING DEFECT PREFLIGHT: VALID
TO-SPECS ROUTING DEFECT INVENTORY: VALID
TO-SPECS ROUTING DEFECT COVERAGE: VALID
Unprotected routing defect requirements: 0
SPEC EXECUTION FEASIBILITY: VALID
Unprotected pending provider requirements: 0
Unprotected downstream local provider requirements: 0
WORKFLOW HANDOFF: VALID
```

If any receipt is missing or stale, do not emit or honor a `$to-tickets` frontier handoff.
