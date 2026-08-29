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

#

---

# Current Session Ledger

> **Ephemeral recovery state only.** Validate repository/tracker facts against their authoritative sources during reconstitution. If this section conflicts with durable state, durable state wins unless the user explicitly resolves the conflict otherwise.

**Last maintained:** 2026-08-29

## Active thread

- The common-sense invariant audit and reasoning model are durable in `docs/process/common-sense-invariant-hardening.md`.
- First-stage transition-bound hardening is durable through `$spec-contract` source-universe closure and commit `91cb99fa7f58f5e145050126b764d1f34792ff7c` (`fix(workflow): enforce transition-bound invariants`).
- A full `$verify-spec` rerun for Spec #240 at exact HEAD `06118a1709f78f3eed9bb322be161ca2621d8f03` produced a false PASS, which exposed **No Self-Certifying Semantic Transition** and **Nested Universe Closure**.
- Second-stage `$verify-spec` hardening is commit `3abffb3ee05a556ef2e8307a10a03dd32ce640b5` (`fix(verify-spec): require independent proof certification`). It introduced durable Proof Objects, nested-domain witnesses, proof-packet hashing, and genuinely fresh non-mutating semantic proof certification.
- The first real run under that model worked adversarially: fresh certifiers rejected proof, exposed the stale backtest fake-contract defect, then exposed an invalid non-empty control-command behavior. Verification repaired those on `spec-240` as `cd6ece5` and `ac6c1b8` respectively. A third fresh certifier was spawned for the final packet, but the Codex usage limit terminated the run before a result or passing receipt was produced. Do not infer that certification result.
- Current `spec-240` candidate HEAD from that interrupted run is `ac6c1b8865fd4e9a1da4ff43c0f171d34f1a1de8`; verify against durable branch state before acting because the user may have advanced it.
- Efficiency hardening is now on `main` in `5ec01e2bcb460f4f364d7aa70558d39f41d65dc5` (`fix(verify-spec): make proof certification incremental`). `$verify-spec` now uses certifier-approved Proof Object invalidation boundaries/evidence stability, deterministic fail-closed carry-forward for unaffected repository-immutable certification, reduced certification slices containing only stale objects, and semantic-first execution that delays broad final gates until proof convergence.

## Session-only continuation notes

- The immediate product step is to merge current `main` into `spec-240` (merge, do not rebase) before relying on the new incremental policy, then rerun `$verify-spec`.
- That merge changes exact HEAD and includes a normative `$verify-spec` proof-policy change. Therefore semantic certification produced under the previous policy is non-inheritable for the first run after the merge; expect one fresh certification pass over the current Proof Objects. The efficiency gain applies to subsequent repair iterations in that run: only stale/uncertified Proof Objects should be sent to new fresh certifiers.
- The first run under `5ec01e2...` should perform candidate semantic proof before broad final gates. Expensive final formatter/linter/type/regression gates are delayed until semantic proof converges unless one is direct Proof Object evidence.
- After a repository repair, retain a prior certification only when the Proof Object hash is unchanged, its fresh certifier approved a complete invalidation boundary and `repository-immutable` evidence stability, proof policy remains compatible, and deterministic changed-path analysis has zero boundary intersection. Any uncertainty makes the object stale.
- Fresh-certifier independence remains mandatory for stale Proof Objects; there is no same-agent/owner override. Token economy must never weaken fail-closed invalidation.
- Do not run `$review-spec` merely to rediscover defects while `$verify-spec` is still incomplete. Complete verification under the current policy first.
- Future workflow hardening should remain generic: first test failures against Transition-Bound Reasoning, Universe Closure, Nested Universe Closure, Explicit Escape Disposition, No Self-Certifying Semantic Transition, falsification-first proof, evidence entailment, and certifier-approved invalidation boundaries before adding a defect-specific rule.
- Temporary hardening branches/scripts/workflows are scratch only and are not workflow authority. The agent owns future ledger maintenance on `main`.
- All Bash command blocks supplied to the user must use a subshell `(...)`.

## Outstanding ephemeral state

- No known uncommitted Polaris product-code change is represented by this ledger. Local repository state must still be verified when relevant.
- Re-read current `main`, `spec-240`, issue #240 verification receipt/history, and Project state before acting in a fresh session; durable state wins if the user has already completed the merge or another verification attempt.
