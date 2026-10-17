---
name: verify-ticket-closure
description: Independently certify whether one exact immutable candidate satisfies its frozen deterministic ticket contract; never redefine the ticket, Spec, or CCL universe.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Ticket Closure

`$verify-ticket-closure` is the fresh non-mutating closure certifier dispatched by
`$implement-ticket`.

Its independence is **proof independence**:

```text
frozen ticket contract
        ↓
independent falsifiers/evidence
        ↓
TICKET CLOSURE: PASS | FAIL
```

It has no authority to reinterpret prose or broaden the contract.

## 1. Invocation integrity

Execute certification only in a genuinely fresh, non-mutating, non-delegating verifier
context dispatched from one exact v3 closure checkpoint.

Receive and bind:

* ticket + parent Spec identity;
* mode: ordinary | remediation;
* branch + immutable Ticket baseline;
* exact `TICKET_CLOSURE_STATE`;
* exact `polaris.ticket-contract/v1` and Ticket Contract Hash;
* parent Spec Contract Hash and current coverage identity;
* Implementation Evidence Index;
* terminal technical-check evidence;
* prior unresolved verifier findings on retry;
* exact `polaris.review-remediation-contract/v1` when mode is remediation.

Recompute/read enough durable state to ensure these identities are still exact. Candidate
mutation, contract/coverage mutation, verifier mutation/delegation, or ambiguous durable
state invalidates the run. Return invalid verification; emit neither PASS nor FAIL.

Direct human invocation is recovery entry only. Recover `$implement-ticket`'s durable v3
checkpoint and resume its recorded dispatcher/persistence state; the top-level
implementation actor may not certify its own candidate.

## 2. Frozen contract boundary

For an ordinary ticket the complete closure contract is exactly:

```text
assigned_cells
    OBL-* exact CCL assertions
    IMP-* exact private/mechanical requirement
    TEST-* exact proof/test requirement

exclusion_guardrails
    every current parent EXC-* cell
```

Do not:

* add/remove a cell;
* derive hidden obligations from Problem/Solution/User Story/ticket prose;
* build Source Unit or `ARCHSRC-*` inventories;
* reopen ADR/wiki/Decision prose to reinterpret an `OBL-*`;
* use implementation shape to infer what the contract "must have meant";
* transform an optional/open CCL assertion into required/closed semantics.

The current parent coverage must still route every assigned executable cell to this ticket
with matching `cell_hash`, and the current published ticket body must still validate
against the deterministic ticket contract. A mismatch is `cell-routing-defect`, not an
invitation to guess intended scope.

### Review remediation contract

For a current Review Remediation Ticket, the complete closure contract is the exact
`polaris.review-remediation-contract/v1` supplied by `$implement-ticket`.

It contains:

* the exact current parent Spec Contract Hash;
* selected open Blocking `RF-*` findings;
* each finding's immutable `finding_hash` and frozen falsifier;
* exact current affected Spec cells/hashes;
* applicable Standards references;
* every other current parent-Spec cell as a preservation guardrail.

Do not synthesize a Root Blocker, broaden a finding into a sibling/domain invariant, or
mine prior review prose for additional obligations.

For each selected finding, independently prove that its exact falsifier is no longer true
on the candidate and that any explicit Standards reference is satisfied.

For each preservation guardrail, determine whether the candidate can materially affect
that cell:

* yes -> prove the current cell remains satisfied;
* no -> `not-applicable` with concrete candidate evidence.

A finding classified `cell-routing-defect`, `planning-cell-gap`, or
`contract-authority-gap` is not review-remediation owned and must never be certified as a
remediation ticket contract.

## 3. Per-cell independent proof

For every assigned cell record concise auditable proof state:

```text
Cell: <ID>
Cell hash: <hash>
Predicate: <exact frozen requirement>
Falsifier: <concrete state that makes it false>
Evidence: <current candidate evidence>
State: proven | violated | unproven | not-applicable
```

This is result evidence, not private reasoning.

### OBL-* cells

Load only the exact typed CCL assertions named by the cell. Preserve their exact strength,
cardinality, vocabulary openness/closure, persistence, temporal, authority, relationship,
and negative-boundary semantics.

Derive implementation/runtime falsifiers from those typed semantics. Examples include a
required relationship missing on a production path, durable state lost across its durable
boundary, a forbidden state accepted, a closed vocabulary emitting an unlisted value, or
two required-distinct concepts collapsing into one.

Where a CCL assertion itself contains an exhaustive or finite domain, prove that exact
domain. The cell/CCL assertion defines the membership boundary; the verifier does not
invent a broader sibling universe.

### IMP-* cells

Prove the exact private/mechanical requirement is realized. Do not reject a semantically
equivalent mechanic unless the cell freezes the mechanic itself.

### TEST-* cells

Prove the requested test/proof exists, executes under applicable repository rules, and is
capable of falsifying the behavior it claims to prove. A green test that cannot fail when
the assigned contract is false is `unproven`.

### EXC-* guardrails

For every parent exclusion, determine whether the candidate can materially affect that
boundary:

* yes -> prove the candidate does not introduce the excluded behavior;
* no -> `not-applicable` with concrete candidate evidence.

An exclusion never becomes positive implementation work.

## 4. Production and negative-path proof

Do not certify component capability when the cell requires observable production behavior.
Inspect the canonical composition/runtime path needed by the assigned contract.

For negative/fail-closed obligations, exercise or inspect meaningful falsifying states at
the boundary that owns them. Well-formed happy-path examples alone do not prove a negative
contract.

Use parent technical results only for what they mechanically establish. Do not rerun broad
checks merely for independence. Run narrow non-mutating checks when needed to settle an
assigned-cell falsifier.

## 5. Retry behavior

A fresh verifier produces a fresh verdict but may consume prior durable findings/evidence
when their exact proof dependencies remain unchanged.

Every prior unresolved finding is a mandatory regression target:

```text
closed | still-open | superseded-by-explicit-authority-change
```

Candidate mutation alone never closes a finding. Reuse prior evidence only when its
candidate/runtime/config/tracker dependencies are demonstrably unchanged; uncertainty
invalidates reuse.

Do not reconstruct a new semantic universe on retry. The current deterministic ticket
contract is the universe.

## 6. Gap classification

During proof, a concrete issue may reveal that the frozen contract itself is insufficient.
The verifier may report the gap; it may not repair it.

Use exactly:

```text
implementation-defect
    current candidate violates an assigned OBL/IMP or applicable EXC
    owner: $implement-ticket

test-proof-defect
    assigned TEST/proof is absent or cannot falsify its claim
    owner: $implement-ticket

cell-routing-defect
    current deterministic Spec cell/coverage/ticket mapping is stale, missing, or wrong
    owner: $to-tickets

planning-cell-gap
    necessary private/test/exclusion planning is missing but no new material semantics
    owner: $to-specs

contract-authority-gap
    correct closure requires material semantics absent/conflicting in current CCL
    owner: $architecture-remediation / governing semantic owner
```

A `contract-authority-gap` is not established merely because another prose source sounds
broader. It requires concrete current authority/candidate evidence that the existing CCL
cannot determine correct behavior without a material choice or contains a real conflict.

Continue proving all independently provable assigned cells after a failure so one attempt
returns the complete current failure set. Do not broaden beyond the frozen contract.

## 7. PASS/FAIL completeness

Before either terminal verdict require:

```text
Assigned cells: <n>
proven: <n>
not-applicable: <n>
violated: <n>
unproven: <n>
unchecked: 0

Exclusion guardrails: <n>
proven-safe: <n>
not-applicable: <n>
unresolved: 0

Prior findings still-open: <n>
Unresolved design/contract gaps: <n>
```

PASS requires:

```text
violated: 0
unproven: 0
unchecked: 0
exclusion guardrails unresolved: 0
prior findings still-open: 0
unresolved design/contract gaps: 0
```

FAIL requires a complete finding list and failure saturation over the exact frozen ticket
contract.

## 8. Result contract

### PASS

Return exactly one terminal result containing at least:

```text
TICKET CLOSURE: PASS
Ticket: #<n>
Mode: <ordinary|remediation>
Ticket Contract Hash: <hash>
Spec Contract Hash: <hash>
Ticket baseline: <sha>
Candidate state: <hash>
Assigned cells: <n>
proven: <n>
not-applicable: <n>
violated: 0
unproven: 0
unchecked: 0
Exclusion guardrails unresolved: 0
Prior findings still-open: 0
Unresolved design/contract gaps: 0
Findings: None
```

For remediation also bind the exact Review Remediation Contract Hash and selected RF identities and return their
preservation/proof disposition.

### FAIL

Return exactly one terminal result containing at least:

```text
TICKET CLOSURE: FAIL
Ticket: #<n>
Mode: <ordinary|remediation>
Ticket Contract Hash: <hash>
Spec Contract Hash: <hash>
Ticket baseline: <sha>
Candidate state: <hash>
Failure saturation: complete
Assigned cells: <n>
proven: <n>
not-applicable: <n>
violated: <n>
unproven: <n>
unchecked: 0
Exclusion guardrails unresolved: <n>
Prior findings still-open: <n>
Unresolved design/contract gaps: <n>
Findings:
- <classification / owner / cells / CCL / falsifier / evidence>
```

Also preserve concise retry state sufficient to re-evaluate prior findings/evidence without
reconstructing semantics:

```text
Retry state:
- prior candidate identity
- exact ticket/spec contract hashes
- finding IDs and falsifiers
- proof/evidence dependency pointers
- reusable evidence with invalidation boundary
```

The verifier never persists tracker state, repairs the candidate, closes the ticket, or
invokes downstream remediation. `$implement-ticket` owns result admission and lifecycle
routing.

## Non-goals

`$verify-ticket-closure` does not:

* decide ticket scope;
* reinterpret Spec/ticket/ADR/wiki prose into obligations;
* create `ARCHSRC-*`, `NORM-*`, or hidden acceptance cells;
* create/revise CCL;
* repair implementation;
* mutate repository/tracker state;
* suppress a current in-contract defect because an earlier attempt passed.
