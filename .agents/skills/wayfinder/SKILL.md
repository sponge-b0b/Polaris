---
name: wayfinder
description: Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Wayfinder

A loose idea has arrived — too big for one agent session, and wrapped in fog: the way from here to the **destination** isn't visible yet.

Wayfinding finds that route rather than charging at the destination. It charts a shared map of decision tickets, then resolves those decisions one at a time until the route is clear.

The destination may be a Spec, a durable decision, or a change made in place. Naming it is the first act of charting because it determines scope.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting.

Prior-session summaries or remembered conclusions are routing context only and must not substitute for durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

## Project Delivery Focus Guard

`$project-delivery-management` owns project-level delivery focus. `$wayfinder` owns Wayfinder planning and must not copy, infer, or persist competing focus state.

The guard applies differently to the two invocation modes:

* **Chart the Map** is capture/planning and is not focus-gated. A new map may be charted while another Wayfinder is focused. Charting must not establish, switch, broaden, or otherwise change focus, and chart-time research needed to form the map remains allowed.
* **Work Through the Map** is substantive advancement and is focus-gated before any durable mutation, including claiming a decision ticket.

Never create a native dependency merely to encode focus or queue preference. Dependency determines eligibility; focus determines intentional project WIP.

### Guard Before Substantive Wayfinder Work

When working through an existing map or decision ticket:

1. resolve the exact governing Wayfinder map from durable tracker relationships/metadata;
2. invoke `$project-delivery-management` `reconcile` so completed or directly ineligible focused maps are reduced before authorization;
3. invoke `$project-delivery-management` `guard <Wayfinder>`;
4. proceed only after the guard returns `PROJECT DELIVERY GUARD: ALLOWED`.

Handle other results without claiming or mutating the decision:

* `PROJECT DELIVERY GUARD: BLOCKED` → report the direct map blockers and stop;
* `PROJECT DELIVERY GUARD: FOCUS REQUIRED` with another focused Wayfinder/set → report the current focus and stop with the explicit human choices to continue current work, run `$project-delivery-management` `switch-focus <Wayfinder>`, or authorize an exact `$project-delivery-management` `parallel-focus <Wayfinder>...` set;
* `PROJECT DELIVERY GUARD: FOCUS REQUIRED` with an empty focused set → ask the human:

  > Establish <Wayfinder Map Title> as the project delivery focus and continue? (yes/no)

  Only an explicit `yes` authorizes invoking `$project-delivery-management` `focus <Wayfinder>` as the human focus decision for this session. Re-run the guard and require `ALLOWED` before continuing. `no` leaves focus empty and ends substantive Wayfinder work.

The empty-focus confirmation is the only focus establishment `$wayfinder` may facilitate. `$wayfinder` must never infer or perform a focus switch, parallel authorization, or broader focus change from its own invocation.

Read-only investigation required to resolve the governing map and project-delivery state is allowed before the guard. Do not claim a decision, post a Decision Analysis, mutate tracker/repository state, or resolve architecture before authorization succeeds.

### Reconcile After Durable Wayfinder Transitions

After a Wayfinder-owned transition that can affect project eligibility, focus validity, or lower-level actionability is durably persisted, invoke `$project-delivery-management` `reconcile` **after** that authoritative mutation succeeds.

Examples include:

* creating/charting a canonical Wayfinder map;
* closing/reopening a Wayfinder decision and updating the map's durable state;
* changing native dependency state owned by the Wayfinder lifecycle;
* any map closure/re-entry performed by the owning lifecycle.

Reconciliation may remove completed/directly ineligible focused maps but must never select a replacement. If reconciliation cannot recover valid project-delivery state, report the failure and do not present a downstream lifecycle handoff that depends on current focus.

A focused map that remains map-eligible but has no currently actionable lower-level decision work because narrower blockers remain is **focused-but-stalled**. Retain focus, surface the blockers, and do not promote them to a synthetic map blocker or silently switch/release focus.

## Plan, Don't Do

Wayfinder is **planning** by default.

Each ticket resolves a decision. The map is complete when nothing material remains to decide before downstream work can proceed.

The urge to implement is usually evidence that the map has reached its destination and should hand off.

An effort may explicitly carry execution inside its **Notes**, but otherwise produce decisions, not destination deliverables.

## Resolve Architecture Before Handoff

For software work that materially affects architecture, use the Living Entity Wiki and its authoritative sources during distillation rather than leaving architectural questions for specification or implementation.

Classify impact as:

```text
none | conforming | extending | changing | retiring
```

Treat unresolved material architecture questions as decision tickets.

Before the route is clear:

* identify affected entities and applicable invariants, decisions, rejections, and boundaries;
* resolve conflicts or intended architecture changes with the owner;
* route durable decisions through `$to-adr-doc`;
* route new non-ADR architecture documentation through `$to-doc`;
* route reclassification of existing non-ADR documentation through `$classify-doc`;
* invoke `$wiki-sync` when authoritative changes require derived wiki maintenance.

Do not duplicate those skills' lifecycle rules here.

Reconciling architectural records is part of resolving the map, not implementing the destination.

### Architecture Implementability Closure

Architectural consistency alone does not make the route clear.

For every materially affected canonical contract, authority path, dependency boundary, or lifecycle, confirm that accepted architecture determines enough durable semantics to implement it without inventing another architectural choice.

Check where applicable:

* canonical owner;
* required typed authority/input source;
* identity, version, or correlation-key semantics;
* lifecycle ordering;
* persistence and retrieval responsibility;
* dependency direction and boundary ownership;
* authoritative consumers;
* fail-closed/failure semantics.

#### Concrete Contract Validation

When a decision requires an existing domain type, interface, durable record, authority object, or lifecycle component to be produced or consumed, inspect that contract far enough to verify the decision is realizable.

Where applicable, confirm:

* required inputs can exist at the required lifecycle point;
* the designated producer has an authoritative source for them;
* required classifications or authority facts are established or deterministically derivable;
* satisfying the contract does not require inventing new durable meaning, authority, classification, or lifecycle semantics.

Do not require missing implementation wiring to already exist.

A missing factory, method, registration call, repository operation, or DI binding is implementation work when architecture already determines the semantics.

Architecture remains unresolved only when implementation would still have to invent a durable architectural choice.

Do **not** require Wayfinder to decide ordinary implementation details such as:

* class or method names;
* private helper structure;
* repository API shape when responsibility is already established;
* SQL/query mechanics;
* local algorithms;
* ordinary code organization.

Ask:

> Could implementation proceed without inventing a durable architectural choice?

If **No**, architecture remains unresolved.

Create or retain the necessary decision/fog under the same map.

When several missing choices jointly define one contract or lifecycle and materially constrain one another, treat them as one coupled decision rather than artificial separate decisions.

The route is not clear merely because every previously stated question has an answer.


### Material Contract Universe Closure

Architecture Implementability Closure is exhaustive over the materially consequential contract universe, not merely over questions that happened to become Wayfinder tickets.

Before route clarity can pass for software work, materialize one working **Material Contract Closure Record**. Seed its candidate universe from the destination, every materially affected canonical entity/owner, accepted Wayfinder decisions and ADRs, current architecture sources needed to interpret those decisions, and known downstream artifacts/components that consume the resulting contract. Do not use the existing ticket list, the map's current fog, or a prior route-clear claim as the completeness denominator.

For every materially affected contract, disposition every applicable dimension below:

* identity representation and generation semantics;
* ownership, cardinality, uniqueness, and first-class-versus-dependent identity;
* public/domain/application type meaning and canonical vocabulary;
* typed cross-component references, relationship roles, and admissible target families;
* lifecycle, correction/supersession ancestry, and current-versus-historical interpretation;
* effective-time, known-at, recorded/observed-time, version, and ordering semantics;
* persistence-visible identity, keys, constraints, and reference contracts;
* application command/query inputs, result distinctions, and current/historical reconstruction boundary;
* authority/provenance meaning;
* externally observable unknown/contested/fail-closed behavior;
* known downstream consumers whose contract would differ if the choice changed.

A dimension that is genuinely irrelevant still receives an explicit not-applicable disposition. Omission is not a disposition.

Use one row per material contract dimension:

~~~text
Contract: <canonical contract / path / lifecycle>
Dimension: <material design dimension>
Candidate source/consumer: <why this row is in the universe>
Authority: <exact durable source(s)>
Disposition: fixed-by-authority | implementation-equivalent | unresolved | not-applicable
Frozen meaning or equivalence boundary: <compact exact result>
Materially-different-implementations falsifier: <what competing implementation would change the contract>
~~~

Rules:

* fixed-by-authority requires exact durable authority that determines the material meaning;
* implementation-equivalent is legal only when plausible alternatives cannot change public, product, domain, architecture, persistence, failure, temporal, authority, or downstream behavior;
* not-applicable requires positive scope/authority;
* unresolved creates or retains Wayfinder decision/fog and blocks route clarity;
* a decision ticket saying a topic is "resolved" is routing evidence, not proof that every material dimension of the resulting contract is frozen;
* implementation precedent may prove realizability or equivalence, but current code does not silently become design authority for an unresolved public/domain contract.

Require:

~~~text
Material contract candidates: <n>
Material contract dimensions: <n>
Fixed by authority: <n>
Implementation-equivalent: <n>
Not applicable with authority: <n>
Unresolved: 0
Unclassified/omitted material dimensions: 0
~~~

Immediately before the route-clear transition, freeze those exact route-clarity inputs and compute one `ROUTE_CLARITY_CANDIDATE_ID` as the SHA-256 of the exact challenger dispatch packet bytes. Then run one **fresh, non-mutating semantic route-clarity challenger** over the frozen map, accepted decisions, their applicable **Certified Decision Contract Domains**, unresolved fog, bounded authoritative source universe, and the Material Contract Closure Record.

The route-level challenger owns only two questions:

1. **composition/coverage:** does the map destination or an exact governing source contain a material obligation that is not represented by any accepted certified decision domain, unresolved decision, or explicit out-of-scope disposition?
2. **certified-domain integrity:** does a candidate expose an in-domain falsifier, actual authority change, or explicit authority contradiction to a previously certified decision domain?

It may not reopen a certified decision domain merely by choosing a broader plausible interpretation.

For every challenger candidate, the parent must build a **Route Candidate Finality Reconciliation** before the candidate may block route clarity or mutate tracker state:

~~~text
Candidate: <material concern>
Exact governing authority: <source>
Applicable certified decision domain: <ID | None>
Prior authority identity: <identity | None>
Current authority identity: <identity>
Authority changed: yes | no
Membership under frozen predicate: in-domain | out-of-domain | ambiguous | no-prior-domain
Explicit authority contradiction: <None | exact clause/source>
Map-destination coverage status: represented | genuinely-unrepresented
Disposition:
  in-domain-falsifier
  authority-changed-domain-stale
  explicit-authority-invalidates-prior-domain
  genuinely-unrepresented-map-obligation
  domain-expansion
  ambiguous
Routing: <existing decision remediation | new decision | Attention-only | blocked-pending-reconciliation>
~~~

Only these dispositions may block route clarity:

* `in-domain-falsifier` — route back to the **same decision domain**; preserve the accepted historical decision and reopen/remediate that decision rather than creating a sibling decision for the omitted inner contract;
* `authority-changed-domain-stale` — rebuild the affected decision domain under the changed authority;
* `explicit-authority-invalidates-prior-domain` — route to the affected decision/domain owner;
* `genuinely-unrepresented-map-obligation` — only when exact destination/source authority proves the obligation belongs to the Wayfinder and no existing certified decision domain represents it;
* `ambiguous` — fail closed until membership/authority is reconciled.

`domain-expansion` under unchanged authority is non-blocking Attention. It must not create a decision ticket, alter the frontier, or make a previously accepted certified domain incomplete.

When a candidate is an in-domain omission discovered after human acceptance, remediation must return to the affected decision and repeat the human gate if the material recommendation changes. Do not distribute one accepted decision's missing inner dimensions into new sibling tickets merely because they can be named separately.

Before any tracker mutation from challenger output require:

~~~text
Route challenger candidates: <n>
Finality reconciliations: <n>
Candidates without reconciliation: 0
Domain-expansion candidates creating work: 0
In-domain omissions routed to original decision domain: <n>
Genuinely unrepresented map obligations: <n>
~~~

The challenger itself remains non-mutating. Its terminal result is exactly one complete semantic payload:

~~~text
WAYFINDER ROUTE CLARITY: PASS | FAIL
Route clarity candidate identity: <ROUTE_CLARITY_CANDIDATE_ID>
Unrepresented map obligations: <count + details>
Certified-domain falsifiers/authority changes: <count + details>
Domain-expansion observations: <count + details>
Candidates awaiting finality reconciliation: <count + details>
~~~

Apply the repository-wide **Independent Semantic Child Result Admission** rule from `AGENTS.md`. Before consuming route clarity require the payload to have actually returned, exactly one terminal route-clarity verdict, an exact candidate-identity match, and every required result category. Pending/ambiguous child state or a missing/malformed/mismatched payload is unresolved and cannot produce `Route clarity: clear`.

Route clarity requires PASS and zero unreconciled candidates. A same-agent or owner-declared substitute is not an equivalent certification boundary; if a fresh challenger is unavailable, do not declare the software route clear.

This route-level certification is intentionally narrower than **Decision-Bounded Contract Certification**. It proves map composition and respects previously frozen semantic domains; it does not perform another open-ended architecture discovery pass inside every accepted decision.

## Repository Persistence

This invariant applies whenever `$wayfinder` creates or modifies repository files.

### Canonical Persistence Isolation

Wayfinder-owned repository authority is canonical on `main`. The checkout from which `$wayfinder` was invoked is a **protected caller worktree**, not the place where canonical authority must be authored.

A dirty caller worktree is valid execution context. It must never force Wayfinder to stash, commit, discard, carry, or otherwise rewrite unrelated downstream work merely to persist accepted architecture.

Before invoking any repository-writing child skill or making the first Wayfinder-owned repository mutation:

1. identify and fingerprint the protected caller worktree. Record at minimum:
   * repository root;
   * caller branch or detached-HEAD state;
   * caller HEAD;
   * staged diff identity;
   * unstaged tracked diff identity;
   * untracked path-and-content identity.

   The fingerprint must distinguish staged from unstaged state and must detect content changes to existing untracked files; `git status` text alone is insufficient.

2. fetch `origin/main` without switching the caller checkout and freeze:
   ```text
   CANONICAL_MAIN_BASE = exact fetched origin/main SHA
   ```

3. create a temporary **isolated Git worktree** detached at exactly `CANONICAL_MAIN_BASE`. Require that isolated worktree to begin clean.

4. run every Wayfinder-owned repository-writing operation inside that isolated worktree, including repository-writing child skills such as `$to-adr-doc` and `$wiki-sync`. A child whose repository mutations cannot be constrained to the isolated worktree is unavailable for this transition; do not fall back to mutating the caller checkout.

5. never switch branches in, stage from, clean, reset, stash, commit from, or otherwise mutate the protected caller worktree as a prerequisite to canonical persistence.

When `$wayfinder` is parent, repository-writing child skills contribute their changes to the Wayfinder commit rather than committing separately.

### Canonical Commit and Concurrency Gate

If the isolated canonical worktree contains repository changes:

1. require every changed path to be Wayfinder-owned for the accepted decision. Unexpected paths are a hard stop; do not broaden staging to absorb them.
2. stage only the intended files. Never use `git add .`.
3. invoke `$conventional-commits` and commit in the isolated worktree. A detached-HEAD commit is valid because `main` is the push destination, not the execution checkout.
4. immediately before push, fetch `origin/main` again and require it still equals `CANONICAL_MAIN_BASE`. If it moved, fail closed and rebuild/reconcile from the new canonical base; never force-push or silently rebase an accepted authority mutation.
5. push normally, without force:
   ```bash
   git push origin HEAD:main
   ```
   A concurrent non-fast-forward rejection is unresolved canonical persistence, never permission to overwrite.
6. fetch `origin/main` and require its exact SHA to equal the committed Wayfinder authority.
7. verify the committed diff contains only the intended Wayfinder-owned files.

If no repository files changed, skip commit/push but still preserve the caller-worktree isolation invariant.

After canonical persistence succeeds, `main` is authoritative even if a downstream continuation branch has not yet inherited that commit.

### Protected Caller Worktree Integrity Gate

Before removing the isolated canonical worktree, and again before any Human Handoff or ordinary return, recompute the protected caller-worktree fingerprint and require an exact match with the pre-persistence fingerprint:

```text
Caller branch/HEAD unchanged: yes
Caller staged state unchanged: yes
Caller unstaged tracked state unchanged: yes
Caller untracked path/content state unchanged: yes
```

A mismatch is a **Hard Blocker**. Do not attempt to "repair" the caller worktree automatically, because doing so could destroy downstream work. Canonical `main` authority already persisted successfully remains authoritative; report the caller-worktree integrity failure separately.

After successful canonical readback and caller-integrity verification, remove/prune the temporary canonical worktree. Temporary execution worktrees and detached commits are mechanics, never durable authority.

### Continuation-Branch Inheritance

When downstream work was routed back to Wayfinder from an existing durable non-`main` continuation branch, inheritance of the canonical repair is a **separate downstream-readiness transition**. It is not a prerequisite for the accepted architecture to become canonical or for the Wayfinder decision itself to be resolved.

After canonical `main` persistence:

1. identify the exact durable continuation branch from tracker/branch lineage. Do not infer a continuation branch merely from whichever checkout happened to invoke Wayfinder.
2. fetch both `origin/main` and the exact remote continuation branch and freeze the continuation remote tip.
3. create a second temporary isolated worktree detached at that exact continuation tip. Do not use or mutate the protected caller worktree for inheritance.
4. merge the exact persisted canonical `main` commit into the isolated continuation worktree using an ordinary merge.
5. if the merge is clean, continue with the concurrency/push/readback gates below.
6. if the merge conflicts, capture the exact conflict-path set, abort only that isolated merge, remove/prune the isolated worktree, and classify continuation inheritance as **semantic reconciliation required**. Do not choose `ours`, `theirs`, manually resolve conflict content, or otherwise let `$wayfinder` decide how downstream implementation/derived state must change to conform to the new authority.
7. before any clean inheritance push, fetch the remote continuation branch again and require its tip still equals the frozen continuation tip. If it moved, fail the inheritance attempt closed rather than overwrite concurrent downstream work.
8. push the isolated merge normally to the exact continuation branch, never with force.
9. fetch both refs and require:
   ```bash
   git merge-base --is-ancestor origin/main "origin/$CONTINUATION_BRANCH"
   ```
10. remove/prune the isolated continuation worktree after successful readback.

The protected caller worktree may still point at an older local tip after remote continuation inheritance. Do not advance or rewrite that checkout to make it appear synchronized. A later workflow executing there must perform its own branch-freshness/worktree guard before mutation.

If continuation inheritance succeeds, downstream durable branch authority is synchronized even though the protected local checkout remains untouched.

If automatic continuation inheritance does not safely complete, classify the result explicitly:

```text
Continuation branch: <branch>
Canonical main authority: <commit>
Continuation inheritance:
  synchronized
  semantic-reconciliation-required
  blocked-by-concurrency
  blocked-by-missing-branch
  not-applicable
Conflict paths: <exact set | None>
```

The dispositions have different consequences:

* `synchronized` — branch-dependent downstream execution may proceed subject to its own guards.
* `semantic-reconciliation-required` — canonical authority and downstream branch state both remain valid inputs, but Git cannot determine their semantic combination. Preserve both. Route through the owning downstream reconciliation lifecycle; do not retry the same merge as if conflict resolution were merely mechanical.
* `blocked-by-concurrency` or `blocked-by-missing-branch` — no downstream workflow may claim the continuation state is current until branch identity/concurrency is recovered.
* `not-applicable` — no durable continuation branch exists for this transition.

A continuation conflict is **not** by itself an unresolved architecture choice or a route-clarity failure. It is evidence that downstream artifacts created under older authority require semantic reconciliation.

Do **not** roll back, reopen, or invalidate the accepted Wayfinder decision solely because continuation synchronization failed.

### Reconciliation Handoff Exception

The prohibition on handing off against stale continuation state applies to workflows that **consume the continuation branch as already-conformant execution state**. It does not apply to a reconciliation workflow whose explicit purpose is to reconcile downstream contracts/state against the newly canonical Wayfinder authority.

For a route-clear Wayfinder whose destination is specification:

* `$to-specs` remains a legal Human Handoff when continuation inheritance is `semantic-reconciliation-required`;
* `$to-specs` owns determining whether the canonical decisions create new Specs or whether existing governed Specs require `$to-remediation-specs`;
* `$to-remediation-specs` owns reconciling the existing Spec contract against the new authority before ticket reconciliation;
* later `$to-tickets` / implementation/review workflows must not treat stale branch-local Spec/ticket/derived state as conformant merely because it still exists.

This exception is narrow. It does not authorize `$wayfinder` to merge conflicted implementation, tests, migrations, derived wiki realization, or other downstream-owned content. It authorizes only the **reconciliation handoff** that makes those downstream states semantically current.

When `semantic-reconciliation-required` is present, the Route Clarity Record and Human Handoff must carry the canonical authority commit, exact continuation branch, and conflict-path set as durable transition context. The receiving reconciliation workflow must be able to recover those facts without relying on chat/session prose.

If there is no durable continuation branch, do not manufacture one merely to restore the caller's checkout.

### Persistence Failure Semantics

Tracker-only changes require no repository commit or canonical worktree.

If isolated canonical worktree creation, repository-writing child isolation, staging, commit, canonical concurrency validation, push, canonical readback, or caller-worktree integrity verification fails:

* do not close a decision whose repository-side architectural record is still unpersisted on `main`;
* do not claim canonical persistence succeeded;
* do not present a downstream Human Handoff that depends on the missing authority;
* preserve the protected caller worktree and report the exact failure.

Once accepted repository-side architecture is committed and read back from `main`, that canonical decision authority is durable. A later continuation-sync failure is a downstream-readiness failure, not a canonical-persistence failure.

A Wayfinder decision that changes repository-side architectural records is repository-complete when those records are committed to and read back from `main`, the committed diff is bounded to Wayfinder-owned paths, and the protected caller worktree is proven unchanged. Continuation-branch inheritance is required only before a downstream handoff that depends on that branch containing the new authority.


## Refer by Name

Every map and ticket is an issue with a title.

In human-facing narration and **Decisions so far**, refer to it by name rather than bare ID, number, or slug.

The ID and URL still travel inside the named link.

## The Map

The map is a single issue labelled `wayfinder:map` — the canonical artifact. Its tickets are child issues.

The map is an **index**, not a store. It lists decisions and points to the tickets holding their detail. A decision lives in exactly one place.

Tracker-specific storage and relationship mechanics come from the repository's configured issue-tracker documentation.

Run `$setup-matt-pocock-skills` if no tracker has been configured.

### Map Body

```markdown
## Destination

<what reaching the end of this map looks like>

## Notes

<domain; skills every session should consult; standing preferences>

## Decisions so far

- [<closed ticket title>](link) — <one-line gist>

## Not yet specified

<in-scope fog not yet sharp enough to ticket>

## Out of scope

<work ruled beyond the destination>
```

### Tickets

Each ticket is a child issue of the map; the tracker issue ID is its identity.

Its body contains the decision question:

```markdown
## Question

<the decision or investigation this ticket resolves>
```

Each ticket carries one:

```text
wayfinder:research
wayfinder:prototype
wayfinder:grilling
wayfinder:task
```

A session claims a ticket by assigning it to the developer driving the map before work.

An open, unassigned ticket is unclaimed.

Blocking uses the tracker's native dependency relationship.

A ticket is **unblocked** when every blocking ticket is closed. The **frontier** is the open, unblocked, unclaimed children.

Keep the ticket body as the decision question. Persist authored decision analysis and recommendations as issue comments; record the accepted answer in the final resolution comment.

## Ticket Types

Every ticket is either **HITL** — human in the loop — or **AFK**, driven by the agent alone.

A HITL ticket resolves only through the live exchange. **The agent must never infer, assume, or supply the human's decision.**

* **Research** (AFK): read documentation, third-party APIs, or local resources to surface a fact a decision waits on. Resolve through a `$research` subagent.
* **Prototype** (HITL): create a cheap concrete artifact via `$prototype` when reaction to behavior or shape will improve the decision.
* **Grilling** (HITL): use `$grilling` and `$domain-modeling`, one question at a time. Default case. For each decision question, provide the recommended answer, persist the required **Decision Analysis**, complete **Decision-Bounded Contract Certification** when the recommendation fixes a material software contract, then explicitly ask **“Do you agree with this recommendation? (yes/no)”** and wait. `yes` accepts the recommendation. `no` keeps the current decision open and explores the disagreement before advancing. Never infer acceptance or resolve the ticket without an explicit user response.
* **Task** (HITL or AFK): prerequisite work that must happen before a decision can be made.

## Decision-Bounded Contract Certification

For every software HITL decision whose recommendation fixes or changes a material product/domain/architecture/public/persistence/downstream contract, semantic completeness must be challenged **before** the human yes/no acceptance gate.

The bounded certification domain is the decision's own authoritative question plus the exact material contracts the proposed recommendation claims to resolve. It is not the entire Wayfinder map and it must not expand into sibling domains merely because adjacent architecture exists.

Before presenting the recommendation to the human:

1. freeze the proposed recommendation;
2. build one **Decision Contract Domain** from the ticket question, governing authority, affected canonical contract(s), and known direct downstream consumers of that decision;
3. disposition every materially consequential design dimension inside that bounded domain using the same material-contract dimensions defined under **Material Contract Universe Closure**;
4. compute one `DECISION_CERTIFICATION_ID` as the SHA-256 of the exact frozen challenger dispatch packet bytes for that recommendation/domain/authority state;
5. dispatch exactly one fresh, non-mutating **decision-domain challenger** over that frozen domain and recommendation;
6. if the challenger finds an in-domain omission or unsupported disposition, revise the same decision recommendation, persist a `## Recommendation Revision` when required, rebuild the affected domain rows, and recertify before asking the human;
7. only after certification PASS may the HITL yes/no gate be presented.

Persist the compact certification state with the decision analysis/revision:

~~~text
Certified Decision Contract Domain: <stable ID>
Decision: <ticket identity>
Authority identity: <exact durable source identities/hashes when available>
Membership predicate: <what material contract/dimension belongs to this decision>
Direct consumer/source sets: <bounded set>
Expected / inspected / dispositioned dimensions: <counts>
Unresolved in-domain dimensions: 0
Decision-domain challenger: PASS
Finality: frozen-under-unchanged-authority after human acceptance
~~~

The decision-domain challenger returns exactly one complete semantic result:

~~~text
DECISION CONTRACT CERTIFICATION: PASS | FAIL
Certification identity: <DECISION_CERTIFICATION_ID>
In-domain omitted dimensions: <count + details>
Unsupported non-blocking dispositions: <count + details>
Out-of-domain observations: <count + concise observations>
~~~

Apply the repository-wide **Independent Semantic Child Result Admission** rule from `AGENTS.md`. Before consuming the result require the payload to have actually returned, exactly one `DECISION CONTRACT CERTIFICATION` verdict, an exact certification-identity match, and all required result categories. Pending/ambiguous child state or a missing/malformed/mismatched payload is unresolved and cannot open the human yes/no gate.

Rules:

* `FAIL` blocks the human acceptance gate; do not ask the human to approve a recommendation known to be semantically incomplete.
* Out-of-domain observations are Attention only at this boundary. They do not enlarge the decision, create sibling tickets, or block acceptance unless exact governing authority proves they are actually members of the bounded decision domain.
* The challenger may not mutate repository/tracker state, redesign the recommendation, create tickets, or choose a missing material contract.
* Once the human accepts a PASS-certified decision, that certified membership boundary is durable under unchanged authority according to **Certified Semantic Domain Finality**. Later actors may find in-domain falsifiers, authority changes, or explicit authority contradictions, but may not silently enlarge the accepted decision domain.

This is the earliest semantic completion boundary for a Wayfinder decision. Route-clear certification later checks composition and map coverage; it does not get a second unrestricted chance to redefine an accepted decision's inner domain.

## Decision Analysis

For every HITL decision ticket, preserve the architectural journey in the ticket before asking the human to accept the recommendation.

After investigation is materially complete and before the explicit yes/no gate, post one authored issue comment beginning with:

```markdown
## Decision Analysis
```

The comment is a durable explanation of how the recommendation follows from repository evidence and architectural constraints. It is **not** a transcript and must not contain raw private scratchpad or chain-of-thought.

Include only sections that carry material information, normally drawn from:

```markdown
### Current State

<relevant implementation and current architecture>

### Future-State Constraints

<accepted-but-not-yet-realized decisions, related Specs/Wayfinders,
dependency chains, and reserved responsibilities that constrain this choice>

### Key Findings

<facts that materially shaped the recommendation>

### Alternatives Considered

<plausible alternatives, why they were plausible, and why they were
rejected or retained>

### Architectural Reasoning

<the concise argument connecting evidence, ownership, lifecycle,
dependency direction, authority, and tradeoffs to the recommendation>

### Recommendation

<the exact recommendation presented to the human>
```

Do not force empty headings or uniform length. A simple decision may need only a few paragraphs; a foundational architectural decision may need substantially more.

Preserve especially:

* evidence or lifecycle facts that were not obvious from the ticket question;
* relevant future-state constraints consulted under **Resolve Architecture Before Handoff**;
* plausible alternatives and why they were rejected;
* assumptions whose later invalidation could justify revisiting the decision;
* first-principles reasoning that prevents a future maintainer from mistaking a deliberate rejection for an overlooked option.

The recommendation in the `Decision Analysis` comment must match the recommendation presented in the live HITL exchange.

For a decision requiring **Decision-Bounded Contract Certification**, the recommendation presented to the human must also be the exact recommendation that received the latest `DECISION CONTRACT CERTIFICATION: PASS`. A semantic revision after certification invalidates that certification and requires recertification before the yes/no gate.

### Recommendation Revision

If the human rejects, challenges, or clarifies the recommendation and further analysis materially changes it, preserve history rather than rewriting the earlier comment.

Before presenting the revised yes/no gate, post a new issue comment beginning with:

```markdown
## Recommendation Revision
```

Record concisely:

* the earlier recommendation or assumption being revised;
* the challenge, new evidence, or concrete-contract finding that changed the analysis;
* why the previous approach no longer holds;
* the revised recommendation.

Then present that revised recommendation in the live exchange and ask the exact required yes/no question again.

Do not create a revision comment for mere wording cleanup that does not change the material recommendation.

After acceptance, keep the final resolution comment concise: record the accepted decision and point to the durable ADR/docs/commits as applicable rather than duplicating the full analysis.

## Fog of War

The map is deliberately incomplete.

Beyond live tickets lies **fog of war** — decisions or investigations that are visibly coming but cannot yet be stated precisely because they depend on unresolved questions.

Record this in **Not yet specified**.

### Fog or Ticket?

* **Ticket** when the question can already be stated precisely.
* **Not yet specified** when it cannot.

**Not yet specified** excludes what is already decided, ticketed, or out of scope.

## Out of Scope

Fog gathers only toward the destination.

Work beyond the destination is **out of scope**, not fog.

When an existing ticket proves to sit beyond the destination, close it and leave one linked line in **Out of scope**.

Do not place it in **Decisions so far**.

## Invocation

Two modes.

Either way, **never resolve more than one ticket per session**, except research tickets.

### Execution Lifecycle Guardrails

#### 1. Pre-Flight Metadata Audit

The moment a GitHub issue number or URL is supplied:

```bash
gh issue view <ISSUE_NUMBER> --json labels,title,body
```

#### 2. Workflow Routing

* `wayfinder:grilling` → `$grilling` and `$domain-modeling`;
* otherwise route by ticket type through `$research`, `$prototype`, or AFK execution.

HITL routing always preserves the **Ticket Types** human-decision invariant.

### Chart the Map

User invokes with a loose idea.

1. **Name the destination.** Run `$grilling` and `$domain-modeling`.
2. **Map the frontier.** Surface open decisions breadth-first. For software architecture, include unresolved architectural consequences and apply **Architecture Implementability Closure** before treating the route as clear.
3. If no fog remains, continue the grilling session to completion instead of creating a map.
4. Otherwise create the map with `wayfinder:map`.
5. Create currently specifiable tickets and wire blocking edges.
6. Fire research subagents for research tickets.
7. Persist repository artifacts through **Repository Persistence** when applicable.
8. After the map/ticket/dependency state is durable, invoke `$project-delivery-management` `reconcile`. Do not establish or change focus as part of charting.
9. Stop. Charting does not hand-resolve tickets.

The same persistence rule applies when charting collapses into a single `$grill-with-docs` session. A collapse that creates no Wayfinder map has no Wayfinder focus or formal Wayfinder artifact to reconcile.

### Work Through the Map

User invokes with a map or decision ticket.

If given a ticket, resolve its parent Wayfinder map using the tracker's native relationship or explicit `Parent Wayfinder` metadata, then treat that ticket as the named decision.

1. Load the **map**, not every ticket body.
2. Apply **Project Delivery Focus Guard** and require `PROJECT DELIVERY GUARD: ALLOWED` before claiming or mutating the decision.
3. Choose the named ticket or first frontier ticket and **claim it** before work.
4. Resolve it. Fetch related detail only as needed. Use `$grilling` and `$domain-modeling` when appropriate. For architecture, apply **Resolve Architecture Before Handoff** and **Architecture Implementability Closure**.
5. For a HITL decision, after investigation is materially complete, persist the required **Decision Analysis** comment before presenting the recommendation and explicit yes/no gate. If further exchange materially changes the recommendation, persist a **Recommendation Revision** before asking again.
6. Do not treat the recommendation as the user's decision. Obtain the explicit human response required by **Ticket Types** before resolution.
7. **Persist the resolution**:

   * reconcile required authoritative architecture records;
   * if repository files changed, complete **Repository Persistence**;
   * only after persistence succeeds, post the concise resolution comment, close the ticket, and append its context pointer to **Decisions so far**.
8. Add newly surfaced decisions, wire dependencies, graduate newly specifiable fog, and move newly out-of-scope work. If the decision invalidates other map state, update or delete affected tickets.
9. After all Wayfinder-owned tracker/repository mutations from this decision are durable, invoke `$project-delivery-management` `reconcile` before the Post-Resolution Gate.

## Post-Resolution Gate

After every resolved decision, **re-evaluate the parent map before ending the session**, including re-entry into an already-closed map.

Confirm:

* no open decision tickets remain;
* **Not yet specified** contains no unresolved in-scope fog;
* no material architecture question remains unresolved;
* **Architecture Implementability Closure** passes for materially affected architecture;
* required authoritative architecture records are reconciled;
* required Decision Analysis and any material Recommendation Revision are durably recorded on the decision ticket;
* the new decision has not left stale or contradictory map state or affected prior decisions unreconciled;
* all Wayfinder-owned repository changes are committed and pushed;
* required project-delivery reconciliation completed successfully.

When a new decision supersedes or invalidates an earlier decision, preserve the historical resolution but update affected map/ticket state enough to make the supersession explicit.

A closed map or existing derived Spec does **not** waive this gate.

For every closed material software decision, require either a current **Certified Decision Contract Domain** or a legacy-equivalent frozen domain recoverable under the compatibility rules of Certified Semantic Domain Finality. A later route-level challenger must reconcile against that boundary before creating or reopening work. Missing legacy finality evidence may make route clarity unresolved, but it does not authorize the challenger to manufacture a broader domain and immediately persist every newly imagined dimension as a ticket.

If another unresolved decision, missing implementability choice, or newly specifiable fog remains, the route is not clear.

Except for additional research tickets permitted by **Invocation**, do not resolve another ticket in the same session.

After updating the map, identify the current frontier from authoritative tracker state before emitting any handoff or returning:

* If one open, unblocked, unclaimed frontier ticket is available, halt with:

  > ✅ **Wayfinder decision resolved.**
  >
  > Please continue with:
  >
  > ```
  > $wayfinder - <Next Decision Ticket Title> (<Ticket URL>)
  > ```

* If multiple frontier tickets are available, output one copy-ready `$wayfinder` line per frontier ticket and let the user choose the next session. The user may run independent frontier tickets in parallel because they remain inside the same focused Wayfinder delivery scope.
* If open decision tickets remain but every one is blocked, keep the map focused when it remains map-frontier eligible, report `PROJECT DELIVERY: FOCUSED-BUT-STALLED`, surface the exact decision blockers, and stop. Do not create a map blocker or release/switch focus.
* If unresolved in-scope fog remains but no frontier ticket can yet be stated, report the remaining fog and stop. Do not present a downstream handoff.

Then stop.

The route is not clear while:

* decision tickets or in-scope fog remain;
* a material architecture question remains unresolved;
* implementation of an affected canonical contract/path/lifecycle would still require inventing a durable architectural choice;
* authoritative records remain unreconciled;
* affected prior map state remains contradictory or stale;
* Wayfinder-owned repository changes remain uncommitted or unpushed;
* project-delivery reconciliation required by the current transition remains unresolved.

When the Post-Resolution Gate passes and the destination is an implementation specification, halt with a Human Handoff Intercept.

If continuation inheritance is `synchronized` or `not-applicable`:

> ✅ **Wayfinder route is clear.**
>
> Please run:
>
> ```
> $to-specs - <Wayfinder Map Title> (<Map URL>)
> ```

If continuation inheritance is `semantic-reconciliation-required`, the route is still architecturally clear, but say so explicitly:

> ✅ **Wayfinder route is clear; downstream semantic reconciliation is required.**
>
> Canonical authority: `<main commit>`
> Continuation branch: `<branch>`
> Automatic inheritance conflicts: `<exact paths>`
>
> Please run:
>
> ```
> $to-specs - <Wayfinder Map Title> (<Map URL>)
> ```
>
> `$to-specs` must reconcile existing governed Specs against the canonical authority before downstream implementation/review resumes.

Do not emit the `$to-specs` handoff for `blocked-by-concurrency` or `blocked-by-missing-branch`; first recover the branch identity/concurrency condition.

Always hand `$to-specs` the **Wayfinder map**, never an individual decision ticket or derived Spec.

`$to-specs` owns deciding whether this creates a new Spec or delegates an existing-Spec update to `$to-remediation-specs`.

The project-delivery focus remains on the governing Wayfinder across this handoff; route clarity does not release or switch focus.

The user may run unblocked tickets in parallel, so expect other sessions to edit the tracker concurrently.

## Transition-Bound Route Clarity

`Route is clear` is a lifecycle transition and must be derived from explicit current state rather than from the absence of newly noticed questions.

Immediately before declaring a map ready for specification, closing a destination-complete map, or emitting the route-clear Human Handoff, build a working **Route Clarity Record** from the complete current map and applicable architecture state:

```text
Open decision tickets: <count + identities>
Blocked/non-actionable open decisions: <count + identities>
Unresolved in-scope Not yet specified fog: <count + items>
Unresolved architecture implementability obligations: <count + items>
Material Contract Closure Record: <complete | incomplete; unresolved count>
Fresh route-clarity challenger: <PASS | FAIL | unavailable>
Route candidate finality reconciliations: <complete | incomplete; unreconciled count>
Domain-expansion candidates creating work: <count>
Unresolved source/authority conflicts: <count + items>
Required authoritative records unreconciled: <count + items>
Wayfinder-owned repository state uncommitted/unpushed: <count/state>
Continuation branch: <branch | None>
Canonical authority commit: <sha | None>
Continuation inheritance: <synchronized | semantic-reconciliation-required | blocked-by-concurrency | blocked-by-missing-branch | not-applicable>
Continuation conflict paths: <exact set | None>
Required project-delivery reconciliation: <complete | unresolved>
Route clarity: <clear | not-clear>
```

`Route clarity: clear` requires:

* open decision tickets = 0;
* blocked/non-actionable open decisions = 0;
* unresolved in-scope fog = 0;
* unresolved architecture implementability obligations = 0;
* Material Contract Closure Record is complete with unresolved = 0 and unclassified/omitted material dimensions = 0;
* fresh route-clarity challenger = PASS;
* route candidate finality reconciliations are complete with unreconciled = 0;
* domain-expansion candidates creating work = 0;
* unresolved source/authority conflicts = 0;
* required authoritative records unreconciled = 0;
* no required Wayfinder-owned repository persistence remains;
* continuation inheritance is not `blocked-by-concurrency` or `blocked-by-missing-branch`;
* `semantic-reconciliation-required` is permitted only when the emitted next step is the owning downstream reconciliation workflow and the Route Clarity Record durably carries the canonical commit, continuation branch, and exact conflict paths;
* required project-delivery reconciliation is complete.

Every current `Not yet specified` item must either remain explicitly unresolved, have graduated to a decision ticket, have been durably resolved/represented, or have moved out of scope with authority. It may not vanish because the known decision tickets are closed.

The existing Post-Resolution Gate remains authoritative procedure; this record is its enforceable transition state. The human-facing handoff may remain concise.
