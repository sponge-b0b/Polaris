# Session Reconstitution

## Purpose

This guide defines how a new agent session should reconstruct enough Polaris context to continue prior work safely and efficiently.

It is a **bootstrap and recovery procedure**, not a source of architectural truth, workflow state, or domain semantics.

The goal is to avoid rebuilding project context from large conversation transcripts when the repository and tracker already preserve durable state, while also preserving the small amount of important session-only context that has not yet acquired another durable home.

## Core Principle

Reconstitute from durable project state first, then restore the minimum necessary ephemeral state from the **Current Session Ledger** at the bottom of this document.

Durable repository/tracker state remains authoritative. The ledger exists only for context that would otherwise be stranded in a conversation, such as:

- the exact task or thread that was in progress;
- the exact workflow checkpoint at which work stopped;
- the last local-only command/result needed to resume safely;
- an uncommitted or unpushed local state that is not visible remotely;
- a temporary decision, sequencing choice, or working assumption that has not yet been persisted to its authoritative artifact;
- a tool/capability handoff that requires the user to perform the next mechanical step outside the agent's available tooling.

The ledger must contain **one active continuation record**, not an accumulating session history. Once older context is durably represented elsewhere or no longer describes the active thread, remove it from the ledger rather than preserving it as background narrative.

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

When the active workflow has a durable branch and baseline/anchor, compare that exact baseline/anchor to the branch `HEAD` and confirm the changed-file surface before assuming what work is present. Do not substitute a broad recent-commit scan when a durable comparison anchor exists.

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

#### Active Continuation Record

The ledger must contain exactly one **Active Continuation Record** with these re-entry coordinates:

```text
Active branch: <branch | None>
Active artifact: <canonical issue/PR/artifact reference>
Workflow owner: <$skill | direct>
Workflow checkpoint: <precise completed stage / next suspended stage>
Last durable commit: <full SHA | None>
Baseline / anchor: <full SHA or durable artifact anchor | None>
Expected next transition: <one concise transition>
```

These fields are routing coordinates, not workflow authority. Verify every applicable coordinate against current durable state before using ledger prose.

Treat the record as stale when any coordinate that should still be true is contradicted by durable state, for example:

- the active artifact has closed or changed lifecycle owner;
- the declared branch no longer exists or no longer points at the recorded durable candidate;
- the baseline/anchor no longer matches the durable workflow artifact;
- the recorded checkpoint has already been completed durably;
- the expected next transition is no longer reachable from the current native frontier.

A stale coordinate does not authorize guessing a replacement from the rest of the ledger. Reconstruct the replacement from durable repository/tracker state, report the conflict when material, and continue from the smallest correct next action.

#### Workflow-Specific Re-entry Coordinates

Use the applicable workflow's current `SKILL.md` as authority for exact guards and semantics. The bundles below are only the minimum recovery coordinates that should normally be checked before reading broader context.

| Workflow owner | Minimum durable re-entry bundle |
| --- | --- |
| `$wayfinder` | active Wayfinder issue/map; current decision/handoff state; native blockers/dependents relevant to the active decision; current governing branch/commit when repository work is involved |
| `$to-specs` | governing Wayfinder/handoff; current derived/remediation Spec children; native dependency state; current branch/anchor required by the handoff |
| `$to-tickets` | parent Spec; Spec branch/workspace baseline; current native ticket children; ticket dependency relationships; current Spec lifecycle state |
| `$implement-ticket` | current default-branch `HEAD`; Ticket branch `HEAD`; Ticket baseline; native direct parent; ticket open/closed state; parent native child frontier; direct ticket dependents; remediation checkpoint/root state when applicable |
| `$verify-spec` | Spec branch candidate `HEAD`; Spec/workspace baseline; Spec state; open implementation/remediation children; current verification receipt/checkpoint or proof state; native blockers relevant to verification actionability |
| `$review-spec` | exact verified candidate `HEAD`; latest valid verification receipt; Spec state; current review/remediation artifact state; open remediation children when any exist |
| `$spec-merge-cleanup` | exact reviewed candidate `HEAD`; current default-branch `HEAD`; durable review/merge authorization state; current PR/merge state when applicable; remaining child/remediation state |
| `$architecture-remediation` | blocked artifact; exact unresolved architecture question/conflict; governing authority set; current remediation/decision artifact and native relationship state |

For an active branch with a durable SHA baseline, compare baseline → `HEAD` and confirm the exact changed-file set. For a suspended workflow, recover the owning skill's current contract and resume at the first incomplete authoritative stage rather than replaying already completed stages.

#### Session-Only Evidence

After the coordinates validate, restore only evidence that is not durably recoverable, such as:

- local clean/dirty working-tree state;
- results of local-only tests, profiling, or service probes;
- an unpushed commit or local branch position;
- the exact output of a human-run `gh`/shell step required by a connector boundary;
- a temporary assumption that has not yet acquired an authoritative home.

For every ledger fact that matters to the resumed task:

1. verify repository/tracker facts against current durable state;
2. treat local-only state as provisional unless the ledger contains the exact result from the prior session or the user confirms current state;
3. discard or revise facts that have become stale, contradicted, completed, or durably persisted elsewhere;
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

## Ledger Maintenance

The agent owns ledger maintenance on `main` whenever a session reaches a continuation point worth preserving.

Update the ledger when the active artifact, workflow owner, candidate commit, baseline/anchor, workflow checkpoint, or expected next transition materially changes and the new continuation state is not already cheaply reconstructable from durable workflow artifacts alone.

When updating:

- keep exactly one Active Continuation Record;
- replace superseded continuation notes rather than appending history;
- remove facts that have acquired another durable authoritative home unless they are still needed as re-entry coordinates;
- preserve only current session-only evidence needed to avoid repeating completed local work;
- use full commit SHAs for durable commit/baseline coordinates;
- never turn the ledger into a substitute verification receipt, review record, architecture decision, root checkpoint, or Project state store.

If there is no meaningful ephemeral continuation state, record that explicitly and keep the ledger minimal.

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

#

---

# Current Session Ledger

> **Ephemeral recovery state only.** Validate every re-entry coordinate against its authoritative repository/tracker source. If this ledger conflicts with durable state, durable state wins unless the user explicitly resolves the conflict otherwise.

**Last maintained:** 2026-08-29

## Active Continuation Record

**Active branch:** `spec-261`  
**Active artifact:** Implementation Ticket #262 — `https://github.com/sponge-b0b/Polaris/issues/262`  
**Workflow owner:** `$implement-ticket`  
**Workflow checkpoint:** repository implementation, targeted verification, commit, and push complete; suspended immediately before ticket closure and deterministic post-closure frontier/dependency/Project reconciliation  
**Last durable commit:** `76067f3af7edf96ea16ffb17cc71f101b564323a`  
**Baseline / anchor:** Ticket baseline `b377381ad236ba0f02e3272b62b20c18dd29bc4d`  
**Expected next transition:** re-run the current `$implement-ticket` pre-closure guards, close #262 if they still pass, derive the native post-closure frontier/dependents, reconcile #262/#261 Project projection, and hand off #261 to `$verify-spec` if no implementation-ticket child remains open

## Session-Only Evidence

- The user ran the final persistence block from the `spec-261` checkout after targeted verification succeeded.
- Targeted verification before persistence: focused Ruff and Mypy passed; the selected pytest scope was classified service-free; all 72 selected tests passed.
- Final local persistence output reported `BRANCH=spec-261`, `HEAD=76067f3af7edf96ea16ffb17cc71f101b564323a`, `UPSTREAM=origin/spec-261`, and no `git status --short` entries.
- The pushed ticket commit is `76067f3af7edf96ea16ffb17cc71f101b564323a` (`refactor(evaluations): decompose risk-authority gate stages`).

## Outstanding Ephemeral State

- No known uncommitted Polaris product-code change is represented by this ledger.
- Re-read current `main`, remote `spec-261`, #262 native parent/state, #261 native child frontier, #262 direct dependents, and the current `$implement-ticket` contract before acting. This process-document commit advances `main` independently of the already-pushed #262 product candidate; do not infer that `spec-261` also contains this ledger update.
