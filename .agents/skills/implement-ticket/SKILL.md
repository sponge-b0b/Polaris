---
name: implement-ticket
description: "Implement one ticket, prepare an immutable closure candidate, dispatch fresh independent semantic certification, and persist/close only the exact certified candidate."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

Implement one ticket and close it only after one fresh independent `$verify-ticket-closure` verdict certifies the exact candidate.

## Base Procedure

Read this file first, then read in full:

```text
.agents/skills/implement-ticket/procedure.md
```

That file preserves the pre-hardening implementation, branch, hierarchy, project-delivery, applicability, helper, verification, persistence, commit, tracker, frontier, and handoff mechanics.

Those mechanics remain normative **except where this `SKILL.md` explicitly supersedes them below**. On conflict, this file wins.

This overlay exists to harden the consequential ticket-completion transition without duplicating the stable implementation procedure.

## Superseded Base Sections

The following base concepts are replaced by this file:

* `Durable Root-Verification Checkpoint` → **Durable Ticket-Closure Checkpoint**;
* remediation-only root-verification re-entry → **common closure re-entry for every ticket**;
* any statement allowing an ordinary ticket to self-certify semantic acceptance and proceed directly to persistence/closure;
* `Spec Review Root Closure` verifier handoff/dispatch/verdict mechanics → the common **Independent Ticket Closure Gate** below;
* direct `$verify-root-closure` certification → `$verify-ticket-closure`;
* `ROOT CLOSURE: PASS|FAIL` as the ticket semantic verdict → `TICKET CLOSURE: PASS|FAIL`.

The base remediation-specific root reasoning, invariant sweep, preservation, and protected-root requirements remain applicable inputs for remediation; they are now certified inside the same common verifier rather than by a separate algorithm.

## Core Authority Invariant

> **The implementation actor may propose closure evidence, but it may not certify its own candidate.**

For every ordinary Implementation Ticket and every Review Remediation Ticket:

```text
implement
    ↓
local / delegated implementation verification
    ↓
Proposed Closure Evidence
    ↓
immutable candidate checkpoint
    ↓
automatic fresh non-mutating $verify-ticket-closure dispatch
    ↓
one TICKET CLOSURE: PASS | FAIL
    ↓
persist / commit / close only after PASS
```

Implementation checks such as `$verify-code`, documentation validation, database proof, tracker rereads, and targeted tests remain required where applicable. They provide evidence; they do not give the implementer semantic closure authority.

## Invocation Termination

This restores the pre-hardening control-flow invariant for the common ticket-closure lifecycle.

This invocation may stop only at:

* **Completed** — all required persistence, evidence, and closure gates completed;
* **Human Handoff** — another applicable workflow authority explicitly requires human authorization or judgment;
* **Hard Blocker** — a concrete external/environmental, branch, baseline, permission, required-tool, or persistence failure prevents further safe work.

Everything else is non-terminal.

In particular, partial progress, verification failure, `TICKET CLOSURE: FAIL`, corrective edits making a verdict stale, remaining actionable in-scope work, an open ticket, an `awaiting-closure-verification` checkpoint, and `TICKET CLOSURE: PASS` before final lifecycle completion do not authorize stopping.

If none applies, continue the workflow.

## Durable Ticket-Closure Checkpoint

Every ticket closure-verification attempt must survive complete session/context loss.

Use exactly one machine-managed ticket comment:

```text
<!-- implement-ticket-closure-checkpoint:v2 -->
```

Persist:

```markdown
<!-- implement-ticket-closure-checkpoint:v2 -->
## Implement Ticket Closure Checkpoint

**Version:** 2
**Stage:** awaiting-closure-verification | verifier-failed | verifier-passed
**Ticket:** #<ticket>
**Mode:** ordinary | remediation
**Ticket branch:** <branch>
**Ticket baseline:** <sha>
**Parent Spec:** #<Spec>
**Spec obligations:** <IDs | None>
**Remediation parent:** <Spec Review #n | None>
**Root:** <RB-n — invariant | None>
**Candidate state:** <TICKET_CLOSURE_STATE>
**Attempt:** <n>

### Proposed Closure Evidence
<complete current proposed acceptance evidence>

### Last verifier result
<None | exact valid TICKET CLOSURE PASS/FAIL result>

### Attempt history
- Attempt <n> | <candidate state> | <PASS|FAIL|invalid> | <concise result>
```

Use zero-or-one marker resolution and exact POST/PATCH/readback mechanics from the base checkpoint procedure, substituting the v2 marker/schema above. More than one active v2 checkpoint is ambiguous and fails closed.

### Legacy remediation checkpoint

A pre-existing `<!-- implement-ticket-root-checkpoint:v1 -->` is historical compatibility state only.

If an open remediation ticket has v1 but no v2 checkpoint:

1. re-read and validate v1 branch/baseline/lineage/root/candidate state under current authority;
2. create exactly one v2 checkpoint carrying the same attempt history and last valid verifier result as historical evidence;
3. do not treat a historical `$verify-root-closure` PASS as certification of a new or changed candidate;
4. if the exact old candidate is still the candidate and no current root/contract state changed, preserve the result only as prior evidence and require `$verify-ticket-closure` before any new closure transition.

Never maintain v1 and v2 as competing active authorities.

## Candidate State

Before verifier dispatch compute one deterministic candidate state over all repository mutations since `TICKET_BASELINE`, including untracked files. Use the base root-state hash procedure, renamed `TICKET_CLOSURE_STATE`.

For tracker-only tickets, bind the checkpoint to exact durable tracker identifiers/state required by the ticket in addition to the repository state.

A certification PASS applies only to the exact:

* ticket contract and `Spec obligations` mapping;
* branch and baseline;
* candidate state;
* lineage;
* remediation/root state when applicable;
* root-required tracker state when applicable.

Any substantive candidate mutation after PASS makes the PASS stale unless an independently certified invalidation boundary plus deterministic fail-closed delta analysis establishes that the proof remains valid. When uncertain, recertify.

## Proposed Closure Evidence

Before independent certification, build the complete **Ticket Acceptance Universe** exactly as required by the base procedure and reconcile every obligation as `proposed-proven | proposed-unproven`.

The implementer's disposition is a proposal, not certification.

For each material obligation preserve enough concise evidence for the verifier to challenge:

```text
Acceptance: TA-<n>
Source: <exact ticket / carried Spec obligation>
Claim: <exact semantic claim>
Domain: <authoritative domain>
Falsifier: <concrete false state>
Proposed evidence: <current evidence>
Proposed state: proposed-proven | proposed-unproven
```

When a claim contains an exhaustive quantifier, identify the nested domain the verifier must independently close. Do not declare a criterion complete merely because changed files or existing tests cover a convenient subset.

For remediation, Proposed Closure Evidence additionally carries the base procedure's Root Blocker invariant, carried cells, Root Invariant Sweep, preservation obligations, and protected roots. These join the common acceptance universe.

If any implementer cell remains `proposed-unproven`, continue actionable implementation/verification. Do not dispatch a knowingly incomplete candidate.

## Independent Ticket Closure Gate

After implementation and all applicable local/delegated checks are complete, but **before commit/push, closure-evidence persistence, ticket close, dependency/frontier mutation, or Completed handoff**:

1. compute current `TICKET_CLOSURE_STATE`;
2. write/update the v2 checkpoint to `Stage: awaiting-closure-verification` with the full Proposed Closure Evidence and incremented Attempt;
3. read it back and verify exact binding;
4. enter dispatcher-only mode and automatically spawn exactly one genuinely fresh `$verify-ticket-closure` verifier for that exact candidate.

Do **not** stop for human authorization between checkpoint creation and verifier dispatch. The user's `$implement-ticket` invocation already authorizes the ticket lifecycle; verifier independence comes from the fresh non-mutating certification actor, not from a second human command.

The durable checkpoint remains mandatory even though normal dispatch is automatic. It is the recovery authority if the session, process, or conversational context disappears before the verifier result is fully consumed and persisted.

## Resume / Dispatch

On every later invocation for an open ticket, recover the v2 checkpoint before choosing continuation and re-run the base branch/hierarchy/project-delivery guards.

Route:

* `awaiting-closure-verification`
  * exact matching ticket/mode/branch/baseline/contract/lineage/root/candidate state → automatically resume dispatcher-only mode and dispatch one fresh verifier;
  * this same route applies after complete session/context loss and when a human directly invokes `$verify-ticket-closure` as an optional recovery/manual entry point;
  * candidate mismatch → checkpoint stale; resume implementation and rebuild proposed evidence.
* `verifier-failed`
  * resume implementation immediately using **all** returned findings;
  * do not re-dispatch the stale candidate;
  * after corrections/checks, rebuild proposed evidence, create a new awaiting attempt, and automatically dispatch a fresh verifier.
* `verifier-passed`
  * require exact candidate/contract/baseline/branch/lineage/root binding;
  * if valid, exit dispatcher-only mode if active and resume Section 4 (`Re-Verify Before Persistence`) of `.agents/skills/implement-ticket/procedure.md` immediately in the same invocation;
  * any mismatch returns to implementation/recertification.

### Dispatcher-only mode

After creating or recovering a valid `awaiting-closure-verification` checkpoint with exact matching state, the `$implement-ticket` main agent may only:

1. capture/reconfirm exact dispatch candidate state and durable bindings;
2. spawn exactly one genuinely fresh verifier subagent;
3. pass the ticket, parent Spec, exact `Spec obligations`, baseline, candidate state, checkpoint, Proposed Closure Evidence, and applicable architecture/policy context;
4. for remediation, also pass the Spec Review, stable root, cumulative root contract, preservation state, and protected-root context;
5. require the subagent to execute `$verify-ticket-closure` as a non-mutating leaf;
6. receive the result;
7. recompute candidate/tracker state and validate verifier integrity;
8. consume only a valid `TICKET CLOSURE: PASS` or `TICKET CLOSURE: FAIL`.

The parent must not inspect toward its own closure verdict, execute `$verify-ticket-closure` itself, mutate the candidate, repair findings, or delegate further while the verifier runs.

## Verifier Result

### FAIL

`TICKET CLOSURE: FAIL` is non-terminal.

Before leaving dispatcher-only mode:

1. persist the exact valid verdict into the v2 checkpoint as `verifier-failed`;
2. preserve every returned finding and the exact candidate/binding state in `Last verifier result`;
3. append the attempt/candidate/result to `Attempt history`;
4. re-read and verify the checkpoint.

Then exit dispatcher-only mode and resume implementation **in the same invocation** when actionable.

All verifier findings remain mandatory until corrected or superseded by explicit authoritative contract change.

After correction, any prior PASS/FAIL is candidate-stale; build a new awaiting attempt and automatically dispatch a new fresh verifier. Continue this lifecycle while work remains actionable; stop only at **Completed**, another genuinely required **Human Handoff**, or a **Hard Blocker**.

### PASS

`TICKET CLOSURE: PASS` is non-terminal and requires verifier-integrity success.

Before accepting PASS require:

* verifier was genuinely fresh and non-mutating;
* no candidate/tracker mutation occurred during dispatch;
* returned ticket/baseline/candidate/contract/mode/root bindings match exactly;
* acceptance coverage has `violated=0`, `unproven=0`, `unchecked=0`;
* every required nested domain is closed;
* no unproven material assumption remains.

Before proceeding:

1. update the durable v2 checkpoint to `Stage: verifier-passed`;
2. preserve the exact valid PASS and its ticket/baseline/candidate/contract/mode/root bindings plus returned acceptance, nested-domain, production-path, negative-path, and protected-root evidence in `Last verifier result`;
3. append the attempt/candidate/result to `Attempt history`;
4. re-read and verify the checkpoint.

Exit dispatcher-only mode and proceed immediately to Section 4 (`Re-Verify Before Persistence`) of `.agents/skills/implement-ticket/procedure.md` **in the same invocation**.

Do not present `TICKET CLOSURE: PASS` to the human as a terminal result. It establishes `CERTIFIED`, not `CLOSED`. Continue the existing persistence/commit/close/frontier lifecycle until **Completed**, another explicit **Human Handoff**, or a **Hard Blocker** is reached.

The parent may validate hashes/counts/identity mechanically. It may not reinterpret a failing semantic cell into PASS.

## Completion Semantics

Use these distinct states:

```text
IMPLEMENTED
Implementation and applicable local/delegated checks are complete.

CERTIFIED
A fresh independent `$verify-ticket-closure` PASS covers the exact candidate.

CLOSED
The exact certified candidate has been persisted/committed/pushed and tracker/frontier lifecycle completed.
```

The base `Completed` terminal state is legal only in `CLOSED` state.

If no valid independent certification exists, the ticket is not complete regardless of green tests, implementation evidence, or the implementer's acceptance reconciliation.
