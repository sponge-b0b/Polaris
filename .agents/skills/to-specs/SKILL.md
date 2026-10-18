---
name: to-specs
description: Project decision-complete planning into implementation Specs from exact Canonical Contract Ledger semantics while preserving Independent Specs and existing Spec identity.
disable-model-invocation: true
---

# To Specs

`$to-specs` owns projection and partition from decision-complete planning into
implementation Specs. It does not design material semantics.

```text
planning source + accepted CCL
        ↓
implementation Spec(s)
```

Material product/domain/architecture/public/persistence/temporal/authority/failure
semantics come only from exact accepted CCL assertions. `$to-specs` never reconstructs
those semantics from Decision Analysis, ADR prose, existing Spec prose, implementation
precedent, or another agent's interpretation.

## Session independence

Recover correctness-critical inputs from the invocation, repository, CCL, and durable
tracker state. Chat/session memory is never authority.

## Governance

### Wayfinder-managed source

Treat the map and its accepted CCL-backed decisions as the planning source.

Before tracker mutation:

1. invoke `$project-delivery-management reconcile`;
2. invoke `guard <Wayfinder>`;
3. require exact `PROJECT DELIVERY GUARD: ALLOWED`.

Do not infer or change project focus inside `$to-specs`.

### Independent source

An intentionally non-Wayfinder planning source remains Independent.

For each material semantic obligation:

* exact active CCL assertion exists → consume it;
* current durable governing/constraint authority already fixes the meaning exactly but it
  is not registered → invoke `$contract-ledger existing-authority`;
* exactly one bounded independent semantic coupling group remains unresolved → Human
  Handoff to `$contract-ledger owner-decision`;
* multiple/coupled decision groups, cross-domain planning, research/prototyping, or project
  partition decisions remain → route to `$wayfinder`.

`$to-specs` never chooses the missing semantic answer.

## Permanent reconciliation rule

For every current planning source, derive the **desired current Spec set and projection**
from current accepted authority.

For each desired Spec identity:

```text
no current Spec
    → create it

existing open Spec + same projection
    → no-op

existing open Spec + different projection
    → amend that same Spec in place

existing completed Spec
    → immutable delivery history; do not rewrite

identity/provenance ambiguous
    → fail closed
```

This rule is ordinary lifecycle behavior. It applies whenever governing accepted CCL or
planning state changes while a Spec is open. Do not create replacement Specs merely to
avoid reconciling an existing open identity.

Preserve existing issue identity, planning provenance, branch/fixed baseline, ticket
history, native dependencies, and Spec Review lineage unless their owning lifecycle
explicitly changes them.

Recover Wayfinder Spec identity from canonical map handoffs plus Spec-local
`wayfinder-source` / `wayfinder-remediation` provenance. Repair only an unambiguous missing
forward/local provenance link as part of normal reconciliation. Ambiguity fails closed;
never infer lineage from Project fields, issue order, branch names, or chat history.

## CCL projection contract

Every software Spec with material semantics carries exactly one machine-managed comment:

```text
<!-- spec-contract-ccl:v1
{
  "schema": "polaris.spec-ccl/v1",
  "obligations": [
    {
      "obligation_id": "OBL-001",
      "source_ref": "<durable planning-source anchor>",
      "ccl": ["<contract-id>@<revision>#<assertion-id>"]
    }
  ]
}
-->
```

Rules:

* `OBL-*` IDs are stable once published;
* every material obligation references one or more exact CCL assertions;
* the manifest contains mapping/provenance only, never a second semantic definition;
* material semantics not reachable through an exact CCL address are not part of an
  implementation-ready Spec.

Generate and validate the human-readable semantic section with:

```bash
python -m scripts.ccl_spec render <manifest.json> contracts/ccl/transactions
python -m scripts.ccl_spec check <spec-body.txt> contracts/ccl/transactions
```

The generated `## Canonical Contract Obligations` section is authoritative human-readable
projection. Do not hand-edit it.

Other Spec prose may explain outcome, implementation plan, testing, and scope, but it must
not strengthen, weaken, enumerate, close, or reinterpret CCL.

## Stable downstream planning cells

Ticketing consumes three non-semantic stable-ID families:

* `IMP-*` — private/mechanical implementation obligations;
* `TEST-*` — explicit proof/test obligations;
* `EXC-*` — exclusions / decomposition guardrails.

These are planning identities, not material semantic authority. Their exact text is hashed
by `$spec-contract`; changing one intentionally changes downstream planning identity.

Problem/Solution prose, User Stories, Architecture Impact explanation, and Further Notes
are human context. They do not create ticket cells merely because they sound normative.

## Stable execution topology

For every implementation-ready software Spec, `$to-specs` also owns exactly one
machine-managed execution-topology comment:

```text
<!-- spec-execution-topology:v1
{
  "schema": "polaris.spec-execution-topology/v1",
  "units": [
    {
      "unit_id": "EU-001",
      "cells": ["OBL-001", "IMP-001", "TEST-001"],
      "depends_on": []
    },
    {
      "unit_id": "EU-002",
      "cells": ["OBL-002", "IMP-002", "TEST-002"],
      "depends_on": ["EU-001"]
    }
  ]
}
-->
```

This topology is durable **planning authority**, not material semantic authority. It records
the finest coherent execution partition that downstream ticketing must project exactly.

Core invariants:

* `EU-*` IDs are stable canonical identities (`EU-001` through `EU-999`); never renumber a
  surviving unit merely for presentation;
* every current non-EXC `OBL/IMP/TEST` cell appears in exactly one execution unit;
* no `EXC-*` appears in an execution unit;
* every execution unit contains at least one material `OBL-*` so each ticket remains a
  vertical material-outcome slice rather than a mechanics-only task;
* unit dependencies name only current execution units, are acyclic, and represent genuine
  execution prerequisites;
* an `IMP-*` or `TEST-*` cell that explicitly references another current cell must be in the
  same unit as that cell or in a unit transitively downstream of it;
* topology must not duplicate material semantics or infer new obligations from prose.

### Finest-coherent partition invariant

The desired topology is the **finest independently executable partition**, not the fewest
possible tickets.

Do not merge two execution units merely because one implementation agent could perform both
in one ticket. Keep responsibilities separate whenever each can be completed and proved as
a non-empty material-outcome slice under the frozen Spec contract and their relationship can
be represented by dependency edges.

Merge cells into one unit only when separating them would make at least one side not
independently completable/provable under the frozen contract, would create a mechanics-only
unit with no material obligation, or would violate an explicit same-commit/atomic execution
requirement already present in planning authority.

This rule is generic. Do not encode product names, current issue numbers, current Spec IDs,
or one-off examples as topology policy.

### Topology reconciliation

For an existing open Spec, topology is reconciled in place with the rest of the projection:

* unchanged unit responsibility → preserve its `EU-*` identity;
* changed cells within the same atomic responsibility → update that unit in place;
* newly independent responsibility → allocate a new unused `EU-*`;
* responsibility removed from current work → remove it from current topology without
  reusing its identity for a different responsibility;
* ambiguous split/merge responsibility → fail closed rather than silently renumbering or
  guessing.

A topology-only amendment changes the Spec body and topology hash but does not change the
material Spec Contract Hash unless the underlying `OBL/IMP/TEST/EXC` cell semantics also
change.

Before any `$to-tickets` handoff, build the current Spec contract and require deterministic
topology derivation:

```bash
python -m scripts.spec_contract build <spec-issue-json> <contract.json>
python -m scripts.spec_contract derive-decomposition \
  <spec-issue-json> <contract.json> <coverage.json> <dependencies.json>
```

Require `TICKET DECOMPOSITION: DERIVED`, an Execution Topology Hash, complete exact coverage,
and valid execution closure. Missing or invalid topology means the Spec is not ticketing
ready and is a `$to-specs` projection defect; never ask `$to-tickets` to infer a fallback.

## Planning Source Partition

Build one working partition over the complete current planning source:

```text
Planning item: PI-<n>
Source: <durable source anchor>
Disposition:
  material-contract
  implementation-equivalent
  deferred-semantic-decision
  already-represented
  out-of-scope
Spec: <candidate/existing Spec | None>
CCL: <exact assertion set | None>
Reason: <compact routing reason>
```

Require every material-contract row to have exact CCL, every specifiable item to have a
Spec candidate, and zero unclassified items. `implementation-equivalent` is legal only
when remaining private choices cannot alter material external/downstream semantics.

## Cross-Spec ownership integrity

When one planning source yields multiple current Specs, the accepted partition is a
correctness boundary, not merely descriptive prose.

Before publishing or reconciling any open Spec, and again before frontier handoff:

1. recover the exact current sibling Spec partition from the durable planning source;
2. inspect the current sibling Specs and native dependency graph;
3. classify every projected `OBL-*` in the candidate Spec as either:
   * `owned` — this Spec implements/certifies the asserted behavior; or
   * `consumed-boundary` — another Spec owns the provider capability and this Spec needs
     the exact assertion only to constrain its own behavior;
4. inspect every `IMP-*` and `TEST-*` against that classification and the accepted
   partition;
5. inspect every execution unit against the same ownership classification and ensure no
   unit crosses a sibling ownership boundary merely to reduce ticket count.

A consumed-boundary projection is legal only when the current Spec has a role-narrow
implementation or proof responsibility that can be completed without implementing the
provider capability. Cross-Spec CCL reference alone does not transfer ownership.

Fail the ownership check if any of the following is true:

* a Spec projects a sibling's complete capability merely because the integrated outcome
  depends on it;
* an `IMP-*` or `TEST-*` tells the current Spec to implement or certify behavior assigned
  to a sibling;
* two sibling Specs are assigned the same executable ownership rather than distinct
  provider/consumer roles;
* an upstream Spec requires completion-time proof of behavior that can only be implemented
  by a downstream Spec that is natively blocked by the upstream Spec;
* prose, CCL projection, planning cells, execution topology, exclusions, and native
  dependency direction disagree about who owns the work.

Shared/cross-cutting assertions may appear in more than one Spec only when each occurrence
has a distinct role-narrow local responsibility. Do not use a sibling's whole contract as
a substitute for that local responsibility.

For an open Spec whose accepted partition changed or whose prior projection violated the
partition:

* reconcile the same Spec in place;
* retire no-longer-current `OBL/IMP/TEST/EXC` IDs without reusing them;
* reconcile the execution topology under the stable-unit rules above;
* preserve closed ticket/history artifacts;
* update native dependencies only when the accepted prerequisite relation itself requires
  it.

If the planning source already fixes the partition, ownership drift is a `$to-specs`
projection defect and `$to-specs` repairs it. If the partition itself is unresolved or
contradictory, fail closed and route to `$wayfinder`.

Invoke `$attention` over the bounded sibling set before publication. Attention may identify
a missing planning item, ownership conflict, bad role classification, CCL gap, or invalid
execution partition; it does not create authority.

## Concrete implementability

Inspect only enough current code to establish that the projected contract can be realized
without another material semantic decision.

Missing classes, methods, migrations, queries, repository calls, DI bindings, local
algorithms, or equivalent wiring are implementation work when CCL already fixes material
semantics.

If realization requires a material semantic choice absent from CCL, route that exact gap
to its semantic owner.

## Software Spec body

Use:

```markdown
<governance/provenance markers>
<spec-contract-ccl:v1 manifest>
<spec-execution-topology:v1 manifest>

## Problem Statement
<explanation>

## Solution
<outcome framing referencing OBL-* where useful>

## User Stories
1. As a <user>, I want <outcome>, so that <value>.

## Architecture Impact
- Affected entities: <...>
- Impact: none | conforming | extending | changing | retiring
- Governing CCL: <contract@revision list>
- Unresolved material semantic questions: none
- Implementation readiness: pass

## Canonical Contract Obligations
<generated by scripts.ccl_spec>

## Implementation Decisions
- `IMP-001` — <private/mechanical implementation obligation>

## Testing Decisions
- `TEST-001` — <proof/test obligation>

## Out of Scope
- `EXC-001` — <independent exclusion>

## Further Notes
<non-authoritative context>
```

Use one independently routable item per planning bullet. If a stable planning section has
no items, write exactly `None.`. Never hide material semantics inside `IMP-*` or `TEST-*`.
Then group those exact current cells into stable execution units under the finest-coherent
partition invariant above; do not let `$to-tickets` rediscover the grouping.

When the planning source defines sibling capability ownership, make the relevant provider,
consumer, composition, and acceptance boundaries explicit in the Spec's human-readable
scope or exclusions. This is explanatory context; the accepted planning source remains the
authority.

## Dependencies and frontier

After publishing/reconciling the complete currently specifiable set, establish every known
native Spec prerequisite before any `$to-tickets` handoff.

Ownership remains:

* same-lineage Wayfinder-managed relationship → `$to-specs` + native dependency helper;
* cross-Wayfinder relationship → `$project-delivery-management dependency ensure`;
* either endpoint Independent → `$to-specs` validates the narrow prerequisite and cycle
  safety, then uses the native dependency helper.

Never use Project fields, publication order, priority, or handoff order as dependency
truth. Reject self-dependency, incomplete blocker graphs, and cycles.

The frontier is every open handled Spec with zero open native blockers, a valid current CCL
projection, and a valid current execution topology. Wayfinder-managed frontier Specs
additionally require an ALLOWED current governor guard.

Do not hand off a Spec whose Cross-Spec ownership integrity or execution topology check is
unresolved.

### Readiness label gate

`ready-for-agent` is a downstream-readiness label, not semantic or dependency authority.
Apply it to a Spec only after that exact current Spec is ticketing-ready under this skill:

* CCL projection validates current;
* planning cells and current execution topology validate current;
* Cross-Spec ownership integrity is resolved;
* concrete implementability has no unresolved material semantic choice;
* `$attention` has completed for the current projection;
* all known native Spec dependencies have been established;
* the Spec is in the current frontier; and
* every required current Wayfinder governor guard is ALLOWED.

If any of those predicates is false, unknown, or later becomes stale while `$to-specs`
owns the reconciliation, do not apply `ready-for-agent`; remove a stale label that this
workflow can prove no longer represents current ticketing readiness. Label state never
substitutes for any readiness proof above.

After any label mutation, re-read the Spec and require exact label state before emitting a
`$to-tickets` handoff.

## Human handoff

Emit one line per actionable Spec:

```text
$to-tickets - <Spec Title> (<Spec URL>)
```

If none are actionable, report exact blockers/unfocused reasons. Never invoke
`$to-tickets` implicitly.

## Fail-closed routing

* semantics fixed but not registered → `$contract-ledger existing-authority`;
* one bounded Independent semantic choice → `$contract-ledger owner-decision`;
* coupled/multi-domain planning → `$wayfinder`;
* Wayfinder-managed changed semantic decision → governing Wayfinder decision;
* downstream architecture blocker → `$architecture-remediation`;
* CCL source conflict → governing semantic owner;
* cross-Spec ownership drift with a fixed accepted partition → `$to-specs` itself;
* missing/invalid/ambiguous execution topology → `$to-specs` itself;
* projection defect → `$to-specs` itself.

`$to-specs` never infers material semantics from prose, runs a second semantic certifier,
delegates material design to implementation, creates implementation tickets, or replaces
an existing open Spec when ordinary reconciliation can preserve its identity.
