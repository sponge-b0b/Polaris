---
name: verify-ticket-closure
description: Independently certify or reject semantic closure of one immutable Implementation Ticket candidate. Ordinary and Spec Review remediation tickets use the same verifier; remediation adds Root Blocker obligations to the common acceptance universe.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Ticket Closure

Independently certify or reject closure of one immutable ticket candidate.

This skill is the **single semantic closure authority** for both ordinary Implementation Tickets and Spec Review remediation tickets.

> The implementation actor may propose closure evidence, but it may not certify its own candidate.

Remediation extends the acceptance universe. It does not create a second verifier or a second verdict.

## Invocation Semantics

`$verify-ticket-closure` has two execution modes. The normal ticket lifecycle uses the fresh verifier leaf; direct human invocation is optional recovery/manual entry, not a required authorization gate.

### Fresh verifier leaf — normal path

After `$implement-ticket` writes and reads back an exact `<!-- implement-ticket-closure-checkpoint:v2 -->` in `Stage: awaiting-closure-verification`, the `$implement-ticket` main agent enters dispatcher-only mode and spawns exactly one genuinely fresh verifier subagent.

Only that fresh subagent executes the certification procedure below. Before doing so it must recover/validate the supplied durable checkpoint and require exact ticket/mode/branch/baseline/contract/lineage/root/candidate binding.

The `$implement-ticket` main agent remains the orchestration owner. The fresh verifier returns one complete verdict to that parent; it does not repair, persist lifecycle state, close the ticket, or spawn another semantic verifier.

### Direct / recovery invocation

A human may still invoke `$verify-ticket-closure - <ticket>` directly for recovery, manual recertification entry, or after complete conversational/session context loss. That command is **not** required in the normal `$implement-ticket` lifecycle and does not authorize the top-level agent to certify the candidate itself.

The top-level agent must recover the ticket's durable `<!-- implement-ticket-closure-checkpoint:v2 -->` comment and resume `$implement-ticket` at the recorded lifecycle state:

* `awaiting-closure-verification` with matching ticket/mode/branch/baseline/contract/lineage/root/candidate state → resume `$implement-ticket` dispatcher-only mode and spawn one fresh verifier;
* `verifier-failed` → do **not** dispatch the stale candidate; resume `$implement-ticket` correction from the complete stored `TICKET CLOSURE: FAIL`;
* `verifier-passed` → do not re-certify; resume `$implement-ticket` persistence after exact-state validation;
* missing, duplicated, malformed, stale, or contradictory checkpoint state after an attempt began → fail closed and return control to `$implement-ticket`.

The same direct command plus the same durable repository/tracker state must produce the same lifecycle continuation whether or not prior conversational context exists.

If this skill is being executed by the `$implement-ticket` main agent rather than by the genuinely fresh dispatched verifier subagent, do not perform certification or emit a ticket-closure verdict.

A direct ad hoc execution outside the `$implement-ticket` checkpoint lifecycle is not a valid certification run.

## Verifier Integrity

Only the fresh dispatched verifier executes the remaining sections.

A valid verifier is:

* fresh — it did not implement the candidate or participate in parent acceptance reconciliation;
* non-mutating — it may read/search/inspect and run non-mutating checks, but may not edit repository/tracker/Git state;
* non-delegating — it may not spawn another semantic verifier;
* candidate-bound — it certifies exactly the supplied Ticket baseline, ticket contract, and candidate state.

Candidate mutation, verifier mutation/delegation, or unrecoverable authoritative state invalidates the run. Return an invalid-verification result; do not emit PASS or FAIL.

## 1. Recover the Immutable Contract

Independently read:

* full ticket and comments;
* native parent and declared lineage;
* `Ticket branch`, pinned `Ticket baseline`, exact current candidate state;
* durable v2 closure checkpoint used for dispatch;
* ticket-governed durable tracker state when applicable;
* parent Spec and exact `Spec obligations` carried by the ticket when present;
* current architecture/Standards/policy authority required by the ticket;
* Proposed Closure Evidence as claims to challenge, never authority.

Determine ticket mode: ordinary or Spec Review remediation.

For remediation also recover:

* remediation parent Spec Review;
* stable Root Blocker ID/invariant;
* cumulative carried acceptance cells;
* remediation and verification obligations;
* same-root preservation obligations;
* previously satisfied other roots whose governed contracts intersect the candidate.

Missing, ambiguous, contradictory, or stale contract/candidate state invalidates verification.

## 2. Build the Authoritative Acceptance Universe

Build the universe independently from durable authority, not from changed files, existing tests, implementation notes, Proposed Closure Evidence, or known defect patterns.

### Ordinary cells

Create one `AC-<n>` cell for every distinct normative ticket obligation, including:

* every explicit acceptance criterion;
* carried `Spec obligations` applicable to this ticket's promised slice;
* required build/preservation/negative-path behavior stated by the ticket;
* required production/authoritative-path proof;
* verification obligations that determine semantic completion.

Do not merge materially distinct claims merely because they share evidence or a subsystem.

### Remediation extension

For remediation add to the same universe:

* every active Root Blocker remediation obligation;
* every carried root acceptance cell;
* every verification-only root obligation;
* every same-root preservation obligation;
* every independently required root sibling/alternate surface;
* every applicable protected-root preservation obligation.

There is still one `AC-*` universe and one verdict.

Before proof require exact authoritative-obligation ↔ acceptance-cell accounting:

```text
Authoritative obligations: <n>
Acceptance cells: <n>
Unmapped obligations: 0
Ambiguous mappings: 0
Merged-distinct obligations: 0
```

If the universe cannot be closed, affected cells are `unproven`.

### Authoritative domain membership

Before proving any material cell whose domain can produce finite, discoverable, alternate, sibling, or adversarial candidates, bind the boundary that determines which candidates belong to that domain:

```text
Domain authority: <durable source(s) that define the boundary>
Membership predicate: <what makes a candidate a member of this domain>
```

Derive the membership predicate from durable authority, including explicit enumerations, normative definitions, and authoritative composition or ownership boundaries. Do not derive it from changed files, implementation structure, existing tests, known defects, lexical similarity, subsystem proximity, or verifier intuition.

Discovery may reveal a candidate. Discovery does not create authority.

If the authoritative domain is semantically open-world rather than finitely enumerable, define the inclusion rule and the exhaustive/discovery mechanism that can establish closure to the practical boundary required by the claim. If membership of a material candidate cannot be resolved from current authority, the candidate is `ambiguous` and the affected cell/domain remains `unproven`; do not silently widen or narrow the authoritative claim.

## 3. Per-Cell Proof Contract

Every material cell binds compact certification state:

```text
Acceptance: AC-<n>
Source: <exact ticket / Spec / root obligation>
Claim: <exact semantic claim>
Domain: <authoritative domain>
Domain authority: <durable source(s) defining membership>
Membership predicate: <what makes a candidate part of this domain>
Nested domains: <None | closed domain manifests>
Predicate: <what must be true>
Falsifier: <concrete state making the claim false>
Evidence: <current evidence excluding the falsifier>
State: <unchecked | proven | violated | unproven>
```

This is proof state, not a private reasoning transcript.

### Evidence entailment

A cell is `proven` only when evidence establishes **that exact predicate** across its exact domain.

Shared evidence may support several cells, but every cell retains its own entailment decision. A broad upstream architectural fact cannot silently certify a narrower externally visible or operational claim.

Ask:

> Could every cited check pass while this exact claim is still false?

If yes, it is not proven.

### Nested Universe Closure

For `all`, `every`, `none`, `only`, `complete`, `highest practical`, all supported profiles, all response paths, all consumers, or equivalent finite/discoverable domains, materialize and completely disposition the nested domain.

Examples include:

* profile × applicable presentation seam;
* contract transition × affected consumer;
* response contract × constructor/adapter/mapper/schema/transport path;
* workflow transition × entry/re-entry/fallback path;
* operational owner × production composition path.

Each nested domain carries its own durable authority and membership predicate. `unchecked = 0` over an incompletely constructed domain is not proof. Familiar-symbol searches and passing tests are supporting evidence unless they are an independently checkable exhaustive mechanism for the authoritative domain.

### Production composition

When the claim is about application/runtime/operational behavior, prove the canonical production path rather than component capability alone.

Inspect applicable provider/factory, DI/bootstrap, entrypoint/runtime owner, consumer, persistence/reconstruction, or analogous workflow/tracker composition only when the claim depends on that composition.

### Negative / fail-closed proof

For `cannot`, `must not`, `fails closed`, `cannot bypass`, blocked/withheld, or equivalent obligations, derive meaningful falsifying states at the boundary being certified and actively test/inspect whether they survive.

Do not prove a fail-closed boundary only with already-sanitized or otherwise well-formed upstream state when that boundary must reject an inconsistent/malformed state.

Do not make thin transports reimplement upstream policy; verify the responsibility assigned to the boundary.

## 4. Delegated Evidence

Existing owner skills provide evidence but do not become semantic closure authority unless the acceptance predicate is exactly mechanically decided by that result.

Examples:

* `$verify-code` owns targeted code checks and its contract transition/consumer closure;
* documentation/wiki workflows own their validations;
* migration/database workflows own required schema/database proof;
* deterministic tracker rereads own exact relationship/state facts.

Require valid terminal results when such evidence is mandatory. Green Ruff/Mypy/pytest counts cannot by themselves prove a different semantic claim.

## 5. Independent Adversarial Sweep

After explicit cells are dispositioned, sweep outward from each material claim/invariant, not inward from the diff.

Inspect only bounded surfaces capable of satisfying or bypassing it, including where applicable:

* constructors/factories/defaults;
* producers/consumers/adapters/facades;
* bootstrap/DI/composition;
* persistence/result/reconstruction paths;
* alternate transport/renderer/schema/catalog paths;
* workflow entry/re-entry/fallback/default paths;
* tracker relationship/projection authority;
* configuration/CI alternates;
* docs/ADR competing authority.

Every candidate inspected because it could plausibly satisfy or bypass the exact claim must first be classified against that claim's authoritative domain membership predicate. Preserve a compact Domain Membership Manifest:

```text
Candidate: <surface/path/member>
Parent: <AC-n | nested-domain cell>
Domain authority: <durable source>
Membership predicate: <predicate>
Disposition: in-domain | out-of-domain | ambiguous
Evidence / authority: <why the disposition follows>
```

Apply the disposition mechanically to the certification universe:

* `in-domain` → the candidate becomes an invariant-sweep or nested-domain cell and must be dispositioned before verdict;
* `out-of-domain` → preserve the observation, but it does not become a ticket acceptance obligation and cannot block certification solely because it is adjacent, similar, or hypothetically exploitable;
* `ambiguous` → the affected acceptance/nested-domain cell remains `unproven`; do not resolve uncertainty by silently broadening durable authority.

Do not classify a candidate `in-domain` solely because it shares a symbol, subsystem, implementation mechanism, or semantic theme with the claim. A broader candidate belongs only when the durable authority or another authoritative carried obligation actually supplies that broader membership predicate.

For remediation this is the Root Invariant Sweep and also re-proves applicable carried same-root cells/protected roots against current authority. Historical PASS/satisfied/unchanged state is evidence history, not current proof.

Do not broaden into unrelated review.

## 6. Completeness and Failure Accumulation

After verifier integrity is established, do not fail fast on implementation/proof defects. Record each and complete the bounded universe so one run returns all independently observable closure failures.

Before verdict require:

```text
Acceptance coverage: <n> cells
proven: <n>
violated: <n>
unproven: <n>
unchecked: 0
Nested domains required: <n>
Nested domains closed: <n>
Open nested-domain candidates: 0
Domain-membership candidates: <n>
in-domain: <n>
out-of-domain: <n>
ambiguous membership: 0
Undispositioned domain candidates: 0
Unproven material assumptions: 0
```

Any violated/unproven/unchecked cell, incomplete nested domain, ambiguous/undispositioned domain candidate, or unproven material assumption blocks PASS.

## 7. Verdict

Return exactly one semantic verdict for the immutable candidate.

### PASS

```text
TICKET CLOSURE: PASS
Ticket: #<n>
Mode: ordinary | remediation
Ticket baseline: <sha>
Candidate state: <hash>
Ticket contract identity: <durable identity>
Acceptance: <n>; proven <n>; violated 0; unproven 0; unchecked 0
Nested domains: <n>; closed <n>; open 0
Domain membership: <n>; in-domain <n>; out-of-domain <n>; ambiguous 0
Production-path obligations: <summary>
Negative/fail-closed obligations: <summary>
Remediation root: <None | RB-n — invariant>
Protected roots: <None | concise dispositions>
Evidence: <compact per-cell/current evidence summary>
```

### FAIL

```text
TICKET CLOSURE: FAIL
Ticket: #<n>
Mode: ordinary | remediation
Ticket baseline: <sha>
Candidate state: <hash>
Acceptance: <n>; proven <n>; violated <n>; unproven <n>; unchecked 0
Nested domains: <n>; closed <n>; open <n>
Domain membership: <n>; in-domain <n>; out-of-domain <n>; ambiguous <n>
Findings:
1. <AC-n / source / falsifier or missing proof / concrete evidence / required correction>
...
Remediation root: <None | RB-n — invariant>
Protected-root regressions: <None | findings>
```

Do not repair. Return the complete verdict to `$implement-ticket`.

## 8. Candidate Binding

PASS authorizes only the exact candidate state, baseline, ticket contract, lineage, and remediation/root state certified.

Any substantive repository/tracker mutation after PASS makes certification stale unless an independently certified invalidation boundary plus deterministic fail-closed delta analysis proves the exact proof remains valid. `$implement-ticket` does not make that semantic judgment itself.

When uncertain, recertify.
