---
name: implement-ticket
description: Implement one exact deterministic ticket contract, run applicable technical checks, obtain fresh independent closure proof, and close only the exact certified candidate.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

## Authoritative procedure composition

Before executing this skill, read all of these files in full:

1. `.agents/skills/implement-ticket/PROCEDURE.md`
2. `.agents/skills/implement-ticket/EXECUTION_ANCHOR.md`
3. `.agents/skills/implement-ticket/POST_ROUTE_RETURN.md`

`PROCEDURE.md` preserves the complete established `$implement-ticket` lifecycle.
`EXECUTION_ANCHOR.md` preserves the accepted Execution Anchor correction that separates
historical ticket lineage from the current attempt's candidate. `POST_ROUTE_RETURN.md` owns the
narrow recovery boundary where a confirmed verifier failure was routed out and the unchanged
contract is durably returned to `$implement-ticket` by existing authority. This file is the
authoritative control-plane entrypoint. On conflict over that route-return boundary,
`POST_ROUTE_RETURN.md` wins; otherwise this file wins. Failure to load any retained file is a
Hard Blocker.

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

The protected control plane uses the canonical protection definitions from
`scripts.workflow_candidate_guard`, but `$implement-ticket` candidate admission is enforced by
the policy-sync-aware wrapper:

```text
.agents/skills/implement-ticket/scripts/candidate_guard.py
```

Protected paths include at minimum:

- `.agents/**`;
- `AGENTS.md`;
- `.github/**`;
- `tests/workflow/**`;
- `docs/process/**`;
- `contracts/ccl/**`;
- `docs/adr/**`;
- `scripts/workflow_*.py`;
- the repository delivery/contract tooling enumerated by the canonical guard.

There is deliberately **no `$implement-ticket` bypass flag**. A ticket that genuinely needs
to change these authorities is not an ordinary implementation candidate; stop and route the
change to the owning workflow/authority process. Human approval of product implementation,
ticket scope, or a scanner repair is not equivalent to control-plane authorization.

### Authorized committed policy synchronization is upstream history

The candidate guard must not misattribute already-committed, non-semantic workflow-policy
synchronization to the ticket merely because the current Execution Anchor predates that sync.
A committed protected path is excluded from the ticket candidate only when all of these
machine checks pass:

1. the Execution Anchor is an ancestor of current `HEAD`;
2. the committed protected path is one of the AGENTS-authorized policy-sync surfaces:
   `.agents/skills/**`, `docs/process/**`, or root `AGENTS.md`;
3. every commit between the anchor and `HEAD` that touches one of those protected paths changes
   policy-sync surfaces only;
4. the current `HEAD` blob for each excluded path exactly equals current `origin/main`; and
5. the path is locally clean relative to `HEAD`.

If any predicate fails, the protected path remains part of the candidate and the guard fails
closed. A local/staged edit to a previously synchronized policy path is always candidate-local
and remains forbidden. `restore-protected` restores such a local edit to current `HEAD`, not to
the older Execution Anchor, so a valid committed policy sync is never rolled back.

### Mandatory candidate guard

Fetch current `origin/main` before relying on policy-sync exclusion. After the Execution Anchor
is captured, run:

```bash
python .agents/skills/implement-ticket/scripts/candidate_guard.py check \
  --anchor <execution-anchor> \
  --remote origin \
  --default-branch main
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
restoration of the protected local path to current committed policy state:

```bash
python .agents/skills/implement-ticket/scripts/candidate_guard.py restore-protected \
  --anchor <execution-anchor> \
  --remote origin \
  --default-branch main
python .agents/skills/implement-ticket/scripts/candidate_guard.py check \
  --anchor <execution-anchor> \
  --remote origin \
  --default-branch main
```

`restore-protected` is intentionally narrow: it restores/deletes only protected candidate
paths and preserves all non-protected product candidate work. After restoration, all
technical evidence that depended on the removed workflow/control-plane mutations is stale
and must be recomputed as applicable.

## Post-route implementation return

A validated `ROUTE_REQUIRED` verifier triage does not permanently consume all future
implementation authority when the owning downstream workflow later returns the **unchanged**
contract to `$implement-ticket` through existing accepted authority.

In that case, follow `POST_ROUTE_RETURN.md`. The original local-attempt count remains historical
and is never reset. The downstream return may create exactly one new bounded post-route attempt
epoch, represented by one managed `polaris.implement-route-return/v1` record. The same
triage/route-result pair may not create a second epoch.

Before the first mutation in that epoch, the managed record must be `IN_PROGRESS`, read back,
and machine-valid. Supply the exact artifact to the formal pre-mutation Attention invocation:

```text
--route-return <implement-route-return.json>
```

The Attention wrapper must prove the returned ticket/contract identity and that the current
candidate still equals the failed candidate bound by the route return before mutation begins.

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
Immediately before them, require a fresh successful policy-sync-aware candidate guard. The
independent `$verify-ticket-closure` invocation must independently run the same guard against
the same Execution Anchor. Any protected candidate path makes verification invalid: emit
neither `TICKET CLOSURE: PASS` nor `TICKET CLOSURE: FAIL` until the candidate is restored to an
admissible product-only state.

All retained persistence, exact-candidate, and dependency/frontier rules remain unchanged.
The retained Human Handoff prose is overridden by the shared outbound gate below wherever
the retained procedure would otherwise terminate with a manually constructed downstream
skill line.

## Outbound Human Handoff boundary

Every terminal **Human Handoff** from `$implement-ticket` must use the shared
`polaris.workflow-handoff/v1` gate. This applies to every outbound lifecycle transition,
including:

- verifier `cell-routing-defect` -> `$to-tickets`;
- verifier `planning-cell-gap` -> `$to-specs`;
- verifier `contract-authority-gap` or material design gap -> the exact owning
  `$architecture-remediation` / semantic workflow;
- pre-implementation routing for the same material-design/decomposition classes;
- architecture-blocker or changed-contract/coverage routing owned by another workflow;
- post-closure frontier handoff to one or more `$implement-ticket` invocations; and
- completed-ticket handoff to `$verify-spec`.

A recommendation, prose instruction, or bare downstream skill command is **not** a Human
Handoff and does not satisfy an invocation terminal condition.

### Route artifact and durability

Before generating a handoff, resolve the exact downstream invocation artifact from durable
state; do not invent it from chat memory.

- `$to-tickets` receives the exact current Parent Spec issue.
- `$to-specs` receives the exact current planning source for the Parent Spec: its governing
  Wayfinder issue when Wayfinder-managed, or its exact Independent planning-source issue.
  A current Spec issue is a durability source, not a substitute planning source.
- `$architecture-remediation` or another semantic owner receives the exact durable artifact
  selected by that owning workflow's current routing contract.
- `$implement-ticket` receives each exact current actionable ticket issue.
- `$verify-spec` receives the exact current Parent Spec issue.

If the required downstream artifact cannot be resolved uniquely from current durable state,
do not manufacture a handoff; remain blocked at the owning boundary and report the exact
ambiguity.

Every handoff manifest uses:

```text
schema: polaris.workflow-handoff/v1
boundary: human-lifecycle
durability.verified: true
```

Its `durability.sources` must be canonical, unique, and sufficient for a fresh downstream
session to reconstruct correctness-critical state. For a verifier-failure route, include at
minimum the current ticket URL, Parent Spec URL, and the exact downstream planning/authority
artifact URL when distinct. For normal post-closure frontier handoff, include the Parent
Spec URL plus every handed-off ticket URL. Add managed-comment or other durable artifact
URLs whenever they are necessary for fresh-session recovery.

### Complete frontier

For a normal post-closure frontier, evaluate the complete current actionable ticket
frontier. Do not stop after the first actionable ticket. Emit one manifest handoff entry
for every independently actionable ticket in deterministic ticket/topology order.

If all executable ticket work is durably closed and the Spec is ready for integrated
verification, emit exactly one `$verify-spec` handoff entry for the Parent Spec.

If zero downstream artifacts are actionable and another workflow is not required, do not
invent an empty Human Handoff manifest; report the exact current blocker/completion state
under the retained lifecycle rules.

### Shared generation and verification gate

Create the manifest outside the repository candidate, then generate and verify the terminal
output only through the shared gate:

```bash
python -m scripts.workflow_handoff generate \
  --manifest <handoff-manifest.json> \
  > <handoff-output.txt>
python -m scripts.workflow_handoff verify \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

Require exact:

```text
WORKFLOW HANDOFF: VALID
```

The user-visible terminal Human Handoff block must reproduce `<handoff-output.txt>`
**byte-for-byte**. It begins with `WORKFLOW HANDOFF: READY`, contains the exact generated
downstream command line(s), and ends with the verified fresh-session durability receipt and
manifest SHA-256.

Do not emit a bare `$to-specs`, `$to-tickets`, `$architecture-remediation`,
`$implement-ticket`, or `$verify-spec` line as a terminal Human Handoff. Do not manually
reconstruct the generated block. Do not claim the `Human Handoff` terminal condition if
generation or verification fails.
