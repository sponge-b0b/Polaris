---
name: to-tickets
description: Decompose one deterministic Spec contract or structured Spec Review remediation contract into executable tickets with human-approved slicing and exact machine coverage.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

`$to-tickets` owns deterministic ticket realization from frozen upstream planning.

It never decides material semantics or ticket grouping. It consumes either:

```text
ordinary Spec
    deterministic OBL / IMP / TEST / EXC contract
    deterministic spec-execution-topology/v1

Spec Review
    deterministic review-findings/v2 + current Spec contract
```

and projects the exact upstream-owned execution units into tickets with explicit human
approval. Ordinary ticket count, cell grouping, and dependency edges are not model choices
in this workflow.

## 1. Resolve source mode

### Ordinary Spec

Require:

* exactly one valid `spec-contract-ccl:v1`;
* exact generated Canonical Contract Obligations;
* stable `IMP-*`, `TEST-*`, `EXC-*`;
* exactly one valid `spec-execution-topology:v1`;
* `Implementation readiness: pass`;
* no open native Spec blocker.

Build/validate the exact current Spec contract. Derive ordinary coverage and dependencies
from the Spec-owned execution topology; never infer a replacement partition from prose or
from existing tickets. If topology is missing or invalid, stop and route `$to-specs`.

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

## 4. Ordinary deterministic decomposition

The Parent Spec owns the atomic execution partition through exactly one
`spec-execution-topology:v1` marker. `$to-tickets` must not draft, merge, split, or reorder
those units. Stable `EU-001` maps to `T1`, `EU-002` to `T2`, and so on.
Derive the only admissible ordinary decomposition:

```bash
python -m scripts.spec_contract derive-decomposition \
  <spec-issue-json> <contract.json> <coverage.json> <dependencies.json>
```

Require current-run receipts beginning with:

```text
TICKET DECOMPOSITION: DERIVED
Execution Topology Hash: <hash>
Atomic execution units: <n>
```

The derived `ticket-coverage/v2` and `ticket-dependencies/v1` files are authoritative for
the proposal. The model may create a concise human-readable title and reason for each
derived ticket, but it must not change the alias, exact cell set, or dependency set.

### Atomic-unit invariant

Each execution unit is an upstream planning assertion that its cells form one smallest
coherent executable responsibility. Therefore:

* every non-EXC cell appears in exactly one unit;
* every unit contains at least one material `OBL-*`;
* one unit becomes exactly one ordinary ticket;
* two units must never be merged merely because one ticket could technically implement
  both;
* one unit must never be split merely to reduce ticket size;
* unit dependencies become the exact native ticket prerequisites;
* explicit `IMP-*` / `TEST-*` cell references must resolve within the same unit or a
  transitively upstream unit.

If the topology is missing, incomplete, contradictory, over-merged, or otherwise appears
wrong, `$to-tickets` does not repair it. Stop and route the decomposition defect to
`$to-specs`, which owns planning partition. `$attention` may expose such a defect but cannot
replace the upstream topology.

## 5. Ordinary deterministic validation

Before approval, validate that the proposal remains an exact projection of the upstream
topology:

```bash
python -m scripts.spec_contract check-decomposition \
  <spec-issue-json> <contract.json> <coverage.json> <dependencies.json>
```

Require exact current-run receipts:

```text
TICKET DECOMPOSITION: VALID
Execution Topology Hash: <hash>
Atomic execution units: <n>
TICKET COVERAGE: VALID
Missing mappings: 0
Duplicate mappings: 0
TICKET EXECUTION CLOSURE: VALID
Dependency graph: VALID
```

`check-decomposition` fails closed if a proposed partition over-merges independent atomic
units, splits an atomic unit, changes a topology-owned dependency, omits/duplicates cells,
or violates execution closure. It also rejects missing/extra destinations, unknown
prerequisites, self-dependencies, and cycles.

Existing v2 coverage state reconciles mechanically against the newly derived exact
partition:

```text
same ID + same hash + same derived destination    unchanged
same ID + new hash or destination                 changed
current-only ID                                   new
manifest-only ID                                  removed
```

Closed tickets remain immutable history. Changed/new work gets a current open owner; do
not rewrite a closed ticket to force it into the new topology. Live-WIP reslicing uses the
recovery rule below.

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

* if an exact current cell is routed contrary to the Spec execution topology, reject the
  proposal and derive the topology-owned destination;
* if the topology itself groups/splits work incorrectly, route `$to-specs`;
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

Before asking for human approval, invoke the formal `$attention` checkpoint exactly as:

```text
Checkpoint: $to-tickets pre-publication
```

Persist the exact formal `$attention` result to a temporary file outside repository
candidate state. It must be either the exact `ATTENTION: CLEAR` form or a complete
`ATTENTION: FINDINGS` result defined by `.agents/skills/attention/SKILL.md`.

Validate that producer result mechanically:

```bash
python -m scripts.workflow_attention validate \
  --result <attention-result-file> \
  --checkpoint '$to-tickets pre-publication' \
  --require-nonblocking
```

Require exact successful stdout beginning with:

```text
ATTENTION PROTOCOL: VALID
Checkpoint: $to-tickets pre-publication
Status: <clear | findings-nonblocking>
Finding count: <n>
Attention Result SHA-256: <sha256>
```

A blocking finding, malformed finding, wrong checkpoint, invented status such as
`ATTENTION: COMPLETE`, or failed validator means proposal readiness has **not** been
certified. Do not ask for approval.

Emit the exact formal `$attention` result before the workflow-receipt block so every
finding remains visible to the human. Then emit one **Pre-publication workflow receipts**
block. This is mandatory; do not replace it with prose summary.

For an ordinary Wayfinder-managed Spec, the block contains these exact receipt forms:

```text
Pre-publication workflow receipts
PROJECT DELIVERY GUARD: ALLOWED
Wayfinder: #<n>
Focused set: <exact set>
SPEC CONTRACT: VALID
Semantic prose classification performed: 0
TICKET DECOMPOSITION: VALID
Execution Topology Hash: <hash>
Atomic execution units: <n>
TICKET COVERAGE: VALID
Missing mappings: 0
Duplicate mappings: 0
TICKET EXECUTION CLOSURE: VALID
Dependency graph: VALID
ATTENTION PROTOCOL: VALID
Checkpoint: $to-tickets pre-publication
Status: <clear | findings-nonblocking>
Finding count: <n>
Attention Result SHA-256: <sha256>
```

The three Project Delivery lines must be copied verbatim from the successful current-run
`scripts.project_delivery guard` stdout. `$to-tickets` must not generate them itself.
The decomposition, topology, coverage, execution-closure, and dependency-graph lines must
be copied from successful current-run `scripts.spec_contract check-decomposition` stdout;
prose reasoning is not a substitute. The five Attention Protocol lines must be copied
verbatim from the successful current-run `scripts.workflow_attention validate` stdout;
`$to-tickets` must not synthesize a completion token or reconstruct that receipt itself.

For an Independent ordinary Spec, omit only the three project-delivery guard lines. For
Spec Review mode, substitute the exact remediation-ledger/contract receipts required by
that mode while retaining any applicable delivery-guard receipt and the same formal
Attention Protocol receipt.

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

Also show the relevant contract hash(es), Execution Topology Hash, atomic-unit count, exact
zero missing/duplicate mappings, successful decomposition/execution/dependency validation,
and that no semantic decomposition agents were used.

Ask for one approval of the complete substantive delta only after the mandatory receipt
block is complete. If the proposal changes materially, revalidate the deterministic contract and exact
topology-derived decomposition, regenerate the receipt block from the new current run, and
ask again.

### Pre-publication Spec Branch Guard

Human approval authorizes the approved ticket delta; it does not waive branch lifecycle
safety. After approval and before **any** ticket mutation in Section 11, execute this guard
for the Parent Spec. The guard applies equally to ordinary and Review Remediation tickets.

All tickets for one Spec use exactly:

```text
SPEC_BRANCH=spec-<parent-spec-number>
```

and one fixed Parent Spec baseline. Before creating, updating, closing, labeling, parenting,
or changing dependencies for any ticket, prove all of the following:

1. **Branch identity** — local/remote branch state names exactly `SPEC_BRANCH`; no alternate
   ticket/remediation branch is introduced.
2. **Baseline authority** — the Parent Spec has exactly one current `## Workspace Metadata`
   record with `**Branch:** SPEC_BRANCH` and one full 40-character
   `**Baseline Commit Hash:** <sha>`, or first-use branch creation will persist exactly that
   record before ticket publication.
3. **Baseline ancestry** — the recorded/captured baseline exists and is an ancestor of the
   current Spec branch; for first-use creation the newly created branch starts exactly at
   the captured baseline.
4. **Remote durability** — `origin/SPEC_BRANCH` exists after setup and the validated remote
   head is read back exactly.
5. **Upstream tracking** — when the caller checkout is used for an existing branch, the
   local branch tracks exactly `origin/SPEC_BRANCH`.
6. **GitHub Development linkage** — `gh issue develop --list <spec>` names exactly the
   expected Spec branch.
7. **Caller-worktree safety** — never stash, reset, clean, commit, discard, or relocate
   unrelated caller work merely to pass this guard.

#### First-use branch creation

When neither local nor remote `SPEC_BRANCH` exists:

* require the caller worktree clean;
* fetch current `origin/main` and require the creation baseline to be the intended fixed
  Parent Spec baseline/current synchronized main state;
* create/link the branch through `gh issue develop <spec> --name "$SPEC_BRANCH" --base main
  --checkout` rather than plain `git branch`;
* push with upstream `origin/$SPEC_BRANCH` without force;
* persist `## Workspace Metadata` on the Parent Spec only if no record exists, containing
  the exact baseline and branch;
* read back Development linkage, Workspace Metadata, upstream tracking, remote branch, and
  branch head before continuing.

Failure of `gh issue develop`, push, metadata persistence, or any readback is a hard branch
guard failure. Do not fall back to a local-only branch.

#### Existing durable branch

When `origin/SPEC_BRANCH` already exists, do not delete/recreate, rename, reset, or move it
merely to satisfy this workflow.

If the caller worktree is dirty, validate the frozen remote Spec-branch head from an
isolated temporary worktree; do not checkout/switch the protected caller worktree. Re-read
the remote head immediately before publication and require it not to have moved during
isolated validation.

If the caller worktree is clean and the existing branch is used locally, require exact
local branch identity and exact upstream `origin/SPEC_BRANCH`.

A pre-existing remote branch without the exact GitHub Development linkage is invalid
runtime lifecycle state. Permanent skills do not embed migration/backfill compatibility
paths. Stop with zero ticket-publication mutations and route the branch-linkage repair to
an explicitly authorized out-of-band administrative operation; do not recreate, rename,
reset, or replace the durable branch to manufacture linkage.

On success emit and retain this current-run receipt:

```text
SPEC BRANCH GUARD: PASS
Branch: spec-<parent-spec-number>
Baseline: <full sha>
Remote head: <full sha>
Development linkage: linked
```

If any branch-rule predicate fails, stop before Section 11 with **zero ticket-publication
mutations**. Do not weaken, bypass, or defer this guard because the approved decomposition
or deterministic contract is otherwise valid.

## 11. Publication/readback

Publication is reachable only from the exact human-approved proposal plus a current
`SPEC BRANCH GUARD: PASS` receipt.

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
* require branch/baseline/provenance equality with approved proposal;
* require every current implementation-ready ticket to carry `ready-for-agent` only after
  these exact readbacks succeed.

`ready-for-agent` is readiness projection, not contract or dependency authority. Do not
apply it before the branch guard or before ticket/body/hierarchy/dependency validation. If
this workflow proves an open ticket no longer represents a current implementation-ready
contract, remove a stale `ready-for-agent` label as part of that reconciliation. Re-read
label state after mutation.

For ordinary Specs, persist exactly one current `ticket-coverage-manifest:v2`. Reconstruct
`polaris.ticket-dependencies/v1` from native dependency readback and rerun
`check-decomposition` against the current Parent Spec body and persisted coverage.
Publication is not complete unless the readback remains an exact projection of the current
execution topology.

For review remediation, do not create a second parent coverage manifest.

## 12. Frontier handoff

An open ticket is actionable when:

* Parent Spec remains open/current;
* branch/baseline metadata is valid;
* no native blocker is open;
* no unresolved/routed architecture blocker makes it inadmissible;
* project-delivery guard is ALLOWED when Wayfinder-managed;
* its ordinary/remediation deterministic contract validates current;
* for ordinary tickets, its route and prerequisites still match the current Spec execution
  topology.

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
* choose ordinary ticket count, cell grouping, or dependency topology.
