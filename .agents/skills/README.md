# Skills

This directory contains the agent skills used to plan, specify, decompose, implement,
verify, review, and complete Polaris work.

This README owns **cross-skill architecture and lifecycle governance**. Individual
`SKILL.md` files own their bounded executable procedures. Root `AGENTS.md` supplies
repository-wide policy and supersession rules.

If these layers materially disagree, treat the disagreement as a workflow defect. Do not
pick whichever wording is convenient.

## Core Workflow Principle

Polaris interprets material semantics once and then transports exact contract identity
through the delivery lifecycle.

```text
requirements / current authority
          ↓
semantic decision boundary
          ↓
Canonical Contract Ledger (CCL)
          ↓
$to-specs projection
          ↓
OBL / IMP / TEST / EXC Spec contract
          ↓
$to-tickets decomposition
          ↓
implementation
          ↓
verification / review against the same frozen contract
```

Natural-language reasoning, ADR rationale, Spec explanation, ticket prose, implementation
shape, verification findings, and review findings may explain or falsify the contract.
They do not silently redefine it.

## Sources of Workflow Authority

Use these layers for different concerns:

```text
AGENTS.md
    repository-wide operating policy and supersession rules

.agents/skills/README.md
    cross-skill lifecycle architecture and ownership

.agents/skills/<skill>/SKILL.md
    bounded executable procedure of one skill

.agents/skills/<skill>/agents/openai.yaml
    platform-specific discovery/invocation metadata
```

Invocation metadata does not determine lifecycle ownership or whether a Human Handoff is
required.

## Workflow Stability and Change Control

Product delivery normally takes priority over workflow refinement. The workflow is frozen
by default during ordinary product delivery.

Workflow architecture changes require explicit human authorization, including changes to:

* lifecycle stages or Human Handoff boundaries;
* semantic authority or contract ownership;
* verifier/reviewer independence boundaries;
* mandatory durable governance artifacts;
* decomposition or remediation ownership.

The current CCL migration is an explicitly authorized workflow redesign. Do not use that
authorization as permission for unrelated cleanup or product changes.

## Cross-Skill Transition Types

Classify every cross-skill transition as exactly one of:

| Transition | Behavior |
| --- | --- |
| Internal composition | Parent invokes the named child and resumes from its result. |
| Ordinary return | Child returns to its caller without a new human boundary. |
| In-skill HITL | Current owner asks the human for a decision and then continues. |
| Lifecycle/user-control boundary | Current workflow stops and emits a Human Handoff. |

A disabled implicit-invocation flag does not by itself create a Human Handoff.

## Canonical Semantic Boundary

### CCL ownership

`$contract-ledger` is the sole CCL transaction writer and owns:

* CCL schema/integrity;
* stable contract IDs and immutable revisions;
* proposal hashes;
* provenance and acceptance binding;
* ledger admission and persistence;
* exact contract/assertion lookup.

It does not independently invent product/architecture decisions.

New or registered CCL state has one provenance mode:

```text
existing-authority
owner-decision
wayfinder-decision
```

`existing-authority` registers semantics already exactly determined by current authority.
It is not a design path.

`owner-decision` resolves one bounded independent semantic coupling group through explicit
human acceptance.

`wayfinder-decision` records a decision reached through a Wayfinder when broader/coupled
planning is required.

Every new/changed material semantic decision binds the human acceptance to the exact CCL
proposal hash. Accepted revisions are immutable.

### Wayfinder remains optional

`$wayfinder` is the orchestration workflow for substantial planning fog, coupled semantic
decisions, cross-domain planning, research/prototyping needed for a decision, or project
partitioning.

A bounded Independent planning source does not acquire a Wayfinder merely because it uses
CCL. `$to-specs` may consume existing CCL or invoke `$contract-ledger existing-authority`;
one bounded unresolved decision routes to owner-decision; broader coupled work routes to
`$wayfinder`.

## CCL-Backed Spec Contract

`$to-specs` owns the transition from decision-complete planning into an implementation
Spec and owns in-place reconciliation of that Spec when its governing contract changes.

For a software Spec, material semantics are represented only by:

```text
OBL-* -> exact contract-id@revision#assertion-id set
```

Stable downstream planning cells are:

```text
IMP-*  private/mechanical implementation planning
TEST-* explicit proof/test planning
EXC-*  exclusions / decomposition guardrails
```

Problem Statement, Solution, User Stories, Architecture Impact explanation, and Further
Notes are human-readable context. They do not create hidden ticket/acceptance obligations.

`$spec-contract` deterministically derives the finite `OBL/IMP/TEST/EXC` contract universe
and hashes. It does not classify arbitrary prose or infer architecture semantics.

### Existing Spec reconciliation

For an existing Wayfinder-managed Spec, `$to-specs` computes the desired current CCL
projection/planning cells and amends the same Spec in place when needed while preserving:

* issue identity;
* original source/remediation provenance;
* branch/fixed baseline;
* existing ticket history;
* native dependencies;
* Spec Review lineage.

`$to-remediation-specs` is temporary compatibility composition only. It may recover and
repair unambiguous Wayfinder handoff/provenance links. It does not interpret CCL or amend
Spec semantics.

## Ticket Decomposition

For an ordinary CCL-backed Spec, `$to-tickets` decomposes the deterministic Spec contract.
It does not rediscover architecture from ADR/wiki/code prose.

Every executable cell routes exactly once; exclusions are preserved separately.
Deterministic routing is persisted in:

```text
<!-- ticket-coverage-manifest:v2 -->
```

with exact `cell + cell_hash + destination` identity.

Human approval remains the execution-slicing control point for substantive ticket changes.
The human chooses vertical execution boundaries; deterministic coverage proves no current
cell was lost, duplicated, or silently altered.

### Existing ordinary tickets

Current v2 state reconciles mechanically:

```text
same ID + same hash       -> unchanged cell
same ID + different hash  -> changed cell
current-only ID            -> new cell
manifest-only ID           -> removed cell
```

Closed tickets remain immutable historical evidence. New current work is mapped to an
open/current owner or a new ticket rather than rewriting history.

A narrative-only Spec edit that leaves the Spec Contract Hash/cell hashes unchanged does
not require ticket-semantic reslicing.

### Legacy ordinary ticket compatibility

For an ordinary Spec with legacy tickets but no v2 coverage, current `$to-tickets` proposes
a fresh human-approved mapping from exact current Spec cells. Historical ticket prose is
execution context only. `$to-remediation-tickets` remains only as a compatibility redirect
for old entry points.

### Spec Review remediation

`$review-spec` persists one structured `review-spec-finding-ledger:v2`. Stable `RF-*`
findings contain exact current cell hashes where applicable, exact Standards references,
and one frozen falsifier.

`$to-tickets` may group open Blocking implementation/test/standards findings into coherent
execution slices. Each slice is compiled deterministically into
`polaris.review-remediation-contract/v1` containing selected finding hashes/falsifiers,
affected current cells, and every other current Spec cell as a preservation guardrail.

Root Blocker ledgers/matrices are historical compatibility only. They are not current
semantic or remediation authority.

## Implementation

All tickets for one Spec share the same Spec branch and fixed Spec baseline. Each ticket
owns its own Ticket baseline; new tickets begin `Pending`, and `$implement-ticket` pins the
exact pre-mutation candidate when implementation begins.

For an ordinary ticket, implementation first derives one deterministic
`polaris.ticket-contract/v1` from the current Spec contract + current v2 coverage + this
ticket destination. It contains exact assigned `OBL/IMP/TEST` cells, their hashes and CCL
addresses, plus every parent `EXC-*` as an exclusion guardrail. The published ticket body
must validate against that exact route.

`$implement-ticket` may choose implementation-equivalent private mechanics but may not
make a missing material semantic decision. Before independent closure verification it
carries a concise Implementation Evidence Index, not a parent-authored semantic proof
matrix. New attempts bind the exact Ticket Contract Hash and candidate in closure
checkpoint v3.

`$verify-ticket-closure` independently derives falsifiers/evidence for that frozen ticket
contract. Independence is proof independence, not authority to broaden the ticket/Spec/CCL
universe. A route defect goes to `$to-tickets`; a planning-cell gap goes to `$to-specs`; a
material semantic gap goes to the owning architecture/semantic workflow.

## Integrated Spec Verification

After all current implementation tickets are complete, `$verify-spec` owns integrated
candidate verification and repair.

It:

1. rebuilds the deterministic current Spec contract;
2. validates `ticket-coverage-manifest:v2` mechanically;
3. runs applicable technical/repository checks;
4. repairs implementation/test defects when current contract already fixes the answer;
5. routes cell/decomposition gaps to `$to-tickets` and contract/planning gaps upstream;
6. stabilizes one exact candidate HEAD;
7. dispatches one fresh non-mutating `$verify-spec-closure` verifier;
8. persists a passing Spec Verification Receipt only for the exact passing candidate.

`$verify-spec-closure` independently derives falsifiers/evidence for every frozen cell and
performs bounded cross-cell composition proof. It may falsify implementation but may not
add/remove/reinterpret contract cells.

## Independent Spec Review

`$review-spec` reviews the exact verified candidate through one fresh reviewer across
three independent axes:

```text
Standards
Spec
Architecture
```

The reviewer challenges implementation and architecture realization against the same
frozen Spec cells/CCL semantics. It does not reconstruct a parallel semantic domain from
prose.

A review finding is classified into the smallest owning category, including:

```text
implementation/test/standards defect -> review remediation
cell-routing defect                  -> $to-tickets
contract/planning gap                -> $to-specs / semantic owner
```

Every reviewed Spec has exactly one conventional `Spec Review: ...` issue. That issue owns
one cumulative `review-spec-finding-ledger:v1` and the final Spec Review Exit Receipt.

A prior verification PASS never suppresses a concrete current in-contract falsifier; it
is provenance only.

## Review Finding Continuity

Open findings survive until explicitly dispositioned. A new reviewer's silence does not
close them.

Stable review finding identity is preserved across re-review. Resolution requires current
evidence against the exact prior falsifier; owner override/scope retirement requires
explicit durable authority.

When the deterministic contract changes, reconcile prior findings by exact changed cell
identity/hash rather than by prose similarity.

Review PASS requires zero open Blocking findings, zero unresolved routing/contract gaps,
zero unaccounted prior findings, complete cell coverage, and a current passing verification
receipt for the reviewed candidate.

## Architecture / Contract Escalation

When downstream work discovers missing or contradictory material semantics, do not repair
that by interpretation in ticketing/implementation/verification/review.

Route based on the smallest semantic owner:

```text
semantics already fixed but unregistered
    -> $contract-ledger existing-authority

one bounded Independent decision
    -> $contract-ledger owner-decision

Wayfinder-governed or coupled decision
    -> governing $wayfinder / semantic decision domain

CCL source conflict
    -> exact governing semantic owner; no local choice
```

`$architecture-remediation` remains the lifecycle routing/disposition owner for genuine
downstream architecture blockers, preserving the parent Spec's established governance
mode. It does not become a second semantic compiler.

## Project Delivery Management

`$project-delivery-management` coordinates intentional delivery WIP across independent
Wayfinder lineages without replacing lifecycle owners.

Keep these questions separate:

> **Dependency determines what may proceed. Focus determines what Polaris chooses to
> proceed with now.**

Key invariants:

* canonical Wayfinders are discovered from durable map identity; there is no duplicate
  map registry;
* project focus is explicit durable human intent, never inferred from Project fields,
  issue activity, ordering, branches, or assignees;
* Wayfinder-managed substantive advancement is guarded by project-delivery focus;
* Independent Specs remain outside Wayfinder focus;
* native `blocked by` relationships remain execution-dependency truth;
* same-lineage Spec dependencies are owned by `$to-specs`;
* cross-Wayfinder semantic dependencies are owned by `$project-delivery-management` at
  the narrowest authoritative artifact;
* focus preference never becomes a synthetic dependency.

A focused Wayfinder whose lower-level work is blocked may remain focused-but-stalled.

## GitHub Project Tracking

The public GitHub Project is an eventually consistent operational projection, not
workflow authority.

Routine lifecycle transitions do not synchronize the Project.

Authorized projection boundaries are:

1. Spec completion through `$spec-merge-cleanup`, which reconstructs/batch-syncs the
   complete completed lineage;
2. explicit human-requested board reconciliation;
3. separately authorized bootstrap/migration.

Do not create pending projection-debt registries. Project drift never rewrites semantic
workflow state.

## Complete Delivery Lifecycle

```text
Ideas / Intake
    ↓ HUMAN promotion when formal planning is needed
$wayfinder OR bounded Independent semantic path
    ↓ decision-complete CCL
$to-specs
    ↓ CCL-backed Spec
$to-tickets
    ↓ HUMAN-approved deterministic ticket decomposition
$implement-ticket
    ↺ HUMAN selects next frontier ticket while tickets remain
    ↓ all current implementation tickets complete
$verify-spec
    ↺ repair implementation-owned failures
    ├─ cell-routing defect -> HUMAN -> $to-tickets
    ├─ contract/planning gap -> HUMAN -> semantic owner / $to-specs
    └─ PASS receipt
           ↓ HUMAN
$review-spec
    ├─ in-contract Blocking findings
    │      -> conventional Spec Review remediation
    │      -> HUMAN -> $to-tickets -> $implement-ticket -> $verify-spec -> $review-spec
    ├─ cell-routing defect
    │      -> HUMAN -> $to-tickets
    ├─ contract/planning gap
    │      -> HUMAN -> $to-specs / semantic owner
    └─ PASS Exit Receipt
           ↓ HUMAN
$spec-merge-cleanup
    ↓ merge/close, cleanup, Wayfinder reconciliation, final Project projection
Spec lifecycle complete
```

This is a state machine, not a forward-only pipeline. Valid blockers can route work
backward through the owning contract/decomposition stage.

## Spec Completion

`$spec-merge-cleanup` is the normal completion owner after a current Spec Review Exit
Receipt passes.

It owns:

* merge/direct Spec closure;
* branch cleanup when applicable;
* closure of the conventional Spec Review issue;
* reconciliation of every governing Wayfinder;
* final completed-lineage Project projection.

The Exit Receipt remains on the conventional Spec Review; verification receipts remain on
the parent Spec.

A candidate-semantic mutation after review invalidates completion authority. A proven
non-semantic policy-only synchronization may preserve the semantic anchor under root
`AGENTS.md`.

## Live-WIP Ticket Reslicing

When existing-ticket reconciliation moves/prerequisites work after a ticket has active
uncommitted WIP, preserve that WIP rather than forcing stash/reset/commit merely to make a
new prerequisite publishable.

Use the established `ticket-reslice-recovery:v1` isolated-worktree recovery model. The
reconciled exact Spec cells determine semantic ownership; WIP transplantation is allowed
only after path/hunk ownership is classified against the new ticket contract. Ambiguous
ownership blocks transplantation.

This recovery mechanism does not change semantic contract ownership.

## Tracker Relationship Semantics

Use hierarchy for decomposition:

```text
Wayfinder Map
    └─ Wayfinder Decision

Spec
    └─ Implementation Ticket

Spec Review
    └─ Review Remediation Ticket
```

Wayfinder→Spec is normally lifecycle provenance, not parent/sub-issue decomposition.

Use native blocking/dependency relationships only for actual execution prerequisites,
never focus/priority/queue preference.

## Human Handoff Convention

A Human Handoff occurs only when the current workflow intentionally stops and the human
must select/authorize/initiate the next lifecycle stage.

For a skill targeting a durable tracker artifact, the copy-ready line is:

```text
$<skill-name> - <Artifact Title> (<Artifact URL>)
```

Use the artifact's exact current title/URL. Keep evidence/rationale outside the command.
Emit one complete line per independently actionable artifact.

### Fresh-session durability

Every Human Handoff must survive total chat/context loss. Before handoff, persist every
correctness-critical blocker, contract identity, provenance, or reason on durable
repository/tracker state that the destination can recover from the invoked artifact.

Do not require the human to restate prior findings or copy surrounding prose into the next
session.

Architecture/blocker/decomposition records remain governed by their owning skill. A
handoff is not durable if the destination must ask “what problem caused this?”

## Parent / Child Ownership

Defaults:

* parent owns lifecycle routing;
* child owns its bounded procedure;
* internal child results return normally to the parent;
* commit/mutation ownership follows the parent contract when declared;
* helpers do not invent sideways lifecycle transitions.

A parent may not substitute its own reconstructed answer when its procedure explicitly
requires an actual child result.

## Independent Verification Boundary

Independent verification protects implementation correctness, not semantic ambiguity.

A fresh verifier/reviewer may:

* derive adversarial falsifiers for exact frozen cells;
* inspect production composition;
* independently validate evidence;
* reject a candidate that violates the contract;
* surface a proven upstream contract/routing gap.

It may not:

* invent a new contract member;
* strengthen/weaken CCL;
* reinterpret examples/rationale into a taxonomy/cardinality/state;
* replace an unresolved upstream decision with verifier judgment.

Dispatch is never a verdict. Parent admission requires an actual terminal result bound to
the exact frozen candidate/contract identity.

## Anti-Patterns

### Semantic archaeology

```text
CCL exists
    ↓
downstream skill rereads Decision/ADR/wiki prose
    ↓
invents or changes contract meaning
```

Invalid. Consume exact CCL/Spec cells or report a gap/conflict.

### Hidden prose obligations

Narrative wording outside `OBL/IMP/TEST/EXC` is not a secret ticket/verification cell.
Reconcile the Spec if it actually needs to be contractual.

### Synthetic Wayfinder

Do not create a Wayfinder solely because an Independent Spec reaches architecture
remediation or CCL registration.

### Project board as authority

Do not use Project fields/columns/labels to prove receipts, approvals, blockers, focus,
verification, review, or semantic state.

### GitHub open/closed as complete lifecycle state

Issue state alone does not establish Polaris workflow completion/supersession/verification.
Use owning receipts/contracts/provenance.

### Handoff ping-pong

Do not turn internal composition into `parent → HUMAN → child → HUMAN → parent`.

### Conversational state as authority

Correctness-critical transition state belongs in durable contract/receipt/blocker records,
not chat memory.

## Adding or Modifying Skills

Before changing a cross-skill edge answer:

1. Who owns the current lifecycle stage?
2. Is the target internal composition or a new lifecycle stage?
3. Is a human decision/authorization required at this edge?
4. What exact durable contract/state crosses the boundary?
5. Can the destination recover after total session loss?
6. Does the change preserve CCL as the sole material semantic IR?
7. Does independent verification remain implementation-conformance independent without
   becoming a second semantic authority?
8. Does the change preserve Independent Spec governance?
9. Is Project synchronization occurring only at an authorized projection boundary?
10. Is the actual structural mutation exactly within the human-authorized delta?

Prefer deleting duplicated interpretation machinery over adding another guard around it.
