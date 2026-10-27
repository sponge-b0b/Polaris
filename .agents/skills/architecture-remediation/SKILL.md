---
name: architecture-remediation
description: Route unresolved material architecture blockers to the smallest current semantic owner without implementing or inventing missing semantics.
compatibility: product=codex product=claude-code system=git system=gh system=python network=required
disable-model-invocation: true
---

# Architecture Remediation

Use when implementation, verification, review, or readiness work cannot continue because a
material architecture/contract choice is absent, contradictory, or no longer valid.

This skill is a **routing and disposition owner**, not a second semantic compiler.

It never implements code and never creates material semantics from blocker prose.

## Session independence

Recover all correctness-critical state from the invocation, repository, CCL, and durable
tracker artifacts. Chat/session memory is context only.

When the source artifact contains one active `<!-- architecture-blocker:v1 -->`, that report
is the exact blocker input. If the invocation explicitly requests an architecture/readiness
audit instead, the human-supplied audit scope is the input. Do not silently substitute one
mode for the other.

## 1. Normalize the blocker set

For each blocker capture only:

* exact unresolved material question or source conflict;
* current durable evidence;
* material consequence;
* affected contract/owner/path/boundary/lifecycle responsibility;
* exact blocked Spec/ticket/review obligation;
* governing CCL/ADR/architecture authority already known.

De-duplicate by independent semantic decision, not by symptom count.

Questions are one coupling group when answering one materially constrains the others. They
remain separate when each can be resolved independently.

Do not answer the question while normalizing it.

## 2. Resolve Spec governance

Read the parent Spec and resolve exactly one:

```text
Wayfinder-managed
Independent
```

Wayfinder-managed means current Spec-local `wayfinder-source` / `wayfinder-remediation`
provenance establishes one or more governors. Resolve the exact governor whose destination
owns this blocker. Ambiguous ownership fails closed.

Independent means no current Wayfinder provenance exists. Do not create a Wayfinder merely
because remediation is needed.

Project fields, issue order, branch names, and prior conversation are never governance
authority.

## 3. Test current authority before creating a decision

For each normalized blocker ask:

> Does current accepted authority already determine this exact material choice at the
> required strength?

If yes:

* identify the exact CCL assertion or governing/constraint authority;
* when semantics are exactly fixed but absent from CCL, use
  `$contract-ledger existing-authority`;
* mark the blocker resolved only after the authoritative state is durable;
* return to `$to-specs` when the Spec projection must change.

If current governing/constraint sources disagree materially at one semantic coordinate,
route the exact disagreement as `CCL SOURCE CONFLICT`. Never choose a winner locally.

If a material choice remains unresolved, continue by governance mode.

### Implement-ticket feasibility consistency gate

When the blocker source workflow is `$implement-ticket`, architecture routing must also prove
that it is consistent with the ticket's pre-implementation feasibility verdict.

Recover the exact `polaris.implement-feasibility/v1` artifact and exact
`polaris.architecture-route-request/v1` artifact persisted with the blocker, then run:

```bash
python .agents/skills/architecture-remediation/scripts/architecture_route_guard.py \
  --feasibility <implement-feasibility.json> \
  --request <architecture-route-request.json>
```

Require exactly:

```text
ARCHITECTURE ROUTE: VALID
```

If the prior feasibility artifact was `PASS`, the route is valid only when the route request
identifies genuinely new post-feasibility evidence. Evidence already enumerated before PASS
cannot be reused to start architecture decision work; that means the earlier feasibility
verdict was wrong and must be corrected by `$implement-ticket` to
`BLOCKED: contract-authority-gap` instead.

A failed preferred mechanism, unavailable vendor feature, difficult persistence technique, or
other implementation-realization problem is not itself a semantic-authority gap. The route
request must name the exact unresolved material `authority_coordinate` and the governing
sources checked. When accepted authority fixes the observable guarantee and leaves physical
encoding, private algorithms, query organization, or equivalent realization to
implementation, do not route to Wayfinder/owner-decision merely because one realization was
rejected.

An `$implement-ticket` architecture blocker that lacks a valid feasibility artifact, route
request, and `ARCHITECTURE ROUTE: VALID` receipt is not valid input for new semantic decision
work under current policy. Do not reopen/create Wayfinder decisions or owner decisions. Leave
the blocker unresolved and return it to the source ticket for feasibility correction.

## 4. Wayfinder-managed blocker

For a Wayfinder-managed Spec, the governing Wayfinder remains the semantic owner.

If the exact governing map is closed and authoritative re-entry is required, reopen that
same map with a concise reason identifying the blocked Spec/work, read back the open state,
and invoke `$project-delivery-management reconcile`.

Create or reuse only decision work that belongs to the exact blocker coupling group. Do not
create a replacement map or duplicate one decision under several maps.

Update the active architecture-blocker disposition to `routed` with the exact decision
references, then emit:

```text
$wayfinder - <Decision Title> (<Decision URL>)
```

Wayfinder owns recommendation analysis, human acceptance, and CCL persistence.

## 5. Independent blocker

For an Independent Spec, use the smallest permanent semantic boundary:

```text
semantics already fixed exactly
    -> $contract-ledger existing-authority

one bounded independent coupling group
    -> $contract-ledger owner-decision

multiple/coupled groups, cross-domain planning, research/prototype campaign,
or project partition/dependency planning
    -> $wayfinder
```

`$architecture-remediation` itself does not conduct a parallel owner-decision protocol,
maintain a second semantic decision map, or persist a competing architecture contract.

After accepted authority is durable, return through `$to-specs` so the existing open Spec
is reconciled against current CCL before ticketing/implementation resumes.

If the Independent blocker legitimately expands into Wayfinder-scale planning, the newly
created Wayfinder is the current semantic owner from that point forward. Do not keep a
parallel Independent semantic state machine.

## 6. Architecture blocker report lifecycle

When the source uses `architecture-blocker:v1`, maintain exactly one active managed report
and update its disposition in place:

```text
unresolved
routed
resolved
```

* `unresolved` — material choice/conflict still blocks progress;
* `routed` — exact owning decision artifact is durable;
* `resolved` — accepted authority now determines the blocker and required Spec projection
  reconciliation has been identified.

Status is routing provenance only; it is not semantic authority.

## 7. Return paths

Resolved by existing/accepted authority and Spec projection may be stale:

```text
$to-specs - <Spec Title> (<Spec URL>)
```

Wayfinder-owned decision:

```text
$wayfinder - <Decision Title> (<Decision URL>)
```

Independent bounded owner-decision:

```text
$contract-ledger owner-decision - <Durable Source Title> (<Source URL>)
```

After owner-decision persistence, resume `$to-specs`.

Invalid `$implement-ticket` architecture routing under the feasibility consistency gate:

```text
$implement-ticket - <Ticket Title> (<Ticket URL>)
```

This return is for feasibility correction only. It does not authorize candidate mutation and
must not be used to bypass a valid `contract-authority-gap` route.

## Attention

Run `$attention` before declaring a blocker fully dispositioned. Attention may expose an
additional material question but cannot answer it or enlarge current authority.

## Non-goals

`$architecture-remediation` does not:

* implement product code;
* infer material semantics from implementation shape;
* create a second contract beside CCL;
* choose among conflicting governing sources;
* create a Wayfinder for a bounded Independent decision;
* turn implementation-mechanism difficulty into a semantic decision;
* accept a post-PASS architecture route based only on evidence available before feasibility;
* rewrite completed historical Specs/tickets/ADRs;
* repair Project projection as though it were lifecycle authority.
