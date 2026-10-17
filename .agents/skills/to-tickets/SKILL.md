---
name: to-tickets
description: Decompose one deterministic Spec contract or structured Spec Review remediation contract into executable tickets with human-approved slicing and exact machine coverage.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

`$to-tickets` owns executable ticket slicing.

It never decides material semantics. It consumes either:

```text
ordinary Spec
    deterministic OBL / IMP / TEST / EXC contract

Spec Review
    deterministic review-findings/v2 + current Spec contract
```

and creates the smallest coherent execution slices with explicit human approval.

## 1. Resolve source mode

### Ordinary Spec

Require:

* exactly one valid `spec-contract-ccl:v1`;
* exact generated Canonical Contract Obligations;
* stable `IMP-*`, `TEST-*`, `EXC-*`;
* `Implementation readiness: pass`;
* no open native Spec blocker.

Build/validate the exact current Spec contract and current v2 coverage when present.

### Spec Review

Resolve exactly one:

```markdown
**Parent Spec:** #<spec>
```

Then recover:

* current Parent Spec body/contract;
* current Spec branch/baseline;
* one active finding-ledger comment containing
  `review-spec-finding-ledger:v2`;
* current Review Remediation Ticket children;
* current native dependencies.

Extract the v2 JSON and run:

```bash
python -m scripts.review_remediation validate-ledger \
  <spec-contract.json> <review-findings.json>
```

Require `REVIEW FINDING LEDGER: VALID`.

Only current open Blocking findings classified as:

```text
implementation-defect
standards-defect
test/proof-defect
```

are eligible for Review Remediation Tickets.

These are not converted into Root Blockers. `cell-routing-defect`,
`planning-cell-gap`, and `contract-authority-gap` remain with their owning upstream
workflows.

## 2. Governance and branch/baseline

Resolve governance from the Parent Spec's local provenance markers.

For a Wayfinder-managed Spec, use the executable Project Delivery boundary:

```bash
python -m scripts.project_delivery reconcile --repo <owner/repo>
python -m scripts.project_delivery guard \
  --repo <owner/repo> \
  --wayfinder <issue-number>
```

Run `reconcile` once for the current repository, require a zero exit status, then run
`guard` once for every current governor. Require at least one fresh zero-exit guard with
this exact stdout shape:

```text
PROJECT DELIVERY GUARD: ALLOWED
Wayfinder: #<n>
Focused set: <exact set>
```

### Guard invocation discipline

`scripts.project_delivery` is the required composed execution boundary. `$to-tickets`
does not implement Project Delivery control-state discovery, reconciliation, frontier
eligibility, or guard classification.

`$to-tickets` must not independently discover the Project Delivery Management singleton,
parse or infer the focused Wayfinder set, derive Wayfinder frontier eligibility, reconcile
focus, or classify a guard result. Do not substitute any of the following for the required
commands:

* `gh search issues` queries;
* direct `gh api` / GraphQL reads of the Project Delivery singleton or Wayfinder frontier;
* issue title/body searches for `project-delivery:management`;
* Project-board fields;
* remembered singleton issue numbers;
* previously observed focus/frontier state;
* an inline recreation of the delivery-guard algorithm.

Direct GitHub reads needed for Spec/ticket lifecycle work remain allowed, but they do not
satisfy Project Delivery reconciliation or guard requirements.

If either command is unavailable, exits non-zero, returns ambiguous/incomplete state, or
cannot produce its owned exact result format, stop with the guard blocked. Do not fall back
to heuristic searches or declare ALLOWED independently.

Preserve the exact fresh ALLOWED stdout lines as the **delivery guard receipt** for the
current run. A paraphrase such as "delivery check passed" or a manually reconstructed exact
string is not the receipt and must not be used at the approval boundary.

Independent Specs never acquire a Wayfinder.

All tickets use:

```text
Spec branch: spec-<parent-spec>
```

and the Parent Spec's fixed baseline. New tickets use:

```text
Ticket baseline: Pending
```

`$implement-ticket` pins the exact pre-mutation ticket baseline.

Do not silently repair ambiguous branch/baseline/provenance state.

## 3. Ordinary Spec contract

Take one exact Spec-body snapshot:

```bash
python -m scripts.ccl_spec check <spec-body-file> contracts/ccl/transactions
python -m scripts.spec_contract build <spec-issue-json> <contract.json>
```

Require:

```text
SPEC CONTRACT: VALID
Semantic prose classification performed: 0
```

`Semantic prose classification performed: 0` is a required workflow receipt, not a request
for another semantic review. Ordinary ticketing is allowed to consume only the deterministic
`OBL-*`, `IMP-*`, `TEST-*`, and `EXC-*` cell universe. It must not derive additional ticket
cells from Problem Statement, Solution, User Stories, Architecture Impact, Further Notes,
ADRs, source prose, or inferred architecture obligations.

Record the receipt only after confirming that zero extra cells were created or routed from
such prose. If any prose-derived cell universe was built or used, the value is not zero and
ordinary ticketing must stop rather than ask for approval.

The complete ordinary denominator is the exact `cells` array.

Cell kinds:

```text
OBL-*  exact material CCL contract
IMP-*  private/mechanical implementation obligation
TEST-* exact proof/test obligation
EXC-*  exclusion guardrail; never positive implementation work
```

Do not build Source Unit, `NORM-*`, `ARCHSRC-*`, or architecture-prose obligation
universes.

## 4. Ordinary ticket slicing

Draft vertical slices:

```text
Alias: T<n>
Title: <imperative outcome>
Cells: <OBL/IMP/TEST IDs>
CCL: <exact union from OBL cells>
Depends on: <aliases | None>
Reason: <compact execution/dependency reason>
```

Rules:

* every non-EXC cell routes exactly once;
* EXC cells remain parent guardrails;
* one ticket may own multiple related cells;
* one cell has exactly one execution owner;
* dependencies express real execution prerequisites only;
* a missing material choice routes upstream rather than entering ticket prose.

Run `$attention` before approval. Attention may expose a missing cell/bad slice but cannot
create semantics.

## 5. Ordinary deterministic coverage

Build:

```json
{
  "schema": "polaris.ticket-coverage/v2",
  "spec_contract_hash": "<hash>",
  "routes": [
    {"cell": "OBL-001", "cell_hash": "<hash>", "destination": "T1"}
  ],
  "exclusions": [
    {"cell": "EXC-001", "cell_hash": "<hash>"}
  ]
}
```

Run:

```bash
python -m scripts.spec_contract check-coverage \
  <contract.json> <coverage.json>
```

Require `TICKET COVERAGE: VALID`.

Existing v2 state reconciles mechanically:

```text
same ID + same hash      unchanged
same ID + new hash       changed
current-only ID          new
manifest-only ID         removed
```

Closed tickets remain immutable history. Changed/new work gets an open/new owner.

## 6. Review remediation slicing

For a Spec Review, the executable denominator is the set of current open
review-remediation-owned `RF-*` findings, not Root Blockers.

A proposed remediation slice records:

```text
Alias: R<n>
Title: <imperative repair outcome>
Findings: <RF IDs>
Affected cells: <union of exact finding cell refs>
Standards refs: <union>
Depends on: <aliases | None>
Reason: <execution/dependency reason>
```

Grouping is execution-only. Never synthesize an invariant broader than the selected
falsifiers.

For each proposed group run:

```bash
python -m scripts.review_remediation build \
  <spec-contract.json> \
  <review-findings.json> \
  "RF-1,RF-2" \
  <remediation-contract.json>
```

Require exact:

```text
REVIEW REMEDIATION CONTRACT: VALID
```

`polaris.review-remediation-contract/v1` contains:

* exact Spec Contract Hash;
* selected `RF-*` + `finding_hash`;
* frozen finding falsifiers;
* exact affected current cells/hashes;
* exact Standards refs;
* every other current Parent Spec cell as a preservation guardrail.

A standards-only finding may have no affected Spec cell, but it must carry exact Standards
authority; then all current Spec cells are preservation guardrails.

### Existing remediation tickets

A current open Review Remediation Ticket is reusable only when its exact selected RF set,
Spec Contract Hash, and Review Remediation Contract Hash match the current proposal.

Closed remediation tickets remain immutable historical evidence. If the finding is open
again/currently violated, new executable work gets a current ticket.

## 7. Review remediation ticket body

Publish each normalized Review Remediation Ticket under the conventional Spec Review native
parent:

```markdown
Parent Spec: #<spec>
Remediation parent: Spec Review #<review>
Spec branch: spec-<spec>
Ticket baseline: Pending
Spec Contract Hash: <hash>
Review Remediation Contract Hash: <hash>

## Review findings

- `RF-1` — implementation-defect — <exact frozen falsifier>
- `RF-2` — standards-defect — <exact frozen falsifier>

## Contract cells

- `OBL-001` — exact CCL: `<contract@revision#assertion>`
- `TEST-001` — <exact current requirement>

```

Use `None.` when there are no affected cells.

Then include:

```markdown
## Preservation guardrails

- `IMP-002` — `<cell_hash>`
- `EXC-001` — `<cell_hash>`

## Acceptance

- Make every selected review falsifier false on the current candidate.
- Satisfy every selected exact Standards reference.
- Preserve every current guardrail in the remediation contract.
```

Use `None.` only when there are genuinely zero preservation cells.

After publication extract the current ledger JSON and validate the exact ticket body:

```bash
python -m scripts.review_remediation validate-ticket \
  <spec-contract.json> \
  <review-findings.json> \
  <ticket-body-file> \
  <remediation-contract.json>
```

Require exact hash/readback.

Review remediation tickets do not modify `ticket-coverage-manifest:v2`; that manifest
continues to describe the original ordinary Spec decomposition. Remediation contracts are
bound independently to the same current Spec Contract Hash.

## 8. Decomposition-defect input

A `decomposition-defects:v1` report is a falsifier candidate.

For ordinary current Specs:

* if the alleged work corresponds to an exact current cell, reconcile its destination;
* if material behavior is absent from OBL, route `$to-specs` / semantic owner;
* if private/test work is absent from IMP/TEST, route `$to-specs`;
* never create `ARCHSRC-*`.

For a Spec Review, a `cell-routing-defect` finding follows the same route and is not turned
into a Review Remediation Ticket.

## 9. Live-WIP reslicing

Before changing ownership/dependencies of an already-started ticket, inspect current
implementation state.

If a proposed reslice can move/precede work already present in active WIP, use the
established `ticket-reslice-recovery:v1` isolated-worktree mechanism:

* protect donor checkout;
* preserve pinned source baseline;
* attribute donor hunks/paths before transplant;
* never stash/reset/clean protected donor state;
* native dependencies determine actionability;
* second closer terminalizes exact source/destination completion commits.

This recovery metadata never changes ticket contract semantics.

## 10. Human approval

Before asking for human approval, emit one **Pre-publication workflow receipts** block.
This is mandatory; do not replace it with prose summary.

For an ordinary Wayfinder-managed Spec, the block contains these exact receipt forms:

```text
Pre-publication workflow receipts
PROJECT DELIVERY GUARD: ALLOWED
Wayfinder: #<n>
Focused set: <exact set>
SPEC CONTRACT: VALID
Semantic prose classification performed: 0
TICKET COVERAGE: VALID
Missing mappings: 0
Duplicate mappings: 0
ATTENTION: COMPLETE
```

The three Project Delivery lines must be copied verbatim from the successful current-run
`scripts.project_delivery guard` stdout. `$to-tickets` must not generate them itself.

For an Independent ordinary Spec, omit only the three project-delivery guard lines. For
Spec Review mode, substitute the exact remediation-ledger/contract receipts required by
that mode while retaining any applicable delivery-guard receipt.

Every line in the receipt block must come from the current run. Do not reconstruct it from
memory, earlier runs, or a paraphrase. If any required receipt is missing, stale, nonzero,
ambiguous, or failed, **do not ask for approval**. Stop at the owning workflow failure.

For every substantive proposal show:

### Ordinary

* ticket title;
* exact cells;
* exact CCL addresses;
* dependencies;
* new/update/preserve/supersede status.

### Review remediation

* ticket title;
* exact `RF-*`;
* exact affected cells;
* exact frozen falsifiers;
* Standards refs;
* preservation-guardrail count;
* dependencies;
* new/update/preserve/supersede status.

Also show the relevant contract hash(es), exact zero missing/duplicate mappings, and that no
semantic decomposition agents were used.

Ask for one approval of the complete substantive delta only after the mandatory receipt
block is complete. If the proposal changes materially, revalidate affected deterministic
contracts, regenerate the receipt block from the new current run, and ask again.

## 11. Publication/readback

Ordinary tickets are native children of the Parent Spec.

Review Remediation Tickets are native children of the conventional Spec Review and retain
`Parent Spec` for branch/lifecycle provenance.

Publish native `blocked by` edges only for actual execution prerequisites. Reject
self-dependency/cycles.

After mutation:

* reread every created/updated ticket;
* reread native hierarchy/dependencies;
* validate ordinary ticket body against its exact route;
* validate remediation ticket body against its exact remediation contract;
* require branch/baseline/provenance equality with approved proposal.

For ordinary Specs, persist exactly one current `ticket-coverage-manifest:v2`, then rerun
`check-coverage`.

For review remediation, do not create a second parent coverage manifest.

## 12. Frontier handoff

An open ticket is actionable when:

* Parent Spec remains open/current;
* branch/baseline metadata is valid;
* no native blocker is open;
* no unresolved/routed architecture blocker makes it inadmissible;
* project-delivery guard is ALLOWED when Wayfinder-managed;
* its ordinary/remediation deterministic contract validates current.

Emit one copy-ready line per actionable ticket:

```text
$implement-ticket - <Ticket Title> (<Ticket URL>)
```

Do not invoke implementation implicitly.

## Non-goals

`$to-tickets` does not:

* infer semantics from review/root/Spec prose;
* create Root Blockers;
* build architecture/source-unit universes;
* create `ARCHSRC-*` or `NORM-*`;
* revise CCL;
* rewrite closed historical tickets;
* create a Wayfinder for an Independent Spec.
