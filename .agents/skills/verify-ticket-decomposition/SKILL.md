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
Source state identity: <Spec body/contract/root hashes or equivalent durable identities>
Proposal identity: <sha256 of exact rendered proposal>
Exact proposed ticket bodies/actions: <complete candidate>
Parent coverage candidate: <exact rendered manifest/delta>
Spec obligation routing: <IDs + dispositions>
Architecture/design source inventory: <durable source identities + anchors + dispositions>
Normative source-unit / ARCHSRC routing: <IDs + source anchors + dispositions>
Parent semantic-carry evidence: <compact rows/pointers>
Design-delegation result: <compact rows/pointers>
```

The packet locates authority efficiently. It does not establish that the source universe, routing, or carry is correct.

Missing, stale, contradictory, or candidate-mismatched dispatch state invalidates verification. Do not emit PASS or FAIL for an unbound candidate.

## Certification Procedure

### 1. Recover and challenge the authoritative universe

Read the originating Spec/remediation authority and every architecture/design source materially identified by the supplied bounded inventory. Follow a current source reference beyond that inventory only when the referenced authority is required to interpret the affected boundary or concretely falsifies source closure.

Independently check that:

* the implementation-ready source contract is the one bound to the proposal;
* every materially normative source unit in the bounded source set is represented by a Spec cell, `ARCHSRC-*`, or an authority-backed non-implementation disposition;
* no material condition, negative rule, temporal boundary, failure state, preservation rule, or implementation destination was hidden by grouping or declared duplicate without semantic entailment;
* no current owning architecture/design source required by the affected boundary was omitted.

Do not broaden the source universe merely to seek extra confidence. Concrete authority relationships and falsifiers control expansion.

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
* verification-only, no-work, exclusion, deferred, and remediation/preservation dispositions have explicit authority and destination where required;
* ticket boundaries are coherent tracer-bullet slices rather than semantic fragments whose correctness depends on an unstated later choice;
* dependency edges preserve required implementation ordering without silently delaying a safety invariant past a ticket that would already expose the affected behavior;
* no ticket acceptance contract contradicts the source, another mapped ticket, or the parent coverage candidate;
* no unresolved material product/domain/public-contract/architecture/persistence choice is delegated to implementation.

Tracker formatting, labels, exact native relationship persistence, and branch mechanics remain parent-owned deterministic checks unless they change semantic meaning.

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
Semantic carry: complete; incomplete 0; ambiguous 0
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
1. Classification: missing-source | missing-predicate | incomplete-carry | misrouted | dependency-safety | design-delegation | contradiction
   Governing source: <durable source + anchor>
   Authoritative requirement: <compact requirement>
   Affected proposal element: <ticket/manifest/dependency>
   Defect: <exact omission/contradiction>
   Required closure condition: <what must become true; do not redesign the ticket set>
...
```

A FAIL is a bounded falsifier report, not a replacement proposal. The parent owns repair, reruns its deterministic/readiness checks on the revised candidate, and returns that exact candidate to the same verifier context for recheck.

Do not emit tentative findings after PASS. Do not continue searching for additional confidence once the authoritative bounded universe and every material carry predicate are closed.
