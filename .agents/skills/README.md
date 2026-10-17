# Skills

This directory contains the agent skills used to plan, specify, decompose, implement,
verify, review, and complete Polaris work.

This README owns **cross-skill architecture and lifecycle governance**. Individual
`SKILL.md` files own bounded executable procedures. Root `AGENTS.md` supplies
repository-wide policy and supersession rules.

If these layers materially disagree, treat the disagreement as a workflow defect. Do not
pick whichever wording is convenient.

## Core Principle

Polaris interprets material semantics once and transports exact contract identity through
delivery.

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

## Authority Layers

```text
AGENTS.md
    repository-wide operating policy and supersession rules

.agents/skills/README.md
    cross-skill lifecycle architecture and ownership

.agents/skills/<skill>/SKILL.md
    bounded executable procedure

.agents/skills/<skill>/agents/openai.yaml
    discovery/invocation metadata only
```

Invocation metadata does not determine semantic authority or lifecycle ownership.

## Semantic Boundary

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

Every new or changed material semantic decision is accepted against an exact CCL proposal
hash. Accepted revisions are immutable.

### Wayfinder remains optional

`$wayfinder` orchestrates substantial planning fog, coupled semantic decisions,
cross-domain planning, research/prototyping needed for a decision, and project
partitioning.

An Independent planning source does not acquire a Wayfinder merely because it uses CCL.
One bounded unresolved semantic choice may use `$contract-ledger owner-decision`; broader
coupled work routes to `$wayfinder`.

## CCL-Backed Specs

`$to-specs` owns transition from decision-complete planning into an implementation Spec and
in-place reconciliation when governing contract state changes.

Material semantics are represented only by:

```text
OBL-* -> exact contract-id@revision#assertion-id set
```

Stable downstream planning cells are:

```text
IMP-*  private/mechanical implementation planning
TEST-* explicit proof/test planning
EXC-*  exclusions / decomposition guardrails
```

Problem Statement, Solution, User Stories, Architecture Impact explanation, and Further
Notes are human context. They do not create hidden obligations.

`$spec-contract` deterministically derives the finite `OBL/IMP/TEST/EXC` universe and cell
hashes. It does not classify arbitrary prose or infer architecture semantics.

Existing Specs are reconciled in place while preserving issue identity, source provenance,
branch/fixed baseline, ticket history, native dependencies, and review lineage.

## Ticket Decomposition

For an ordinary CCL-backed Spec, `$to-tickets` decomposes the deterministic Spec contract.
It does not rediscover architecture from ADR/wiki/code prose.

Every executable cell routes exactly once; exclusions are preserved separately in:

```text
<!-- ticket-coverage-manifest:v2 -->
```

with exact `cell + cell_hash + destination` identity.

Human approval remains the execution-slicing control point for substantive ticket changes.
Closed tickets remain immutable history. A narrative-only Spec edit that leaves contract
and cell hashes unchanged requires no semantic reslicing.

Legacy ordinary tickets without v2 coverage are reconciled directly by `$to-tickets`
against the **current exact Spec cells**. Historical ticket prose is execution context, not
semantic authority.

## Implementation Ticket Contract

For an ordinary ticket, `$implement-ticket` derives:

```text
current Spec contract
+ ticket-coverage-manifest:v2
+ ticket destination
        ↓
polaris.ticket-contract/v1
```

That contract contains exact assigned `OBL/IMP/TEST` cells, their hashes and inherited CCL
addresses, plus all parent `EXC-*` cells as guardrails.

Implementation may choose implementation-equivalent private mechanics but may not make a
missing material semantic decision. Closure checkpoint v3 binds the exact Ticket Contract
Hash and candidate state.

`$verify-ticket-closure` independently proves the frozen contract. Independence means
proof independence, not authority to broaden the ticket/Spec/CCL universe.

## Integrated Spec Verification

After all current implementation tickets are complete, `$verify-spec` owns integrated
candidate verification and repair. It rebuilds the deterministic Spec contract, validates
v2 coverage, runs applicable technical/repository checks, repairs implementation-owned
failures, stabilizes one exact candidate, and dispatches one fresh non-mutating
`$verify-spec-closure` verifier.

`$verify-spec-closure` derives independent falsifiers/evidence for every frozen cell and
bounded cross-cell composition. It may falsify implementation but may not add, remove, or
reinterpret contract cells.

## Independent Spec Review

`$review-spec` reviews the exact verified candidate through one fresh reviewer across:

```text
Standards
Spec
Architecture
```

Every reviewed Spec has exactly one conventional `Spec Review: ...` issue. That issue owns
one cumulative structured ledger:

```text
<!-- review-spec-finding-ledger:v2 -->
polaris.review-findings/v2
```

Stable `RF-*` findings carry exact current cell hashes when applicable, exact Standards
references, and one frozen falsifier. Reviewer silence never erases an open finding.

Finding ownership is bounded:

```text
implementation/test/standards defect -> review remediation through $to-tickets
cell-routing defect                  -> $to-tickets
contract/planning gap                -> $to-specs / semantic owner
new material semantic choice         -> $contract-ledger / governing $wayfinder
```

A prior verification PASS never suppresses a concrete current falsifier.

### Review remediation

Open Blocking implementation/test/standards findings are the finite remediation
denominator. `$to-tickets` may group several findings for coherent execution, but grouping
creates no new invariant or semantic domain.

Each group compiles deterministically to:

```text
current Spec contract
+ exact review-findings/v2 rows
        ↓
polaris.review-remediation-contract/v1
```

The contract contains selected finding hashes/falsifiers, exact affected current cells,
exact Standards refs, and every other current Spec cell as a preservation guardrail.

Historical Root Blocker state is migration evidence only. It is not current semantic,
remediation, ticketing, or verification authority.

`$implement-ticket` and `$verify-ticket-closure` consume the exact remediation contract in
the same implementation/independent-proof lifecycle as ordinary tickets.

## Review Exit and Spec Completion

Review PASS requires a current verification receipt, valid deterministic Spec contract,
valid v2 ticket coverage, valid v2 finding ledger, complete reviewer coverage, and zero
open Blocking/routing/contract-planning findings.

The Spec Review Exit Receipt binds the exact reviewed candidate and exact v2 finding-ledger
hash. It contains no historical Root Blocker transport fields.

`$spec-merge-cleanup` consumes that v2 state directly. It owns:

* pre-completion versus post-completion recovery detection;
* branch-backed merge or branchless direct close;
* idempotent/fail-closed branch cleanup;
* closing the conventional Spec Review;
* governing Wayfinder completion reconciliation;
* project-delivery reconciliation;
* one final authoritative Project reconstruction/projection attempt.

Project failure after authoritative completion is reported as `PROJECT TRACKING: DRIFT` and
never rolls lifecycle state backward.

## Architecture / Contract Escalation

Downstream work never repairs missing material semantics by interpretation.

```text
semantics already fixed but unregistered
    -> $contract-ledger existing-authority

one bounded Independent decision
    -> $contract-ledger owner-decision

Wayfinder-governed or coupled decision
    -> governing $wayfinder / semantic decision domain

CCL source conflict
    -> exact governing semantic owner; no local choice
```

`$architecture-remediation` remains the routing/disposition owner for genuine downstream
architecture blockers. It does not become a second semantic compiler.

## Project Delivery Management

`$project-delivery-management` coordinates intentional delivery WIP across independent
Wayfinder lineages without replacing lifecycle owners.

> **Dependency determines what may proceed. Focus determines what Polaris chooses to
> proceed with now.**

Native `blocked by` relationships remain execution-dependency truth. Independent Specs
remain outside Wayfinder focus. Project focus never becomes a synthetic dependency.

## GitHub Project Tracking

The GitHub Project is an eventually consistent operational projection, not workflow
authority.

Routine lifecycle transitions may leave Project projection stale. Authorized projection
boundaries are Spec completion through `$spec-merge-cleanup`, explicit human-requested
reconciliation, and separately authorized bootstrap/migration.

Do not create projection-debt registries. Project drift never rewrites semantic workflow
state.

## Complete Delivery Lifecycle

```text
Ideas / Intake
    ↓ HUMAN promotion when formal planning is needed
$wayfinder OR bounded Independent semantic path
    ↓ decision-complete CCL
$to-specs
    ↓ CCL-backed Spec
$to-tickets
    ↓ HUMAN-approved deterministic ticket decomposition
$implement-ticket
    ↺ HUMAN selects next frontier ticket while tickets remain
    ↓ all current implementation tickets complete
$verify-spec
    ↺ repair implementation-owned failures
    ├─ cell-routing defect -> HUMAN -> $to-tickets
    ├─ contract/planning gap -> HUMAN -> semantic owner / $to-specs
    └─ PASS receipt
           ↓ HUMAN
$review-spec
    ├─ remediation-owned Blocking RF findings
    │      -> HUMAN -> $to-tickets -> $implement-ticket -> $verify-spec -> $review-spec
    ├─ cell-routing defect
    │      -> HUMAN -> $to-tickets
    ├─ contract/planning gap
    │      -> HUMAN -> $to-specs / semantic owner
    └─ PASS Exit Receipt
           ↓ HUMAN
$spec-merge-cleanup
    ↓ merge/close, cleanup, Wayfinder reconciliation, final Project projection
```

## Workflow Change Control

Product delivery normally takes priority over workflow refinement. Workflow architecture
changes require explicit human authorization, including changes to semantic authority,
lifecycle stages, verifier/reviewer independence, mandatory durable artifacts,
decomposition ownership, or remediation ownership.

Do not use an authorization for one workflow redesign as permission for unrelated product
or workflow changes.
