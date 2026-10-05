---
name: verify-ticket-decomposition
description: Independently certify or reject semantic completeness and fidelity of one frozen $to-tickets proposal before human approval. This verifier checks decomposition only; it does not redesign, mutate, publish, or certify implementation.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Verify Ticket Decomposition

Independently certify or reject one exact frozen `$to-tickets` proposal before human approval.

> `$to-tickets` may author and self-check the decomposition, but it may not independently certify its own semantic carry.

This verifier exists to catch omissions, semantic compression, misrouting, or hidden design delegation in the exact proposed ticket contracts. It is not a second decomposition author, a general adversarial review, or an implementation verifier.

## Invocation Boundary

Normal invocation is internal to `$to-tickets` after parent-owned `TICKET PROPOSAL READINESS: PASS` and before the proposal is shown for approval.

For one substantive proposal lifecycle, `$to-tickets` dispatches exactly one genuinely fresh verifier context executing this skill. The parent remains the orchestration and mutation owner.

The fresh verifier is:

* **fresh** — it did not author, route, or repair the proposal;
* **non-mutating** — it may read/search/inspect only;
* **non-delegating** — it may not spawn another semantic verifier or challenger;
* **candidate-bound** — it certifies exactly one supplied proposal identity and source state;
* **source-grounded** — parent matrices and findings are retrieval maps, not semantic authority.

If the verifier returns FAIL and the parent repairs the proposal, resume the same verifier context against the revised exact candidate when the execution environment supports continuation. Do not start a fresh challenger cascade. If that verifier context becomes unavailable, treat the prior certification attempt as invalid and use only one replacement recovery verifier, with the replacement disclosed in the final readiness summary.

Metadata-only deterministic normalization that `$to-tickets` is already authorized to publish without substantive approval does not require this semantic verifier.

## Required Dispatch Packet

The parent supplies a compact retrieval packet containing:

```text
Source artifact: <durable identity>
Mode: fresh | remediation
Source state identity: <Spec Body Hash + Spec Contract Hash + root hashes or equivalent durable identities>
Parent TCM identity: <persisted pre-publication Spec Body Hash + Spec Contract Hash when a TCM exists>
Proposal identity: <sha256 of exact rendered proposal>
Exact proposed ticket bodies/actions: <complete candidate>
Parent coverage candidate: <exact rendered manifest/delta, including proposed Spec Body Hash + Spec Contract Hash when the TCM is part of substantive reconciliation>
Spec obligation routing: <IDs + dispositions>
Architecture/design source inventory: <durable source identities + anchors + dispositions>
Normative source-unit / ARCHSRC routing: <IDs + source anchors + dispositions>
Parent semantic-carry evidence: <compact rows/pointers>
Parent semantic-consumer impact evidence: <None | compact changed-invariant/consumer rows when remediation or changed authority makes it applicable>
Parent Context-Fit Manifest: <per-ticket scenario/domain/modality/proof-family summary + disposition>
Design-delegation result: <compact rows/pointers>
```

The packet locates authority efficiently. It does not establish that the source universe, routing, consumer propagation, or carry is correct.

Missing, contradictory, or candidate-mismatched dispatch state invalidates verification. A stale persisted parent TCM also invalidates verification except in a substantive remediation where `$to-tickets` explicitly carries that stale TCM as pre-publication state, the exact proposed parent coverage candidate is part of the frozen proposal, and that candidate repairs the identity to the bound current Spec contract. In that bounded case, the persisted stale TCM is an input to be repaired rather than evidence of candidate mismatch.

## Certification Procedure

### 1. Recover and challenge the authoritative universe

Read the originating Spec/remediation authority and every architecture/design source materially identified by the supplied bounded inventory. Follow a current source reference beyond that inventory only when the referenced authority is required to interpret the affected boundary or concretely falsifies source closure.

Independently check that:

* the implementation-ready source contract is the one bound to the proposal;
* when a parent Ticket Coverage Manifest exists and the proposal does **not** include substantive reconciliation of that TCM, the persisted TCM and bound current Spec contract have equal Spec Body Hash and Spec Contract Hash values;
* when a substantive remediation explicitly includes the parent TCM as part of the frozen proposal because `$to-tickets` cannot legally normalize it before semantic verification, the persisted TCM may differ only as the declared pre-publication state being repaired; the exact proposed parent coverage candidate must carry the bound current Spec Body Hash and Spec Contract Hash, and the verifier must independently certify its identity, routing, semantic delta, and publication action as part of the candidate;
* a stale persisted TCM without that exact bound proposed repair is contradictory dispatch state and invalidates verification before PASS/FAIL; matching body text, cell counts, cell-ID sets, or routing counts may not be used to infer contract equivalence;
* the proposed TCM candidate may not silently erase or bypass the stale-state discrepancy: the exact frozen actions must update the persisted TCM to the certified candidate only after verifier PASS and parent-owned human approval/publication;
* for a fresh Spec proposal, the exact Spec-cell ID set rendered in the parent Ticket Coverage Manifest is **identical** to the exact Spec-cell ID set emitted by the bound `$spec-contract` manifest;
* for that equality check, independently compute both directional differences and require missing source-derived cells = 0 and extra/non-source-derived cells = 0; a proposal containing every source cell plus one synthetic cell must FAIL;
* every disposition in a fresh-Spec Ticket Coverage Manifest refers to an existing source Spec cell; workflow/lifecycle/publication mechanics may not appear as synthetic Spec cells unless `$spec-contract` itself emits them;
* every materially normative source unit in the bounded source set is represented by a Spec cell, `ARCHSRC-*`, or an authority-backed non-implementation disposition;
* no material condition, negative rule, temporal boundary, failure state, preservation rule, or implementation destination was hidden by grouping or declared duplicate without semantic entailment;
* no current owning architecture/design source required by the affected boundary was omitted.

Do not broaden the source universe merely to seek extra confidence. Concrete authority relationships and falsifiers control expansion.

### 1A. Independently trace semantic consumers of changed invariants

For every materially normative source unit, Spec predicate, or `ARCHSRC-*` obligation that is new, changed, rerouted, or implicated by remediation, identify the semantic subject/invariant it governs. Then independently inspect the exact proposed/retained active ticket universe for operations over that subject.

A ticket is a **semantic-consumer candidate** when its contract creates, mutates, revises, corrects, retracts, reassesses, validates, interprets, reconstructs, replays, persists, serializes, migrates, exposes, authorizes, or otherwise makes a semantic claim about the changed subject.

Discovery must not stop at producer ownership. In particular:

* correction/revision paths consume the current invariant of the entity they correct;
* reconstruction/replay/read paths consume the invariant when they derive current or historical meaning from it;
* persistence/migration paths consume it when schema/codec/store behavior can admit or preserve an invalid semantic state;
* explicit ticket language that defers or hands ownership to another ticket, such as “correction interpretation remains owned by #N”, must be followed to that current destination and challenged there;
* native dependencies, common files, and existing ADR citations are discovery hints, not the completeness denominator;
* absence of an explicit citation to the changed architecture source does not establish non-applicability.

For each changed invariant × candidate ticket derive an independent row:

```text
Changed obligation/source unit: <Spec cell | ARCHSRC-* | source anchor>
Semantic subject/invariant: <exact changed meaning>
Consumer ticket: <ticket identity>
Consumer operation: <create | mutate | correct | retract | reassess | validate | interpret | reconstruct | replay | persist | serialize | migrate | expose | authorize | other>
Discovery evidence: <exact ticket/source relation>
Invariant applicability: applies | does-not-apply | ambiguous
Durable carry present: yes | no | n/a
Reason/authority: <why>
```

PASS requires:

* every `applies` row to have durable obligation carry in that consumer ticket or an explicit authority-backed active destination that executes before the consumer becomes actionable;
* every explicit downstream ownership handoff to terminate at a current destination whose applicable governing invariants were evaluated;
* every `does-not-apply` row to have positive semantic reason/authority, not merely “different ticket”, “no shared file”, or “not named by the source”;
* zero ambiguous applicability rows;
* zero active semantic consumers omitted from the parent manifest/ticket routing.

For remediation proposals, compare this independently derived set with the parent's Semantic-Consumer Impact Matrix when supplied. The parent matrix is retrieval evidence only; independently finding one additional applicable consumer is a decomposition FAIL.

Use a bounded falsifier question for every changed invariant:

> **Can any active ticket legally create, correct, reinterpret, reconstruct, persist, migrate, or expose this semantic subject in a way that would be wrong if it followed only its current contract and ignored the changed invariant?**

If yes, that ticket is an applicable consumer and must carry the obligation before the proposal can PASS.

Require:

```text
Changed semantic invariants challenged: <n>
Semantic-consumer candidates: <n>
Applicable semantic consumers: <n>
Applicable consumers with durable carry: <n>/<n>
Missing applicable consumer mappings: 0
Ambiguous consumer applicability: 0
Explicit downstream ownership handoffs untraced: 0
```

### 2. Independently certify semantic carry

For every implementation-bound Spec cell and `ARCHSRC-*` obligation, compare the authoritative requirement with the exact mapped ticket body or bodies.

PASS requires the ticket contract to preserve every materially significant predicate, including where applicable:

* conjunctions, exhaustive sets, identity/cardinality/uniqueness;
* conditions, triggers, eligibility, and deferred activation;
* effective/known/recorded-time semantics and evaluation order;
* positive and negative field/claim semantics;
* attribution, provenance, basis roles, ownership, and authority distinctions;
* atomicity, concurrency, expected-version, idempotency/replay, and conflict behavior;
* typed failure, fail-closed, contested/ambiguous, and no-recency/no-fallback rules;
* correction ancestry, replacement, restoration, and sibling behavior;
* preservation/non-regression obligations;
* explicit exclusions and forbidden representations/dependencies;
* required proof modality when the authority specifically requires real-service, concurrency, architecture, runtime, or negative-path proof.

An obligation ID or broad source citation is provenance only. It is never proof of semantic carry.

When one obligation spans tickets, certify the union and also verify that any predicate required independently at an earlier slice is present in that slice. No material choice may be left between tickets for `$implement-ticket` to invent.

### 3. Certify decomposition and dependency fidelity

Check that:

* every implementation obligation has one complete destination;
* every explicit cross-ticket semantic ownership/deferment handoff has a current destination and the destination has been evaluated for every governing invariant of the handed-off semantic subject;
* verification-only, no-work, exclusion, deferred, and remediation/preservation dispositions have explicit authority and destination where required;
* ticket boundaries are coherent tracer-bullet slices rather than semantic fragments whose correctness depends on an unstated later choice;
* dependency edges preserve required implementation ordering without silently delaying a safety invariant past a ticket that would already expose the affected behavior;
* no ticket acceptance contract contradicts the source, another mapped ticket, or the parent coverage candidate;
* no unresolved material product/domain/public-contract/architecture/persistence choice is delegated to implementation.

Tracker formatting, labels, exact native relationship persistence, and branch mechanics remain parent-owned deterministic checks unless they change semantic meaning.

### 4. Independently certify ticket context fit

Treat the parent Context-Fit Manifest as a falsifiable claim, not authority.

For every proposed implementation/remediation ticket, independently derive the smallest authoritative set of:

* independently implementable semantic scenario families;
* material semantic closure domains;
* required proof modalities or runtime/service boundaries;
* proof/invalidation families that require materially different evidence.

Then challenge the proposed slice:

* if two subsets can each be implemented and semantically verified while leaving a green intermediate state, require separate tracer bullets unless durable authority requires atomic co-delivery;
* do not infer small scope from file count, line count, a single test module, or absence of production-code changes;
* do not multiply complexity merely because one semantic predicate carries several provenance IDs; equivalent authority may map to one scenario family;
* conversely, do not hide several lifecycle transitions, authority boundaries, failure families, temporal modes, or correction paths inside one broad acceptance criterion and count them as one family;
* normal PASS requires a credible one-fresh-context implementation/verification/closure lifecycle;
* an `indivisible-two-window-exception` is valid only when the verifier can identify durable authority or unavoidable green-state coupling that makes a smaller split invalid, and the resulting slice still plausibly fits within two fresh contexts;
* if context fit is ambiguous, treat the ticket as oversized rather than relying on the implementation agent to discover the split later;
* require each exact proposed ticket body's durable `Context fit` field to equal the verifier-derived disposition; for an `indivisible-two-window-exception`, require its durable reason to match the independently validated authority/green-state justification without changing meaning.

This is a decomposition gate, not a performance benchmark. Do not FAIL merely because a difficult defect could be discovered during implementation; FAIL when the **ordinary authorized slice itself** is knowingly too semantically dense.

Require:

```text
Tickets assessed for context fit: <n>
One-window tickets: <n>
Validated indivisible two-window exceptions: <n>
Oversized tickets: 0
Ambiguous context-fit dispositions: 0
Durable ticket `Context fit` fields matching verifier disposition: <n>/<n>
Mismatched/missing durable Context-fit fields: 0
```

## Verdict

Return exactly one complete verdict to the `$to-tickets` parent.

PASS:

```text
TICKET DECOMPOSITION: PASS
Source: <identity>
Mode: fresh | remediation
Source state identity: <identity/hash>
Proposal identity: <sha256>
Verifier: fresh-independent
Source closure: complete; missing material sources/units 0
Spec-cell identity: exact; source <n>; manifest <n>; missing 0; extra 0
Semantic consumers: candidates <n>; applicable <n>; accounted <n>/<n>; missing 0; ambiguous 0; untraced ownership handoffs 0
Semantic carry: complete; incomplete 0; ambiguous 0
Context fit: one-window <n>; validated indivisible two-window exceptions <n>; oversized 0; ambiguous 0; durable fields matched <n>/<n>
Design delegation: 0
Dependency/slice semantic defects: 0
Findings: 0
```

FAIL:

```text
TICKET DECOMPOSITION: FAIL
Source: <identity>
Mode: fresh | remediation
Source state identity: <identity/hash>
Proposal identity: <sha256>
Findings:
1. Classification: missing-source | invented-source-cell | missing-predicate | incomplete-carry | misrouted | consumer-omission | dependency-safety | oversized-slice | design-delegation | contradiction
   Governing source: <durable source + anchor>
   Authoritative requirement: <compact requirement>
   Affected proposal element: <ticket/manifest/dependency>
   Defect: <exact omission/contradiction>
   Required closure condition: <what must become true; identify the semantic condition without drafting replacement tickets>
...
```

A FAIL is a bounded falsifier report, not a replacement proposal. The parent owns repair, reruns its deterministic/readiness checks on the revised candidate, and returns that exact candidate to the same verifier context for recheck.

Do not emit tentative findings after PASS. Do not continue searching for additional confidence once the authoritative bounded universe, semantic-consumer closure, and every material carry predicate are closed.
