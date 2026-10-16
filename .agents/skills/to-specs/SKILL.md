---
name: to-specs
description: Project decision-complete planning into implementation Specs from exact Canonical Contract Ledger semantics while preserving Independent Specs and existing Spec identity.
disable-model-invocation: true
---

# To Specs

`$to-specs` owns the transition from decision-complete planning into implementation
specification.

Its job is **projection and partition**, not semantic design:

```text
planning source + CCL
        ↓
implementation Spec(s)
```

Material product/domain/architecture/public/persistence/temporal/authority/failure
semantics come from exact Canonical Contract Ledger (CCL) assertions. `$to-specs`
does not reconstruct those semantics from Decision Analysis, ADR prose, existing Spec
prose, implementation precedent, or another agent's interpretation.

`$to-specs` also owns in-place semantic reconciliation of existing Wayfinder-managed
Specs. `$to-remediation-specs` remains temporarily as a **mechanical recovery/provenance
helper only** so older cross-skill wiring stays compatible during migration; it may not
interpret or amend Spec semantics.

## Session Independence

Assume no prior conversational state. Recover correctness-critical inputs from the
invocation, repository, CCL, and durable tracker artifacts. Chat summaries are context
only.

If required durable state cannot be recovered, stop rather than infer it.

## Governance

Resolve the planning source first.

### Wayfinder source

A Wayfinder-managed invocation consumes the map, its durable Spec handoffs, and the
accepted CCL transaction references recorded by the governing decisions.

Before tracker mutation:

1. invoke `$project-delivery-management reconcile`;
2. invoke `$project-delivery-management guard <Wayfinder>`;
3. require exact `PROJECT DELIVERY GUARD: ALLOWED`.

Do not reconstruct focus manually or establish/switch focus inside `$to-specs`.

A Wayfinder map is specification-ready only when its current route-clear state proves
that every material destination semantic obligation is represented by accepted CCL
assertions or is explicitly implementation-equivalent/private, deferred, or out of
scope.

### Independent source

An intentionally non-Wayfinder planning source remains Independent. Do not invent a
Wayfinder merely because `$to-specs` was invoked.

For each material semantic obligation required by the source:

* if an exact active CCL assertion already represents it, consume that assertion;
* if current durable governing/constraint authority already determines it exactly but
  it is not yet registered, invoke `$contract-ledger existing-authority` as internal
  composition and consume the resulting exact CCL address;
* if one bounded independent semantic coupling group remains unresolved, stop with a
  Human Handoff to `$contract-ledger owner-decision` against the durable planning
  artifact;
* if resolution requires multiple/coupled decision groups, cross-domain planning,
  research/prototyping, or project partition decisions, stop and route to `$wayfinder`.

`$to-specs` never chooses the missing semantic answer.

## CCL Projection Contract

Every software Spec that contains material semantics carries exactly one machine-managed
manifest comment:

```text
<!-- spec-contract-ccl:v1
{
  "schema": "polaris.spec-ccl/v1",
  "obligations": [
    {
      "obligation_id": "OBL-001",
      "source_ref": "<durable planning-source anchor>",
      "ccl": [
        "<contract-id>@<revision>#<assertion-id>"
      ]
    }
  ]
}
-->
```

Rules:

* `obligation_id` is stable inside the Spec once published;
* every material Spec obligation references one or more exact CCL assertions;
* one CCL assertion may support several Spec obligations when the planning partition
  genuinely uses the same semantic contract;
* the manifest contains provenance/mapping only; it does not restate semantic meaning;
* material semantics not reachable through an exact manifest CCL address are not part
  of an implementation-ready Spec contract.

Generate and validate the exact human-readable semantic section with:

```bash
python -m scripts.ccl_spec render <manifest.json> contracts/ccl/transactions
python -m scripts.ccl_spec check <spec-body.txt> contracts/ccl/transactions
```

The generated section is titled:

```markdown
## Canonical Contract Obligations
```

and is the Spec's authoritative material-semantic projection. It renders the typed CCL
assertions exactly enough for humans and not-yet-migrated downstream tooling to inspect
them without reparsing upstream prose.

Other Spec prose may explain the problem, user outcome, implementation plan, testing
strategy, and scope. It may refer to `OBL-*` identities, but it must not strengthen,
weaken, close, enumerate, or otherwise reinterpret the material semantics represented
by the generated CCL projection.

If explanatory prose reveals that another material semantic assertion is actually
required, add an exact CCL assertion through the owning semantic workflow first; do not
make the prose authoritative.

## Planning Source Partition

Build one working partition over the complete current planning source before creating or
amending Specs.

For each distinct planning item record:

```text
Planning item: PI-<n>
Source: <durable decision/destination/request anchor>
Disposition:
  material-contract
  implementation-equivalent
  deferred-semantic-decision
  already-represented
  out-of-scope
Spec: <candidate/existing Spec | None>
CCL: <exact assertion address set | None>
Reason: <compact routing/partition reason>
```

Enforcement:

* every material-contract item has a non-empty exact CCL set;
* implementation-equivalent means plausible private implementation choices cannot
  change public/product/domain/architecture/persistence/temporal/authority/failure or
  downstream semantics;
* deferred-semantic-decision remains upstream work and blocks publication only for the
  affected scope;
* already-represented names the exact existing Spec obligation;
* out-of-scope requires durable planning-source authority;
* omission is not a disposition.

This partition replaces the former Spec Material Contract Matrix, reverse normative
claim audit, and independent semantic design-readiness verifier. Do not recreate those
systems under new names.

Before publication require:

```text
Planning-source items: <n>
Partition rows: <same n>
Unclassified items: 0
Material-contract rows without CCL: 0
Specifiable items without a Spec candidate: 0
```

Invoke `$attention` after the partition and candidate Specs are complete but before
publication. Attention may surface a real missing planning item or CCL gap; it does not
create semantic authority.

## Spec Set and Existing-Spec Reconciliation

Publish the complete currently specifiable set. Do not serialize Spec creation merely
because one Spec depends on another.

### Recover existing Wayfinder handoffs

For a Wayfinder source with existing handoffs, invoke `$to-remediation-specs` only to
recover/reconcile the handed-off Spec identities and source/remediation markers. Admit
its returned identity/provenance set, then perform all semantic reconciliation in this
parent workflow. The helper must not classify CCL meaning, compute semantic deltas, or
amend a Spec body.

Reconcile both forward and Spec-local provenance for:

* **Derived Spec** — Spec created from this Wayfinder; and
* **Remediation Spec** — existing Spec whose original planning provenance is preserved
  while this Wayfinder supplies later governing semantics.

Keep the existing markers:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
<!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision> -->
```

and map body handoffs:

```markdown
## Spec Handoff
**Derived Spec:** #<spec>
**Remediation Spec:** #<spec>
```

Reverse evidence may repair an unambiguous missing handoff link, but never change a
Derived Spec into a Remediation Spec or replace original source provenance.

### Reconcile in place

For every in-progress handed-off Spec, compute the **desired** planning partition,
`spec-contract-ccl:v1` manifest, generated Canonical Contract Obligations section, and
non-semantic planning text from current durable state.

Then:

* if current and desired projection are identical, leave the Spec unchanged;
* if they differ, amend the existing Spec issue in place;
* preserve issue identity, source/remediation provenance, branch, fixed baseline,
  existing tickets, review lineage, and native dependency edges;
* do not create a replacement Spec merely because CCL revisions changed;
* closed historical tickets remain history; `$to-tickets` later reconciles executable
  decomposition against the amended Spec.

Exact `contract@revision#assertion` addresses are the semantic consumption identity.
Legacy `wayfinder-decision-states:v1` markers may be preserved as historical provenance
but are no longer created, advanced, or consulted to decide semantic synchronization.

### Legacy Spec migration

An in-progress software Spec without `spec-contract-ccl:v1` is a legacy projection.
Migrate it in place when its planning source is otherwise ready:

1. derive the desired material obligations only from current accepted CCL;
2. generate the canonical CCL section;
3. retain planning/implementation/testing prose only as explanatory/private-mechanics
   text tied to `OBL-*` identities;
4. do not carry forward a material semantic claim that has no exact CCL address;
5. if such a claim is still required by the durable planning source, stop and route the
   missing semantic decision upstream;
6. if the claim was accidental unsupported specificity not required by the planning
   source, remove it rather than inventing a replacement taxonomy/cardinality/type.

This is projection repair, not an architecture decision.

If a durable `architecture-blocker:v1` exists solely because a downstream workflow
interpreted now-removed unsupported Spec specificity as missing architecture, record the
same blocker as resolved by CCL projection repair with the exact controlling CCL
addresses. Do not mark a genuine unresolved semantic question resolved this way.

## Concrete Implementability

After CCL projection, inspect only enough current code to ensure the Spec can be realized
without another material semantic decision.

A missing class, method, migration, query, repository call, DI binding, local algorithm,
or equivalent wiring is implementation work when CCL already fixes all material
semantics.

If realization still requires choosing a material semantic contract absent from CCL,
stop and route that exact gap to the semantic owner. Do not add another design matrix or
semantic verifier.

## Spec Body

Use this structure for software Specs:

```markdown
<governance/provenance markers>
<spec-contract-ccl:v1 manifest>

## Problem Statement

<user/problem framing; explanatory, not a stronger semantic contract>

## Solution

<solution framing referencing OBL-* where material behavior matters>

## User Stories

1. As a <user>, I want <outcome under OBL-*>, so that <value>.

## Architecture Impact

- Affected entities: <...>
- Impact: none | conforming | extending | changing | retiring
- Governing CCL: <contract@revision list>
- Unresolved material semantic questions: none
- Implementation readiness: pass

## Canonical Contract Obligations

<generated by scripts.ccl_spec; do not hand-edit>

## Implementation Decisions

<private/mechanical plan and module/interface responsibilities. Refer to OBL-* for
material behavior. Do not create new material semantics.>

## Testing Decisions

<external-behavior tests proving OBL-* plus implementation-equivalent test mechanics>

## Out of Scope

- <one materially independent exclusion per bullet>

## Further Notes

<non-authoritative context>
```

Do not include specific implementation file paths or working code snippets unless a
prototype snippet is itself the already-authorized compact representation of a private
mechanic. Material semantics always remain in CCL.

A non-software Spec that genuinely has no material software contract may omit the CCL
manifest/section. Do not use that exception for a software Spec merely because the
semantics are inconvenient to register.

## Dependencies and Frontier

After publishing/amending the complete Spec set, establish every known native Spec
prerequisite before any `$to-tickets` handoff.

A Spec dependency means the consumer may not advance until the blocker Spec completes
its authoritative lifecycle.

Ownership:

* same-lineage Wayfinder-managed Spec relationship — `$to-specs` owns semantics and
  invokes `$github-issue-dependencies` for the native edge;
* cross-Wayfinder relationship — delegate semantic validation/mutation to
  `$project-delivery-management dependency ensure`;
* when either endpoint is Independent — `$to-specs` validates the exact narrow Spec
  prerequisite and cycle safety, then invokes `$github-issue-dependencies`.

Never use Project fields, publication order, priority, or handoff order as dependency
truth. Reject self-dependency, incomplete blocker graphs, and cycles.

The **Spec dependency frontier** is every open handled Spec with zero open native blockers
and a valid current CCL projection (`python -m scripts.ccl_spec check` for software
Specs).

For each Wayfinder-managed frontier Spec, invoke project-delivery reconciliation and
`guard` for every current Spec-local governing Wayfinder. It is actionable when at least
one governor returns exact `PROJECT DELIVERY GUARD: ALLOWED`.

Independent frontier Specs are actionable without Wayfinder focus.

Do not persist a separate active-Spec queue/frontier artifact.

## Wayfinder Lifecycle Consequence

After Wayfinder Spec publication/reconciliation, re-read its complete Derived/Remediation
Spec handoff set.

If at least one governed Spec remains open, downstream execution is in **Spec Delivery**.
The GitHub Project is eventually consistent and is not synchronized here unless the human
explicitly requested a board refresh.

## Human Handoff

Emit one line for each actionable Spec:

```text
$to-tickets - <Spec Title> (<Spec URL>)
```

If none are actionable, report each exact blocker/unfocused reason and stop.

Never invoke `$to-tickets` implicitly.

## Fail-Closed Routing

Use the smallest owner:

* missing exact CCL registration but semantics already fixed by current authority ->
  internal `$contract-ledger existing-authority`;
* one bounded unresolved semantic choice for Independent planning -> Human Handoff to
  `$contract-ledger owner-decision`;
* coupled/multi-domain unresolved planning -> `$wayfinder`;
* Wayfinder-managed missing/changed semantic decision -> governing `$wayfinder` decision;
* genuine downstream architecture blocker on an existing Independent Spec ->
  `$architecture-remediation` under its Independent mode;
* CCL source conflict -> governing semantic decision owner; never choose locally.

A projection defect in an existing Spec stays with `$to-specs`; it is not architecture
remediation.

## Non-Goals

`$to-specs` does not:

* infer material semantics from prose when an exact CCL assertion is absent;
* independently certify/reinterpret CCL through a second semantic model;
* maintain decision-state hashes as a parallel semantic identity;
* delegate material design to implementation;
* create implementation tickets;
* create a Wayfinder for decision-complete Independent work;
* replace an existing Spec when in-place reconciliation is possible.
