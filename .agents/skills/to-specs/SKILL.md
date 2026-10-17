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

Invoke `$attention` before publication. Attention may identify a missing planning item or
CCL gap; it does not create authority.

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

The frontier is every open handled Spec with zero open native blockers and a valid current
CCL projection. Wayfinder-managed frontier Specs additionally require an ALLOWED current
governor guard.

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
* projection defect → `$to-specs` itself.

`$to-specs` never infers material semantics from prose, runs a second semantic certifier,
delegates material design to implementation, creates implementation tickets, or replaces
an existing open Spec when ordinary reconciliation can preserve its identity.
