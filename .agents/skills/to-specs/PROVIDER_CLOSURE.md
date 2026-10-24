# `$to-specs` production-provider and composition closure

This document is authoritative `$to-specs` planning policy and runs over the same bounded
sibling Spec set used by execution-feasibility and cross-Spec ownership analysis.

Its purpose is to prevent a semantically correct CCL partition from projecting an impossible
execution plan because concrete production collaborators are hidden inside a shared query,
transaction, or composition contract.

## 1. Expand material cells to concrete production seams

For every current material `OBL-*`, trace the production path far enough to identify every
cross-owner collaborator required for that Spec's own completion/proof: authoritative
readers, target/context owners, negative/selection guards, persistence participants, current
basis/revalidation services, composition roots, and other typed ports.

Do not stop at CCL overlap. A broad assertion such as a complete basis/query contract may
contain several independently owned production providers.

For each seam record the durable owner, current Spec, native dependency relation, and whether
the current Spec needs the provider for **capability completion** or only contributes/consumes
a stable inward port whose production assembly belongs to a later composition Spec.

Test doubles, fixtures, mocks, and optional injection are not evidence that production
composition exists.

## 2. Ownership-homogeneous material cells

One current material OBL cell must have one executable ownership disposition.

A material cell is invalid when it mixes:

- CCL assertions whose executable implementation is locally owned by the current Spec; and
- CCL assertions whose executable implementation belongs to a sibling provider or later
  composition Spec.

When accepted planning authority already distinguishes those responsibilities, reconcile the
open Spec in place:

1. retire the mixed `OBL-*` identity;
2. create new unused OBL identities for the independently owned responsibilities;
3. preserve the exact CCL assertions and source anchors without weakening semantics;
4. update affected `IMP-*`, `TEST-*`, exclusions, and execution topology to reference only
   current cells; and
5. preserve closed ticket/history artifacts and live-WIP recovery handles.

Do not reuse the retired OBL identity for a different contract.

## 3. Capability implementation versus deferred composition

A downstream composition Spec is lawful when the planning source explicitly defines a
capability/composition split. In that case a capability Spec may implement and certify:

- its own domain-owned provider ports;
- its own target/context/claim/version readers;
- role-narrow consumers against already fixed inward contracts; and
- fail-closed behavior at that inward boundary,

without owning the later production composition root.

Record this as `deferred-composition`, not as a missing upstream provider, only when all are
true:

- accepted planning authority explicitly names the later composition boundary;
- the capability Spec does not claim end-to-end production assembly or integrated proof for
  that seam;
- no sibling domain semantics are synthesized locally; and
- the later composition Spec consumes the completed capability providers and owns the actual
  production assembly/integration proof.

If the current Spec claims complete production composition, a downstream provider is a real
planning contradiction and must not be hidden as deferred composition.

## 4. Composition-owner completeness

For every deferred-composition seam, the designated composition Spec must itself contain
current planning cells that require:

- assembly of the real production providers from every required owner;
- exact propagation of typed failure/no-basis/stale outcomes;
- transaction participation where the accepted contract requires atomic revalidation; and
- integration tests using production providers rather than only fakes.

A planning repair is incomplete if it merely removes composition work from a capability Spec
without making the composition owner responsible for it.

## 5. Dependency implications

Capability Specs that only contribute providers or role-narrow consumers remain independent
when the planning source permits independence. Do not add artificial sibling dependencies
merely because their providers later compose.

The composition Spec must remain natively blocked by every open capability Spec whose
production provider it assembles. Integrated acceptance remains downstream of composition.

If accepted planning authority cannot determine whether a seam belongs to capability or
composition, fail closed to the planning/semantic owner instead of choosing an order.

## 6. Required reconciliation receipt

Before publication/readiness mutation or a `$to-tickets` handoff, report:

```text
TO-SPECS PROVIDER CLOSURE: VALID
Mixed-ownership material cells: 0
Unowned production seams: 0
Illegal downstream capability providers: 0
Deferred composition seams without composition owner: 0
Composition owners without complete provider coverage: 0
```

Any non-zero count blocks the frontier. This receipt supplements the retained execution
feasibility and cross-Spec ownership receipts; it does not replace them.
