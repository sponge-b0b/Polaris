# Skills

This directory contains the agent skills used to plan, implement, verify, review, and maintain Polaris work.

This README documents **cross-skill architecture and governance**. It explains how skills compose, where human control belongs, how lifecycle ownership moves, and which invariants must remain true across skill boundaries.

Individual `SKILL.md` files remain authoritative for their own executable procedure. Do not duplicate detailed commands, templates, or skill-specific algorithms here.

If this README and a `SKILL.md` disagree, treat that as a workflow defect to reconcile rather than guessing which behavior to follow.

## Sources of Authority

Use these layers for different concerns:

```text
.agents/skills/README.md
    cross-skill architecture, lifecycle, conventions, and invariants

.agents/skills/<skill>/SKILL.md
    executable behavior and responsibility of one skill

.agents/skills/<skill>/agents/openai.yaml
    Codex-specific metadata and invocation policy when present

other platform-specific metadata
    platform-specific discovery or invocation controls
```

Invocation metadata controls whether a platform may discover or select a skill automatically. It does **not**, by itself, determine whether a cross-skill transition is a Human Handoff.

## Governing Workflow-Boundary Rule

> **A Human Handoff is required only when the current workflow intentionally ends and the human should choose, authorize, or initiate the next lifecycle stage.**

Classify every cross-skill transition as one of these four cases:

| Transition | Required behavior |
| --- | --- |
| **Internal composition** | Parent invokes the named child directly. |
| **Ordinary return** | Child returns its result and the caller resumes directly. |
| **In-skill HITL** | Current skill asks the user for a decision and then continues itself. |
| **Lifecycle / user-control boundary** | Current skill halts and emits an explicit Human Handoff. |

Do not create Human Handoffs merely because the target skill disables implicit invocation.

## Invocation Semantics

Polaris distinguishes **automatic skill selection** from **delegated workflow composition**.

When a human explicitly authorizes a parent workflow and that workflow explicitly prescribes a named child skill as part of its procedure, the child may be invoked as internal composition.

Example:

```text
Human invokes $to-tickets
    ↓
$to-tickets explicitly invokes $github-issue-dependencies
    ↓
valid internal composition
```

This is different from an agent independently deciding that another skill seems useful.

For Codex, `policy.allow_implicit_invocation: false` is treated as a restriction on model-initiated automatic selection, not as a universal requirement for a new human authorization at every prescribed child edge.

For cross-platform portability, individual skills may also carry platform-specific invocation controls such as `disable-model-invocation: true`. Preserve those controls, but determine Human Handoffs from lifecycle semantics rather than metadata alone.

## Skill Lifecycle

### Primary Delivery Lifecycle

```text
$wayfinder
    ↓ HUMAN
$to-specs
    ↓ HUMAN
$to-tickets
    ↓ HUMAN
$implement-ticket
    ├─ HUMAN → next $implement-ticket
    └─ HUMAN → $verify-spec
                    ↓ HUMAN
                $review-spec
                    ├─ internal → $review-spec-remediation
                    │                 ↓ HUMAN
                    │              $to-tickets
                    │
                    └─ HUMAN → $spec-merge-cleanup
```

Each Human Handoff above marks an intentional lifecycle or fresh-session boundary where the user controls whether and how the next stage begins.

### Review and Remediation Loop

`$review-spec` owns independent review and parent reconciliation.

When architecture-conforming Blocking findings remain:

```text
$review-spec
    ↓ persist durable review-remediation input
$review-spec-remediation
    ↓ synthesize/update durable root remediation state
    ↓ HUMAN
$to-tickets
```

`$review-spec-remediation` is internal composition, not a separate human-authorized lifecycle stage.

The **Pending Review Remediation** packet remains intentionally durable even though the transition is internal. It provides an explicit, recoverable contract between independent review/reconciliation and remediation synthesis.

### Architecture Escalation

When a workflow cannot continue without a new or changed durable architectural choice:

```text
active lifecycle owner
    ↓ HUMAN
$architecture-remediation
    ↓ HUMAN when owner decision is required
$wayfinder
```

Do not treat missing realization of already accepted architecture as a new architecture decision. The owning skill decides whether the blocker is implementation work or genuinely unresolved architecture.

### Independent Root Closure Verification

`$verify-root-closure` is a special independent certification path for Spec Review remediation tickets:

```text
$implement-ticket
    ↓ HUMAN authorization
fresh verifier subagent executes $verify-root-closure
    ↓ verifier result
$implement-ticket resumes
```

The human invocation authorizes independent verification. It does not transfer implementation ownership to the verifier.

`$verify-root-closure` is a non-mutating leaf workflow. `$implement-ticket` fingerprints candidate repository state before dispatch and again after the verifier returns. Any repository-state change during verification invalidates the verifier result; the attempt is neither `PASS` nor `FAIL`.

## Skill Roles

Use role classification to reason about composition without maintaining a brittle catalog of every invocation edge.

### Lifecycle Owners

Lifecycle owners control a major phase and own transitions into the next phase. Examples include:

```text
$wayfinder
$to-specs
$to-tickets
$implement-ticket
$verify-spec
$review-spec
$spec-merge-cleanup
$architecture-remediation
```

### Internal Composition and Helper Skills

Helpers perform part of an already-authorized parent workflow and normally return their result to that parent. Examples include remediation helpers, tracker relationship helpers, architecture reviewers, wiki/document helpers, formatting, targeted verification, database migration support, and code-analysis utilities.

Examples:

```text
$to-remediation-specs
$to-remediation-tickets
$github-issue-dependencies
$review-spec-remediation
$review-architecture
$wiki-sync
$wiki-lint
$database-migrations
$format-code
$verify-code
$deduplicate-code
```

A helper should not jump directly into another lifecycle owner unless its contract explicitly owns that transition. Prefer returning structured state to the parent so the lifecycle owner performs any required Human Handoff.

### Independent Verifier

```text
$verify-root-closure
```

Independent verification must remain isolated from implementation/remediation ownership.

### Interactive / HITL Utilities

Interactive utilities may ask the user questions while remaining inside the current workflow. Examples include `$grilling`, `$domain-modeling`, and `$prototype`.

HITL inside a skill is not automatically a lifecycle handoff.

## Human Handoff Convention

Use a Human Handoff only at an intentional lifecycle or fresh-session boundary.

A handoff should:

1. state why the current lifecycle is stopping;
2. identify the next skill;
3. provide a copy-ready invocation using durable titles/URLs when available;
4. stop after the handoff;
5. avoid alternative continuation that bypasses the boundary.

Typical structure:

```text
⚠️ <why the current lifecycle must stop>

Please run:

$next-skill - <Durable Artifact Title> (<URL>)
```

Do not add a Human Handoff solely because the target has `allow_implicit_invocation: false` or another platform-specific invocation gate.

## Return Semantics

Returning from an invoked child to its caller is ordinary workflow continuation and requires no Human Handoff.

Examples:

```text
$to-tickets
    ↓
$to-remediation-tickets
    ↓ result
$to-tickets resumes
```

```text
$review-spec
    ↓
$review-spec-remediation
    ↓ result
$review-spec resumes or propagates the child's terminal lifecycle result
```

Avoid handoff ping-pong such as:

```text
parent → HUMAN → child → HUMAN → parent
```

when the child is only performing internal work for the parent.

## Durable Workflow State

Correctness-critical state must survive fresh sessions and agent context loss.

Prefer durable repository or tracker artifacts over conversational memory whenever later workflow stages depend on exact state.

Examples include:

* Spec baseline metadata;
* Ticket baseline;
* Spec Verification Receipt;
* Spec Review Exit Receipt;
* Root Blocker Ledger;
* cumulative acceptance matrix;
* Pending Review Remediation packet;
* Root Closure Evidence.

A durable intermediate artifact may remain valuable even when both producing and consuming skills are internal composition.

Do not remove durable state merely because a former Human Handoff was removed. First determine whether the artifact also provides recovery, isolation, exact-state binding, auditability, or provenance.

## Parent / Child Ownership

Use these defaults unless a skill explicitly establishes a different contract:

* **Parent owns lifecycle routing.** A helper reports state upward; the lifecycle owner decides whether to continue, stop, or issue a Human Handoff.
* **Child owns its bounded procedure.** The parent should not duplicate the child's internal algorithm.
* **Return is ordinary control flow.** A child result resumes the parent without new authorization.
* **Parent owns commit scope when declared.** Repository-writing child skills contribute their mutations to the parent's commit when the parent workflow establishes commit ownership.
* **Children do not invent lifecycle transitions.** If a helper detects a condition requiring an upstream or sideways lifecycle change, return that condition to the parent unless the helper explicitly owns the transition.

Example:

```text
$to-remediation-tickets detects architecture-blocked root
    ↓
returns architecture-blocked result
    ↓
$to-tickets owns the Human Handoff to the appropriate review lifecycle
```

## Verification Independence

Independent verification must not collapse into implementation.

For `$verify-root-closure` specifically:

* the verifier is fresh;
* the verifier is non-mutating;
* it does not delegate;
* it does not repair failures;
* it returns a consolidated verdict only after its bounded scan;
* repository state is deterministically fingerprinted before and after dispatch;
* any mutation invalidates the attempt rather than becoming verifier-owned implementation.

The exact fingerprint algorithm and dispatch protocol belong in `$implement-ticket` and `$verify-root-closure`; do not duplicate them here.

## Adding or Modifying Skills

Before adding or changing a cross-skill edge, answer these questions in order:

1. **Who owns the current lifecycle stage?**
2. **Is the target performing internal composition or starting a new lifecycle stage?**
3. **Does the human make a meaningful decision, authorization, or selection at this edge?**
4. If **yes**, use a Human Handoff.
5. If **no**, invoke the child directly.
6. **Does the child return to its caller?** If yes, resume the caller directly.
7. **Does correctness require durable state across sessions?** Persist it before relying on transient context.
8. **Who owns repository/tracker mutations and commits?** Keep ownership explicit.
9. **Who owns lifecycle routing when the child detects a blocker?** Prefer the parent lifecycle owner.
10. **Does the change preserve reviewer/verifier independence?** Never trade independence for convenience.

When changing an existing skill, preserve unrelated behavior. Cross-skill governance changes should be lean and surgical.

## Anti-Patterns

Avoid these patterns:

### Metadata-Driven Handoffs

```text
allow_implicit_invocation=false
    ⇒ Human Handoff
```

This is not a valid lifecycle rule by itself.

### Handoff Ping-Pong

```text
parent → HUMAN → helper → HUMAN → parent
```

when the helper is simply part of the parent's work.

### Child-Owned Sideways Routing

```text
helper detects blocker
    ↓
helper independently jumps to unrelated lifecycle owner
```

Prefer returning the blocker to the parent lifecycle owner.

### Conversational State as Durable Authority

Do not rely on prior-session memory for branch identity, baselines, review findings, closure state, or other correctness-critical workflow inputs when durable recovery is possible.

### README Procedure Duplication

Do not copy detailed commands, templates, acceptance algorithms, or skill-specific procedures into this README. Link responsibility to the owning skill instead.

### Automatic Lifecycle Continuation

Do not automatically continue into a stage intentionally designed for user selection, authorization, independent review, certification, merge/cleanup, or another fresh-session boundary.
