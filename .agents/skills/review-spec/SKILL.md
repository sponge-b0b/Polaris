---
name: review-spec
description: Independently review one verified CCL-backed Spec candidate along Standards, Spec, and Architecture axes without redefining its frozen contract; persist finding continuity and an exact exit receipt.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

`$review-spec` is the final independent adversarial review of the exact candidate already
passed by `$verify-spec`.

Review independence is about finding implementation, standards, integration, and
architecture-realization defects that verification missed. It is **not** authority to
reinterpret planning prose into new obligations.

The review contract is the exact deterministic Spec cell universe:

```text
OBL-* -> exact CCL assertions
IMP-* -> private/mechanical planning
TEST-* -> proof/test planning
EXC-* -> exclusions
```

## 1. Bind the exact verified candidate

Recover:

* parent Spec and governance mode;
* fixed baseline, branch, exact current HEAD;
* latest passing `## Spec Verification Receipt`;
* exact receipt-bound `SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH`;
* deterministic current `$spec-contract` build;
* exact current `ticket-coverage-manifest:v2`;
* implementation ticket set/closure evidence;
* existing conventional `Spec Review: ...` issue and its managed finding ledger, if one
  already exists.

Require the current candidate to match the passing verification receipt, except for an
explicitly proven non-semantic policy-only synchronization allowed by `AGENTS.md`.

Rebuild the deterministic contract and require the receipt-bound contract identity to
remain current. No semantic contract-builder/reviewer is used.

If current Spec projection/coverage is invalid, review cannot reinterpret it:

* exact cell routing defect -> `$to-tickets`;
* missing material contract -> `$to-specs` / semantic owner;
* malformed CCL projection -> `$to-specs`.

## 2. Conventional Spec Review issue

Every reviewed Spec has exactly one conventional issue:

```text
Spec Review: <Spec title>
```

whose body contains:

```markdown
**Parent Spec:** #<spec>
```

Create it before the first review dispatch if absent. Reuse it across re-review and
remediation; never create one issue per pass.

That issue owns:

* `<!-- review-spec-finding-ledger:v1 -->` Finding Continuity Ledger;
* review-remediation/root state when compatibility remediation is required;
* final `## Spec Review Exit Receipt`.

The parent Spec continues to own Workspace Metadata, Spec Verification Receipts, and
Ticket Coverage Manifest v2.

## 3. One fresh reviewer, three independent axes

Dispatch exactly one fresh non-mutating reviewer for the exact candidate. The reviewer
executes these axes sequentially:

1. Standards, when applicable;
2. Spec, always;
3. Architecture, when applicable.

Do not fan the axes out to separate automatic reviewers. Another independent reviewer or
challenger requires explicit human authorization.

Shared factual evidence may be reused; semantic conclusions may not be copied from one
axis to another.

The reviewer receives the exact frozen contract cells/CCL addresses and may not add,
remove, or redefine them.

### Standards axis

Review the candidate against current applicable repository engineering/coding/testing/
workflow standards that govern the implementation surfaces actually changed by the Spec.

A Standards finding must identify the exact governing standard and current violating
surface. Standards do not create new product/domain semantics.

### Spec axis

Adversarially challenge whether the integrated candidate actually satisfies every frozen
cell, including production composition and negative behavior, and whether the passing
verification missed a concrete falsifier.

A current in-contract defect remains Blocking even though verification previously passed;
the prior PASS is provenance, not suppression.

The reviewer may not convert narrative Problem/Solution/User Story prose into a new cell.

### Architecture axis

Review whether the implemented structure realizes the exact CCL material semantics and
respects current architecture constraints that are implementation consequences of those
contracts.

ADR rationale/wiki narrative may explain why, but may not silently strengthen CCL.

If a current architecture authority appears to require material behavior absent from
CCL/OBL, classify **contract-authority-gap** rather than inventing a review-owned
obligation. That gap blocks Exit until the semantic owner reconciles it.

## 4. Finding model

Every finding has:

```text
Finding ID: RF-<stable n>
Axis: Standards | Spec | Architecture
Severity: Blocking | Advisory
Classification:
  implementation-defect
  standards-defect
  test/proof-defect
  cell-routing-defect
  contract-authority-gap
  planning-cell-gap
Cells: <exact OBL/IMP/TEST/EXC IDs | None>
CCL: <exact addresses | None>
Evidence: <concrete current evidence>
Falsifier / consequence: <what is actually wrong>
Owner: <workflow owner>
Status: open | resolved | owner-overridden | scope-retired
```

Routing:

* implementation/test/standards defect inside current cells -> review remediation path;
* `cell-routing-defect` -> `$to-tickets`;
* `contract-authority-gap` / `planning-cell-gap` -> `$to-specs` and, when required,
  `$contract-ledger` / governing `$wayfinder`;
* genuine new material semantic choice -> architecture/semantic decision owner;
* Advisory -> never blocks Exit unless explicitly promoted through current authority.

Do not create `ARCHSRC-*`, new Spec cells, or broaden CCL while reviewing.

## 5. Finding continuity

Maintain exactly one machine-managed ledger comment on the conventional Spec Review:

```markdown
<!-- review-spec-finding-ledger:v1 -->
## Review Finding Continuity Ledger

**Spec:** #<spec>
**Reviewed contract:** <SPEC_CONTRACT_HASH>

| Finding | Axis | Classification | Cells | Status | Evidence / disposition |
| --- | --- | --- | --- | --- | --- |
| RF-1 | Spec | implementation-defect | OBL-001 | open | ... |
```

Rules:

* preserve stable finding IDs across re-review;
* a fresh reviewer's silence never erases an existing open finding;
* candidate mutation alone never resolves a finding;
* `resolved` requires current evidence against the exact prior falsifier;
* `owner-overridden` requires explicit durable owner authority;
* `scope-retired` requires explicit current scope authority;
* when the contract changes, reconcile every prior finding against exact changed cell
  identities/hashes; do not guess continuity from similar prose.

Hash the exact managed ledger body for the Exit Receipt.

## 6. Compatibility review-remediation state

Ordinary CCL-backed ticketing no longer reconstructs semantic roots. Until Spec Review
remediation is migrated to a deterministic finding/cell delta, preserve a narrow
compatibility Root Blocker representation **only for open Blocking implementation/
test/standards findings already inside exact current cells**.

Each compatibility root must reference:

```text
RB-<n>
Current exact finding IDs
Exact current cell IDs/hashes
Exact CCL addresses for OBL cells
Invariant: close those falsifiers without violating any current parent cell/exclusion
```

Do not synthesize a broader sibling/domain universe. Do not use Root Blocker machinery to
admit a contract-authority gap, planning-cell gap, or cell-routing defect.

`$to-remediation-tickets` may consume this compatibility root state; every resulting
executable obligation must map back to exact current Spec cells plus the specific frozen
review finding falsifier. This compatibility boundary is temporary.

## 7. Decomposition and contract-gap persistence

For a proven `cell-routing-defect`, persist/update the canonical
`<!-- decomposition-defects:v1 -->` record on the current `$to-tickets` source owner. The
record names exact current cells/hashes and the missing/misrouted destination. It never
creates an architecture obligation outside the contract.

For a proven contract/planning gap, persist the durable blocker on the parent Spec with:

* exact missing material/private/test/exclusion concern;
* current cells demonstrating absence;
* governing current authority that proves the gap, when any;
* whether a new semantic decision is required;
* owning next workflow.

Do not disguise a contract gap as ticket decomposition work.

## 8. Review Attention

Before Exit invoke `$attention` against the exact reviewed candidate. Attention may expose
an implementation defect, routing defect, or upstream contract gap, but it cannot create
a new semantic contract.

Any resulting concern must be classified through the same finding model before Exit.

## 9. Human-facing aggregate

Always present the axes in this exact shape:

```markdown
## Standards

### Blocking
- <findings or None.>

### Advisory
- <findings or None.>

## Spec

### Blocking
- <findings or None.>

### Advisory
- <findings or None.>

## Architecture

### Blocking
- <findings or None.>

### Advisory
- <findings or None.>
```

Keep findings under their originating axis/severity.

Then show compact supplemental state:

```text
Reviewed HEAD: <sha>
Spec Contract Hash: <hash>
Contract cells reviewed: <n>/<n>
Open Blocking findings: <n>
Open cell-routing defects: <n>
Open contract/planning gaps: <n>
Finding continuity unresolved: <n>
```

## 10. Exit Gate

PASS is reachable only when:

```text
Verification receipt: current and passed
Deterministic Spec contract: VALID
Ticket coverage v2: VALID
Reviewer coverage: complete
Unchecked contract cells: 0
Open Blocking findings: 0
Open cell-routing defects: 0
Open contract-authority gaps: 0
Open planning-cell gaps: 0
Unaccounted prior findings: 0
Unresolved continuity cells: 0
Candidate changed during review: no
```

Advisory findings may remain.

If blocking implementation/remediation findings remain, persist/update compatibility
review-remediation state and hand off through `$to-tickets` on the conventional Spec
Review.

If a cell-routing defect remains, hand off `$to-tickets` on the current durable owner.

If a contract/planning gap remains, hand off to `$to-specs` / owning semantic workflow.

## 11. Persist the Spec Review Exit Receipt

On PASS persist on the conventional Spec Review issue:

```markdown
## Spec Review Exit Receipt

**Status:** passed
**Spec Review:** #<review issue>
**Reviewed HEAD:** <full SHA>
**Reviewed Baseline:** <full Spec baseline SHA>
**Branch:** spec-<spec>
**Spec Body Hash:** <hash>
**Spec Contract Hash:** <hash>
**Finding Ledger Hash:** <sha256 of exact managed ledger body>
**Blocking findings:** 0
**Open blocking findings:** 0
**Unaccounted prior findings:** 0
**Unresolved continuity cells:** 0
**Unresolved decomposition defects:** 0
**Root blockers:** satisfied/owner-overridden/scope-retired
**Candidate new roots:** 0
**Review coverage:** complete
**Unchecked coverage cells:** 0
```

The legacy-compatible zero fields remain because `$spec-merge-cleanup` consumes this
schema. They must reflect actual current state, never be hard-coded around unresolved
work.

Before persistence re-read the candidate, verification receipt, deterministic contract,
v2 coverage, and finding ledger. Any stale identity blocks Exit.

## 12. Handoff

On PASS:

```text
$spec-merge-cleanup - <Spec Title> (<Spec URL>)
```

Do not invoke cleanup implicitly.

On FAIL, emit exactly the current owning lifecycle handoff after durable state is
persisted.

## Non-goals

`$review-spec` does not:

* reinterpret Spec prose into contract cells;
* reconstruct architecture obligation universes outside CCL;
* use a prior PASS to suppress a current in-contract falsifier;
* create semantic requirements during review;
* repair implementation itself;
* mutate CCL;
* treat Project fields as review authority.
