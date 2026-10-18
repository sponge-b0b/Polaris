---
name: implement-ticket
description: Implement one exact deterministic ticket contract, run applicable technical checks, obtain fresh independent closure proof, and close only the exact certified candidate.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

## Authoritative procedure composition

Before executing this skill, read both of these files in full:

1. `.agents/skills/implement-ticket/PROCEDURE.md`
2. `.agents/skills/implement-ticket/EXECUTION_ANCHOR.md`

`PROCEDURE.md` preserves the complete established `$implement-ticket` lifecycle.
`EXECUTION_ANCHOR.md` preserves the accepted Execution Anchor correction that separates
historical ticket lineage from the current attempt's candidate. This `SKILL.md` is the
authoritative entrypoint and adds the control-plane mutation boundary below. On conflict,
this file wins. Failure to load either retained file is a Hard Blocker.

The retained procedure continues to own Invocation termination, durable ticket recovery,
hierarchy/dependency/project-delivery admission, architecture-blocker admission,
deterministic contract construction, implementation scope, technical checks, Durable
closure checkpoint v3, Independent closure dispatch, certified persistence/closure, and
Frontier handoff except where the retained Execution Anchor correction or this entrypoint
explicitly overrides older mechanics.

## Execution-anchor invariant

Retain the accepted distinction exactly:

```text
Ticket baseline
    immutable per-ticket historical / lineage anchor

Execution Anchor
    exact fetched remote shared-Spec-branch commit at which the current implementation
    attempt begins, before substantive ticket-owned mutation
```

Do not require the current shared branch to equal that historical SHA. Before a fresh
attempt, fetch the actual remote ticket branch and, only while clean, fast-forward only when
the local branch is strictly behind and is an ancestor. The pre-mutation machine gate remains
directly executable; no `PYTHONPATH` workaround is required.

The retained Execution Anchor correction replaces the candidate diff base `TICKET_BASELINE`
with `EXECUTION_ANCHOR`. The formal pre-mutation invocation still includes:

```text
--remote origin
polaris.implement-ticket-attention/v2
```

and all pre-closure/verification invocations still bind:

```text
--execution-anchor <execution-anchor>
```

No substantive mutation is allowed until the formal pre-mutation gate succeeds.

## Control-plane mutation boundary

An ordinary `$implement-ticket` invocation has **zero authority** to alter repository
workflow/control-plane or semantic-authority files. Product implementation scope, a
duplicate-code finding, formatting, architecture verification, wiki synchronization, test
repair, or any other delegated skill does not expand this authority.

The protected control plane is machine-defined by `scripts.workflow_candidate_guard` and
includes at minimum:

- `.agents/**`;
- `AGENTS.md`;
- `.github/**`;
- `tests/workflow/**`;
- `docs/process/**`;
- `contracts/ccl/**`;
- `docs/adr/**`;
- `scripts/workflow_*.py`;
- the repository delivery/contract tooling enumerated by the guard.

There is deliberately **no `$implement-ticket` bypass flag**. A ticket that genuinely needs
to change these authorities is not an ordinary implementation candidate; stop and route the
change to the owning workflow/authority process. Human approval of product implementation,
ticket scope, or a scanner repair is not equivalent to control-plane authorization.

### Mandatory candidate guard

After the Execution Anchor is captured, run:

```bash
python -m scripts.workflow_candidate_guard check \
  --anchor <execution-anchor>
```

Require:

```text
WORKFLOW CANDIDATE GUARD: VALID
Protected control-plane paths: 0
```

Run this guard:

1. immediately after every substantive mutation batch;
2. before and after any delegated skill that may repair candidate bytes, including
   `$deduplicate-code`, `$format-code`, and `$verify-code`;
3. before the pre-closure Attention sweep;
4. before writing the v3 `awaiting-closure-verification` checkpoint;
5. again after any retry mutation and before persistence.

If the guard reports a protected path, stop normal implementation immediately. Do not
refactor, suppress, format, "fix", or otherwise continue changing that path.

The only candidate-local mutation allowed while recovering from this violation is exact
restoration of the protected paths to the Execution Anchor:

```bash
python -m scripts.workflow_candidate_guard restore-protected \
  --anchor <execution-anchor>
python -m scripts.workflow_candidate_guard check \
  --anchor <execution-anchor>
```

`restore-protected` is intentionally narrow: it restores/deletes only protected candidate
paths and preserves all non-protected product candidate work. After restoration, all
technical evidence that depended on the removed workflow/control-plane mutations is stale
and must be recomputed as applicable.

## Delegated duplicate-code boundary

When invoking `$deduplicate-code` in `ticket-differential` mode, supply the exact
`EXECUTION_ANCHOR`, not the immutable historical `TICKET_BASELINE`, as the differential
comparison base. Shared-branch changes between Ticket baseline and Execution Anchor are
already-durable upstream history and are not ticket-attributable duplicate debt.

`$deduplicate-code` never authorizes a protected control-plane edit. If a scanner relation
would require changing a protected path, the ticket repair loop must leave that path
untouched and report the finding/routing to the owning workflow instead.

## Closure and independent verifier

The pre-closure Attention gate and candidate identity remain Execution-Anchor-bound.
Immediately before them, require a fresh successful candidate guard. The independent
`$verify-ticket-closure` invocation must independently run the same guard against the same
Execution Anchor. Any protected candidate path makes verification invalid: emit neither
`TICKET CLOSURE: PASS` nor `TICKET CLOSURE: FAIL` until the candidate is restored to an
admissible product-only state.

All retained persistence, exact-candidate, dependency/frontier, and Human Handoff rules
remain unchanged.
