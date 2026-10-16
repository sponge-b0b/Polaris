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
Specs. `$to-remediation-specs` remains temporarily as a mechanical recovery/provenance
helper only; it may not interpret or amend Spec semantics.

## Session independence

Recover correctness-critical inputs from the invocation, repository, CCL, and durable
tracker state. Chat/session memory is never authority.

## Governance

### Wayfinder source

Treat the map and its accepted CCL-backed decisions as the planning source.

Before tracker mutation:

1. invoke `$project-delivery-management reconcile`;
2. invoke `guard <Wayfinder>`;
3. require exact `PROJECT DELIVERY GUARD: ALLOWED`.

Do not infer or change project focus inside `$to-specs`.

A Wayfinder is specification-ready only when route clarity proves every material
destination semantic obligation is represented by accepted CCL assertions or is
explicitly implementation-equivalent/private, deferred, or out of scope.

### Independent source

An intentionally non-Wayfinder planning source remains Independent. Do not invent a
Wayfinder merely because `$to-specs` was invoked.

For each material semantic obligation:

* exact active CCL assertion exists → consume it;
* current durable governing/constraint authority already fixes the meaning exactly but
  it is not registered → invoke `$contract-ledger existing-authority` internally;
* exactly one bounded independent semantic coupling group remains unresolved → Human
  Handoff to `$contract-ledger owner-decision` against the durable planning artifact;
* multiple/coupled decision groups, cross-domain planning, research/prototyping, or
  project partition decisions remain → route to `$wayfinder`.

`$to-specs` never chooses the missing semantic answer.

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
* every material Spec obligation references one or more exact CCL assertions;
* the manifest contains mapping/provenance only, never a second semantic definition;
* material semantics not reachable through an exact CCL address are not part of an
  implementation-ready Spec.

Generate and validate the human-readable semantic section with:

```bash
python -m scripts.ccl_spec render <manifest.json> contracts/ccl/transactions
python -m scripts.ccl_spec check <spec-body.txt> contracts/ccl/transactions
```

The generated section is `## Canonical Contract Obligations` and is the authoritative
human-readable projection of material semantics. Do not hand-edit it.

Other Spec prose may explain user outcome, implementation plan, testing strategy, and
scope, but it must not strengthen, weaken, enumerate, close, or reinterpret CCL.

## Stable downstream planning cells

Ticketing consumes three additional stable-ID families directly from controlled Spec
sections:

* `IMP-*` — private/mechanical implementation obligations;
* `TEST-*` — explicit external-behavior/proof obligations;
* `EXC-*` — exclusions constraining decomposition but never implementation work.

These IDs are planning identities, not semantic authority. Their exact text is
mechanically hashed by `$spec-contract`; intentionally changing one changes the
planning/decomposition contract without creating CCL semantics.

Problem/Solution prose, User Stories, Architecture Impact explanation, and Further Notes
are human-readable context. They do not become ticket cells merely because they contain
normative-sounding language.

If explanatory prose reveals that another material semantic assertion is actually
required, establish that assertion through the owning semantic workflow before
publication.

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

Enforcement:

* every `material-contract` row has a non-empty exact CCL set;
* `implementation-equivalent` is legal only when remaining private choices cannot change
  public/product/domain/architecture/persistence/temporal/authority/failure/downstream
  semantics;
* `deferred-semantic-decision` remains upstream and blocks only affected scope;
* `already-represented` names the exact existing `OBL-*`/Spec;
* `out-of-scope` requires durable source authority;
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

Invoke `$attention` after candidate completion and before publication. Attention may
surface a missing planning item or CCL gap; it does not create authority.

## Existing Wayfinder handoffs

When a Wayfinder already has in-progress Derived/Remediation Specs, invoke
`$to-remediation-specs` only to recover/reconcile exact Spec identities and provenance
markers. Admit that mechanical result, then perform all semantic/body reconciliation here.

Preserve:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
<!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision> -->
```

and map `## Spec Handoff` metadata. Never change Derived ↔ Remediation roles or replace
original source provenance.

For each in-progress handed-off Spec compute the desired current partition, CCL manifest,
Canonical Contract Obligations section, and stable planning cells. If current and desired
projection differ, amend the same issue in place while preserving issue identity, branch,
fixed baseline, tickets, review lineage, and native dependencies.

Exact `contract@revision#assertion` addresses are semantic consumption identity. Legacy
`wayfinder-decision-states:v1` markers may remain as historical provenance but are no
longer created or consulted for synchronization.

### Legacy Spec migration

An in-progress software Spec without `spec-contract-ccl:v1` is a legacy projection.
Migrate it in place when its planning source is otherwise ready:

1. derive material obligations only from current accepted CCL;
2. generate the canonical CCL section;
3. assign stable `IMP-*`, `TEST-*`, and `EXC-*` cells;
4. retain narrative prose only as explanation;
5. remove accidental unsupported specificity not required by planning authority;
6. if missing semantics are genuinely required, stop and route them upstream.

Projection repair is not architecture remediation.

## Concrete implementability

Inspect only enough current code to establish that the projected contract can be
realized without another material semantic decision.

Missing classes, methods, migrations, queries, repository calls, DI bindings, local
algorithms, or equivalent wiring are implementation work when CCL already fixes material
semantics.

If realization requires a material semantic choice absent from CCL, route that exact gap
to its semantic owner. Do not create another design matrix or semantic verifier.

## Software Spec body

Use:

```markdown
<governance/provenance markers>
<spec-contract-ccl:v1 manifest>

## Problem Statement
<explanation>

## Solution
<outcome framing referencing OBL-* where needed>

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
- `IMP-001` — <one private/mechanical implementation obligation>

## Testing Decisions
- `TEST-001` — <one external-behavior/proof obligation>

## Out of Scope
- `EXC-001` — <one independent exclusion>

## Further Notes
<non-authoritative context>
```

For each of the three stable planning sections, use one independently routable item per
bullet. If a section has no items, write exactly `None.`. Never place material semantics
into `IMP-*` or `TEST-*` to avoid creating a CCL assertion.

A non-software Spec with no material software contract may omit the CCL machinery; do
not use that exception for software work.

## Dependencies and frontier

After publishing/amending the complete currently specifiable set, establish every known
native Spec prerequisite before any `$to-tickets` handoff.

Ownership remains:

* same-lineage Wayfinder-managed relationship → `$to-specs` + native dependency helper;
* cross-Wayfinder relationship → `$project-delivery-management dependency ensure`;
* either endpoint Independent → `$to-specs` validates the exact narrow prerequisite and
  cycle safety, then uses the native dependency helper.

Never use Project fields, publication order, priority, or handoff order as dependency
truth. Reject self-dependency, incomplete blocker graphs, and cycles.

The Spec dependency frontier is every open handled Spec with zero open native blockers
and a valid current CCL projection. Wayfinder-managed frontier Specs additionally require
at least one current governing Wayfinder guard `ALLOWED`; Independent Specs do not.

## Wayfinder lifecycle consequence

If at least one governed Spec remains open after publication/reconciliation, the map is
in Spec Delivery. Routine `$to-specs` work does not synchronize the GitHub Project.

## Human handoff

Emit one line per actionable Spec:

```text
$to-tickets - <Spec Title> (<Spec URL>)
```

If none are actionable, report each exact blocker/unfocused reason. Never invoke
`$to-tickets` implicitly.

## Fail-closed routing

* semantics fixed but not registered → internal `$contract-ledger existing-authority`;
* one bounded Independent semantic choice → `$contract-ledger owner-decision`;
* coupled/multi-domain planning → `$wayfinder`;
* Wayfinder-managed changed semantic decision → governing Wayfinder decision;
* genuine downstream architecture blocker on Independent work → `$architecture-remediation`;
* CCL source conflict → governing semantic decision owner;
* projection defect → `$to-specs` itself.

`$to-specs` never infers material semantics from prose, runs a second semantic certifier
over CCL, delegates material design to implementation, creates implementation tickets,
or replaces an existing Spec when in-place reconciliation is possible.
