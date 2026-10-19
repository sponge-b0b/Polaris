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
authoritative entrypoint and adds the machine-enforced planning-worktree, execution-
feasibility, legacy-completed compatibility, and outbound Human Handoff gates below. On
conflict, this file wins. Failure to load the retained procedure is a Hard Blocker.

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

## Machine-enforced execution feasibility

The retained Cross-Spec ownership-integrity rules remain authoritative. In particular, an
upstream Spec cannot be ticketing-ready when one of its execution units requires
completion-time proof from a sibling provider capability that is still open and is not a
native prerequisite of that consumer.

The same fail-closed rule applies **inside one Spec**. An execution unit cannot be
implementation-ready when completion or proof of one of its frozen cells requires a fact,
producer capability, historical record, transaction participant, or proof surface owned by
a different execution unit that is not already a transitive prerequisite of the consumer.
A structurally acyclic topology can therefore still be execution-infeasible.

Local structural success is **not** sufficient:

```text
CCL projection valid
+ derive-decomposition valid
+ acyclic local execution topology
!= execution feasibility
```

Before publication/readiness mutation and again immediately before frontier handoff, build
one bounded `polaris.to-specs-execution-feasibility/v1` manifest outside the repository.
It must include every current handled sibling Spec and every additional provider Spec used
by a completion dependency. Each Spec entry points to a fresh issue JSON snapshot that
contains at least:

```text
number, title, url, state, body, blockedBy
```

The manifest also contains the canonical `spec_order` from the planning source.

### Current/open and topology-bearing Specs

Every OPEN Spec must contain a current `spec-execution-topology:v1` marker. A missing
topology on an OPEN Spec is always invalid.

For every Spec that has execution topology, including a CLOSED Spec created under the
topology regime, the manifest must contain exactly one `unit_analysis` record for every
current/historical `EU-*` in that Spec's actual topology. Such a Spec may not use the
legacy-completed compatibility path to skip unit analysis.

Each execution-unit analysis must state:

- `completion_basis`: non-empty exact durable/CCL evidence used to reason about the unit's
  production completion path;
- `provider_requirements`: every sibling/provider Spec capability whose production
  implementation must already exist for this unit itself to be completed and proved;
- for each external provider requirement: exact provider Spec number, reason, and non-empty
  basis;
- `local_provider_requirements`: every **different execution unit in the same Spec** whose
  production capability must already exist for this unit itself to be completed and proved;
- for each local provider requirement: exact `provider_unit`, reason, and non-empty basis;
- if neither external nor local providers are required, an explicit
  `local_completion_attestation` with `result: true`, reason, and non-empty basis. Empty
  external/local provider lists without that positive attestation are invalid.

`local_provider_requirements` is mandatory even when empty. A same-unit capability is not a
local provider edge; use `local_completion_attestation` when the unit can produce and prove
its own required capability. A distinct local provider must be in the current topology and
must be reachable through the consumer unit's transitive `depends_on` prerequisites. A
consumer may never declare a downstream or unrelated local execution unit as a completion
provider.

### Immutable legacy-completed Specs

A CLOSED Spec that predates `spec-execution-topology:v1` is immutable delivery history.
Do **not** retrofit synthetic `EU-*` topology, planning cells, or CCL markers merely to make
the feasibility gate accept it.

A topology-less Spec may participate in the bounded sibling/provider set only when all of
the following are true:

- the fresh issue snapshot says exactly `CLOSED`;
- its manifest entry contains `legacy_completed`;
- `legacy_completed.result` is exactly `true`;
- `legacy_completed.reason` is non-empty;
- `legacy_completed.completion_basis` is a non-empty list of exact durable sources proving
  that the provider capability was completed/accepted;
- `unit_analysis` is absent or empty.

Example:

```json
{
  "issue_json": "357.json",
  "legacy_completed": {
    "result": true,
    "reason": "completed before execution-topology manifests were introduced",
    "completion_basis": [
      "https://github.com/<owner>/<repo>/issues/357",
      "https://github.com/<owner>/<repo>/issues/357#issuecomment-<verification>"
    ]
  }
}
```

This is a compatibility attestation only. It means the CLOSED provider is already durable
for dependency purposes; it does not create retroactive execution-unit authority, make the
Spec actionable again, or permit an OPEN topology-less Spec. A CLOSED Spec that already
contains topology must still use normal `unit_analysis`.

### Completion-path analysis

Do not derive provider requirements merely from textual CCL overlap. Trace the actual
**production success and proof path** implied by every frozen cell: required authoritative
reads, typed owner/absence guards, transaction participants, provider-produced facts,
historical facts/judgments named by an assertion, composition boundaries, and any other
completion-time capability. This trace must cover both sibling Specs and distinct execution
units in the same Spec. Test doubles, optional injection seams, local mocks, or a
structurally valid ticket decomposition do not establish production provider availability.

For a local execution-unit provider, record the exact unit whose production output is
needed. The machine gate checks the current topology. If `EU-A` needs `EU-B` to complete,
`EU-B` must be a transitive prerequisite of `EU-A`; if `EU-B` is downstream or unrelated,
the topology is execution-infeasible even when it is acyclic and every cell is mapped once.

Validate with:

```bash
python -m scripts.workflow_to_specs check-feasibility \
  --manifest <execution-feasibility.json>
```

Require exact:

```text
SPEC EXECUTION FEASIBILITY: VALID
Unprotected pending provider requirements: 0
Unprotected downstream local provider requirements: 0
```

The machine gate parses every topology-bearing supplied Spec and requires exact
unit-analysis coverage. It separately validates immutable `legacy_completed` entries for
CLOSED pre-topology Specs. For every declared external provider requirement, an open
provider must be protected by a native prerequisite path from the consumer Spec; a closed
provider is already durable. For every declared local provider requirement, the named
execution unit must be a current unit and a transitive prerequisite of the consumer. A
required open sibling provider without a native path, or a required local provider that is
downstream/unrelated, makes the plan invalid even when every individual Spec's
`derive-decomposition` result is valid.

If this gate is invalid, `$to-specs` owns reconciliation under the retained rules when the
accepted partition already determines ownership. Reconcile the existing open Spec(s) in
place by the finest coherent lawful change: move/split/defer the consumer completion/proof
unit, establish the exact prerequisite relation, or otherwise repair the execution topology
without inventing semantics. A frozen material cell may not be split merely to make the
machine gate pass; if the accepted CCL/planning authority does not permit a lawful cell or
unit repair, fail closed to the planning owner. Preserve existing Spec identities, closed
ticket history, and live WIP recovery handles.

`$attention` must inspect the completed execution-feasibility manifest before any frontier
handoff. Attention does not replace the machine gate.

## Frontier readiness override

A Spec is actionable for `$to-tickets` only when all retained readiness predicates pass
**and** the current execution-feasibility manifest is valid. `ready-for-agent`, current
Ticket Contract hashes, local decomposition validity, or zero native blockers cannot
substitute for execution feasibility.

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
