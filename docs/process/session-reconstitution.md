# Session Reconstitution

## Purpose

This guide defines how a new agent session should reconstruct enough Polaris context to continue prior work safely and efficiently.

It is a **bootstrap and recovery procedure**, not a source of architectural truth, workflow state, or domain semantics.

The goal is to avoid rebuilding project context from large conversation transcripts when the repository and tracker already preserve durable state, while also preserving the small amount of important session-only context that has not yet acquired another durable home.

## Core Principle

Reconstitute from durable project state first, then restore the minimum necessary ephemeral state from the **Current Session Ledger** at the bottom of this document.

Durable repository/tracker state remains authoritative. The ledger exists only for context that would otherwise be stranded in a conversation, such as:

- the exact task or thread that was in progress;
- the last local-only command/result needed to resume safely;
- an uncommitted or unpushed local state that is not visible remotely;
- a temporary decision, sequencing choice, or working assumption that has not yet been persisted to its authoritative artifact;
- a tool/capability handoff that requires the user to perform the next mechanical step outside the agent's available tooling.

If remembered conversation or the Current Session Ledger conflicts with current durable state, surface the conflict and prefer the applicable authority defined by `AGENTS.md` unless the user explicitly resolves it otherwise.

## Authority

Start with `AGENTS.md` and follow its authority model.

In particular:

- code, configuration, executable checks, and relevant tests describe implementation reality;
- accepted ADRs define active architectural decisions;
- `docs/current/` describes current architecture;
- `wiki/entities/` contains derived architectural knowledge;
- workflow artifacts and native tracker relationships define delivery state;
- the GitHub Project is an operational projection and does not override authoritative repository or tracker state;
- the Current Session Ledger is an ephemeral recovery aid and never overrides any of the above.

Do **not** read `CONTEXT.md` merely because a session is being reconstructed. Follow the `AGENTS.md` rules for when canonical domain vocabulary actually requires it.

## Reconstitution Procedure

### 1. Establish repository state

Inspect the current default branch and recent relevant commits.

Determine whether the user's local working tree may contain uncommitted or unpushed state that cannot be observed remotely. Never assume remote repository state includes those changes.

### 2. Load repository operating policy

Read `AGENTS.md` before interpreting project state or making changes.

Load narrower skills only when their responsibility is relevant to the active work. Prefer current skill contracts over remembered behavior from earlier sessions.

Common workflow skills include:

- `$wayfinder`
- `$to-specs`
- `$to-tickets`
- `$implement-ticket`
- `$verify-spec`
- `$review-spec`
- `$spec-merge-cleanup`
- `$architecture-remediation`
- `$project-tracking`

For source-code changes, follow `$coding-standards`.

For commits, follow `$conventional-commits` in `.agents/skills/conventional-commits/SKILL.md`. Do not reconstruct commit-message rules from memory or restate a divergent local convention.

For Living Entity Wiki work, use the current contracts for `$wiki-sync`, `$wiki-lint`, and `$wiki-synthesize` as applicable.

### 3. Identify the active durable artifacts

Determine which repository and tracker artifacts represent the work currently in progress.

Depending on the task, inspect only the smallest relevant set, such as:

- active Wayfinder maps;
- Specs and their dependency relationships;
- Tickets and Ticket baselines;
- verification or review receipts;
- current architecture documents and ADRs;
- `wiki/index.md` and relevant `wiki/entities/` pages;
- research or audit documents under `docs/research/`;
- process guidance under `docs/process/`;
- relevant GitHub Issues, pull requests, and Project projection state.

Do not perform a broad repository tour when narrower evidence is sufficient.

### 4. Reconstruct workflow state from durable evidence

Treat the delivery workflow as a state machine rather than assuming a one-way pipeline.

The normal path is approximately:

```text
$wayfinder
    ↓
$to-specs
    ↓
$to-tickets
    ↓
$implement-ticket
    ↓
$verify-spec
    ↓
$review-spec
    ↓
$spec-merge-cleanup
```

Verification failure, review findings, remediation, or genuine architectural ambiguity may cause re-entry into an earlier state.

Keep these concepts distinct:

- **technical dependency** — what is allowed to advance;
- **project focus** — what the team has chosen to advance now;
- **workflow state** — where an artifact is in its lifecycle;
- **Project state** — the board's projection of durable state.

Do not invent dependency edges to express project focus or work-in-progress preference.

### 5. Reconstruct architectural context only as needed

Use Wayfinders for genuine architectural uncertainty, not as a mandatory wrapper around ordinary cleanup or implementation.

Typical routing:

- obvious mechanical cleanup → direct change or focused Spec;
- dead or stale code with clear ownership → direct cleanup;
- structural refactor with known semantics → Refactor Spec;
- implementation of already accepted architecture → implementation work;
- unclear canonical ownership → Wayfinder;
- competing abstractions or unresolved boundaries → Wayfinder;
- implementation that would need to invent or change durable semantics → architecture re-entry.

Do not infer architectural uncertainty merely from file size, complexity, duplication, or poor metrics.

### 6. Restore the Current Session Ledger

After durable state is reconstructed, read the **Current Session Ledger** at the bottom of this document.

Use it only to restore the exact stopping point and session-only context that cannot be recovered cheaply or reliably from the repository/tracker.

For every ledger entry that matters to the resumed task:

1. verify any repository/tracker facts against current durable state;
2. treat local-only state as provisional until the user confirms it or supplies current output;
3. discard or revise entries that have become stale, contradicted, completed, or durably persisted elsewhere;
4. continue from the smallest correct next action rather than replaying completed work.

The user should not need to provide a separate `LAST ACTIVE THREAD` when the ledger is current.

### 7. Check for conflicts before continuing

Before resuming work, identify any material conflict among:

- the Current Session Ledger;
- current repository state;
- current tracker state;
- applicable skill contracts;
- architectural authorities.

Surface genuine conflicts explicitly rather than silently selecting whichever state is easiest to continue from.

### 8. Report the recovered state concisely

The initial response after reconstitution should state only:

- the current repository/workflow state;
- the active objective;
- the exact stopping point;
- the next logical action;
- any genuine uncertainty or blocker.

Do not respond with a generic Polaris overview or repeat every artifact inspected.

## Collaboration Boundary

Perform work directly through available repository, GitHub, and other connected tooling whenever possible.

The normal collaboration model is:

1. the agent performs every safe workflow/repository/tracker step that its available tools support;
2. when a required step depends on local state or an unavailable connector capability, the agent gives the user the exact command(s) needed to perform only that missing step;
3. the user runs the command(s) and returns the output;
4. the agent treats that output as evidence and resumes the workflow from the correct durable checkpoint rather than restarting completed work.

A connector limitation is not, by itself, a reason to abandon an otherwise executable workflow. For example, when the connected GitHub tool cannot perform an operation that the authenticated GitHub CLI can perform, provide the exact `gh` commands for the user to run outside Codex and continue from the returned result.

When the user explicitly asks for the literal `gh`/Bash commands that a workflow or skill would execute, answer at that command layer. Do not substitute another skill invocation or redirect the user back through the workflow when the requested underlying commands can be provided safely.

Ask the user to run local commands only when the required state or operation is unavailable remotely, such as:

- uncommitted local changes;
- local test execution;
- profiling;
- local repository-analysis tools;
- environment-specific scripts or services;
- GitHub operations that are supported by the user's authenticated `gh` CLI but not by the available connector.

When local execution is required:

- provide exact Linux/bash commands;
- **every Bash command block must be a subshell using `(...)`**;
- make the block fail closed where practical (`set -euo pipefail`, explicit expected-state checks, or equivalent safeguards);
- minimize the commands to the missing operation rather than handing the whole workflow back to the user;
- use the returned output as evidence before mutating subsequent durable state.

## Current Session Ledger Maintenance

The agent owns maintenance of the **Current Session Ledger** appended to this document.

### Maintenance responsibility

Update the ledger on `main` whenever materially important session context has accumulated that is needed for accurate continuation but is not durably persisted in another authoritative repository/tracker artifact.

The user should not need to notice that the ledger is stale or ask for an update. The agent decides when an update is warranted.

Natural maintenance checkpoints include:

- after a meaningful workflow transition when some continuation context remains session-only;
- after the user supplies important local-only command output that affects the next action;
- after an accepted decision or sequencing choice that has not yet acquired its authoritative home;
- before moving into another long or multi-stage thread when the current stopping point would otherwise exist only in conversation;
- when a tool limitation creates a user-executed handoff that must survive session loss;
- when the active objective or exact next action changes materially.

Do not update the ledger for every exchange. Prefer compact, high-signal checkpoint updates.

### What belongs in the ledger

Record only context whose loss would materially reduce reconstitution accuracy or force the user to explain the session again, for example:

- current active thread and exact stopping point;
- current intended next action when it is not already obvious from durable workflow state;
- local-only state or command results that remain relevant;
- temporary unresolved decisions/assumptions awaiting durable persistence;
- important collaboration/tool handoffs in progress;
- explicit user direction about near-term sequencing that is not represented by tracker dependencies or another durable artifact.

### What does not belong in the ledger

Do not duplicate facts that are already cheaply recoverable from their authoritative source, including:

- full Spec requirements or contracts;
- issue bodies, verification/review receipts, or blocker ledgers;
- current architecture already defined by ADRs/docs/wiki;
- commit histories or branch contents;
- GitHub Project fields;
- large command logs once their result is durably reflected elsewhere.

Reference the authoritative artifact instead when useful.

### Ledger lifecycle

Treat the ledger as a maintained scratch pad, not an append-only historical log.

- revise existing entries when the active state changes;
- remove entries once their information becomes durably persisted elsewhere or is no longer relevant;
- remove stale local-only assumptions after they are verified or superseded;
- keep the ledger short enough to scan during every reconstitution;
- preserve only the **current** recovery state, not a narrative history of prior sessions.

Ledger maintenance is always committed directly to `main`, even when active product work is occurring on another branch. Do not write the ledger checkpoint onto the feature/Spec branch or wait for that branch to merge. Update only this process document for the ledger checkpoint and follow `$conventional-commits` for the commit message.

## Recommended New-Session Prompt

A new session normally needs only this bootstrap message:

```markdown
We are continuing work on Polaris:
https://github.com/sponge-b0b/Polaris

Reconstitute our working session using
`docs/process/session-reconstitution.md`.

Read the repository's current durable state and the Current Session Ledger;
do not assume previous conversation state is still correct.

After reconstructing the state, tell me where we are, what should happen next,
and whether you have any genuine blocking questions.
```

The user may add local-only information when something changed after the ledger was last maintained, but a routine session restart should not require a manually written handoff.

## Design Constraint

Keep the permanent portion of this document focused on **how to recover context**. Keep the Current Session Ledger focused on the small amount of **current ephemeral context** needed to finish recovery.

If a rule, architectural decision, workflow contract, domain definition, audit finding, or delivery state already has an authoritative home elsewhere in Polaris, reference that source rather than copying it into the ledger.

That keeps reconstitution durable without turning this document into a second source of truth.

---

# Current Session Ledger

> **Ephemeral recovery state only.** Validate repository/tracker facts against their authoritative sources during reconstitution. If this section conflicts with durable state, durable state wins unless the user explicitly resolves it otherwise.

**Last maintained:** 2026-08-29

## Active thread

- The active thread is **common-sense invariant hardening across Polaris agent workflows**: converting correctness-critical prose reasoning into transition-bound state where a mistaken or skipped reasoning step could otherwise authorize `PASS`, `proven`, publication, mutation, closure, routing, or another durable lifecycle transition.
- The complete audit, design principles, per-skill findings, counterexamples, and hardening order are durably recorded in `docs/process/common-sense-invariant-hardening.md`.
- The first hardening target, `$spec-contract`, is complete on `main`. It now requires a complete Source Unit Inventory before manifest construction so zero unmapped obligations cannot be achieved by silently failing to notice a normative source unit.
- The intended next hardening target is `$implement-ticket`, followed by `$verify-root-closure`, `$review-spec`, `$review-architecture`, and `$verify-code` unless new evidence changes the order.

## Session-only continuation notes

- The user intentionally paused the active Spec #240 / ticket #260 execution thread to complete the common-sense invariant audit and hardening sequence first.
- Review/remediation work should become progressively harder to surprise upstream stages: ordinary explicit obligations should be caught by Spec contract, ticket decomposition, implementation, or verification rather than repeatedly rediscovered during review.
- Hardening must remain generic. Do not encode the latest historical symptom (for example, one fake/fixture or CLI-help defect) as the invariant; bind the underlying proof/universe/semantic-transition rule instead.
- Avoid creating a universal `$reasoning-integrity` helper that can itself become another checkbox. Enforcement belongs in the transition-owning skill's local state schema.
- After the hardening sequence is paused or completed and work returns to Spec #240, revalidate current durable branch/tracker state. Because `main` has advanced during hardening, `spec-240` may need another clean `main` merge before ticket #260 pins its `Ticket baseline`.
- All Bash command blocks supplied to the user must use a subshell `(...)`.

## Outstanding ephemeral state

- No local-only command result is required to continue the hardening thread; the relevant audit and completed `$spec-contract` change are already durable on `main`.
- Do not begin ticket #260 from remembered branch state. Re-read current `main`, `spec-240`, issue #260, and applicable skills before resuming that lifecycle.
