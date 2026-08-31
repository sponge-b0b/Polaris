# Session Reconstitution

## Purpose

This guide defines how a ChatGPT-hosted Polaris working session should:

1. reconstruct enough durable project context to continue prior work safely and efficiently; and
2. maintain the small amount of session-only continuation state that would otherwise be lost if the ChatGPT conversation ends unexpectedly.

It is a **ChatGPT bootstrap, recovery, and active-session continuity procedure**, not a source of architectural truth, workflow state, or domain semantics.

The goal is to avoid rebuilding project context from large conversation transcripts when the repository and tracker already preserve durable state, while durably checkpointing only the ephemeral continuation state that the repository and tracker cannot recover cheaply or reliably.

## Runtime Scope

This process exists specifically for **ChatGPT-hosted Polaris working sessions** where conversational context can be lost between sessions.

It is **not** a Codex workflow skill, is not part of the Polaris delivery state machine, and must not be invoked or composed by repository workflow skills.

Codex agents do not need to consider or maintain the ChatGPT Session Ledger unless a human explicitly asks them to modify this process itself.

During a ChatGPT working session, the ChatGPT agent that reconstitutes the session owns subsequent ledger synchronization for the remainder of that active session.

## Core Principle

Reconstitute from durable project state first, then restore the minimum necessary ephemeral state from the dedicated **ChatGPT Session Ledger** GitHub singleton.

Durable repository/tracker state remains authoritative. The ledger exists only for context that would otherwise be stranded in a conversation, such as:

- the exact task or thread that was in progress;
- the exact workflow checkpoint at which work stopped;
- the last local-only command/result needed to resume safely;
- an uncommitted or unpushed local state that is not visible remotely;
- unreferenced Git blobs, trees, or other temporary recovery handles needed to recover a candidate exactly;
- a temporary decision, sequencing choice, or working assumption that has not yet been persisted to its authoritative artifact;
- a tool/capability handoff that requires the user to perform the next mechanical step outside the agent's available tooling.

The ledger must contain **one active continuation record**, not an accumulating session history. Once older context is durably represented elsewhere or no longer describes the active thread, remove it from the ledger rather than preserving it as background narrative.

If remembered conversation or the ChatGPT Session Ledger conflicts with current durable state, surface the conflict and prefer the applicable authority defined by `AGENTS.md` unless the user explicitly resolves it otherwise.

## Authority

Start with `AGENTS.md` and follow its authority model.

In particular:

- code, configuration, executable checks, and relevant tests describe implementation reality;
- accepted ADRs define active architectural decisions;
- `docs/current/` describes current architecture;
- `wiki/entities/` contains derived architectural knowledge;
- workflow artifacts and native tracker relationships define delivery state;
- the GitHub Project is an operational projection and does not override authoritative repository or tracker state;
- the ChatGPT Session Ledger is an ephemeral recovery aid and never overrides any of the above.

Do **not** read `CONTEXT.md` merely because a session is being reconstructed. Follow the `AGENTS.md` rules for when canonical domain vocabulary actually requires it.

## ChatGPT Session Ledger Singleton

The mutable ledger lives outside Git history in exactly one dedicated open GitHub issue.

Canonical singleton identity:

```text
Title: ChatGPT Session Ledger
Issue body marker: <!-- polaris-chatgpt-session-ledger-control:v1 -->
State comment marker: <!-- polaris-chatgpt-session-ledger-state:v1 -->
```

The singleton is ChatGPT recovery infrastructure only. It must not be treated as a Wayfinder, Spec, Ticket, verification/review artifact, dependency authority, Project Delivery artifact, or GitHub Project item.

Resolve the singleton from current GitHub state. Require exactly one open issue with the exact title and control marker. Multiple matching issues fail closed.

The issue must contain exactly one machine-managed state comment with the state marker. Zero state comments are valid only during first-time bootstrap when the current continuation state can be reconstructed safely; otherwise missing state is invalid. Multiple state comments fail closed.

### Ledger State Contract

The state comment contains exactly one current continuation record using this shape:

```text
<!-- polaris-chatgpt-session-ledger-state:v1 -->
# Current Session Ledger

**Version:** 1
**Generation:** <positive integer>
**Maintained at:** <RFC 3339 timestamp with timezone offset>

## Active Continuation Record

**Active branch:** <branch | None>
**Active artifact:** <canonical issue/PR/artifact reference | direct task>
**Workflow owner:** <$skill | direct>
**Workflow checkpoint:** <precise completed stage / next suspended stage>
**Last durable commit:** <full SHA | None>
**Baseline / anchor:** <full SHA or durable artifact anchor | None>
**Candidate state:** <durable candidate/recovery description | None>
**Expected next transition:** <one concise transition>

## Session-Only Evidence

- <only current evidence that cannot be recovered cheaply from durable authority>

## Recovery Handles

- <exact local/unreferenced recovery handle needed to resume | None>
```

`Generation` is monotonic. Every successful synchronization increments the prior generation exactly once. `Maintained at` records when that generation was durably written; elapsed time alone never triggers an update.

The routing coordinates are not workflow authority. Verify every applicable coordinate against current durable state before using ledger prose.

Treat the record as stale when any coordinate that should still be true is contradicted by durable state, for example:

- the active artifact has closed or changed lifecycle owner;
- the declared branch no longer exists or no longer points at the recorded durable candidate;
- the baseline/anchor no longer matches the durable workflow artifact;
- the recorded checkpoint has already been completed durably;
- the expected next transition is no longer reachable from the current native frontier.

A stale coordinate does not authorize guessing a replacement from the rest of the ledger. Reconstruct the replacement from durable repository/tracker state, report the conflict when material, and continue from the smallest correct next action.

## Phase 1 — Session Reconstitution

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

### 6. Restore the ChatGPT Session Ledger

After durable state is reconstructed, resolve the ChatGPT Session Ledger singleton and read its state comment.

Use it only to restore the exact stopping point and session-only context that cannot be recovered cheaply or reliably from the repository/tracker.

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
- exact unreferenced Git blob/tree IDs or equivalent recovery handles;
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

- the ChatGPT Session Ledger;
- current repository state;
- current tracker state;
- applicable skill contracts;
- architectural authorities.

Surface genuine conflicts explicitly rather than silently selecting whichever state is easiest to continue from.

### 8. Repair and activate continuity

After reconstruction, compare the ledger coordinates with the recovered authoritative state.

If the ledger is stale but the correct replacement can be established safely from durable state plus trustworthy current-session evidence, synchronize it immediately before substantive work continues. If missing ephemeral evidence prevents safe repair, report the gap rather than inventing replacement state.

After a valid or repaired ledger is established, retain its exact normalized continuation state as the in-session `LAST_SYNCED_CONTINUATION_STATE` and activate **Phase 2 — Active Session Continuity** for the remainder of the ChatGPT working session.

### 9. Report the recovered state concisely

The initial response after reconstitution should state only:

- the current repository/workflow state;
- the active objective;
- the exact stopping point;
- the next logical action;
- any genuine uncertainty or blocker.

Do not respond with a generic Polaris overview or repeat every artifact inspected.

## Phase 2 — Active Session Continuity

### Continuity Invariant

After successful reconstitution, the ChatGPT agent owns synchronization of the singleton for the rest of the active ChatGPT working session.

Do **not** wait until the conversation appears likely to end. A ChatGPT session may terminate unexpectedly. Continuation state must be checkpointed when it materially changes.

Freshness is **state-based, not time-based**:

```text
CURRENT_CONTINUATION_STATE != LAST_SYNCED_CONTINUATION_STATE
```

Elapsed time alone is never a synchronization trigger. A long interval with no continuation-state change may require no write; several meaningful workflow transitions in a short interval may require several writes.

### Mandatory Synchronization Points

At each event below, recompute the current continuation state. If it differs from `LAST_SYNCED_CONTINUATION_STATE`, synchronize the singleton before proceeding past the boundary.

| Event | Required action |
| --- | --- |
| Active artifact changes | Synchronize |
| Workflow owner changes | Synchronize |
| Active branch changes | Synchronize |
| Baseline/anchor becomes known or changes | Synchronize |
| Durable candidate commit/`HEAD` changes | Synchronize |
| Workflow checkpoint materially advances | Synchronize |
| Expected next transition changes | Synchronize |
| A workflow completes and another becomes next | Synchronize |
| User supplies local-only evidence required for continuation | Synchronize |
| Local-only validation, profiling, service-probe, or test evidence becomes important to re-entry | Synchronize |
| Uncommitted or unpushed state becomes important to continuation | Synchronize |
| Unreferenced Git blobs/trees or another fragile temporary recovery handle are created | **Synchronize immediately** |
| Previously ephemeral state becomes durable elsewhere | Synchronize and remove redundant ledger evidence |
| A human handoff is reached | Synchronize **before returning control** |
| A hard blocker is reached | Synchronize **before returning control** |
| A completed response establishes a new exact stopping point | Synchronize **before returning control** |
| No meaningful ephemeral continuation state remains | Synchronize to the minimal current durable coordinates |

A state transition that matches a Mandatory Synchronization Point is the trigger. Do not replace this table with a subjective test such as “worth preserving,” “important enough,” or “session seems nearly finished.”

### Fragile-State Immediate Checkpoint

Fragile state is session-only state that may become unrecoverable if the current conversation or tool context disappears, including:

- unreferenced Git blob/tree/commit objects;
- temporary candidate-tree identifiers;
- local-only command output required to avoid repeating or mis-sequencing work;
- unpushed commits or branch positions not observable from the remote;
- other opaque recovery handles whose identifiers exist only in the active conversation/tool context.

When such state is created or becomes necessary for exact continuation, synchronize it **immediately**. Do not wait for a later workflow handoff.

If the state cannot be durably represented safely, record the limitation and the smallest reproducible reconstruction path instead of implying that the exact candidate is recoverable.

### Synchronization Protocol

For every required synchronization:

1. resolve and revalidate the canonical singleton issue;
2. read the one state-marker comment and its current `Generation`;
3. derive `CURRENT_CONTINUATION_STATE` from current authoritative state plus only necessary session-only evidence;
4. remove stale or now-durable evidence rather than appending history;
5. increment `Generation` by exactly one;
6. set `Maintained at` to the current RFC 3339 timestamp with timezone offset;
7. replace the existing state comment in one write;
8. read back that exact comment;
9. require the persisted body to equal the intended body exactly;
10. only after exact readback succeeds, set `LAST_SYNCED_CONTINUATION_STATE` to the newly persisted normalized state.

Do not create a new comment for every synchronization. The singleton keeps exactly one mutable state comment so it represents current continuation state rather than a session history.

If the write succeeds but exact readback fails, do not assume continuity state is healthy. Report the mismatch and recover the canonical state before relying on the ledger again.

### ChatGPT Return Guard

Once Phase 2 is active, the ChatGPT agent must not intentionally return control at a meaningful continuation boundary with stale ledger state.

Before a response that:

- asks the user to run a command whose result is required to continue;
- hands off to another workflow or lifecycle owner;
- reports a hard blocker;
- reports completion;
- or otherwise establishes a new exact stopping point,

compare `CURRENT_CONTINUATION_STATE` with `LAST_SYNCED_CONTINUATION_STATE`.

If they differ, synchronize first.

The practical guard question is:

```text
Would a fresh ChatGPT session need a different continuation record after this response?
```

If yes, synchronization is required before the response is treated as the stopping point.

### Ledger Hygiene

At every synchronization:

- keep exactly one Active Continuation Record;
- replace superseded continuation notes rather than appending history;
- remove facts that have acquired another durable authoritative home unless still needed as re-entry coordinates;
- preserve only current session-only evidence needed to avoid repeating completed local work;
- use full commit SHAs for durable commit/baseline coordinates;
- store exact opaque recovery handles when they are necessary and safe to persist;
- never turn the ledger into a substitute verification receipt, review record, architecture decision, root checkpoint, workflow state store, or Project state store.

If there is no meaningful ephemeral continuation state, record that explicitly and keep the ledger minimal.

## Collaboration Boundary

Perform work directly through available repository, GitHub, and other connected tooling whenever possible.

The normal collaboration model is:

1. the agent performs every safe workflow/repository/tracker step that its available tools support;
2. when a required step depends on local state or an unavailable connector capability, the agent gives the user the exact command(s) needed to perform only that missing step;
3. the user runs the command(s) and returns the output;
4. the agent treats that output as evidence and resumes the workflow from the correct durable checkpoint rather than restarting completed work.

A connector limitation is not, by itself, a reason to abandon an otherwise executable workflow. For example, when the connected GitHub tool cannot perform an operation that the authenticated GitHub CLI can perform, provide the exact `gh` commands for the user to run outside ChatGPT and continue from the returned result.

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
