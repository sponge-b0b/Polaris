---
name: review-spec
description: Independently review one verified CCL-backed Spec candidate against its frozen deterministic contract; persist stable structured findings and route exact finding remediation without creating new semantics.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

`$review-spec` is the final independent adversarial review of the exact candidate already
passed by `$verify-spec`.

Review independence is about finding implementation, standards, integration, and
architecture-realization defects that verification missed. It is **not** authority to
reinterpret planning prose, create a new contract cell, or broaden CCL.

The review contract is the exact deterministic Spec cell universe:

```text
OBL-* -> exact CCL assertions
IMP-* -> private/mechanical planning
TEST-* -> proof/test planning
EXC-* -> exclusions
```

## 1. Bind the exact verified candidate

Recover from durable state:

* parent Spec and governance mode;
* fixed baseline, branch, exact current `HEAD`;
* latest passing `## Spec Verification Receipt`;
* receipt-bound `SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH`;
* deterministic current `$spec-contract`;
* current `ticket-coverage-manifest:v2`;
* implementation ticket/closure evidence;
* exactly one conventional `Spec Review: ...` issue, creating it if absent;
* current review finding ledger, if present.

Require the current candidate to match the passing verification receipt, except for a
proven policy-only synchronization allowed by `AGENTS.md`.

Rebuild the deterministic Spec contract and v2 coverage. If projection/coverage is stale:

```text
cell-routing-defect      -> $to-tickets
contract/planning gap    -> $to-specs / semantic owner
malformed CCL projection -> $to-specs
```

Do not reinterpret the defect locally.

## 2. Conventional Spec Review issue

The one review issue contains:

```markdown
**Parent Spec:** #<spec>
```

It owns:

* one active structured Review Finding Continuity Ledger;
* Review Remediation Ticket lineage;
* the final Spec Review Exit Receipt.

The parent Spec continues to own Workspace Metadata, Spec Verification Receipts, and
Ticket Coverage Manifest v2.

## 3. One fresh reviewer, three axes

Dispatch exactly one fresh non-mutating reviewer for the exact candidate. Execute
sequentially:

1. Standards, when applicable;
2. Spec, always;
3. Architecture, when applicable.

The reviewer receives the exact frozen Spec cells/CCL addresses. It may independently
derive falsifiers and evidence, but may not add/remove/redefine contract cells.

### Standards

Review current applicable repository engineering/coding/testing/workflow standards that
govern the changed implementation surfaces.

Standards findings must cite the exact governing standard. Standards may constrain
implementation quality; they do not create new product/domain semantics.

### Spec

Challenge whether the integrated candidate satisfies every frozen cell, including
production composition, negative behavior, and test adequacy.

A current in-contract defect is Blocking even when verification previously passed.

### Architecture

Challenge whether implementation structure realizes exact CCL semantics and current
architecture constraints that are implementation consequences of those contracts.

ADR/wiki rationale may explain why. It may not strengthen CCL.

If current architecture authority proves material behavior absent from CCL/OBL, classify
`contract-authority-gap`; do not invent a review-owned obligation.

## 4. Finding model

Every current finding has exactly:

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
Cells: <exact current cells + hashes | empty when legitimately standards-only>
Standard refs: <exact standards authority | empty>
Falsifier: <concrete state making the finding true>
Evidence: <concrete current evidence>
Owner: <workflow owner>
Status: open | resolved | owner-overridden | scope-retired
```

Routing:

```text
implementation-defect
standards-defect
test/proof-defect
    -> Review Remediation Ticket path through $to-tickets

cell-routing-defect
    -> $to-tickets on the current decomposition owner

contract-authority-gap
planning-cell-gap
    -> $to-specs / semantic owner

genuine new material semantic choice
    -> $contract-ledger / governing $wayfinder as applicable
```

Advisory findings do not become remediation tickets unless explicitly promoted through
current authority.

## 5. Structured finding continuity ledger v2

Maintain exactly one active review-ledger comment. For compatibility with
`$spec-merge-cleanup`, retain the historical outer marker while embedding the canonical v2
JSON payload:

```markdown
<!-- review-spec-finding-ledger:v1 -->
<!-- review-spec-finding-ledger:v2
{
  "schema": "polaris.review-findings/v2",
  "spec": "#<spec>",
  "spec_contract_hash": "<hash>",
  "findings": [
    {
      "finding_id": "RF-1",
      "axis": "Spec",
      "severity": "Blocking",
      "classification": "implementation-defect",
      "cells": [
        {"cell": "OBL-001", "cell_hash": "<hash>"}
      ],
      "standard_refs": [],
      "falsifier": "<exact frozen falsifier>",
      "evidence": "<current evidence>",
      "owner": "$to-tickets",
      "status": "open"
    }
  ]
}
-->
## Review Finding Continuity Ledger

<deterministic human-readable projection>
```

The JSON payload is authoritative finding/remediation state. The rendered table/text below
it is a human-readable view only.

Before persisting or consuming the ledger, extract its JSON and run:

```bash
python -m scripts.review_remediation validate-ledger \
  <spec-contract.json> <review-findings.json>
```

Require exact:

```text
REVIEW FINDING LEDGER: VALID
```

Continuity rules:

* preserve stable `RF-*` identity across re-review when the same finding remains;
* reviewer silence never erases an existing open finding;
* candidate mutation alone never resolves a finding;
* `resolved` requires current evidence against the exact frozen falsifier;
* `owner-overridden` requires explicit owner authority;
* `scope-retired` requires explicit current scope authority;
* if an affected cell hash changes, the old finding is stale until explicitly reconciled
  against the new contract; never preserve it by prose similarity;
* a remediation-owned finding's `falsifier` is frozen while open. If the actual defect
  materially changes, create/reconcile finding identity explicitly rather than silently
  broadening it.

For `OBL-*`, CCL addresses are derived from the exact current Spec cell. Do not duplicate a
second hand-authored semantic statement in the finding.

### Legacy ledger migration

A historical v1 table / Root Blocker state is migration input only.

On the next fresh review:

1. preserve prior `RF-*` IDs when current axis/classification/cell identity makes continuity
   unambiguous;
2. require the current reviewer to establish an exact v2 falsifier/evidence row;
3. mark historical rows no longer current as resolved/scope-retired/owner-overridden only
   with valid current evidence/authority;
4. persist the new v2 ledger;
5. do not synthesize or retain Root Blockers as current remediation authority.

If continuity is ambiguous, keep the historical record as history and allocate a new
current finding ID rather than guessing.

## 6. Review remediation contract boundary

Open Blocking findings classified:

```text
implementation-defect
standards-defect
test/proof-defect
```

are the only findings eligible for implementation remediation.

They are **not** grouped into semantic Root Blockers.

`$to-tickets` may group several eligible findings into one ticket when that is the smallest
coherent execution slice. The deterministic remediation contract is built from:

```text
current Spec contract
+ exact v2 finding rows
        ↓
polaris.review-remediation-contract/v1
```

It contains the selected findings/falsifiers, exact affected cells, exact Standards refs,
and every other current parent-Spec cell as a preservation guardrail.

Grouping findings changes execution slicing only. It does not create a new invariant,
semantic domain, sibling set, or architecture obligation.

## 7. Review Attention

Before Exit invoke `$attention` against the exact reviewed candidate. Attention is
report-only. Any material concern must enter the same finding model before it can affect
review state.

## 8. Human-facing aggregate

Always report:

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

Then:

```text
Reviewed HEAD: <sha>
Spec Contract Hash: <hash>
Contract cells reviewed: <n>/<n>
Open Blocking findings: <n>
Open remediation-owned findings: <n>
Open cell-routing defects: <n>
Open contract/planning gaps: <n>
Finding continuity unresolved: <n>
```

## 9. Exit Gate

PASS requires:

```text
Verification receipt: current and passed
Deterministic Spec contract: VALID
Ticket coverage v2: VALID
Review finding ledger v2: VALID
Reviewer coverage: complete
Unchecked contract cells: 0
Open Blocking findings: 0
Open cell-routing defects: 0
Open contract-authority gaps: 0
Open planning-cell gaps: 0
Unaccounted prior findings: 0
Candidate changed during review: no
```

Advisory findings may remain.

When remediation-owned Blocking findings remain, persist the current v2 ledger and hand off
directly:

```text
$to-tickets - Spec Review: <Feature Name> (<Review URL>)
```

Do **not** invoke `$review-spec-remediation`; Root Blocker synthesis is retired.

Cell-routing defects hand off to `$to-tickets` on their decomposition owner. Contract or
planning gaps hand off to `$to-specs` / semantic owner.

## 10. Spec Review Exit Receipt

On PASS persist:

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

The two Root-blocker fields are **legacy receipt transport only** until
`$spec-merge-cleanup`'s historical parser is separately retired. No live Root Blocker
ledger is required or authorized; on a valid v2 PASS these compatibility fields carry no
semantic state.

Before receipt persistence re-read candidate, verification receipt, deterministic contract,
v2 coverage, and finding ledger. Any stale identity blocks Exit.

## 11. Handoff

On PASS:

```text
$spec-merge-cleanup - <Spec Title> (<Spec URL>)
```

Do not invoke cleanup implicitly.

On FAIL emit exactly the current owning lifecycle handoff after durable state is persisted.

## Non-goals

`$review-spec` does not:

* reinterpret Spec prose into contract cells;
* reconstruct architecture obligation universes outside CCL;
* create Root Blockers for current remediation;
* invent semantic requirements during review;
* repair implementation itself;
* mutate CCL;
* treat Project fields as review authority.
