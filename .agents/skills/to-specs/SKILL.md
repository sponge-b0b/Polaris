---
name: to-specs
description: Project decision-complete planning into implementation Specs from exact Canonical Contract Ledger semantics while preserving Independent Specs and existing Spec identity.
disable-model-invocation: true
---

# To Specs

## Authoritative procedure composition

Before executing this skill, read `.agents/skills/to-specs/PROCEDURE.md` in full.

`PROCEDURE.md` preserves the complete established `$to-specs` lifecycle, including CCL
projection, stable planning cells, execution topology, planning-source partition,
Cross-Spec ownership integrity, concrete implementability, Spec reconciliation, native
dependency ownership, readiness labels, and fail-closed routing. This `SKILL.md` is the
authoritative entrypoint and adds the machine-enforced planning-worktree, cross-Spec
execution-feasibility, and outbound Human Handoff gates below. On conflict, this file wins.
Failure to load the retained procedure is a Hard Blocker.

## Clean/current planning-worktree gate

`$to-specs` must not execute from a dirty implementation candidate worktree and must not
use stale `$to-specs` control-plane bytes merely because tracker readback is current.

Before planning analysis or tracker mutation:

```bash
git fetch origin main
python -m scripts.workflow_to_specs preflight \
  --repo . \
  --main-ref origin/main
```

Require exact:

```text
TO-SPECS PREFLIGHT: VALID
```

The preflight fails closed when the worktree is dirty or when the current worktree's
`$to-specs` / shared-handoff control-plane blobs differ from current `origin/main`. If it
fails, use a separate clean planning worktree containing the current workflow repair. Do
not stash, reset, clean, merge, or otherwise disturb an active implementation candidate to
make `$to-specs` runnable.

## Machine-enforced cross-Spec execution feasibility

The retained Cross-Spec ownership-integrity rules remain authoritative. In particular, an
upstream Spec cannot be ticketing-ready when one of its execution units requires
completion-time proof from a sibling provider capability that is still open and is not a
native prerequisite of that consumer.

Local structural success is **not** sufficient:

```text
CCL projection valid
+ derive-decomposition valid
+ acyclic local execution topology
!= cross-Spec execution feasibility
```

Before publication/readiness mutation and again immediately before frontier handoff, build
one bounded `polaris.to-specs-execution-feasibility/v1` manifest outside the repository.
It must include every current handled sibling Spec and every additional provider Spec used
by a completion dependency. Each Spec entry points to a fresh issue JSON snapshot that
contains at least:

```text
number, title, url, state, body, blockedBy
```

The manifest also contains the canonical `spec_order` from the planning source and exactly
one `unit_analysis` record for every current `EU-*` in each Spec's actual
`spec-execution-topology:v1`.

Each execution-unit analysis must state:

- `completion_basis`: non-empty exact durable/CCL evidence used to reason about the unit's
  production completion path;
- `provider_requirements`: every sibling/provider capability whose production
  implementation must already exist for this unit itself to be completed and proved;
- for each provider requirement: exact provider Spec number, reason, and non-empty basis;
- if no external provider is required, an explicit `local_completion_attestation` with
  `result: true`, reason, and non-empty basis. An empty provider list without that positive
  attestation is invalid.

Do not derive provider requirements merely from textual CCL overlap. Trace the actual
**production success and proof path** implied by the frozen cells: required authoritative
reads, typed owner/absence guards, transaction participants, provider-produced facts,
composition boundaries, and any other completion-time capability. Test doubles, optional
injection seams, local mocks, or a structurally valid ticket decomposition do not establish
production provider availability.

Validate with:

```bash
python -m scripts.workflow_to_specs check-feasibility \
  --manifest <execution-feasibility.json>
```

Require exact:

```text
SPEC EXECUTION FEASIBILITY: VALID
Unprotected pending provider requirements: 0
```

The machine gate parses each supplied Spec's actual execution topology and requires exact
unit-analysis coverage. For every declared provider requirement, an open provider must be
protected by a native prerequisite path from the consumer Spec; a closed provider is already
durable. A required open provider with no such path makes the plan invalid even when every
individual Spec's `derive-decomposition` result is valid.

If this gate is invalid, `$to-specs` owns reconciliation under the retained rules when the
accepted partition already determines ownership. Reconcile the existing open Spec(s) in
place by the finest coherent lawful change: split/defer the consumer completion/proof unit,
establish the exact prerequisite relation, or otherwise repair the execution topology
without inventing semantics. Preserve existing Spec identities, closed ticket history, and
live WIP recovery handles. If the accepted partition cannot determine the repair, fail
closed to the planning owner rather than guessing.

`$attention` must inspect the completed execution-feasibility manifest before any frontier
handoff. Attention does not replace the machine gate.

## Frontier readiness override

A Spec is actionable for `$to-tickets` only when all retained readiness predicates pass
**and** the current execution-feasibility manifest is valid. `ready-for-agent`, current
Ticket Contract hashes, local decomposition validity, or zero native blockers cannot
substitute for cross-Spec execution feasibility.

If the feasibility repair changes a Spec's planning cells, execution topology, or native
prerequisites, re-run every retained projection/decomposition/readback gate invalidated by
that mutation before handoff.

## Canonical outbound Human Handoff

The retained bare-line Human Handoff section is overridden here.

After the feasibility gate succeeds, derive the actionable frontier and exact current Spec
titles/URLs from the same fresh issue snapshots; never abbreviate or reconstruct titles
from memory. Build the shared handoff manifest mechanically:

```bash
python -m scripts.workflow_to_specs build-handoff \
  --manifest <execution-feasibility.json> \
  --output <handoff-manifest.json>
```

Require exact:

```text
TO-SPECS HANDOFF MANIFEST: VALID
```

Then generate and verify the terminal Human Handoff only through the shared gate:

```bash
python -m scripts.workflow_handoff generate \
  --manifest <handoff-manifest.json> \
  > <handoff-output.txt>
python -m scripts.workflow_handoff verify \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

Require exact:

```text
WORKFLOW HANDOFF: VALID
```

The user-visible terminal block must reproduce `<handoff-output.txt>` **byte-for-byte**.
Every actionable Spec line therefore has the canonical form:

```text
$to-tickets - <exact current Spec title> (<exact canonical Spec URL>)
```

with one entry for every actionable frontier Spec in canonical planning-source order.
Do not emit an abbreviated title, omit a URL, stop after the first actionable Spec, manually
reconstruct the block, or claim a successful Human Handoff if either machine gate fails.

If the validated frontier is empty, do not create an empty handoff manifest; report the
exact durable blockers instead.
