---
name: to-tickets
description: Decompose one CCL-backed Spec contract into implementation tickets with exhaustive deterministic cell coverage, explicit human approval, and exact publication readback.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

`$to-tickets` owns the transition from an implementation-ready Spec contract into
executable ticket work.

For an ordinary CCL-backed software Spec, this workflow is **decomposition only**:

```text
Spec contract cells
        ↓
vertical ticket slices
        ↓
exact exhaustive coverage
```

It does not reconstruct material semantics from Spec prose, ADRs, wiki pages, code,
Wayfinder analysis, or another model's interpretation. Material semantics arrive only
through `OBL-*` cells whose payload is exact CCL addresses.

## Session independence

Recover correctness-critical state from the current Spec, repository, CCL, linked
tickets, native relationships, and current Ticket Coverage Manifest. Chat/session memory
is never authority.

## 1. Resolve source mode

### Ordinary Spec

Use the parent Spec itself.

A software Spec is admissible to the CCL-backed path only when it has:

* exactly one valid `spec-contract-ccl:v1` manifest;
* an exact generated `## Canonical Contract Obligations` section;
* stable-ID `IMP-*`, `TEST-*`, and `EXC-*` rows or exact `None.` in their controlled
  sections;
* `Implementation readiness: pass`;
* no open native Spec blocker.

If an active software Spec lacks that representation, stop and hand it back to
`$to-specs` for projection migration. Do not reconstruct a legacy semantic manifest here.

### Spec Review compatibility path

A `Spec Review: ...` source remains temporarily owned by `$to-remediation-tickets`
because Root Blocker remediation has not yet been normalized into the CCL ticket-cell
model.

Invoke that helper as internal composition and preserve its existing Root Blocker
semantics. This compatibility path must not reinterpret or modify the parent Spec's
`OBL-*` / CCL semantics. Any parent-Spec material contract change routes through
`$to-specs` first.

This path is temporary and is not a reason to retain legacy semantic reconstruction for
ordinary Specs.

## 2. Governance and project-delivery guard

Resolve Spec governance from the Spec-local markers in `AGENTS.md`.

For a Wayfinder-managed Spec, before branch/ticket mutation:

1. invoke `$project-delivery-management reconcile`;
2. invoke `guard <Wayfinder>` for every current Spec-local governor;
3. require at least one exact `PROJECT DELIVERY GUARD: ALLOWED`.

An Independent Spec never acquires a Wayfinder merely because ticketing begins.

## 3. Establish the shared Spec branch and fixed baseline

All initial and later implementation tickets for one Spec use the same branch:

```text
spec-<spec_issue_number>
```

and the same fixed Spec baseline.

Before ticket publication require exactly one valid branch/baseline state:

* the expected Spec branch exists or is created from the then-current default-branch
  head before implementation mutation;
* local/upstream identity resolves to the exact expected remote branch where local Git
  is available;
* GitHub Development linkage identifies that branch, or a pre-existing historical branch
  satisfies the established compatibility evidence;
* the parent Spec has exactly one durable `## Workspace Metadata` comment containing one
  full 40-character `Baseline Commit Hash` and the exact branch;
* the recorded baseline exists and is an ancestor of the current Spec branch;
* an already-recorded valid baseline is immutable.

If branch/baseline state is ambiguous, stop before ticket mutation. Never initialize a
Ticket baseline from the Spec baseline.

Every new ticket starts with:

```text
Ticket baseline: Pending
```

`$implement-ticket` owns replacing `Pending` with its exact pre-mutation HEAD.

## 4. Build the deterministic current Spec contract

Take one exact current Spec-body snapshot and require:

```bash
python -m scripts.ccl_spec check <spec-body-file> contracts/ccl/transactions
```

Then invoke `$spec-contract` in build mode for the same body/baseline/branch/HEAD state.

Require:

```text
SPEC CONTRACT: VALID
Semantic prose classification performed: 0
```

Retain the exact handoff's:

* `spec_body_hash`;
* `spec_contract_hash`;
* complete `cells` array;
* every `cell_hash`;
* every `OBL-*` CCL address set.

Do not run a second semantic builder, Source Unit classifier, Architecture/Design Source
Inventory, `ARCHSRC-*` discovery pass, Ticket Semantic Carry Matrix, or independent
semantic ticket-decomposition verifier.

The complete ordinary-Spec decomposition denominator is the exact deterministic cell
universe returned by `$spec-contract`.

## 5. Cell semantics for decomposition

Use cell kinds exactly as supplied.

### `material-contract` (`OBL-*`)

Ticket acceptance carries the exact cell ID and exact CCL addresses. Do not paraphrase a
CCL assertion into a stronger/weaker ticket requirement.

### `implementation` (`IMP-*`)

Private/mechanical implementation plan. It is ticketable but cannot override any CCL
assertion.

### `testing` (`TEST-*`)

Explicit proof/test work. Assign it to the ticket that can most directly prove the
behavior, or to a dedicated test ticket only when independently executable work genuinely
requires one.

### `exclusion` (`EXC-*`)

Never create implementation work for an exclusion. Carry it in the parent coverage
manifest and, where materially relevant, in ticket guardrails.

If an `IMP-*` or `TEST-*` cell appears to require new material semantics absent from the
`OBL-*` CCL set, ticketing stops. The defect is in the Spec projection/planning contract,
not permission for `$to-tickets` to design architecture.

## 6. Draft vertical ticket slices

Prefer the smallest set of tracer-bullet tickets that delivers coherent vertical
behavior.

A proposed ticket records:

```text
Alias: T<n>
Title: <imperative outcome>
Cells: <OBL/IMP/TEST IDs>
CCL: <union of exact CCL addresses from assigned OBL cells>
Depends on: <ticket aliases | None>
Reason for slice: <compact execution/dependency reason>
```

Rules:

* every non-exclusion contract cell is owned by exactly one ticket destination;
* a ticket may own multiple related cells;
* do not split one cell semantically across several tickets; choose one owning ticket and
  use native ticket dependencies for prerequisite ordering;
* do not create one ticket per field/type/test merely because the cell list is granular;
* do not delegate a material contract decision to implementation;
* code discovery may identify the likely implementation seam, but code never adds a
  semantic cell;
* no ticket may contain an `OBL-*`, `IMP-*`, or `TEST-*` absent from the exact current
  Spec contract.

Run `$attention` on the proposed slices before approval. Attention may identify a missing
Spec/CCL cell, bad vertical boundary, or overlooked dependency. It cannot authorize a new
semantic obligation.

## 7. Deterministic coverage proof

Materialize the proposal as:

```json
{
  "schema": "polaris.ticket-coverage/v2",
  "spec_contract_hash": "<current hash>",
  "routes": [
    {
      "cell": "OBL-001",
      "cell_hash": "<current cell hash>",
      "destination": "T1"
    }
  ],
  "exclusions": [
    {
      "cell": "EXC-001",
      "cell_hash": "<current cell hash>"
    }
  ]
}
```

Run:

```bash
python -m scripts.spec_contract check-coverage <contract.json> <coverage.json>
```

Require exact `TICKET COVERAGE: VALID`.

This replaces the former semantic decomposition-certifier boundary for ordinary
CCL-backed Specs. Coverage completeness is now finite and deterministic because the
semantic denominator was frozen upstream.

## 8. Existing ordinary-Spec ticket reconciliation

### Current v2 coverage exists

When the parent has one current `ticket-coverage-manifest:v2`, compare the current exact
cell universe to its persisted `cell + cell_hash` routes.

Classify mechanically:

```text
unchanged cell  = same ID + same cell_hash
changed cell    = same ID + different cell_hash
new cell        = current ID absent from manifest
removed cell    = manifest ID absent from current contract
```

Then reconcile executable ownership:

* unchanged cell whose owning ticket remains valid → preserve mapping;
* changed/new cell → map through the current approved proposal to an existing open ticket
  or a new ticket;
* removed cell on an open ticket → remove that current obligation; if the ticket has no
  remaining current work, propose it for superseded closure;
* closed tickets remain immutable historical evidence and are never rewritten/reopened;
* if a changed/new current cell requires work after its historical ticket closed, create
  or reuse a current open owner.

A purely narrative Spec edit that changes only `SPEC_BODY_HASH` while
`SPEC_CONTRACT_HASH` and every cell/hash remain unchanged requires no ticket-semantic
reconciliation.

### Legacy ticket/manifest state

If linked implementation tickets exist but no current v2 coverage exists, use
`$to-remediation-tickets` only as a one-time legacy mapping compatibility helper.

Its returned proposal is admissible only when every current executable obligation maps to
an exact current `$spec-contract` cell and no returned architecture/prose-derived
obligation exists outside that cell universe. After owner approval/publication, persist
v2 coverage. Future ordinary-Spec reconciliation is deterministic from v2 state.

If the legacy helper cannot map old state cleanly onto exact current cells, stop and route
the parent Spec through `$to-specs`; do not preserve an unexplained legacy semantic row.

## 9. Decomposition-defect reports

A downstream `decomposition-defects:v1` report is a falsifier candidate, not ticketing
authority.

For an ordinary CCL-backed Spec:

* if alleged missing work corresponds to an exact current cell, reconcile its ticket
  destination;
* if it alleges material behavior absent from current `OBL-*`, return to `$to-specs` /
  the semantic owner;
* if it alleges only private/test work absent from `IMP-*`/`TEST-*`, return to
  `$to-specs` for planning-contract reconciliation;
* never create `ARCHSRC-*` obligations from the report.

Keep the durable report identity/status lifecycle intact until existing terminal
resolution rules are satisfied.

## 10. Human approval

Human approval remains the execution-slicing control point even though coverage is
deterministic.

Before requesting approval show, for each proposed ticket:

* title;
* exact cells;
* exact inherited CCL addresses;
* dependencies;
* whether it is new, updated, preserved, or proposed superseded.

Also show:

```text
Spec Contract Hash: <hash>
Contract cells: <n>
Routed executable cells: <n>/<n>
Exclusions preserved: <n>/<n>
Missing/duplicate/stale cells: 0
Independent semantic decomposition agents used: 0
```

Ask for one approval of the complete substantive ticket delta.

If the exact proposal changes afterward, rerun affected deterministic coverage checks and
request approval again. Do not silently add semantic work during publication.

A zero-semantic-delta reconciliation that changes only stale manifest identity metadata
may proceed without a new decomposition approval after deterministic proof/readback.

## 11. Publish tickets

Use the configured GitHub tracker and ordinary Spec hierarchy.

Each implementation ticket body contains at least:

```markdown
Parent Spec: #<spec>
Spec branch: spec-<spec>
Ticket baseline: Pending
Spec Contract Hash: <hash>

## Contract cells

- `OBL-001` — exact CCL: `<contract@revision#assertion>`, ...
- `IMP-001` — <exact private/mechanical requirement text>
- `TEST-001` — <exact test requirement text>

## Acceptance

- Implement/prove the assigned cells without changing their CCL semantics.
- Preserve applicable parent `EXC-*` exclusions.

## Dependencies

<None or exact ticket references>
```

For `OBL-*`, cite exact CCL addresses rather than re-authoring semantic prose. A
human-readable rendering may be included only as a generated/explanatory projection.

Parent every ordinary implementation ticket under the Spec using the native hierarchy
mechanism. Publish native `blocked by` edges only for actual execution prerequisites.
Reject self-dependency and cycles.

Re-read every created/updated ticket and native relationship and require exact agreement
with the approved proposal.

## 12. Persist Ticket Coverage Manifest v2

Maintain exactly one active parent comment:

```text
<!-- ticket-coverage-manifest:v2
{
  "schema": "polaris.ticket-coverage/v2",
  "spec_body_hash": "...",
  "spec_contract_hash": "...",
  "routes": [
    {
      "cell": "OBL-001",
      "cell_hash": "...",
      "destination": "#401"
    }
  ],
  "exclusions": [
    {
      "cell": "EXC-001",
      "cell_hash": "..."
    }
  ]
}
-->
```

Use issue numbers/URLs after publication, not proposal aliases.

Before successful return:

1. rebuild the exact current `$spec-contract`;
2. run `check-coverage` against the persisted v2 manifest;
3. re-read every ticket and native dependency;
4. require exact current cell IDs/hashes and approved destinations;
5. require zero unknown/missing/duplicate routes.

The v2 manifest is decomposition state, not semantic authority. CCL + Spec cells remain the
contract source.

## 13. Implementation frontier and handoff

An open implementation ticket is actionable when:

* its parent Spec remains open and implementation-ready;
* its body matches its current v2 cell mapping;
* `Ticket baseline` is `Pending` or a valid pinned SHA under implementation rules;
* it has no open native blocker;
* no unresolved/routed architecture-blocker record makes it inadmissible;
* project-delivery guard is allowed when the parent Spec is Wayfinder-managed.

Emit one copy-ready line per independently actionable frontier ticket:

```text
$implement-ticket - <Ticket Title> (<Ticket URL>)
```

Do not invoke implementation implicitly. The user chooses the next fresh-session ticket.

## Non-goals

For ordinary CCL-backed Specs, `$to-tickets` does not:

* infer material semantics from arbitrary prose;
* reopen ADRs/wiki/docs to rediscover contract meaning;
* create Architecture/Design Source Inventories or `ARCHSRC-*` cells;
* run a semantic challenger/certifier over ticket decomposition;
* create new Spec obligations;
* change CCL;
* rewrite closed historical tickets;
* create a Wayfinder for an Independent Spec.
