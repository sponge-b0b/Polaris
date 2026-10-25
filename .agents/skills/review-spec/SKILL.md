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
* current review finding ledger, if present;
* current review coverage receipt, if present.

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
* one active candidate-bound Review Coverage Receipt;
* Review Remediation Ticket lineage;
* the final Spec Review Exit Receipt.

The parent Spec continues to own Workspace Metadata, Spec Verification Receipts, and
Ticket Coverage Manifest v2.

## 3. Two fresh reviewers, complementary duties

Dispatch exactly two fresh non-mutating reviewers for the exact candidate, sequentially.
They receive the exact frozen Spec cells/CCL addresses and may independently derive
falsifiers and evidence, but may not add/remove/redefine contract cells.

### Reviewer A — contract-cell adversarial sweep

Execute sequentially:

1. Standards, when applicable;
2. Spec, always;
3. Architecture, when applicable.

Reviewer A must inspect the complete frozen contract even after discovering a Blocking
finding. **A Blocking finding does not terminate the sweep**, reduce the remaining cell
universe, or authorize an early remediation handoff.

For every contract cell, Reviewer A must produce the candidate-bound coverage row defined
in Section 3A. The coverage row is not a prose assertion that a cell was "looked at"; it
must inventory concrete implementation/proof/authority/composition surfaces and record
adversarial probes for the required review lenses.

#### Standards

Review current applicable repository engineering/coding/testing/workflow standards that
govern the changed implementation surfaces.

Standards findings must cite the exact governing standard. Standards may constrain
implementation quality; they do not create new product/domain semantics.

#### Spec

Challenge whether the integrated candidate satisfies every frozen cell, including
production composition, negative behavior, and test adequacy.

A current in-contract defect is Blocking even when verification previously passed.

#### Architecture

Challenge whether implementation structure realizes exact CCL semantics and current
architecture constraints that are implementation consequences of those contracts.

ADR/wiki rationale may explain why. It may not strengthen CCL.

If current architecture authority proves material behavior absent from CCL/OBL, classify
`contract-authority-gap`; do not invent a review-owned obligation.

### Reviewer B — coverage challenger

After Reviewer A has produced a complete draft coverage artifact and draft finding set,
dispatch a second fresh reviewer as the **coverage challenger**. Reviewer B does not merely
repeat Reviewer A's cell-by-cell conclusions. It challenges whether the proposed coverage
itself omitted a materially distinct implementation, proof, lifecycle, commit-boundary,
read/write, sibling, or composition surface that is implicated by the frozen cell.

Reviewer B receives:

* exact candidate and Spec contract;
* implementation ticket/closure evidence already recovered by the workflow;
* Reviewer A's complete draft coverage artifact;
* current/draft finding ledger.

For every `OBL-*` cell in particular, Reviewer B must test whether broad or cross-cutting
behavior was collapsed into one superficial probe when materially independent paths exist.
For `TEST-*`, Reviewer B must challenge whether proof exercises the authoritative claim and
its materially relevant negative behavior rather than merely proving the implemented happy
path.

A coverage omission is a `$review-spec` workflow blocker until it is investigated and the
coverage artifact is corrected. If the omitted surface exposes an actual in-contract defect,
record it through the normal RF finding model. If it exposes no defect, add the missing
surface/probe evidence without inventing new semantics.

Reviewer B must complete its coverage challenge across the entire contract even when it
finds an omission or defect. There is no early handoff on the first problem.

## 3A. Machine-validated review completeness

Reviewer completeness is represented by exactly one JSON artifact with schema:

```text
polaris.review-coverage/v1
```

The top-level artifact binds:

```text
schema
spec_contract_hash
reviewed_head
cells
```

It contains exactly one row for every current Spec contract cell, in canonical Spec-contract
order. Each row binds the exact `cell`, `cell_hash`, and `kind`, then records:

* `surfaces` — concrete reviewed production/proof/composition/authority surfaces, each with
  a stable row-local `surface_id`, role, and evidence locator;
* `lenses` — the complete required review-lens set for that cell kind, each explicitly
  `covered` or `not-applicable`; a not-applicable lens requires a concrete rationale;
* `probes` — concrete adversarial falsifier/evidence rows tied to one covered lens and one
  or more declared surfaces, with any resulting `RF-*` identities.

Required lenses are machine-owned by `scripts.workflow_review_coverage`:

```text
material-contract -> positive, negative, composition, proof
implementation    -> implementation, composition, proof
testing           -> proof, negative
exclusion         -> exclusion
```

A reviewer may mark a lens `not-applicable` only with an explicit rationale. It may not
silently omit the lens. Every `covered` lens requires at least one adversarial probe, and
every declared surface must be exercised by at least one probe.

After Reviewer B and after every coverage reconciliation, run:

```bash
python -m scripts.workflow_review_coverage validate \
  <spec-contract.json> <review-coverage.json>
```

Require exact successful receipt beginning with:

```text
REVIEW COVERAGE: VALID
Reviewed HEAD: <sha>
Spec Contract Hash: <hash>
Contract cells reviewed: <n>/<n>
Unchecked contract cells: 0
Declared review surfaces: <n>
Adversarial probes: <n>
Review Coverage SHA-256: <hash>
```

Do not manually construct these lines. Copy them only from the successful current-run
validator stdout.

Persist exactly one active coverage comment on the conventional Spec Review issue:

```markdown
<!-- review-spec-coverage:v1
<exact polaris.review-coverage/v1 JSON>
-->
## Review Coverage Receipt

<exact machine receipt>
```

Read the managed comment back exactly, re-extract its JSON, rerun the validator against the
same current Spec contract, and require the same Review Coverage SHA-256 before Exit or any
FAIL remediation handoff.

A stale `reviewed_head`, stale Spec Contract Hash, missing/duplicate/reordered cell, stale
cell hash, omitted required lens, covered lens with no probe, or declared surface with no
probe is incomplete review state. Remain in `$review-spec`; do not route implementation
remediation yet.

The coverage artifact is proof of review process completeness, not a new product contract.
Its surfaces, probes, and not-applicable rationales cannot create or strengthen CCL.

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

Maintain exactly one active review-ledger comment whose canonical v2 JSON payload is the
only current finding/remediation state:

```markdown
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

Only after both reviewers have completed and the machine review-coverage validator passes,
invoke `$attention` against the exact reviewed candidate. Attention is report-only. Any
material concern must enter the same finding model before it can affect review state.

If Attention exposes a previously omitted review surface or probe rather than an actual
finding, reconcile the coverage artifact and rerun the coverage validator before Exit.

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

Then copy the exact current-run review-coverage validator receipt, followed by:

```text
Open Blocking findings: <n>
Open remediation-owned findings: <n>
Open cell-routing defects: <n>
Open contract/planning gaps: <n>
Finding continuity unresolved: <n>
Coverage challenger: complete
```

The `Contract cells reviewed` and `Unchecked contract cells` values come only from
`scripts.workflow_review_coverage`; do not self-report or reconstruct them.

## 9. Exit Gate

PASS requires:

```text
Verification receipt: current and passed
Deterministic Spec contract: VALID
Ticket coverage v2: VALID
Review finding ledger v2: VALID
Review coverage v1: VALID
Reviewer A: complete
Coverage challenger: complete
Unchecked contract cells: 0
Open Blocking findings: 0
Open cell-routing defects: 0
Open contract-authority gaps: 0
Open planning-cell gaps: 0
Unaccounted prior findings: 0
Candidate changed during review: no
```

Advisory findings may remain.

A FAIL result caused by remediation-owned Blocking findings still requires both reviewers,
full-contract coverage validation, durable exact coverage readback, and Attention. Finding a
Blocking defect early is not permission to stop reviewing the remaining cells.

When remediation-owned Blocking findings remain **and review completeness is valid**, persist
the current v2 finding ledger and coverage receipt and hand off directly:

```text
$to-tickets - Spec Review: <Feature Name> (<Review URL>)
```

There is no intermediate remediation-synthesis workflow; `$to-tickets` consumes the v2
finding ledger directly.

Cell-routing defects hand off to `$to-tickets` on their decomposition owner. Contract or
planning gaps hand off to `$to-specs` / semantic owner.

If review coverage is incomplete or invalid, do not emit a remediation handoff. The current
owner remains `$review-spec` until completeness is proven.

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
**Review Coverage Hash:** <Review Coverage SHA-256>
**Blocking findings:** 0
**Open blocking findings:** 0
**Unaccounted prior findings:** 0
**Unresolved continuity cells:** 0
**Unresolved decomposition defects:** 0
**Review coverage:** complete
**Coverage challenger:** complete
**Unchecked coverage cells:** 0
```

Before receipt persistence re-read candidate, verification receipt, deterministic contract,
v2 coverage, finding ledger, and managed review-coverage comment. Any stale identity blocks
Exit.

## 11. Handoff

On PASS:

```text
$spec-merge-cleanup - <Spec Title> (<Spec URL>)
```

Do not invoke cleanup implicitly.

On FAIL emit exactly the current owning lifecycle handoff after durable state is persisted
and only after the complete review/coverage gate in Section 9 has passed.

## Non-goals

`$review-spec` does not:

* reinterpret Spec prose into contract cells;
* reconstruct architecture obligation universes outside CCL;
* create Root Blockers for current remediation;
* invent semantic requirements during review;
* repair implementation itself;
* mutate CCL;
* treat Project fields as review authority;
* use review-coverage surfaces or probes as a second semantic contract.
