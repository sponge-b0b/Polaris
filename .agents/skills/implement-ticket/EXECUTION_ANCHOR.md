---
name: implement-ticket
description: Implement one exact deterministic ticket contract, run applicable technical checks, obtain fresh independent closure proof, and close only the exact certified candidate.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

## Authoritative procedure composition

Before executing this skill, read `.agents/skills/implement-ticket/PROCEDURE.md` in full.
That file preserves the complete established `$implement-ticket` procedure. This
`SKILL.md` is the authoritative entrypoint and owns the execution-anchor corrections below;
on conflict, this file wins. Failure to load the retained procedure is a hard blocker.

The retained procedure continues to own Invocation termination, durable ticket recovery,
hierarchy/dependency/project-delivery admission, architecture-blocker admission, deterministic
contract construction, implementation scope, technical checks, Durable closure checkpoint
v3, Independent closure dispatch, certified persistence/closure, and Frontier handoff except
where this entrypoint explicitly replaces Ticket-baseline-relative candidate mechanics.

## Execution-anchor invariant

`Ticket baseline` and `Execution Anchor` are different authorities:

```text
Ticket baseline
    immutable per-ticket historical / lineage anchor

Execution Anchor
    exact fetched remote shared-Spec-branch commit at which this implementation attempt
    begins, before this ticket makes substantive candidate changes
```

A pinned Ticket baseline remains immutable. Legitimate shared-branch advancement after that
baseline may include accepted CCL/ADR/Spec reconciliation, prerequisite ticket completion,
workflow-policy synchronization, or other already-durable shared-branch history. Such
advancement is not automatically this ticket's implementation candidate.

The current ticket candidate is **only** the Git-relevant path state that differs from the
Execution Anchor (plus untracked non-ignored paths). Do not compute candidate identity from
the historical Ticket baseline once an Execution Anchor has been admitted.

This distinction does not weaken fail-closed behavior. A new Execution Anchor may be minted
only before substantive mutation, from a clean worktree at the exact fetched remote shared
branch tip, after the current ticket contract and all admission guards validate. An existing
current v3 closure checkpoint means resume that checkpoint's attempt; do not mint a fresh
Execution Anchor to launder or hide an earlier candidate.

## Guard branch, immutable Ticket baseline, and current remote state

Apply the retained `## 1. Recover durable ticket state`, hierarchy, native blocker,
architecture-blocker, and project-delivery guards first. Build and validate the exact current
ticket/remediation contract before pre-mutation Attention.

Keep the retained Ticket-baseline rules with these corrections:

* `Pending` still pins the exact shared-branch HEAD before first substantive mutation and is
  then immutable.
* A full-SHA Ticket baseline must exist and be an ancestor of the admitted Execution Anchor.
  Do not require the current shared branch to equal that historical SHA.
* Never recompute or overwrite a pinned baseline merely because accepted upstream/shared
  branch history advanced.

Before a fresh pre-mutation Attention gate:

1. require a clean worktree and the exact declared ticket branch;
2. fetch the actual remote ticket branch, not merely the local tracking ref;
3. if local HEAD is behind the fetched remote tip and is its ancestor, fast-forward only
   (`git merge --ff-only`) while still clean; this synchronization is shared-branch recovery,
   not ticket candidate mutation;
4. if local HEAD is ahead, diverged, dirty, or cannot fast-forward exactly, stop as a Hard
   Blocker rather than guessing, resetting, stashing, or force-updating;
5. re-run/re-read current parent Spec, coverage, ticket contract, native blockers,
   architecture-blocker state, and project-delivery admission on that synchronized state;
6. resolve the current `implement-ticket-closure-checkpoint:v3`. If one exists, use the
   retained resume/dispatch rules and its recorded Execution Anchor. Do not start a new
   pre-mutation attempt over it.

The machine gate itself fetches the remote branch again and rejects a stale local HEAD, so a
stale `origin/<branch>` tracking ref cannot satisfy this guard by itself.

## Pre-mutation Attention and Execution Anchor capture

The retained formal `$attention` checkpoint remains mandatory with exactly:

```text
Checkpoint: $implement-ticket pre-mutation
```

Write that exact formal result to a temporary file outside the candidate, then invoke the
machine gate directly as documented; no `PYTHONPATH` workaround is required:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py pre-mutation \
  --ticket <ticket-number> \
  --contract <ticket-or-remediation-contract.json> \
  --baseline <immutable-ticket-baseline> \
  --branch <ticket-branch> \
  --remote origin \
  --attention-result <pre-mutation-attention-result-file>
```

Require:

```text
IMPLEMENT TICKET ATTENTION: PRE-MUTATION VALID
Ticket baseline: <immutable sha>
Execution Anchor: <exact fetched remote branch tip>
```

Capture the exact `Execution Anchor` and `Attention Receipt Hash`. The receipt schema is
`polaris.implement-ticket-attention/v2` and binds ticket, branch, immutable Ticket baseline,
Execution Anchor, exact current contract hash, pre-mutation Attention result, and the clean
candidate state relative to the Execution Anchor.

No substantive mutation is allowed until this command succeeds.

The old retained rule that admitted `baseline -> HEAD` only when it was default-branch
workflow-policy synchronization is superseded. Non-retroactivity is now enforced by the
clean exact-remote Execution Anchor plus the rule that HEAD may not change after the
pre-mutation gate until certification/persistence.

## Candidate identity and pre-closure Attention

Every retained candidate-state algorithm remains byte-for-byte the same except replace the
Git diff base `TICKET_BASELINE` with `EXECUTION_ANCHOR`:

```text
path universe =
    git diff --no-renames --name-only -z <execution-anchor> --
    union untracked non-ignored paths
```

This `TICKET_CLOSURE_STATE` therefore identifies only this attempt's candidate, excluding
already-durable shared-branch history between Ticket baseline and Execution Anchor.

Before closure dispatch, run the retained pre-closure Attention sweep and bind it with:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py pre-closure \
  --ticket <ticket-number> \
  --contract <ticket-or-remediation-contract.json> \
  --baseline <immutable-ticket-baseline> \
  --branch <ticket-branch> \
  --execution-anchor <execution-anchor> \
  --attention-result <pre-closure-attention-result-file>
```

Then verify the frozen receipt with:

```bash
python .agents/skills/implement-ticket/scripts/attention_gate.py verify \
  --ticket <ticket-number> \
  --contract <ticket-or-remediation-contract.json> \
  --baseline <immutable-ticket-baseline> \
  --branch <ticket-branch> \
  --execution-anchor <execution-anchor> \
  --expected-receipt-hash <attention-receipt-hash>
```

Require `IMPLEMENT TICKET ATTENTION: PRE-CLOSURE VALID` and then
`IMPLEMENT TICKET ATTENTION: VALID`. The gate rejects any committed HEAD movement after the
Execution Anchor and any stale candidate bytes.

## Durable closure checkpoint v3 and independent verifier binding

The retained `implement-ticket-closure-checkpoint:v3` schema is strengthened with:

```markdown
**Ticket baseline:** <immutable historical sha>
**Execution Anchor:** <exact pre-mutation fetched shared-branch sha>
**Candidate state:** <hash relative to Execution Anchor>
```

Persist/read back the Execution Anchor anywhere the retained procedure currently binds
Ticket baseline and candidate identity. Dispatch `$verify-ticket-closure` with both values.
The verifier result must bind both values exactly.

An existing v3 checkpoint without an Execution Anchor is not silently upgraded by minting a
new attempt over the same candidate. If its exact candidate was created under the older
receipt schema, fail closed and route to the owning recovery path; do not retroactively
assert a v2 pre-mutation receipt.

## Persistence and representation independence

Before commit/push, the Attention verifier runs while HEAD still equals the Execution Anchor.
After independent closure PASS, commit only the exact certified candidate and push without
force under the retained persistence rules.

Representation independence is preserved: recomputing candidate content relative to the
same Execution Anchor before and after committing the exact bytes yields the same candidate
identity. Ticket baseline remains immutable lineage evidence and is never substituted for
the Execution Anchor in candidate hashing.

## Frontier handoff

The retained Frontier handoff remains authoritative after exact persistence, ticket closure,
and dependency/frontier readback. Execution-anchor recovery does not change native
dependency actionability or authorize implementation of a blocked sibling.
