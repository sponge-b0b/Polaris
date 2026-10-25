---
name: review-spec
description: Independently review one verified CCL-backed Spec candidate against its frozen deterministic contract; persist stable structured findings and route exact finding remediation without creating new semantics.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

`$review-spec` is the final independent adversarial review of the exact candidate already
passed by `$verify-spec`.

Review independence is about finding implementation, standards, integration, proof, and
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
* current review coverage receipt, if present;
* current review finding-adjudication receipt, if present;
* current Session Ledger continuation record.

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
* one active Review Finding Adjudication Receipt;
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
in Section 3A. The row must inventory concrete implementation/proof/authority/composition
surfaces and record adversarial probes for the required review lenses.

Reviewer A also produces a draft finding set. Draft findings are not lifecycle authority
and must not be persisted as the active v2 finding ledger until Reviewer B adjudicates them.

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

### Reviewer B — coverage and finding challenger

After Reviewer A has produced a complete draft coverage artifact and draft finding set,
dispatch a second fresh reviewer as the **coverage challenger** and finding adjudicator.

Reviewer B does not merely repeat Reviewer A. It must challenge both:

1. whether coverage omitted a materially distinct implementation, proof, lifecycle,
   commit-boundary, read/write, sibling, or composition surface implicated by a frozen
   cell; and
2. whether every draft finding is factually supported, correctly scoped to the exact
   affected cells, and expressed by a falsifier no broader than current contract authority.

Reviewer B receives:

* exact candidate and Spec contract;
* implementation ticket/closure evidence already recovered by the workflow;
* Reviewer A's complete draft coverage artifact;
* prior active v2 finding ledger for continuity;
* Reviewer A's draft finding set.

For every `OBL-*`, Reviewer B must test whether broad/cross-cutting behavior was collapsed
into one superficial probe when materially independent paths exist.

For every `TEST-*`, Reviewer B must challenge whether proof exercises the authoritative
claim and materially relevant negative behavior rather than merely the implemented happy
path.

For every draft finding Reviewer B must:

* re-open **every concrete cited code/test evidence locator** rather than trusting Reviewer A's
  summary;
* compare the evidence claim against what the cited source actually demonstrates;
* challenge every proposed affected cell and identify any governing affected cell omitted
  from the draft;
* challenge whether any named behavior/path/family is already proved by another cited or
  recovered test;
* challenge the frozen falsifier for overbreadth, invented semantics, and false negatives.

The disposition for each draft finding is exactly one of:

```text
confirmed
corrected
rejected
```

`corrected` means reconcile the draft finding before persistence: preserve RF identity only
when continuity rules permit it, correct evidence/falsifier/cells, then adjudicate the final
row again. `rejected` means the draft must not enter the final finding ledger or coverage
finding links.

The final persisted ledger may contain only rows that Reviewer B has independently
`confirmed` after all corrections. A reviewer may not persist a row while its evidence or
affected-cell scope remains disputed.

Reviewer B must complete its challenge across the entire contract even when it finds an
omission, incorrect finding, or product defect. There is no early handoff on the first
problem.

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
order. Each row binds exact `cell`, `cell_hash`, and `kind`, then records:

* `surfaces` — concrete reviewed production/proof/composition/authority surfaces, each with
  stable row-local `surface_id`, role, and evidence locator;
* `lenses` — complete required review-lens set for that cell kind, each explicitly
  `covered` or `not-applicable`; not-applicable requires concrete rationale;
* `probes` — concrete adversarial falsifier/evidence rows tied to one covered lens and one
  or more declared surfaces, with any resulting `RF-*` identities.

Required lenses are machine-owned by
`.agents/skills/review-spec/scripts/review_coverage.py`:

```text
material-contract -> positive, negative, composition, proof
implementation    -> implementation, composition, proof
testing           -> proof, negative
exclusion         -> exclusion
```

A reviewer may mark a lens `not-applicable` only with explicit rationale. It may not
silently omit the lens. Every `covered` lens requires at least one adversarial probe, and
every declared surface must be exercised by at least one probe.

After Reviewer B and after every coverage reconciliation, run:

```bash
python .agents/skills/review-spec/scripts/review_coverage.py validate \
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

Do not manually construct these lines. Copy them only from successful current-run validator
stdout.

Persist exactly one active coverage comment on the conventional Spec Review issue:

```markdown
<!-- review-spec-coverage:v1
<exact polaris.review-coverage/v1 JSON>
-->
## Review Coverage Receipt

<exact machine receipt>
```

Read it back exactly, re-extract JSON, rerun the validator against the same current Spec
contract, and require the same Review Coverage SHA-256 before Exit or FAIL handoff.

A stale reviewed HEAD, stale Spec Contract Hash, missing/duplicate/reordered cell, stale
cell hash, omitted required lens, covered lens with no probe, or declared surface with no
probe is incomplete review state. Remain in `$review-spec`.

The coverage artifact proves review-process coverage. It is not a second semantic contract.
Its surfaces/probes/rationales cannot create or strengthen CCL.

## 3B. Machine-validated final finding correctness

Reviewer B's final adjudication is represented by exactly one JSON artifact:

```text
polaris.review-finding-adjudication/v1
```

It binds:

```text
schema
spec_contract_hash
reviewed_head
findings
```

There is exactly one adjudication row for every final v2 finding row, in final ledger order.
Each row contains:

```text
finding_id
finding_sha256
verdict
evidence_checks
cell_scope_checks
falsifier_check
```

The final `verdict` is always `confirmed`. Draft `corrected` and `rejected` states are
resolved before final validation.

For each final finding:

* `finding_sha256` binds the exact canonical final v2 finding row;
* `evidence_checks` records every concrete code/test locator cited in final finding evidence,
  the exact claim made about that locator, what Reviewer B observed there, and result
  `supports`;
* `cell_scope_checks` covers every affected cell/hash in the final row and explains why the
  defect/proof gap actually affects that exact cell;
* `falsifier_check` explains why the final falsifier is current, concrete, and no broader
  than the frozen contract.

The final coverage and final finding ledger must agree bidirectionally. For every `RF-*`,
the exact set of cells whose coverage probes cite that RF must equal the exact affected-cell
set in the final ledger. Unknown RF references, missing RF links, or extra RF/cell links
fail closed.

Run:

```bash
python .agents/skills/review-spec/scripts/review_findings.py validate \
  <spec-contract.json> \
  <review-coverage.json> \
  <review-findings.json> \
  <review-adjudication.json>
```

Require exact success beginning with:

```text
REVIEW FINDINGS: VALID
Reviewed HEAD: <sha>
Spec Contract Hash: <hash>
Final findings adjudicated: <n>/<n>
Coverage/finding cell links: VALID
Unchecked cited code evidence locators: 0
```

A final finding is not durable review authority until this validator passes.

Persist exactly one active adjudication comment on the conventional Spec Review issue:

```markdown
<!-- review-spec-finding-adjudication:v1
<exact polaris.review-finding-adjudication/v1 JSON>
-->
## Review Finding Adjudication Receipt

<exact machine receipt>
```

Read the comment back exactly and rerun `review_findings.py validate` against the read-back
final ledger, read-back coverage artifact, and same Spec contract. Require the same Finding
Adjudication SHA-256 before Exit or FAIL handoff.

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
    -> $to-tickets on current decomposition owner

contract-authority-gap
planning-cell-gap
    -> $to-specs / semantic owner

genuine new material semantic choice
    -> $contract-ledger / governing $wayfinder as applicable
```

Advisory findings do not become remediation tickets unless explicitly promoted through
current authority.

A finding may cite only cells actually affected by its frozen falsifier. A nearby cell,
shared implementation surface, or same domain is not sufficient.

For a `test/proof-defect`, distinguish carefully:

* product behavior absent/broken -> implementation defect;
* frozen proof requirement not demonstrated -> test/proof defect;
* proof exists elsewhere in the candidate -> no proof finding for that behavior.

Do not claim a target family, error branch, owner path, or test surface is uncovered until
Reviewer B has checked the recovered test inventory for that exact behavior.

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

The JSON payload is authoritative finding/remediation state. The rendered projection is
human-readable only.

Before persisting or consuming the ledger, extract JSON and run:

```bash
python -m scripts.review_remediation validate-ledger \
  <spec-contract.json> <review-findings.json>
```

Require:

```text
REVIEW FINDING LEDGER: VALID
```

Then require `REVIEW FINDINGS: VALID` from Section 3B before the final ledger is treated as
review authority.

Continuity rules:

* preserve stable `RF-*` identity across re-review when the same finding remains;
* reviewer silence never erases an existing open finding;
* candidate mutation alone never resolves a finding;
* `resolved` requires current evidence against the exact frozen falsifier;
* `owner-overridden` requires explicit owner authority;
* `scope-retired` requires explicit current scope authority;
* if an affected cell hash changes, the old finding is stale until explicitly reconciled;
* a remediation-owned finding's `falsifier` is frozen while open;
* if evidence shows a draft finding was materially over-scoped or false, correct/reject it
  before persistence rather than preserving bad wording for continuity.

For `OBL-*`, CCL addresses derive from the exact current Spec cell. Do not duplicate a
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
+ exact final v2 finding rows
        ↓
polaris.review-remediation-contract/v1
```

It contains selected findings/falsifiers, exact affected cells, exact Standards refs, and
every other current parent-Spec cell as a preservation guardrail.

Grouping changes execution slicing only. It does not create a new invariant, semantic
domain, sibling set, or architecture obligation.

## 7. Review Attention

Only after both reviewers, coverage validation, final finding adjudication, and
coverage↔finding validation complete, invoke `$attention` against the exact reviewed
candidate.

Attention is report-only. Any material product concern must enter the same finding model.
Any newly exposed coverage omission must reconcile coverage and rerun both validators. Any
concern that an RF is factually unsupported or mis-scoped returns to Reviewer B adjudication
before persistence/Exit.

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

Then copy exact current-run coverage validator receipt and exact current-run finding
adjudication validator receipt, followed by:

```text
Open Blocking findings: <n>
Open remediation-owned findings: <n>
Open cell-routing defects: <n>
Open contract/planning gaps: <n>
Finding continuity unresolved: <n>
Coverage challenger: complete
Finding adjudication: complete
```

Do not self-report/reconstruct machine-owned counts or hashes.

## 9. Exit Gate

PASS requires:

```text
Verification receipt: current and passed
Deterministic Spec contract: VALID
Ticket coverage v2: VALID
Review finding ledger v2: VALID
Review coverage v1: VALID
Review finding adjudication v1: VALID
Reviewer A: complete
Coverage challenger: complete
Finding adjudication: complete
Unchecked contract cells: 0
Unchecked cited code evidence locators: 0
Coverage/finding cell links: VALID
Open Blocking findings: 0
Open cell-routing defects: 0
Open contract-authority gaps: 0
Open planning-cell gaps: 0
Unaccounted prior findings: 0
Candidate changed during review: no
```

Advisory findings may remain.

A FAIL result caused by remediation-owned Blocking findings still requires both reviewers,
full-contract coverage validation, final-finding adjudication, durable exact readback of
coverage/ledger/adjudication, and Attention. Finding a Blocking defect early is not
permission to stop reviewing the remaining cells.

When remediation-owned Blocking findings remain **and all review correctness gates are
valid**, the owning lifecycle destination is `$to-tickets`.

Cell-routing defects route to `$to-tickets` on current decomposition owner. Contract or
planning gaps route to `$to-specs` / semantic owner.

If review coverage, finding adjudication, or coverage↔finding linkage is incomplete/invalid,
do not emit a remediation handoff. The current owner remains `$review-spec`.

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
**Finding Adjudication Hash:** <Finding Adjudication SHA-256>
**Blocking findings:** 0
**Open blocking findings:** 0
**Unaccounted prior findings:** 0
**Unresolved continuity cells:** 0
**Unresolved decomposition defects:** 0
**Review coverage:** complete
**Coverage challenger:** complete
**Finding adjudication:** complete
**Unchecked coverage cells:** 0
```

Before receipt persistence re-read candidate, verification receipt, deterministic contract,
v2 ticket coverage, final finding ledger, managed review-coverage comment, and managed
finding-adjudication comment. Any stale identity blocks Exit.

## 11. Durable terminal reconciliation and Human Handoff

Before any terminal PASS or FAIL Human Handoff:

1. persist final finding ledger, coverage receipt, and finding-adjudication receipt;
2. read all three back and rerun their validators;
3. reconcile the managed ChatGPT Session Ledger continuation record to the final reviewed
   state;
4. increment its generation and record exact semantic candidate, authorized delivery tip
   when policy sync applies, final RF statuses, Review Coverage SHA-256, Finding
   Adjudication SHA-256, review comment IDs/URLs, and the next workflow owner;
5. read the Session Ledger back and require that it matches the final review frontier.

If Session Ledger reconciliation/readback fails, do not emit a terminal Human Handoff. The
current owner remains `$review-spec`.

Build one `polaris.workflow-handoff/v1` manifest with exactly one handoff and at least these
durability sources:

* final review finding ledger comment;
* final review coverage receipt comment;
* final finding-adjudication receipt comment;
* reconciled Session Ledger comment.

For PASS use `outcome: success` and destination `$spec-merge-cleanup`.

For any non-success terminal route use `outcome: warning` and the destination selected by
the Exit Gate.

Finalize the Human Handoff only through:

```bash
python .agents/skills/review-spec/scripts/review_spec_handoff.py finalize \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

Require exact stdout:

```text
WORKFLOW HANDOFF: VALID
```

Then emit the contents of `<handoff-output.txt>` byte-for-byte as the terminal handoff block.

A bare lifecycle invocation such as `$to-tickets - ...`, `$to-specs - ...`, or
`$spec-merge-cleanup - ...` is **not** a valid `$review-spec` terminal Human Handoff.

Do not invoke cleanup or remediation implicitly.

## Non-goals

`$review-spec` does not:

* reinterpret Spec prose into contract cells;
* reconstruct architecture obligation universes outside CCL;
* create Root Blockers for current remediation;
* invent semantic requirements during review;
* repair implementation itself;
* mutate CCL;
* treat Project fields as review authority;
* use review-coverage surfaces or probes as a second semantic contract;
* treat a structurally valid coverage row as proof that a finding's evidence is true;
* preserve an incorrect draft finding merely to avoid changing RF wording.
