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
* exact Attention Receipt Hash;
* parent Spec Contract Hash and current coverage identity;
* Implementation Evidence Index;
* terminal technical-check evidence;
* prior unresolved verifier findings on retry;
* exact `polaris.review-remediation-contract/v1` when mode is remediation.

Before semantic proof, write/recover the exact supplied ordinary ticket contract or review
remediation contract as one JSON file and mechanically admit the Attention lifecycle state:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py verify \
  --ticket <ticket-number> \
  --contract <ticket-or-remediation-contract.json> \
  --baseline <ticket-baseline> \
  --branch <ticket-branch> \
  --expected-receipt-hash <attention-receipt-hash>
```

Require:

```text
IMPLEMENT TICKET ATTENTION: VALID
```

and require the printed candidate state to equal the exact dispatched
`TICKET_CLOSURE_STATE`. A missing local receipt, missing pre-mutation or pre-closure gate,
wrong contract/branch/baseline, mismatched receipt hash, or stale candidate is invalid
verification: emit neither PASS nor FAIL. Do not reconstruct or self-assert a replacement
Attention receipt in the verifier.

Recompute/read enough durable state to ensure all remaining identities are still exact.
Candidate mutation, contract/coverage mutation, verifier mutation/delegation, or ambiguous
durable state invalidates the run. Return invalid verification; emit neither PASS nor FAIL.

Direct human invocation is recovery entry only. Recover `$implement-ticket`'s durable v3
checkpoint and its exact Attention Receipt Hash, then resume its recorded dispatcher/
persistence state; the top-level implementation actor may not certify its own candidate.

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

### Bounded counterexample-class saturation

Failure saturation is both **cell-complete** and, for every failed negative/proof cell,
**counterexample-class-complete**. Finding one concrete escape is not permission to return
immediately when the same frozen predicate is enforced across other materially distinct
candidate surfaces.

When an assigned cell or applicable exclusion first becomes `violated` or `unproven`
because of a concrete falsifier:

1. Freeze a bounded set of materially distinct counterexample classes from the exact frozen
   predicate plus the candidate surfaces already present or directly implicated by current
   evidence. Do not invent hypothetical architectures or search outside the contract.
2. For every applicable class, exercise or inspect at least one representative falsifier,
   unless existing evidence proves the whole class covered. Record one of:
   `escape-confirmed | covered | not-applicable | blocked-by-explicit-gap`.
3. Treat different enforcement surfaces as different classes when defeating them requires
   materially different mechanics. Typical classes, only when actually implicated, include
   domain/model invariants; production composition/runtime/API boundaries; persistence
   model/schema/adapters; migration/DDL mechanics; the executed durable schema; wire/config
   boundaries; and the proof/test harness itself.
4. Group syntactic variants that share the same causal escape class. This rule does **not**
   require exhaustive bug search, mutation testing of every token, or multiple equivalent
   examples after one representative falsifier establishes the class.
5. Do not recurse indefinitely from newly discovered implementation details. Expand the
   frozen class set only when current evidence reveals an already-existing materially
   distinct enforcement surface capable of defeating the same predicate.

A terminal FAIL may claim `Failure saturation: complete` only when every assigned cell and
exclusion is dispositioned **and** every applicable counterexample class for each failed
negative/proof cell is dispositioned. Any unchecked applicable counterexample class keeps
failure saturation incomplete and forbids a terminal FAIL.

This bounded rule is specifically intended to avoid serial verifier attempts where one
TEST/proof cell has several materially distinct escape surfaces (for example, modeled
schema assertions versus migration mechanics versus the executed durable schema) that can
be challenged in the same immutable verification attempt.

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
contract, including bounded counterexample-class saturation for every failed negative/proof
cell.

## 8. Result contract

### PASS

Return exactly one terminal result containing at least:

```text
TICKET CLOSURE: PASS
Ticket: #<n>
Mode: <ordinary|remediation>
Ticket Contract Hash: <hash>
Attention Receipt Hash: <hash>
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
Attention Receipt Hash: <hash>
Spec Contract Hash: <hash>
Ticket baseline: <sha>
Candidate state: <hash>
Failure saturation: complete
Counterexample-class saturation: complete
Assigned cells: <n>
proven: <n>
not-applicable: <n>
violated: <n>
unproven: <n>
uncontrolledu checked: 0
Exclusion guardrails unresolved: <n>
Prior findings still-open: <n>
Unresolved design/contract gaps: <n>
Counterexample classes:
- <failed cell / class / surface / escape-confirmed|covered|not-applicable|blocked-by-explicit-gap / falsifier-or-evidence>
Findings:
- <classification / owner / cells / CCL / falsifier / evidence>
```

If no failed negative/proof cell requires counterexample classes, return
`Counterexample classes: None applicable`; the saturation field remains `complete` only
when that disposition is justified by the exact failure set.

Also preserve concise retry state sufficient to re-evaluate prior findings/evidence without
reconstructing semantics:

```text
Retry state:
- prior candidate identity
- exact ticket/spec contract hashes
- exact Attention Receipt Hash
- finding IDs and falsifiers
- counterexample classes and their dispositions
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
* mint or repair an Attention receipt;
* suppress a current in-contract defect because an earlier attempt passed.
