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

## Certified Semantic Domain Finality

This section is authoritative and strengthens every later domain-construction/closure rule in this file.

When PASS depends on closing a material finite/discoverable semantic domain, the fresh verifier is not only proving the candidate. It is also certifying the **membership interpretation** used to define that domain.

For every such domain, preserve one compact **Certified Closure Domain** record in the verifier PASS returned to `$implement-ticket`:

```text
Certified Closure Domain: <stable ND/domain ID>
Parent claim/root: <AC-n / RB-n when applicable>
Authority identity: <exact durable source identities/hashes when available>
Membership predicate: <what makes a candidate a member>
Dimensions / authoritative source sets: <explicit sets or bounded sources>
Closure criterion: <expected count | independently checkable open-world criterion>
Expected/generated/inspected/dispositioned: <counts when finite>
Material out-of-domain boundary observations: <concise list/families when needed>
Finality: frozen-under-unchanged-authority
```

A domain record is required when domain construction materially contributes to semantic PASS. Do not hide the final membership interpretation only inside narrative evidence.

Before PASS require:

```text
Material closure domains required: <n>
Certified closure-domain records: <n>
Missing domain records: 0
Unresolved domain identities: 0
```

The verifier must derive each record from the same durable authority/membership predicate already required below. The record does not broaden that authority.

### Meaning of finality

A later actor may challenge whether an **in-domain** member was incorrectly proven or later regressed. PASS never makes implementation behavior unquestionable.

But while the recorded authority identity is unchanged, a later actor may not silently replace the frozen membership predicate/source sets with a broader plausible interpretation and call that enlargement ordinary remediation.

A later candidate outside the frozen predicate is a domain-expansion observation unless:

* governing authority materially changed after certification; or
* unchanged durable authority contains an exact explicit contradiction to the certified predicate/source set that establishes a certification-integrity defect.

Lexical similarity, sibling APIs, implementation adjacency, subsystem proximity, or a broader plausible reading do not themselves invalidate the certified domain.

### Durability

`$implement-ticket` persists the complete verifier result in the durable closure checkpoint. The Certified Closure Domain records are therefore part of ticket/root semantic completion state and must remain recoverable after conversational/session loss.

A historical verifier result without these explicit records is not retroactively strengthened by this rule; later consumers may treat it as an equivalent frozen domain only when its durable record already contains enough authority, membership, construction, and boundary state to reconstruct the same interpretation without guesswork.

## Architecture / Design Decomposition Integrity

Ticket closure certification reuses the parent Spec's current `Ticket Coverage Manifest`, including its `Architecture / Design Obligation Coverage` (`ARCHSRC-*`) rows, and the ticket's exact `## Architecture obligations` IDs.

That artifact is routing/accounting evidence, not semantic authority.

Before acceptance-cell construction, independently derive the bounded architecture/design source set materially governing this ticket's promised slice and compare it with:

* the current parent-Spec Architecture/Design Obligation Disposition Manifest;
* the ticket's exact `Architecture obligations` IDs;
* the ticket's build/acceptance/preservation contract.

Require:

```text
Applicable material architecture/design obligations: <n>
Manifest rows covering applicable obligations: <n>
Missing manifest obligations: 0
Ambiguous manifest obligations: 0
Misrouted manifest obligations: 0
Ticket architecture IDs missing from manifest mapping: 0
Manifest implementation obligations absent from ticket contract: 0
```

Two failure classes are distinct:

* **implementation defect** — the architecture obligation is correctly decomposed/mapped to this ticket but the candidate does not satisfy it; return an ordinary `TICKET CLOSURE: FAIL` finding owned by `$implement-ticket`;
* **decomposition defect** — current governing architecture/design contains a material implementation obligation absent from, incompletely represented by, or misrouted in the parent manifest/ticket contract; return `TICKET CLOSURE: FAIL` with:

```text
Finding classification: decomposition-defect
Finding owner: $to-tickets
Governing source: <exact durable source + section>
Missing/misrouted obligation: <requirement>
Current manifest state: absent | incomplete | misrouted
```

The fresh verifier remains non-mutating. It does not update the parent manifest, ticket, or decomposition-defect record. The `$implement-ticket` parent persists the durable `DD-*` record and performs the Human Handoff to the current `$to-tickets` source owner.

Certified Closure Domains remain useful for independently freezing nested semantic membership **inside a correctly decomposed ticket claim**. They are not authority to suppress an explicit upstream architecture/design obligation that the decomposition failed to carry.

## Invocation Semantics

For ordinary ticket-candidate certification, the normal ticket lifecycle uses the fresh verifier leaf; direct human invocation is optional recovery/manual entry, not a required authorization gate. Architecture/design decomposition defects are reported as classified FAIL findings and routed by `$implement-ticket` to `$to-tickets`; this skill does not run a separate historical-certification reconciliation lifecycle.

### Fresh verifier leaf — normal path

After `$implement-ticket` writes and reads back an exact `<!-- implement-ticket-closure-checkpoint:v2 -->` in `Stage: awaiting-closure-verification`, the `$implement-ticket` main agent enters dispatcher-only mode and spawns exactly one genuinely fresh verifier subagent.

Only that fresh subagent executes the certification procedure below. Before doing so it must recover/validate the supplied durable checkpoint and require exact ticket/mode/branch/baseline/contract/lineage/root/candidate binding.

The supplied checkpoint, Proposed Closure Evidence, changed-surface/check summaries, and authority pointers are a compact **retrieval map**, not semantic authority. The verifier independently validates the durable sources needed for each claim and expands retrieval whenever bounded evidence is insufficient. It does not inherit or require the implementation actor's exploratory transcript.

The `$implement-ticket` main agent remains the orchestration owner. The fresh verifier returns one complete verdict to that parent; it does not repair, persist lifecycle state, close the ticket, or spawn another semantic verifier.

### Retry attempts — cumulative knowledge, fresh verdict

A genuinely fresh verifier is independent from candidate authorship and prior verifier execution; it is **not** a blank-slate verifier.

For Attempt 2 or later after a valid, saturated `TICKET CLOSURE: FAIL`, recover the exact prior verifier result and Attempt history from the durable checkpoint before reconstructing semantic state. The previous verifier's authority-derived construction is cumulative evidence and must be reused when its governing inputs remain valid.

When governing authority is unchanged, reuse rather than rediscover:

* bounded authority-source identities and dispositions;
* acceptance-cell identities and authoritative obligation mappings;
* frozen authority-first proof-plan identities;
* domain-construction manifests, membership predicates, authoritative source sets, member inventories or independently recoverable closure criteria;
* prior out-of-domain boundary observations;
* every prior finding and falsifier.

Freshness does not invalidate those authority-derived artifacts merely because a different verifier actor is running.

Prior cell, nested-member, or adversarial-candidate **dispositions** are reusable only when all of the following remain unchanged for that proof:

* governing authority;
* candidate-dependent evidence inputs;
* implementation surface on which the proof depends;
* relevant runtime/tracker/configuration/dependency inputs.

Determine invalidation from the actual candidate delta and the proof dependencies preserved in the prior retry state. Re-prove every cell/domain/member whose predicate could materially be affected by the repair or its blast radius. When uncertainty remains about whether a prior disposition is still valid, invalidate and re-prove the smallest semantic surface that resolves the uncertainty.

Every prior finding is a mandatory regression target. Attempt N+1 must explicitly classify each earlier unresolved finding as:

```text
closed | still-open | superseded-by-explicit-authority-change
```

Candidate mutation alone can never make a prior finding disappear. A finding classified `closed` requires direct evidence against the exact prior falsifier plus any materially adjacent state exposed by the repair.

After closing prior findings, perform the independent adversarial sweep over the repair blast radius and every acceptance obligation whose proof was invalidated. The final verdict remains a verdict over the **whole current candidate**, not merely over the repaired finding.

If the prior durable verifier result lacks enough authority, construction, inventory, or proof-dependency state to support safe reuse, reconstruct only the missing or ambiguous state. Do not rebuild an unchanged universe merely because a new verifier actor started, and do not pretend reuse is valid when the durable record is insufficient.

> **Verifier attempts are cumulative in evidence and adversarial knowledge, but independent in verdict. Do not rediscover the universe; re-certify the candidate.**

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

Only the fresh dispatched verifier executes the remaining ticket-candidate certification sections.

A valid verifier is:

* fresh — it did not implement the candidate or participate in parent acceptance reconciliation;
* non-mutating — it may read/search/inspect and run non-mutating checks, but may not edit repository/tracker/Git state;
* non-delegating — it may not spawn another semantic verifier;
* candidate-bound — it certifies exactly the supplied Ticket baseline, ticket contract, and candidate state.

Candidate mutation, verifier mutation/delegation, or unrecoverable authoritative state invalidates the run. Return an invalid-verification result; do not emit PASS or FAIL.

## 1. Recover the Immutable Contract

Recover the smallest authoritative context sufficient to construct and certify the complete ticket acceptance universe. Start from the dispatch/checkpoint retrieval map, but independently validate every durable source that materially contributes to the verdict.

Read:

* the full ticket body plus machine-managed or explicitly referenced ticket comments required by its current contract; do **not** ingest the complete ticket comment history by default — resolve known markers/IDs first and broaden only when needed to establish completeness, provenance, or resolve ambiguity;
* native parent and declared lineage;
* `Ticket branch`, pinned `Ticket baseline`, exact current candidate state;
* durable v2 closure checkpoint used for dispatch;
* ticket-governed durable tracker state when applicable;
* the exact parent-Spec clauses identified by the ticket's `Spec obligations`, plus any specifically referenced completion/architecture section needed to interpret them; do **not** read unrelated parent-Spec sections by default, but broaden when the carried clauses depend on a cross-cutting rule or otherwise cannot be interpreted completely in isolation;
* the current parent-Spec `Ticket Coverage Manifest`, including Architecture/Design Obligation Disposition Manifest rows, and the ticket's exact `Architecture obligations` IDs;
* current architecture/Standards/policy authority materially required by the ticket's acceptance cells or candidate;
* Proposed Closure Evidence as claims and evidence pointers to challenge, never authority.

For Attempt 2 or later, also recover the prior valid verifier result and its cumulative retry state from the checkpoint before rebuilding any authority/source, acceptance, proof-plan, or domain-construction artifact already proven reusable under **Retry attempts — cumulative knowledge, fresh verdict**.

For large paginated tracker payloads or comment histories, fetch/filter by marker, ID, section, or another deterministic selector before exposing content for semantic inspection when that bounded reduction preserves the required authority. Expand to the larger source when the bounded result cannot establish the required universe or resolve contradictory state.

Determine ticket mode: ordinary or Spec Review remediation.

For remediation also recover:

* remediation parent Spec Review;
* stable Root Blocker ID/invariant;
* cumulative carried acceptance cells;
* remediation and verification obligations;
* same-root preservation obligations;
* previously satisfied other roots whose governed contracts intersect the candidate.

Missing, ambiguous, contradictory, or stale contract/candidate state invalidates verification. Context efficiency never authorizes omitting authority required to close a material claim or domain.

### Authority Source Coverage Manifest

Before acceptance-cell construction, close the bounded **authority-source universe** that materially defines this ticket's promised slice. This prevents a verifier from proving every obligation it noticed while silently omitting an explicit requirement from an architecture/design source the ticket claims to consume.

Start from:

* the ticket's normative body and acceptance/verification/preservation obligations;
* the carried parent-Spec clauses identified by `Spec obligations`;
* the exact architecture/design sections required to interpret the ticket's promised slice, including sources named by the ticket/Spec as governing that slice.

Do not ingest unrelated sections merely because a large design document is referenced. Broaden only when a bounded section depends on another source or cannot be interpreted completely in isolation.

Classify every materially normative source unit in that bounded authority-source set:

```text
Authority unit: AUTH-<n>
Source: <durable source + section/anchor>
Requirement: <compact normative obligation>
Disposition: current-ticket | preservation | verification-only | deferred-existing-owner | not-applicable
Destination: <AC/ND ID | durable other ticket/Spec/owner | None>
Reason/authority: <required for every non-current-ticket disposition>
```

Rules:

* `current-ticket` obligations must enter the acceptance universe;
* `preservation` obligations must enter the preservation proof universe;
* `verification-only` obligations must have an explicit proof destination in this verifier;
* `deferred-existing-owner` requires durable authority naming the other owner; do not invent a future destination to make the manifest close;
* `not-applicable` requires exact authority/reason;
* a broad statement that the ticket "consumes" a design source does not permit cherry-picking only the clauses already reflected in implementation/tests;
* implementation shape, existing tests, Proposed Closure Evidence, and known findings may help locate evidence but may not define which authority units exist.

Before continuing require:

```text
Bounded authority sources: <n>
Material normative authority units: <n>
Authority disposition rows: <n>
Unmapped authority units: 0
Ambiguous authority units: 0
Current-ticket authority units absent from acceptance cells: 0
Deferred units without durable existing owner: 0
```

Any non-zero value leaves the affected ticket acceptance universe unproven and prohibits PASS.

On a retry, an unchanged, durably recoverable prior Authority Source Coverage Manifest satisfies this construction gate. Revalidate its authority identities and only reconstruct rows whose governing source changed or whose durable prior state is insufficient.

## 2. Build the Authoritative Acceptance Universe

Build the universe independently from durable authority, not from changed files, existing tests, implementation notes, Proposed Closure Evidence, or known defect patterns.

On Attempt 2 or later, “build” includes reusing the prior saturated verifier's unchanged authority-derived acceptance universe. Do not regenerate acceptance cells solely because the verifier actor is fresh; revalidate the governing authority identities and reconstruct only changed or insufficiently durable portions.

### Ordinary cells

First enumerate every authoritative obligation carried by the ticket, including:

* every explicit acceptance criterion;
* carried `Spec obligations` applicable to this ticket's promised slice;
* carried `Architecture obligations` and current-ticket authority units;
* required build/preservation/negative-path behavior stated by the ticket;
* required production/authoritative-path proof;
* verification obligations that determine semantic completion.

Then create one `AC-<n>` cell per **distinct semantic predicate**, preserving an explicit reverse mapping from every authoritative obligation to its semantic cell.

Many authoritative IDs may map to one cell only when they are materially equivalent for certification: the same semantic subject, quantifier, domain/membership boundary, predicate, material conditions/exceptions, failure meaning, temporal/order semantics, authority role, and required proof modality. This is semantic entailment, not shared wording or shared evidence.

Examples of valid many-to-one mapping include a ticket acceptance criterion that faithfully restates carried Spec/ARCHSRC obligations at the same boundary, or several provenance IDs that constrain the exact same invariant.

Do **not** merge claims that merely:

* touch the same subsystem or changed file;
* share a test or evidence source;
* overlap partially while one adds a material condition, negative rule, temporal boundary, authority distinction, or broader/narrower domain;
* would require different falsifier families or independently closable semantic domains.

Conversely, do not manufacture duplicate acceptance cells solely because the same predicate has multiple provenance IDs. Traceability is many-to-one when authority is semantically coextensive.

### Remediation extension

For remediation add to the same universe:

* every active Root Blocker remediation obligation;
* every carried root acceptance cell;
* every verification-only root obligation;
* every same-root preservation obligation;
* every independently required root sibling/alternate surface;
* every applicable protected-root preservation obligation.

There is still one `AC-*` universe and one verdict.

Before proof require exact authoritative-obligation ↔ semantic-acceptance-cell accounting:

```text
Authoritative obligations: <n>
Semantic acceptance cells: <n>
Many-to-one authority mappings: <n>
Unmapped obligations: 0
Ambiguous mappings: 0
Merged-distinct obligations: 0
Duplicate semantic cells: 0
```

If the universe cannot be closed, affected cells are `unproven`.

### Authority-first proof-plan freeze

Before inspecting candidate implementation/tests or using Proposed Closure Evidence as proof, construct the semantic proof plan for every material acceptance cell from durable authority alone. The dispatch/checkpoint retrieval map may identify where authority lives, but implementation shape, existing tests, proposed evidence, and known defect patterns may not determine what the verifier decides to test.

A retry may reuse a prior frozen proof plan when its governing authority, cell identity, membership predicate, dimensions, and material conditions remain unchanged. The prior implementation finding may guide which already-authorized falsifier to re-attack, but it may not redefine the proof plan around the repair.

Freeze this compact transition state before evidence disposition begins:

```text
Acceptance: AC-<n>
Subject: <semantic subject>
Quantifier: <one | all | none | only | complete | other exact quantifier>
Material conditions/exceptions: <authoritative conditions and exclusions>
Domain authority: <durable source(s)>
Membership predicate: <what belongs>
Dimensions / authoritative partitions: <bounded semantic dimensions>
Composition/order seams: <None | authoritative state/operation compositions to close>
Falsifier families: <boundary states that would make the claim false>
Generation / closure mechanism: <enumeration | Cartesian product | bounded exhaustive search | other independently checkable criterion>
Proof-plan state: frozen-before-evidence
```

Rules:

* derive the plan from the obligation and its governing authority before inspecting how the candidate chose to implement or test it;
* when authority makes behavior depend on state, time, lifecycle, operation ordering, concurrency, correction, retry/replay, or another composition seam, include those material compositions as dimensions rather than proving only one convenient direction;
* do not require a blind Cartesian product when a smaller authoritative partition or exhaustive mechanism closes the claim; use the smallest complete domain justified by authority;
* later implementation/evidence inspection may change member dispositions and may discover additional candidates that satisfy the already-bound membership predicate, but it may not silently shrink or redefine the proof plan to fit the candidate;
* any newly discovered in-domain candidate must be added and dispositioned in the same run; ambiguous membership remains `unproven` under the normal domain rules;
* a material cell may not leave `unchecked` until its authority-first proof plan is frozen.

This gate is the local enforcement of Transition-Bound Reasoning and Universe Closure. It prevents implementation-shaped verification while preserving lean, authority-bounded discovery.

### Authoritative domain membership

Before proving any material cell whose domain can produce finite, discoverable, alternate, sibling, or adversarial candidates, bind the boundary that determines which candidates belong to that domain:

```text
Domain authority: <durable source(s) that define the boundary>
Membership predicate: <what makes a candidate a member of this domain>
```

Derive the membership predicate from durable authority, including explicit enumerations, normative definitions, and authoritative composition or ownership boundaries. Do not derive it from changed files, implementation structure, existing tests, known defects, lexical similarity, subsystem proximity, or verifier intuition.

Discovery may reveal a candidate. Discovery does not create authority.

For every finite or discoverable domain, bind a **Domain Construction Manifest** before disposition begins:

```text
Domain: ND-<n>
Parent: <AC-n | ND-n>
Authority: <durable source(s)>
Membership predicate: <predicate>
Dimensions / authoritative source sets: <explicit sets or bounded sources>
Generation mechanism: <enumeration | Cartesian product | bounded exhaustive search>
Expected members: <n | open-world closure criterion>
Generated members: <n>
```

For finite domains, `Generated members` must equal the independently recoverable `Expected members` before the domain can be closed. For discoverable/open-world domains, the generation mechanism must establish the stated closure criterion. A later finding may change member dispositions; it may not retroactively shrink the construction manifest.

On a retry, reuse an unchanged prior Domain Construction Manifest and its member inventory/closure criterion rather than regenerating it. Reconstruct only when governing authority, membership predicate, source set, or generation mechanism changed, or when the prior durable record is insufficient to recover the exact domain.

If the authoritative domain is semantically open-world rather than finitely enumerable, define the inclusion rule and the exhaustive/discovery mechanism that can establish closure to the practical boundary required by the claim. If membership of a material candidate cannot be resolved from current authority, the candidate is `ambiguous` and the affected cell/domain remains `unproven`; do not silently widen or narrow the authoritative claim.

## 3. Per-Cell Proof Contract

Every material cell binds compact certification state:

```text
Acceptance: AC-<n>
Source: <exact ticket / Spec / root obligation>
Claim: <exact semantic claim>
Subject / quantifier / material conditions: <authority-derived proof-plan identity>
Domain: <authoritative domain>
Domain authority: <durable source(s) defining membership>
Membership predicate: <what makes a candidate part of this domain>
Dimensions / authoritative partitions: <bounded semantic dimensions>
Composition/order seams: <None | required seams>
Nested domains: <None | ND manifests>
Predicate: <what must be true>
Falsifier families: <concrete states making the claim false>
Evidence: <current evidence excluding the falsifier families>
Proof-plan state: frozen-before-evidence
State: <unchecked | proven | violated | unproven>
```

This is proof state, not a private reasoning transcript.

### Evidence entailment

A cell is `proven` only when evidence establishes **that exact predicate** across its exact domain.

Shared evidence may support several cells, but every cell retains its own entailment decision. A broad upstream architectural fact cannot silently certify a narrower externally visible or operational claim.

Ask:

> Could every cited check pass while this exact claim is still false?

If yes, it is not proven.

On Attempt 2 or later, a prior `proven` cell/member disposition may remain proven without re-execution only when the retry invalidation rule establishes that its authority, candidate-dependent evidence inputs, implementation surface, and relevant dependencies are unchanged. Preserve the reuse decision explicitly; “passed last attempt” alone is insufficient.

### Nested Universe Closure

For `all`, `every`, `none`, `only`, `complete`, `highest practical`, all supported profiles, all response paths, all consumers, or equivalent finite/discoverable domains, materialize and completely disposition the nested domain.

Examples include:

* profile × applicable presentation seam;
* contract transition × affected consumer;
* response contract × constructor/adapter/mapper/schema/transport path;
* workflow transition × entry/re-entry/fallback path;
* operational owner × production composition path.

Each nested domain carries its own durable authority, membership predicate, and Domain Construction Manifest. Track construction separately from disposition:

```text
Domain: ND-<n>
Expected / closure criterion: <n | criterion>
Generated: <n>
Inspected: <n>
Dispositioned: <n>
Remaining generated members: 0
Construction complete: yes
Sweep complete: yes
```

`unchecked = 0` over an incompletely constructed domain is not proof. A parent cell becoming `violated` does **not** close, waive, or disposition the rest of its nested domain. Continue generating, inspecting, and dispositioning every remaining authoritative member so the same run accumulates all independently observable failures.

Familiar-symbol searches and passing tests are supporting evidence unless they are an independently checkable exhaustive mechanism for the authoritative domain.

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

* `$verify-code` owns targeted code checks and constructs Contract Transition / Consumer Closure manifests as supporting technical evidence; when those manifests report `prepared for ticket certification`, independently certify their semantic universe completeness here rather than requiring another verifier;
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

Finding one falsifier establishes that PASS is impossible for the current candidate, but it does not complete verification. Latch verdict polarity to FAIL and continue the same bounded generation and disposition procedure for every remaining acceptance cell, nested-domain member, sibling, alternate, composition/order seam, and adversarial candidate already authorized by the proof plans/domain manifests. Do not narrow the remaining sweep to the first defect or its implementation mechanism.

For remediation this is the Root Invariant Sweep and also re-proves applicable carried same-root cells/protected roots against current authority. Historical PASS/satisfied/unchanged state is evidence history, not current proof of member disposition; **the certified membership boundary itself remains authoritative under the finality rules above until its governing authority changes or an explicit closure-authority defect is reconciled.**

Do not broaden into unrelated review.

For Attempt 2 or later, the independent sweep starts from the prior saturated universe plus the current invalidation map. Explicitly re-attack every prior falsifier, sweep the repair blast radius for regressions/new bypasses, and revisit every previously dispositioned candidate whose proof dependencies changed. Unaffected, safely reusable prior dispositions need not be rediscovered solely to demonstrate freshness.

## 6. Completeness and Failure Saturation

After verifier integrity is established, do not fail fast on implementation/proof defects. Record each and complete the bounded universe so one run returns all independently observable closure failures.

A first falsifier changes **verdict polarity** to FAIL; it does not establish **verification completion**. PASS and FAIL therefore require the same authority-first proof-plan, universe-construction, composition, and sweep-saturation gates. A violated parent cell remains open for search until every authoritative nested member, sibling, and required composition/order seam has been generated and dispositioned.

Before either verdict require:

```text
Acceptance coverage: <n> cells
proven: <n>
violated: <n>
unproven: <n>
unchecked: 0
Material acceptance proof plans required: <n>
Authority-first proof plans frozen: <n>/<n>
Proof plans frozen after implementation/evidence inspection: 0
Required composition/order seams: <n>
Dispositioned composition/order seams: <n>
Remaining composition/order seams: 0
Nested domains required: <n>
Domain construction manifests complete: <n>/<n>
Nested domains closed: <n>
Open nested-domain candidates: 0
Generated authoritative members: <n>
Inspected authoritative members: <n>
Dispositioned authoritative members: <n>
Remaining authoritative members: 0
Violated cells with incomplete domain sweep: 0
Domain-membership candidates: <n>
in-domain: <n>
out-of-domain: <n>
ambiguous membership: 0
Undispositioned domain candidates: 0
Independent actionable findings: <n>
Unexplored authoritative siblings: 0
Unproven material assumptions: 0
Material closure domains required: <n>
Certified closure-domain records: <n>
Missing domain records: 0
Unresolved domain identities: 0
```

For Attempt 2 or later, additionally track:

```text
Prior-attempt findings: <n>
closed: <n>
still-open: <n>
superseded-by-explicit-authority-change: <n>
Reused prior dispositions with unresolved invalidation: 0
```

A PASS requires `still-open: 0`. A FAIL may retain prior findings as still-open, but must carry them forward together with every new independently actionable finding.

For a finite domain, generated/inspected/dispositioned counts must reconcile to the authoritative expected member count. For a discoverable/open-world domain, the declared exhaustive mechanism must satisfy its closure criterion before either PASS or FAIL is legal.

Every independently actionable defect discovered during the saturated sweep must appear as a finding even when several findings violate the same acceptance cell. Derivative acceptance failures may reference the same root defect rather than duplicating it, but they do not replace independently actionable findings.

Any missing/late proof plan, undispositioned required composition/order seam, violated/unproven/unchecked cell, incomplete domain construction, incomplete nested sweep, ambiguous/undispositioned domain candidate, unexplored authoritative sibling, unproven material assumption, missing required Certified Closure Domain record, or unresolved domain identity blocks PASS. Any incomplete authority-first proof planning, construction, composition, or sweep also blocks FAIL; return an invalid/incomplete verification result rather than a partial failure set.

## 7. Verdict

Return exactly one semantic verdict for the immutable candidate only after Section 6 saturation is complete.

### PASS

```text
TICKET CLOSURE: PASS
Ticket: #<n>
Mode: ordinary | remediation
Ticket baseline: <sha>
Candidate state: <hash>
Ticket contract identity: <durable identity>
Authority mapping: obligations <n>; semantic cells <n>; many-to-one <n>; unmapped 0; merged-distinct 0; duplicate cells 0
Acceptance: <n>; proven <n>; violated 0; unproven 0; unchecked 0
Proof plans: <n>/<n> authority-first; remaining composition/order seams 0
Nested domains: <n>; closed <n>; open 0
Domain construction: <n>/<n> complete; remaining authoritative members 0
Domain membership: <n>; in-domain <n>; out-of-domain <n>; ambiguous 0
Certified closure domains: <n>; frozen <n>; unresolved 0
Prior-attempt findings: <n>; closed <n>; still-open 0; superseded-by-explicit-authority-change <n>
Reused semantic state: <None | compact AC/ND/member summary>
Re-proven invalidated state: <compact AC/ND/member summary>
Production-path obligations: <summary>
Negative/fail-closed obligations: <summary>
Remediation root: <None | RB-n — invariant>
Protected roots: <None | concise dispositions>
Evidence: <compact per-cell/current evidence summary>

<!-- certified-closure-domain:v1 -->
Certified Closure Domains:
- <complete records required by Certified Semantic Domain Finality>
```

### FAIL

```text
TICKET CLOSURE: FAIL
Ticket: #<n>
Mode: ordinary | remediation
Ticket baseline: <sha>
Candidate state: <hash>
Authority mapping: obligations <n>; semantic cells <n>; many-to-one <n>; unmapped 0; merged-distinct 0; duplicate cells 0
Acceptance: <n>; proven <n>; violated <n>; unproven <n>; unchecked 0
Proof plans: <n>/<n> authority-first; remaining composition/order seams 0
Nested domains: <n>; closed <n>; open <n>
Domain construction: <n>/<n> complete; remaining authoritative members 0
Domain membership: <n>; in-domain <n>; out-of-domain <n>; ambiguous <n>
Failure saturation: complete; independent actionable findings <n>; unexplored authoritative siblings 0
Prior-attempt findings: <n>; closed <n>; still-open <n>; superseded-by-explicit-authority-change <n>

Cumulative Retry State:
Authority identity: <durable authority/source identities proving the universe boundary>
Acceptance/proof-plan identity: <stable AC IDs plus source/claim/proof-plan identities sufficient for reuse>
Domain construction state: <stable ND IDs plus authority, membership predicate, generation/closure mechanism, and recoverable member inventory/criterion>
Candidate-dependent proof dependencies: <AC/ND/member groups -> implementation/evidence/runtime/tracker/configuration dependencies>
Reusable prior dispositions: <AC/ND/member groups whose dependencies remain unchanged>
Mandatory falsifiers for next attempt: <finding IDs / exact falsifiers>

Findings:
1. <AC-n / source / falsifier or missing proof / concrete evidence / required correction>
...
Remediation root: <None | RB-n — invariant>
Protected-root regressions: <None | findings>
```

On every valid saturated FAIL that can lead to another implementation attempt, `Cumulative Retry State` is mandatory. It must preserve enough compact durable state for a fresh later verifier to reuse the unchanged authority-derived universe and determine semantic invalidation without relying on conversational memory. Counts alone are insufficient. When reuse depends on a finite member inventory, preserve that inventory itself or an independently recoverable deterministic identity/manifest for it.

Do not repair. Return the complete saturated verdict to `$implement-ticket`.

## 8. Candidate Binding

PASS authorizes only the exact candidate state, baseline, ticket contract, lineage, remediation/root state, and Certified Closure Domain membership interpretations certified.

Any substantive repository/tracker mutation after PASS makes member dispositions stale unless an independently certified invalidation boundary plus deterministic fail-closed delta analysis proves the exact proof remains valid. `$implement-ticket` does not make that semantic judgment itself.

A repository mutation alone does not silently change frozen domain membership. Membership becomes stale only when its recorded governing authority changes or an explicit closure-authority defect is reconciled.

When uncertain about candidate proof, recertify. When uncertain about frozen domain membership, do not silently broaden it.