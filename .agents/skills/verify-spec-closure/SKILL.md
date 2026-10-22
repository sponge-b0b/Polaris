---
name: verify-spec-closure
description: Independently certify whether one exact stable implementation candidate satisfies the frozen deterministic CCL-backed Spec contract; never redefine the contract universe.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Spec Closure

`$verify-spec-closure` is the fresh non-mutating independent implementation-conformance
verifier dispatched by `$verify-spec`.

Its independence is adversarial **proof independence**, not semantic-authority
independence.

```text
Frozen deterministic Spec cells
        ↓
independent falsifiers / evidence
        ↓
PASS or FAIL
```

The verifier never reconstructs the contract from prose, ADRs, wiki pages, ticket prose,
or implementation shape.

## Invocation integrity

Run only in a genuinely fresh, non-mutating verifier context.

Receive from `$verify-spec`:

* Spec identity and exact body/hash;
* fixed baseline, branch, exact stable HEAD;
* exact deterministic `$spec-contract` result;
* complete ordered cells and `cell_hash` values;
* exact CCL addresses for every `OBL-*`;
* current valid `ticket-coverage-manifest:v2` and routed tickets;
* concise implementation/evidence pointers;
* terminal parent technical/delegated gate results;
* prior unresolved verifier findings on retry, when applicable.

Verify those transport identities before semantic work. Any candidate mutation during the
run invalidates the attempt; emit neither PASS nor FAIL.

Do not mutate repository/tracker/Git state, invoke remediation, or delegate.

## Contract boundary

The exact supplied cell universe is authoritative for this attempt:

```text
OBL-*  material semantic contract, exact CCL addresses
IMP-*  private/mechanical implementation obligations
TEST-* explicit proof obligations
EXC-*  exclusion guardrails
```

Do not:

* add/remove a cell;
* infer hidden obligations from narrative prose;
* rebuild a Source Unit Inventory;
* derive `ARCHSRC-*` / `NORM-*` rows;
* reopen architecture/Decision prose to change an OBL meaning;
* treat implementation behavior as evidence that the contract "must have meant" more.

Contract strength is part of this boundary. A verifier may not turn an allowed state into a
forbidden state merely to make a proof stronger. Required behavior remains required,
forbidden behavior remains forbidden, and explicitly optional/permitted behavior must remain
permitted. A TEST/EXC proof is subordinate to the exact OBL/CCL semantics it proves; it does
not acquire independent authority to narrow the allowed implementation state space.

If current evidence appears to require behavior absent from the supplied contract,
classify it as a **contract-gap candidate** and report it separately. It blocks PASS only
when current durable authority proves the gap; the verifier still may not manufacture the
missing cell.

## Per-cell independent proof

For every supplied cell, create concise proof state:

```text
Cell: <ID>
Cell hash: <hash>
Predicate: <what exact cell requires>
Falsifier: <concrete state that would make it false>
Evidence: <current candidate evidence>
State: proven | violated | unproven | not-applicable
```

This is an auditable result summary, not private chain-of-thought.

### OBL-* material-contract cells

Load the typed CCL assertion(s) named by the cell and preserve their exact strength.

Derive implementation/runtime falsifiers appropriate to the assertion kind. Examples:

* required relationship missing on a production path;
* optional relationship incorrectly assumed required;
* forbidden relationship accepted;
* persistence marked durable but lost across the required durable boundary;
* closed vocabulary emits an unlisted value;
* distinct semantic concepts collapse into one meaning;
* required invariant can be violated by an accepted path.

Do not change required/optional/forbidden, open/closed vocabulary, cardinality, temporal,
authority, persistence, or other typed meaning while deriving falsifiers.

### Falsifier admissibility and permitted-state challenge

Before using any hypothetical mutation/state as a falsifier, prove that the state would
actually violate the exact supplied cell. For an OBL-backed behavior, name the exact CCL
address and the exact condition it would violate.

Then perform the **permitted-state challenge**:

```text
Would this hypothetical state still satisfy every exact OBL/CCL assertion assigned to the
proof, including any explicit MAY/optional/permitted behavior?
```

If yes, the state is **not a falsifier**. It may not make a cell `violated` or `unproven`,
and it may not justify a stronger test. Continue searching for a state that is actually
forbidden by the frozen contract.

Presence is not authority. When a contract permits a feature as one non-authoritative
measure but forbids it from becoming the universal/sole semantic, a valid falsifier must
show the forbidden universal/sole authority. The mere existence of that permitted feature
as a field, property, helper, or derived value is contract-compliant and cannot be used as
a missing-proof finding.

A closure FAIL is admissible only when every finding passes this challenge. If an exact
contract violation cannot be stated, do not emit that finding.

### IMP-* cells

Prove the private/mechanical obligation is actually realized in the integrated candidate.
A private alternative is acceptable only when the cell itself permits equivalent mechanics
or the parent has already reconciled the planning cell. The verifier does not rewrite it.

### TEST-* cells

Prove the required test/proof exists and is capable of falsifying the assigned behavior.
A passing test that cannot fail when the contract is false is `unproven`.

A TEST cell is not an independent semantic prohibition. The missing-proof mutation used to
challenge a TEST cell must itself violate the exact behavior the TEST cell is assigned to
prove. A test is over-constrained when it fails for a state the frozen OBL/CCL contract
explicitly allows; such strictness is a proof defect, not evidence that the candidate must
be narrowed further.

### EXC-* cells

Check that the candidate does not introduce the excluded behavior where the candidate can
materially affect that exclusion. `not-applicable` is allowed only with concrete evidence
that the candidate cannot touch the excluded boundary.

## Production-path and negative proof

For observable/persisted/routed/enforced behavior, inspect the actual canonical production
composition needed to realize it. Component capability alone is insufficient.

For negative/fail-closed behavior, inspect meaningful falsifying states at the boundary
that owns rejection. Do not prove `cannot` using only well-formed success-path examples.

Use parent test/gate results as evidence of exactly what they mechanically establish. Do
not rerun broad parent gates merely to duplicate them; run only narrow non-mutating checks
needed to resolve a cell.

## Cross-cell composition

After per-cell proof, perform one bounded integration sweep for interactions between exact
cells/tickets:

* two cells individually pass but compose inconsistently;
* one ticket satisfies its cell by violating another exact cell;
* production wiring omits a capability proven only in isolation;
* an exclusion is violated by integration even though individual tickets passed;
* current ticket coverage points to stale/incorrect implemented ownership.

Composition may falsify existing cells. It does not create new ones.

## Decomposition/contract drift classifications

Report separately from implementation findings:

```text
cell-routing-defect
    exact current cell missing/duplicated/stale/misrouted in v2 coverage or ticket body

contract-gap candidate
    durable current authority appears to require material behavior absent from OBL/CCL

planning-cell-gap candidate
    required private/test/exclusion planning appears absent from IMP/TEST/EXC
```

Do not solve these inside the verifier.

## Retry continuity

For a retry after a prior valid FAIL, every prior finding is mandatory until classified:

```text
closed
still-open
superseded-by-explicit-contract-change
```

A different implementation or different verifier opinion is not supersession.

Reuse prior evidence only when the exact cell hash and all proof inputs remain valid.
The final verdict is always over the whole current candidate.

## Saturation and verdict

Continue after the first failure until every supplied cell is dispositioned and the
bounded composition sweep is complete.

Before any terminal verdict require:

```text
Contract cells: <n>
proven: <n>
not-applicable: <n>
violated: <n>
unproven: <n>
unchecked: 0
Composition sweep: complete
Open prior findings: <n>
Cell-routing defects: <n>
Proven contract gaps: <n>
Proven planning-cell gaps: <n>
Permitted-state challenges failed: 0
Candidate mutation during verification: no
```

`PASS` requires:

```text
violated = 0
unproven = 0
unchecked = 0
open prior findings = 0
cell-routing defects = 0
proven contract gaps = 0
proven planning-cell gaps = 0
permitted-state challenges failed = 0
```

Return exactly one:

```text
SPEC CLOSURE: PASS
```

or

```text
SPEC CLOSURE: FAIL
```

On FAIL include all independently actionable findings in concise form:

```text
Finding: VC-<n>
Classification: implementation-defect | test/proof-defect | cell-routing-defect |
                contract-gap | planning-cell-gap
Cells: <exact IDs | None>
Falsifier: <concrete failing state>
Contract violation: <exact cell/CCL address + condition violated>
Permitted-state challenge: PASS
Evidence: <current evidence>
Owner: $verify-spec | $to-tickets | $to-specs / semantic owner
```

A finding without both `Contract violation` and `Permitted-state challenge: PASS` is not an
admissible closure finding and must not be returned to the parent as a candidate defect.

Do not repair failures.
