# Skills

This directory contains the agent skills used to plan, specify, decompose, implement,
verify, review, and complete Polaris work.

This README owns cross-skill lifecycle architecture. Individual `SKILL.md` files own their
bounded procedures. Root `AGENTS.md` supplies repository-wide policy.

If those layers materially disagree, treat it as a workflow defect.

## Core principle

Polaris interprets material semantics once and transports exact contract identity through
delivery:

```text
requirements / current authority
          ↓
semantic decision boundary
          ↓
Canonical Contract Ledger (CCL)
          ↓
$to-specs
          ↓
OBL / IMP / TEST / EXC Spec contract
          ↓
$to-tickets
          ↓
implementation
          ↓
verification / review against the same frozen contract
```

Natural-language reasoning, ADR rationale, Spec explanation, ticket prose, implementation
shape, verification findings, and review findings may explain or falsify the contract.
They do not silently redefine it.

## Semantic boundary

### `$contract-ledger`

`$contract-ledger` is the sole CCL transaction writer. It owns schema/integrity, stable
contract IDs, immutable revisions, proposal hashes, provenance/acceptance binding,
admission/persistence, and exact lookup.

It does not independently invent product or architecture decisions.

CCL provenance modes are:

```text
existing-authority
owner-decision
wayfinder-decision
```

Every new or changed material semantic decision binds acceptance to an exact proposal hash.
Accepted revisions are immutable.

### Wayfinder remains optional

`$wayfinder` orchestrates substantial planning fog, coupled semantic decisions,
cross-domain planning, research/prototyping needed for a decision, and project partitioning.

An Independent source does not acquire a Wayfinder merely because it uses CCL. One bounded
unresolved semantic choice may use `$contract-ledger owner-decision`; broader coupled work
routes to `$wayfinder`.

## CCL-backed Specs

`$to-specs` owns transition from decision-complete planning into implementation Specs and
ordinary in-place reconciliation while a Spec remains open.

For each desired Spec identity:

```text
missing current Spec       -> create
open + same projection     -> no-op
open + changed projection  -> amend same Spec
completed Spec             -> immutable history
ambiguous identity         -> fail closed
```

That reconciliation rule is permanent lifecycle behavior, not a conversion mechanism.

Material semantics are represented only by:

```text
OBL-* -> exact contract-id@revision#assertion-id set
```

Stable downstream planning cells are:

```text
IMP-*  private/mechanical implementation planning
TEST-* proof/test planning
EXC-*  exclusions / decomposition guardrails
```

Narrative Spec sections are human context and create no hidden obligations.

`$spec-contract` deterministically derives exactly one `polaris.spec-contract/v1` containing
`spec_body_hash`, `spec_contract_hash`, and the ordered `cells` array. It emits no
source-unit or semantic-classification compatibility representation.

## Ticket decomposition

`$to-tickets` decomposes the current deterministic Spec contract. It does not rediscover
architecture from ADR/wiki/code prose.

Every executable cell routes exactly once; exclusions are preserved separately in:

```text
polaris.ticket-coverage/v2
```

Human approval remains the execution-slicing control point. Closed tickets are immutable
history. Current ticket state is reconciled only from current deterministic coverage and
current open ticket identities.

## Implementation ticket contract

For an ordinary ticket, `$implement-ticket` derives:

```text
current Spec contract
+ ticket-coverage-manifest:v2
+ ticket destination
        ↓
polaris.ticket-contract/v1
```

It contains exact assigned `OBL/IMP/TEST` cells plus all parent `EXC-*` guardrails.
Implementation may choose implementation-equivalent private mechanics but may not make a
missing material semantic decision.

Current closure state is `implement-ticket-closure-checkpoint:v3`. No other checkpoint
schema is current closure authority.

`$verify-ticket-closure` independently proves the frozen contract. Independence means proof
independence, not authority to broaden ticket/Spec/CCL meaning.

## Integrated Spec verification

After all current implementation tickets are complete, `$verify-spec` rebuilds the current
deterministic Spec contract, validates v2 coverage, runs applicable technical checks,
repairs implementation-owned failures, stabilizes one exact candidate, and dispatches one
fresh non-mutating `$verify-spec-closure` verifier.

`$verify-spec-closure` may falsify implementation but may not add/remove/reinterpret
contract cells.

## Independent Spec review

`$review-spec` reviews the exact verified candidate across Standards, Spec, and Architecture
using the same frozen cell universe.

Every reviewed Spec has one conventional `Spec Review: ...` issue owning one current:

```text
review-spec-finding-ledger:v2
polaris.review-findings/v2
```

Stable `RF-*` findings carry exact current cell hashes when applicable, exact Standards
references, and one frozen falsifier. Reviewer silence never erases an open finding.

Finding ownership:

```text
implementation/test/standards defect -> review remediation through $to-tickets
cell-routing defect                  -> $to-tickets
contract/planning gap                -> $to-specs / semantic owner
new material semantic choice         -> $contract-ledger / governing $wayfinder
```

### Review remediation

Open Blocking implementation/test/standards findings are the finite remediation
denominator. `$to-tickets` may group several for coherent execution, but grouping creates no
new invariant or semantic domain.

Each group compiles to:

```text
current Spec contract
+ exact review-findings/v2 rows
        ↓
polaris.review-remediation-contract/v1
```

The contract contains selected finding hashes/falsifiers, exact affected cells, exact
Standards refs, and every other current Spec cell as a preservation guardrail.

## Review exit and Spec completion

Review PASS requires current verification, valid deterministic Spec contract, valid v2
ticket coverage, valid v2 finding ledger, complete reviewer coverage, and zero open
Blocking/routing/contract-planning findings.

The Exit Receipt binds the exact reviewed candidate and exact v2 finding-ledger hash.

`$spec-merge-cleanup` owns authoritative Spec completion, idempotent/fail-closed cleanup,
closing the conventional Spec Review, governing Wayfinder completion reconciliation,
project-delivery reconciliation, and one final authoritative Project reconstruction attempt.

Project failure after authoritative completion is `PROJECT TRACKING: DRIFT`; it never rolls
lifecycle truth backward.

## Architecture / contract escalation

Downstream work never repairs missing material semantics by interpretation:

```text
semantics fixed but unregistered
    -> $contract-ledger existing-authority

one bounded Independent decision
    -> $contract-ledger owner-decision

Wayfinder-governed or coupled decision
    -> governing $wayfinder

CCL source conflict
    -> exact governing semantic owner; no local choice
```

`$architecture-remediation` is a routing/disposition owner. It does not maintain a second
semantic decision state machine.

## Project delivery management

`$project-delivery-management` coordinates intentional delivery WIP without replacing
lifecycle owners.

> Dependency determines what may proceed. Focus determines what Polaris chooses to proceed
> with now.

Native `blocked by` relationships remain dependency truth. Independent Specs remain outside
Wayfinder focus. Focus never becomes a synthetic dependency.

## GitHub Project tracking

The GitHub Project is an eventually consistent operational projection, not workflow
authority.

Routine lifecycle transitions may leave Project projection stale. Authorized projection
boundaries are Spec completion through `$spec-merge-cleanup`, explicit human-requested
reconciliation, and separately authorized administrative reconstruction.

Do not create projection-debt registries. Project drift never rewrites semantic workflow
state.

## Complete delivery lifecycle

```text
Ideas / Intake
    ↓ HUMAN promotion when formal planning is needed
$wayfinder OR bounded Independent semantic path
    ↓ accepted CCL
$to-specs
    ↓ CCL-backed Spec
$to-tickets
    ↓ HUMAN-approved deterministic ticket decomposition
$implement-ticket
    ↺ HUMAN selects next frontier ticket while tickets remain
    ↓ all current implementation tickets complete
$verify-spec
    ↓ PASS receipt
$review-spec
    ├─ remediation-owned Blocking RF findings
    │      -> HUMAN -> $to-tickets -> $implement-ticket -> $verify-spec -> $review-spec
    ├─ cell-routing defect -> HUMAN -> $to-tickets
    ├─ contract/planning gap -> HUMAN -> $to-specs / semantic owner
    └─ PASS Exit Receipt
           ↓ HUMAN
$spec-merge-cleanup
    ↓ merge/close, cleanup, Wayfinder reconciliation, final Project projection
```

## Workflow change control

Workflow architecture changes require explicit human authorization, including semantic
authority, lifecycle stages, verifier/reviewer independence, durable governance artifacts,
decomposition ownership, or remediation ownership.

Do not embed one-time repository transition procedures in permanent skills. Repository
transition work is executed out of band against the permanent lifecycle contracts.
