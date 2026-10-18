---
name: implement-ticket
description: Implement one exact deterministic ticket contract, run applicable technical checks, obtain fresh independent closure proof, and close only the exact certified candidate.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

`$implement-ticket` owns implementation and lifecycle completion of one published ticket.
It does **not** decide what the ticket means.

For an ordinary CCL-backed ticket, the executable contract is derived mechanically:

```text
current Spec contract
+ ticket-coverage-manifest:v2
+ this ticket destination
        ↓
polaris.ticket-contract/v1
        ↓
assigned OBL/IMP/TEST cells + parent EXC guardrails
```

The implementation actor may choose implementation-equivalent private mechanics. It may
not add, remove, strengthen, weaken, or reinterpret a material semantic obligation.

## Invocation termination

This invocation may stop only at exactly one of these terminal conditions:

* **Completed** — all required implementation, verification, persistence, readback, ticket
  closure, recovery reconciliation, and frontier handoff work for this invocation is done;
* **Human Handoff** — a current owning workflow explicitly requires human authorization or
  a material human decision before this invocation can legally continue;
* **Hard Blocker** — a concrete external/environmental, branch, baseline, permission,
  required-tool, persistence, or contradictory durable-state failure prevents further safe
  work.

Everything else is non-terminal. In particular, partial progress, an implementation/test
failure, `TICKET CLOSURE: FAIL`, an open ticket, an `awaiting-closure-verification` or
`verifier-failed` checkpoint, corrective edits that make prior evidence stale, remaining
actionable in-scope work, and `TICKET CLOSURE: PASS` before exact persistence/closure do
not authorize stopping.

When none of the three terminal conditions applies, continue the lifecycle in the same
invocation.

## 1. Recover durable ticket state

Assume no chat/session state.

Read the current ticket, its native direct parent, parent Spec, current Spec body, current
Ticket Coverage Manifest v2, native blockers/dependencies, branch/baseline state, current
CCL ledger, and the one current closure checkpoint when present.

Determine mode:

```text
ordinary
    native parent = Parent Spec

remediation
    native parent = conventional Spec Review
    Parent Spec remains lifecycle/branch provenance
```

Missing, ambiguous, or contradictory native/textual lineage fails closed. `$implement-ticket`
validates hierarchy; `$to-tickets` owns repairing it.

Resolve governance from the parent Spec's local provenance markers. Independent Specs never
acquire a Wayfinder. For Wayfinder-managed Specs, perform the prescribed
`$project-delivery-management reconcile` + guard calls and require an admitted ALLOWED
result before substantive mutation.

Require open native ticket blockers to be closed. Resolve any current
`architecture-blocker:v1`; unresolved/routed state follows its current owning handoff and
never gets self-resolved by implementation.

## 2. Guard branch and ticket baseline

All tickets under one Spec use the published shared Spec branch. A declared Ticket branch
must exactly equal the current branch before ordinary mutation.

`Ticket baseline` is per-ticket and immutable after pinning:

* `Pending` -> pin the exact pre-mutation shared-branch HEAD, persist it in the ticket,
  and read it back;
* full SHA -> require it to exist and be an ancestor of the current ticket candidate;
* anything else -> fail closed.

Do not silently create/switch/repair the branch.

### Live-WIP reslice recovery

If current durable state contains `ticket-reslice-recovery:v1`, preserve its established
isolated-worktree safety invariant:

* the protected caller checkout is immutable donor/recovery state;
* execute the actionable participant in an isolated worktree when the record requires it;
* attribute every donor hunk/path to an exact durable owner before transplanting it;
* never stash/reset/clean/overwrite the protected donor checkout;
* native dependencies, not recovery metadata, determine actionability;
* the participant closing second terminalizes the record as `source-reconciled` with both
  exact certified completion commits;
* ambiguous ownership or completion identity is a Hard Blocker.

This recovery mechanism transports WIP only. It cannot change the current ticket
contract.

## 3. Build the deterministic ticket contract

### Ordinary CCL-backed ticket

Take one exact current parent-Spec body snapshot and build the deterministic Spec contract:

```bash
python -m scripts.ccl_spec check <spec-body-file> contracts/ccl/transactions
python -m scripts.spec_contract build <spec-issue-json> <spec-contract.json>
python -m scripts.spec_contract check-coverage <spec-contract.json> <coverage.json>
```

Then bind this published ticket to its exact route:

```bash
python -m scripts.spec_contract build-ticket \
  <spec-contract.json> \
  <coverage.json> \
  "#<ticket-number>" \
  <ticket-body-file> \
  <ticket-contract.json>
```

Require:

```text
TICKET CONTRACT: VALID
```

The resulting `polaris.ticket-contract/v1` owns ordinary ticket contract identity:

* `spec_contract_hash`;
* `ticket_contract_hash`;
* exact assigned `OBL-*`, `IMP-*`, and `TEST-*` cells with current `cell_hash` values;
* exact CCL addresses for assigned `OBL-*` cells;
* every current parent `EXC-*` as a guardrail.

All parent exclusions are transported as guardrails so implementation does not have to
interpret which exclusions "probably apply". The verifier may later disposition an
exclusion `not-applicable` only from concrete candidate evidence.

The published ticket `## Contract cells` section must be the exact human-readable
projection of those assigned cells. A stale hash, missing/extra cell, changed CCL address,
or changed private/test requirement is a ticket/decomposition defect. Stop and return to
`$to-tickets`; do not reconstruct intended meaning from ticket prose.

### Spec Review remediation ticket

A current Review Remediation Ticket does not use Root Blocker semantics.

Recover the conventional Spec Review's one active v2 finding ledger and build the exact
review remediation contract:

```bash
python -m scripts.review_remediation validate-ledger \
  <spec-contract.json> <review-findings.json>

python -m scripts.review_remediation validate-ticket \
  <spec-contract.json> \
  <review-findings.json> \
  <ticket-body-file> \
  <review-remediation-contract.json>
```

Require:

```text
REVIEW FINDING LEDGER: VALID
REVIEW REMEDIATION CONTRACT: VALID
```

`polaris.review-remediation-contract/v1` is the executable remediation contract. It binds:

* exact current `SPEC_CONTRACT_HASH`;
* exact open Blocking `RF-*` findings owned by review remediation;
* each selected finding's immutable `finding_hash` and frozen falsifier;
* exact current affected Spec cells/hashes;
* exact applicable Standards references;
* every other current parent-Spec cell as a preservation guardrail.

A remediation ticket may group several findings for execution convenience. Grouping does
not create a new semantic invariant, root, sibling universe, or architecture obligation.

If a finding is a cell-routing defect, planning-cell gap, or contract-authority gap, it is
not admissible to this remediation contract. Route it to its owning workflow instead.

## 4. Implement only the frozen ticket contract

Before first substantive mutation run `$attention` with the ticket/candidate context.
Attention is report-only and cannot enlarge the contract.

For each assigned cell:

* `OBL-*` — implement the exact typed CCL semantics without changing their strength;
* `IMP-*` — implement the exact private/mechanical planning obligation; equivalent private
  mechanics are allowed only when the cell permits them;
* `TEST-*` — create/adjust the exact requested proof/test capability;
* `EXC-*` — do not implement excluded behavior and do not use an exclusion as positive work.

Use `$coding-standards`, `$database-migrations`, `$wiki-sync`, `$verify-code`, repository
architecture checks, documentation checks, and other established helpers when their
current applicability rules select them. Observe the repository pytest service-preflight
rule before any pytest command.

The parent must fix known implementation/test/technical failures before dispatching closure
verification. Passing technical checks are evidence, not semantic closure.

### Material design gap

If correct implementation requires a material semantic choice not present in assigned CCL
assertions, implementation stops before choosing it.

Classify:

```text
planning-cell-gap
    private/test work is missing but no new material semantics are required
    -> $to-specs

contract-authority-gap
    a new/change material semantic decision is required
    -> $architecture-remediation / owning semantic decision path

cell-routing-defect
    an existing exact current Spec cell is assigned incorrectly or absent from this ticket
    -> $to-tickets
```

Persist existing blocker/defect state through its owning workflow; do not create parallel
semantic authority in this skill.

## 5. Build the Implementation Evidence Index

The implementation actor does **not** build a Ticket Acceptance Universe or assign its own
semantic `proven` verdicts.

After applicable implementation/checks are complete, build only this concise retrieval
index:

```text
Ticket Contract Hash: <hash>
Candidate state: <TICKET_CLOSURE_STATE>
Changed/implemented surfaces: <compact path/component groups>

Evidence:
- <cell(s)> -> <implementation surface>; <test/check/evidence pointer>
- ...

Applicable technical checks:
- <check> -> PASS on <candidate/scope identity>
- ...

Known unresolved implementation failures: 0
Known unresolved design/architecture blockers: 0
```

Evidence rows are pointers for the independent verifier. They are not semantic PASS
claims and need not be one row per predicate when cells share the same implementation
surface.

For remediation, also include the exact Review Remediation Contract Hash, selected `RF-*`
identities, frozen falsifiers, Standards references, and preservation/proof pointers.

## 6. Candidate identity

Before closure dispatch compute `TICKET_CLOSURE_STATE` over the final Git-relevant path
state relative to the immutable Ticket baseline.

The path universe is the union of:

* `git diff --no-renames --name-only -z <baseline> --`;
* untracked non-ignored paths.

For sorted raw paths hash:

```text
path\0<raw-path>\0
state\0DELETED\0
```

for absent paths, otherwise:

```text
path\0<raw-path>\0
mode\0<100644|100755|120000>\0
sha256\0<final-content-or-symlink-target-sha256>\0
```

Hash that byte stream with SHA-256. This identity is independent of staged/untracked/
committed representation when final bytes/mode are unchanged.

Tracker-only tickets additionally bind the exact required tracker state.

Use the same algorithm at dispatch, verifier-return admission, pre-persistence recheck,
and stale-PASS detection.

## 7. Durable closure checkpoint v3

Use exactly one machine-managed comment:

```text
<!-- implement-ticket-closure-checkpoint:v3 -->
```

Persist at least:

```markdown
<!-- implement-ticket-closure-checkpoint:v3 -->
## Implement Ticket Closure Checkpoint

**Version:** 3
**Stage:** awaiting-closure-verification | verifier-failed | verifier-passed
**Ticket:** #<ticket>
**Mode:** ordinary | remediation
**Ticket branch:** <branch>
**Ticket baseline:** <sha>
**Parent Spec:** #<spec>
**Spec Contract Hash:** <hash>
**Ticket Contract Hash:** <hash>
**Assigned cells:** <IDs>
**CCL:** <exact inherited addresses | None>
**Remediation parent:** <Spec Review #n | None>
**Review Remediation Contract Hash:** <hash | None>
**Review findings:** <RF IDs | None>
**Candidate state:** <TICKET_CLOSURE_STATE>
**Attempt:** <n>

### Implementation Evidence Index
<exact current index>

### Last verifier result
<None | exact current TICKET CLOSURE result>

### Attempt history
- Attempt <n> | <candidate> | <PASS|FAIL|invalid> | <summary>
```

Zero or one active v3 marker is allowed; more than one fails closed. POST/PATCH the one
managed comment and read it back exactly after every write.

## 8. Independent closure dispatch

After implementation and applicable technical checks are complete, before commit/push or
ticket closure:

1. recompute the exact ticket contract;
2. recompute `TICKET_CLOSURE_STATE`;
3. write/read back v3 `awaiting-closure-verification` with a new Attempt;
4. enter dispatcher-only mode;
5. spawn exactly one genuinely fresh non-mutating `$verify-ticket-closure` verifier.

Pass only the exact durable inputs needed for certification:

* ticket + parent Spec identity;
* exact `polaris.ticket-contract/v1`;
* branch/baseline/candidate state;
* current coverage identity;
* Implementation Evidence Index;
* applicable terminal technical-check evidence;
* for remediation, the exact `polaris.review-remediation-contract/v1`.

Do not pass an alternate prose-derived semantic universe.

While dispatcher-only the parent may only dispatch, receive the result, recompute exact
candidate/tracker bindings, mechanically validate verdict shape/identity, and persist the
result. It may not perform its own semantic closure review.

## 9. Consume verifier result

### Invalid result

Missing/malformed/mismatched verifier output is neither PASS nor FAIL. Record the attempt
as `invalid`, keep the candidate immutable, and dispatch a new fresh verifier if the
candidate/bindings remain exact.

### FAIL

Persist the exact FAIL as `verifier-failed`, including all findings. Then route each
finding by owner:

* implementation/test defect inside assigned cells -> resume implementation now;
* `cell-routing-defect` -> durable decomposition record + Human Handoff to `$to-tickets`;
* `planning-cell-gap` -> Human Handoff to `$to-specs`;
* `contract-authority-gap` / material design gap -> Human Handoff to
  `$architecture-remediation` / governing semantic owner;
* remediation finding violation -> resume implementation when implementation-owned;
  route a newly proven contract/routing gap to its owning workflow.

A contract/routing gap blocks local correction that depends on the missing authority.
Preserve independent ordinary implementation findings, but do not guess the missing
contract.

After any candidate correction, the old verdict is stale. Re-run invalidated technical
checks, build a new evidence index, and dispatch a fresh attempt.

### PASS

Require exact returned Ticket Contract Hash, branch, baseline, candidate state, mode, and
Review Remediation Contract Hash and selected finding identities when applicable.

For the returned contract require:

```text
assigned cells unchecked: 0
assigned cells violated: 0
assigned cells unproven: 0
exclusion guardrails unresolved: 0
unresolved design/contract gaps: 0
```

Persist the exact PASS as `verifier-passed`. PASS means `CERTIFIED`, not `CLOSED`.

## 10. Persist the exact certified candidate

Before persistence:

1. recompute ticket contract and candidate state;
2. re-run project-delivery/actionability guard when required by current governance;
3. require the v3 PASS still binds exactly;
4. require no new blocker/contract/coverage change;
5. run only checks invalidated since certification, if any; any candidate mutation requires
   fresh certification.

Commit only ticket-owned changes with an appropriate message. Push the shared Spec branch
without force. Re-read the pushed commit and require the certified candidate content to
match exactly.

Persist the ticket's normal closure evidence including exact completion commit, Ticket
Contract Hash, candidate identity, terminal technical evidence, and verifier PASS.

Close the ticket only after exact pushed readback and durable closure evidence succeed.
Never rewrite a closed ticket to represent later work.

Reconcile any active live-WIP recovery record under its order-independent terminalization
rule. Never delete/reset a protected donor checkout while another nonterminal recovery
record depends on it.

## 11. Frontier handoff

After closure, re-read the parent Spec's current v2 coverage, implementation tickets,
native blockers, and current contract identity.

If another implementation ticket is independently actionable, emit one copy-ready line per
frontier ticket:

```text
$implement-ticket - <Ticket Title> (<Ticket URL>)
```

If all current executable cells are covered by durably closed tickets and no open ticket
work remains, hand off:

```text
$verify-spec - <Spec Title> (<Spec URL>)
```

If current contract/coverage changed during closure, do not infer the frontier from stale
state; return to `$to-tickets` as appropriate.

## Non-goals

`$implement-ticket` does not:

* infer hidden obligations from Spec/ticket/ADR/wiki prose;
* build an architecture/source-unit semantic universe;
* create or revise CCL;
* reslice tickets;
* repair native ticket hierarchy;
* certify its own candidate;
* make a missing material design decision;
* treat a passing technical check as semantic closure.
