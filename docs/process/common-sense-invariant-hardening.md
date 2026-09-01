# Common-Sense Invariant Hardening Audit

**Status:** Active hardening record  
**Audit date:** 2026-08-29

## Purpose

Polaris agent skills contain many rules that are correct in prose but are still vulnerable to a common execution failure:

> A prose reasoning invariant without an enforceable state transition can be acknowledged, nodded at, and bypassed.

This document preserves the cross-skill audit that identified that failure mode, the reasoning behind it, the affected skills, the counterexamples that already avoid it, and the hardening sequence.

This document is a process design record and hardening backlog. It is **not** an executable substitute for any individual `SKILL.md`. Each skill remains authoritative for its own procedure. Hardening is complete only when the transition-owning skill makes the relevant invariant part of its enforceable state.

## Core Problem

A workflow rule can sound strict and still be operationally weak.

Examples:

* "check every consumer";
* "confirm architecture is complete";
* "ensure every requirement is covered";
* "seek counterexamples";
* "use the narrowest authoritative dependency";
* "the route is clear";
* "no durable wiki knowledge changed".

If the workflow can still emit `PASS`, `proven`, `checked-no-finding`, publish tickets, consume a decision, mutate a native dependency, close an artifact, or advance lifecycle state without recording and validating the reasoning result that authorizes that transition, the rule is advisory in practice even when its prose says `must`.

The audit therefore used this test:

> **Could the agent produce every artifact currently required by the skill and take the authorized transition while the stated reasoning invariant was actually false?**

If yes, the invariant is bypassable.

## Five Failure Modes

### 1. Unbound Reasoning

The skill says to determine, confirm, reason about, or ensure a condition, but the result is not required state consumed by the transition.

Example shape:

```text
reason about X
    ↓
"looks good"
    ↓
PASS / publish / mutate / close
```

The prose may be excellent. The state machine does not care whether it happened.

### 2. Incomplete Universe

The skill has good accounting over the items it discovered, but the authoritative candidate universe was never completely materialized.

Example:

```text
Discovered obligations: 31
Mapped obligations:     31
Unmapped:                 0
```

This does not prove completeness if the source actually contained 34 obligations and three never entered the discovered set.

The important rule is:

> `unchecked = 0` proves only that the constructed universe was dispositioned. It does not prove the universe itself was complete.

### 3. Escape by Omission

A candidate can disappear instead of receiving an explicit disposition.

Common escape meanings include:

* not applicable;
* inherited;
* already covered;
* duplicate;
* no implementation work;
* verification-only;
* scope-retired;
* existing authority already covers it;
* no durable knowledge change.

When those states are valid, they should be explicit. Omission must not be a hidden state transition.

### 4. Self-Certifying Semantic State

The first transition-bound hardening pass exposed a deeper loophole: explicit state is not automatically enforceable when the same semantic actor creates the state, interprets it, and certifies that it is complete.

Observed failure shape:

```text
parent creates proof fields
    ↓
parent declares falsifier excluded
    ↓
parent declares incomplete proof records = 0
    ↓
deterministic validator checks only that those declarations exist
    ↓
PASS
```

A state machine can therefore reproduce prose-only bypass under more formal names. Aggregate declarations such as `survivability excluded`, `route clear`, `architecture resolved`, or `unclassified = 0` are not independently checkable merely because they are fields.

The stronger test is:

> **Can a different actor or deterministic mechanism verify the semantic authorization from the persisted/inspectable witness without trusting the actor that wants the transition?**

If no, the transition may still be self-certifying.

### 5. Nested Universe Omission

Closing the outer workflow universe is not enough when one outer claim itself quantifies over another domain.

Example shape:

```text
Outer Spec universe: 86/86 cells accounted for

US-X:
  "all affected substitutes conform to their contracts"

Inner universe:
  which affected substitutes?
```

If the inner domain is never materialized, the verifier can prove the outer cell with evidence about a convenient subset while reporting perfect outer coverage.

The generic rule is:

> Exhaustive predicates require closure of the domain they quantify over, recursively when necessary.

The nested domain may be proven by explicit enumeration or by an equivalent independently checkable exhaustive mechanism. A known-pattern search is not domain closure unless the authoritative predicate is itself defined by that pattern.

## Cross-Skill Hardening Principles

### Transition-Bound Reasoning

> **Any normative reasoning result that can authorize or suppress a lifecycle transition, mutation, closure, PASS, `proven` disposition, inheritance, scope retirement, skip/not-applicable decision, or routing choice must be represented by explicit state that the transition consumes. Prose acknowledgment is not transition evidence.**

The state does not need to preserve private chain-of-thought. It needs only enough concise, inspectable state to establish what was decided and why that transition is legal.

Typical forms include:

```text
Claim / obligation
Domain
Falsification condition
Evidence
Disposition
```

or:

```text
Candidate
Classification
Authority / reason
Destination
```

### Universe Closure

> **When a claim or transition depends on `all`, `every`, `complete`, `no`, `zero`, or equivalent exhaustive reasoning, the authoritative candidate universe must itself be materialized and completely dispositioned. `unchecked = 0` over an incompletely constructed universe is not proof of completeness.**

A strong finite-universe workflow normally has two distinct gates:

```text
Universe construction complete?
            ↓
Every universe cell dispositioned?
```

These are not the same question.

### Explicit Escape Disposition

> **`not-applicable`, inherited, already-covered, duplicate, no-work, verification-only, scope-retired, existing-authority-covered, and similar escape states must be explicit dispositions with supporting authority or evidence. They may not be represented by omission.**

### No Self-Certifying Semantic Transition

> **A consequential semantic transition may not be authorized solely by semantic state whose correctness is asserted by the same actor that created it. The transition requires an independently checkable witness: deterministic validation when the predicate is mechanically decidable, or genuinely fresh semantic certification when judgment remains.**

Deterministic validation is appropriate for facts such as exact IDs, hashes, counts, branch ancestry, schema membership, and command results.

Fresh semantic certification is required when transition authority depends on judgments such as evidence entailment, completeness of a semantic domain, architecture sufficiency, requirement coverage, or whether a counterexample survives and those judgments cannot be mechanically recomputed from authoritative state.

The fresh certifier does not need private reasoning transcripts. It needs the authoritative claim, bounded proof object, current evidence references, and enough inspectable state to challenge the transition.

A same-agent or owner override must not be offered when it would recreate the exact self-certifying semantic transition the gate exists to prevent.

### Nested Universe Closure
> **When an obligation inside an already-complete outer universe quantifies over its own finite or discoverable domain, that nested domain must itself be materialized and completely dispositioned, or replaced by an independently checkable exhaustive mechanism whose semantics cover the full authoritative boundary.**

This rule is recursive. `Outer coverage = 100%` does not establish a universal inner predicate if the inner candidates were never enumerated.

Unknown-unknowns cannot be eliminated, but known/discoverable members must not disappear before counting begins.

### Certified Invalidation Boundaries

Independent semantic certification does not require blanket re-execution after every unrelated mutation. A fresh certifier may approve not only a proof result but also a bounded **Invalidation Boundary** and evidence-stability classification for that Proof Object.

> **A previously certified semantic proof may survive a later repository mutation only when deterministic delta analysis proves that the exact Proof Object is unchanged, its evidence is repository-immutable, proof policy remains compatible, and the complete changed-surface set has zero intersection with its certifier-approved invalidation boundary. Any uncertainty makes the proof stale.**

This preserves **No Self-Certifying Semantic Transition**: the parent does not decide semantic sufficiency after the fact. The independent certifier established the proof and the boundary; the parent may only apply deterministic invalidation mechanics to decide whether that existing certification still applies.

### Semantic-First Cost Control

Correctness gates should be ordered to avoid paying repeatedly for expensive whole-system checks during semantic discovery.

> **Run the minimum direct evidence needed to construct and independently certify semantic proof first. Defer broad final gates until semantic proof converges, then run them once at the stable candidate HEAD. If a later repair mutates state, rerun only affected gates and recertify only Proof Objects made stale by fail-closed invalidation analysis.**

This is an execution-efficiency rule, not a waiver. Every required final gate and every semantic proof must still be valid at the exact final state.

### Local Enforcement

Do not solve this by creating a universal helper that every skill merely says it invoked.

A shared principle is useful, but enforcement belongs at the transition owner. The local state schema should make it impossible to legally cross the transition without the required disposition.

Otherwise a hypothetical `$reasoning-integrity` helper could itself become another prose checkbox.

### Preserve Lean Workflows

Not every heuristic or design preference needs a state machine.

Hardening is warranted when the reasoning result controls a consequential transition. Advisory design guidance may remain prose when it does not independently authorize lifecycle state, mutation, closure, or proof.

The goal is not maximum bureaucracy. The goal is the **minimum explicit state needed to prevent silent bypass**.

## Audit Results

### `$spec-contract` — Critical

Strengths:

* stable source-derived obligation IDs;
* independent source counts;
* explicit mapping requirements;
* `Unmapped source items: 0`;
* `Duplicate source mappings: 0`;
* `Ambiguous source items: 0`;
* deterministic contract hash.

Gap:

The finite numbered sections are well bounded, but discovery of "other materially unique normative clauses" remains semantic. The skill can notice three such clauses, map all three, and report zero unmapped items even when a fourth clause never entered the source-item universe.

This is the deepest upstream form of the problem because `$verify-spec` and `$review-spec` trust this contract as their Spec obligation universe.

Required hardening direction:

* materialize a complete source-unit classification before manifest construction;
* every candidate source unit must become normative, non-normative, or an explicit duplicate/reference to an already represented obligation;
* require zero unclassified source units;
* only then allow `SPEC CONTRACT: VALID`.

### `$implement-ticket` — High

Strengths:

* durable ticket baseline;
* branch/hierarchy/project-delivery guards;
* explicit invocation terminal states;
* durable root-verification checkpoint;
* Claim-Proof Integrity language;
* applicability-driven change-surface classification.

Gaps:

1. Ordinary acceptance-criterion Claim-Proof Integrity is still reasoning prose unless the criterion's falsifier/evidence/disposition becomes required proof state before marking it `proven`.
2. Helper/check applicability can be declared `not-applicable` without a normalized universe proving all required disciplines were considered from the actual change surfaces.
3. Architecture-versus-implementation routing is consequential: a mistaken "architecture already resolves this" or "architecture blocker" changes lifecycle routing without a compact required routing record.

Required hardening direction:

* bind acceptance-criterion proof to explicit claim/falsifier/evidence state;
* make applicability decisions explicit rather than omission-based;
* bind architecture-routing outcomes to the exact missing or already-resolved durable semantic.

### `$verify-root-closure` — Critical

Strengths:

* independent non-mutating verifier;
* durable verifier integrity requirements;
* Root Closure Coverage Manifest;
* explicit RC states `unchecked | proven | violated | unproven`;
* carried acceptance and preservation cells;
* invariant-sweep cells;
* protected-root handling;
* completeness gate with `unchecked = 0`;
* Claim-Proof Integrity language.

Gap:

Claim-Proof Integrity is not part of the RC cell state. A verifier can acknowledge the instruction to derive subject/quantifier/domain/predicate/falsifier and still mark `State: proven` from familiar evidence without preserving enough state to prove that evidence excludes the falsification condition.

This is structurally the same problem as a verification skill saying "seek counterexamples" while allowing `PASS` to be emitted from a coverage row containing only obligation, surfaces, state, and evidence.

Required hardening direction:

* require each material RC cell to bind its proof predicate/falsifier and evidence-sufficiency result before `proven` is legal;
* preserve concise traceability, not private reasoning transcripts.

### `$review-spec` — High

Strengths:

* deterministic Spec Contract dependency;
* separate Standards, Spec, and Architecture universes;
* genuinely fresh reviewer execution by default;
* explicit owner override when fresh contexts are unavailable;
* per-cell dispositions;
* reviewer Claim-Proof Integrity.

Gap:

Independent reviewers reduce correlated errors but do not mechanically enforce sound reasoning. Each reviewer can still individually nod at Claim-Proof Integrity. A `checked-no-finding` disposition does not currently require compact state proving the falsification condition was excluded.

There are two separate gates:

```text
review universe complete?
        ↓
cell proof sound?
```

Fresh contexts help the second, but do not eliminate either problem.

Required hardening direction:

* bind clean per-cell dispositions to falsifier/evidence-sufficiency state;
* preserve the existing universe-completeness mechanics;
* do not confuse reviewer independence with proof completeness.

### `$review-architecture` — High

Strengths:

* coverage-driven review;
* explicit `ARCH-*` cells;
* every supplied cell must end in one state;
* `not-applicable` requires a reason;
* authority-first and adversarial-surface-first strategies;
* required evidence for every coverage cell.

Gaps:

1. Architecture universe construction itself remains partly open-world: "every affected entity", "every governing authority", "relevant sibling or alternate paths", and applicable dimensions require semantic discovery.
2. `checked-no-finding` does not mechanically require the falsifier/survivability reasoning that establishes the clean state.

Required hardening direction:

* explicitly close architecture-universe construction from bounded authoritative sources;
* bind `checked-no-finding` to evidence sufficient to exclude the relevant architectural falsifier.

### `$verify-code` — Critical for Shared-Contract Changes

Strengths:

* targeted verification;
* explicit Contract-Impact Closure concept;
* requirement to search callers, implementations, protocols, adapters, fakes, fixtures, configuration, bootstrap, and other consumers;
* requirement for zero unexplained superseded consumers.

Gap:

The final state is only:

```text
Contract-impact closure: passed | not applicable
```

There is no consumer-closure manifest. An agent can run a few familiar searches, find nothing, and declare `passed` while a stale explicit or indirect consumer remains.

This is the same class of failure that allowed stale fake/fixture contract sinks to survive earlier work.

Required hardening direction:

```text
Authoritative contract
Superseded contract/falsifier
Consumer universe
- consumer A -> conforming
- consumer B -> migrated
- consumer C -> explicitly authorized compatibility
Unexplained consumers: 0
Survivability: excluded
```

The rule must remain generic and must not encode one historical fake/fixture pattern.
### `$to-tickets` — High

Strengths:

* explicit fresh-vs-remediation modes;
* publication-ready remediation proposal;
* user approval before semantic publication;
* branch guard;
* native hierarchy/dependency mechanics;
* strong requirement not to silently omit remediation obligations.

Gap:

Fresh Spec decomposition lacks an authoritative Spec-obligation -> ticket-coverage artifact. A set of well-formed tracer-bullet tickets can cover every obligation the agent noticed while silently losing obligations that never entered ticket planning.

Required hardening direction:

For Spec sources, use the Spec Contract Manifest as the candidate universe and require each obligation to be explicitly dispositioned to:

* one or more implementation tickets;
* verification-only responsibility;
* intentionally no implementation work, with reason;
* explicit authoritative exclusion/out-of-scope treatment.

Require zero unmapped/ambiguous obligations before publication.

### `$to-remediation-tickets` — High

Strengths:

* Root Blocker Ledger and cumulative acceptance matrix are durable finite inputs;
* explicit partition into remediation, verification, and preservation obligations;
* root-complete ticketing model;
* no reopening/rewrite of closed tickets;
* architecture-blocked roots are separated from ordinary remediation.

Gap:

The skill has a finite source universe available but does not require an exact root-cell -> delta disposition table before returning the delta. The prose says every active cell must be carried correctly, but completeness can still depend on successful human-like enumeration.

Required hardening direction:

* materialize every current active root cell exactly once in the delta reconciliation;
* disposition each as remediation, verification, preservation, overridden/retired, or otherwise non-actionable by explicit durable authority;
* require zero undispositioned cells before returning a complete delta.

### `$to-specs` — High

Strengths:

* decision-first planning;
* architecture preflight;
* current Spec handoff reconciliation;
* native Spec dependencies;
* actionable frontier derivation;
* no placeholder Spec for unresolved architecture.

Gaps:

1. "publish the complete currently specifiable set" is a consequential completeness claim without a planning-source -> Spec partition manifest.
2. "architecture impact is understood" and "no material architecture question remains" can authorize publication without a compact transition-bound implementability record.

Required hardening direction:

* partition the planning source into explicit disposition units before declaring the currently specifiable set complete;
* every unit must map to a Spec, unresolved architecture/fog, explicit out-of-scope state, or already represented obligation;
* bind architecture preflight to the exact durable semantics required for each materially architecture-dependent Spec obligation.

### `$to-remediation-specs` — High

Strengths:

* explicit decision provenance;
* per-Spec/per-Wayfinder decision delta;
* in-place amendment;
* architecture completeness preflight;
* provenance markers record consumed decisions.

Gap:

A resolved Wayfinder decision can be marked consumed after only partial semantic incorporation. Once the provenance marker says the decision was consumed, future sessions correctly exclude it from the delta, turning an incomplete interpretation into durable workflow truth.

Required hardening direction:

Before a decision enters consumed provenance, require an explicit per-decision disposition:

```text
Decision
Affected obligations/sections
Architecture implementability
Semantic representation: complete | incomplete
Consumption authorized: yes | no
```

Only `complete` may advance provenance.

### `$architecture-remediation` — High

Strengths:

* routes into the existing governing Wayfinder;
* preserves provenance;
* reopens closed governing maps when required;
* avoids inventing resolutions;
* de-duplicates blockers by independent architectural decision.

Gaps:

Two important questions are prose gates:

* whether multiple blocker questions are one coupled decision or independent;
* whether current authority already resolves the exact blocker sufficiently to avoid creating decision work.

A mistaken "existing authority covers it" can suppress a required architecture decision entirely.

Required hardening direction:

* explicit blocker -> decision-coupling disposition;
* explicit blocker -> authority-coverage disposition showing the exact durable choice already determined or the exact unresolved semantic;
* unresolved blockers must not disappear by grouping or topic overlap.

### `$project-delivery-management` — High for Semantic Dependency Mutation

Strengths:

* durable focus singleton;
* exact human-owned focus mutations;
* complete native cycle guard;
* deterministic mutation and reread mechanics;
* explicit cross-Wayfinder ownership;
* whole-map dependency restriction.

Gap:

The mechanics are stronger than the semantic authorization. Before `dependency ensure`, the skill asks whether blocker completion fully satisfies the prerequisite and whether a narrower authoritative boundary exists. Those answers authorize a durable native dependency mutation but are not themselves represented by required semantic-placement state.

Required hardening direction:

Before mutation, bind:

```text
Prerequisite
Consumer boundary
Blocker completion boundary
Why blocker completion fully satisfies prerequisite
Narrower candidate boundaries considered/dispositioned
Placement: valid | ambiguous
```

Mechanical mutation should remain unchanged.

### `$wayfinder` — Medium-High

Strengths:

* explicit decision tickets;
* durable Decision Analysis;
* exact human yes/no acceptance for HITL decisions;
* unresolved fog represented under `Not yet specified`;
* repository persistence before resolution;
* post-resolution gate;
* project projection after durable state.

Gap:

The transition to `Ready to Spec` ultimately depends on the open-world conclusion that the route is clear and implementation can proceed without inventing another durable architectural choice.

Required hardening direction:

A concise Route Clarity state should prove at least:

```text
Open decisions: 0
Unresolved in-scope fog: 0
Unresolved implementability obligations: 0
Unreconciled authority conflicts: 0
Unpersisted architecture state: 0
```

This cannot eliminate unknown unknowns, but it prevents known-yet-unaccounted work from disappearing.

### `$wiki-lint` — High

Strengths:

* ordered eight-category audit;
* explicit finding taxonomy;
* claim-specific authority rules;
* strong conflict/drift distinctions;
* constrained mechanical-fix policy.

Gap:

`Wiki lint: 0 issues found` can be emitted without an audit-coverage artifact proving the repository-wide candidate universes were actually exhausted.

Potential missing universes include:

* registered entities;
* entity pages;
* citations;
* authoritative claims;
* Planned entries;
* Open Questions;
* project-owned documents;
* cross-entity comparison candidates.

Required hardening direction:

* build bounded audit inventories from authoritative registries/files before clean completion;
* require explicit per-category coverage totals and zero undispositioned candidates;
* a zero finding count must not mean only "zero among things noticed".

### `$wiki-sync` — Medium-High

Strengths:

* intentionally bounded per-change synchronization;
* good source authority model;
* pre/post change routing;
* explicit durable-knowledge threshold;
* no mutation when durable knowledge did not change.

Gap:

"No durable knowledge changed" may be caused by under-routing the affected entity/claim set. Context economy is correct, but it creates an omission risk if no explicit affected-knowledge routing state exists.

Required hardening direction:

* derive the affected authoritative surfaces first;
* explicitly map them to affected entity claims or an evidence-backed no-entity/no-durable-knowledge disposition;
* only then allow "no entity update required".

### `$database-migrations` — Medium

Strengths:

* executable Alembic lifecycle;
* explicit pre/post-1.0 policy;
* concrete environment rules;
* round-trip verification;
* unresolved tests do not become passes;
* strong destructive-reset boundary.

Remaining semantic risk:

* authoritative model/schema comparison is still a human-style audit rather than a manifest;
* classification of an environment as clearly disposable development/test is consequential and partly semantic.

Hardening should be selective. The skill already has many strong executable checks; do not add bureaucracy unless a concrete omission failure appears or a transition needs stronger state.

### `$spec-merge-cleanup` — Low-Medium

Strengths:

* exact durable Exit Receipt;
* reviewed HEAD binding;
* strict pre/post-completion phase detection;
* PR/merge-state verification;
* branch drift protection;
* explicit completion contradictions.

Remaining semantic risk:

Wayfinder completion reconciliation still includes reasoning about unresolved decision/fog and governed-Spec completeness, though most of that state is already durable and enumerable.

This is not an early hardening priority.

### `$project-tracking` — Low / Positive Example

This skill is a useful model for transition-bound invariants.

It has:

* explicit projection inputs;
* compatibility tables;
* invalid combinations that fail closed;
* one deterministic execution path;
* schema/current-row reads;
* computed deltas;
* post-mutation verification.

The transition cannot simply claim that a projection is valid without satisfying the state table.

### `$github-issue-dependencies` — Low / Positive Example

This helper cleanly separates:

```text
semantic owner decides the relationship
        ↓
mechanical helper mutates one exact relationship
        ↓
caller rereads exact postcondition
```

A zero process exit code is explicitly insufficient proof.

This is a good model for keeping semantic and mechanical authority separate while making the mechanical transition enforceable.

### `$diagnosing-bugs` — Low / Positive Example

Phase 1 does not merely say "build a good repro". It requires a concrete already-executed command that is:

* red-capable for the exact symptom;
* deterministic;
* fast;
* agent-runnable.

No qualifying red-capable command means no Phase 2.

This is a strong example of converting common-sense advice into a transition gate without over-engineering the workflow.

### `$coding-standards` and `$codebase-design` — Policy/Heuristic Sources, Not Defects

These skills intentionally contain design and coding heuristics. They should not independently become heavy lifecycle state machines.

The appropriate enforcement point is the lifecycle owner that uses a rule to authorize proof, mutation, or closure.

For example, `$coding-standards` may define Authoritative Contract Changes and Compatibility, while `$verify-code` owns the consumer-closure proof needed to say the changed contract is verified.

### `$tdd` and `$deduplicate-code` — Low-Medium

These are methodology/helper skills rather than major lifecycle owners. Some prose rules can still be nodded at, but they do not by themselves normally authorize Spec/ticket completion or project-state transitions.

Harden only where a parent lifecycle depends on one of their conclusions as a correctness gate.

## Structural Insight

The audit exposes a recurring architecture pattern:

```text
Semantic authorization                 Mechanical transition
----------------------                 ---------------------
"is this complete?"             ->     emit PASS
"does authority cover this?"    ->     suppress architecture ticket
"is this the right dependency?" ->     add native blocked-by edge
"is the route clear?"           ->     Ready to Spec
"is this requirement covered?"  ->     publish tickets
```

Polaris has already hardened many mechanical transitions. The next maturity step is to bind the semantic authorization immediately upstream of those transitions.

The goal is not to eliminate reasoning. It is to make the **result of consequential reasoning inspectable, independently checkable where semantic judgment remains, and consumable by the state transition**.

## Preferred Generic State Shapes

Use the smallest shape appropriate to the local problem.

### Proof Cell

```text
Cell
Authoritative claim
Domain / material conditions
Falsification condition
Evidence
Disposition: proven | violated | unproven | not-applicable
```

### Coverage / Decomposition Cell

```text
Source item
Classification
Mapped destination(s)
Reason / authority for non-work disposition
State: mapped | duplicate | verification-only | excluded | ambiguous
```

### Semantic Mutation Authorization

```text
Requested transition/mutation
Authoritative semantic predicate
Candidate alternatives/boundaries
Disposition
Evidence / authority
Mutation authorized: yes | no
```

### Universe Gate

```text
Universe source
Candidate count
Classified/dispositioned count
Unclassified: 0
Ambiguous: 0
```

These are patterns, not a requirement to force identical schemas into every skill.

## Hardening Sequence

Prioritize upstream leverage and places where a mistaken reasoning conclusion becomes durable workflow truth.

1. **Acceptance/universe foundation**
   * `$spec-contract`
2. **Proof gates**
   * `$implement-ticket`
   * `$verify-root-closure`
   * `$review-spec`
   * `$review-architecture`
   * `$verify-code`
3. **Decomposition propagation**
   * `$to-tickets`
   * `$to-remediation-tickets`
   * `$to-specs`
   * `$to-remediation-specs`
4. **Semantic mutation/routing gates**
   * `$architecture-remediation`
   * cross-Wayfinder dependency placement in `$project-delivery-management`
5. **Completeness/audit gates**
   * `$wayfinder`
   * `$wiki-lint`
   * `$wiki-sync`
6. **Selective/low priority**
   * `$database-migrations`
   * `$spec-merge-cleanup`
7. **Leave largely unchanged unless concrete evidence requires more**
   * `$project-tracking`
   * `$github-issue-dependencies`
   * `$coding-standards`
   * `$codebase-design`
   * `$tdd`
   * `$deduplicate-code`

## Hardening Review Questions

For each skill being hardened, ask:

1. What exact transition, mutation, closure, PASS, skip, or routing decision is at risk?
2. What semantic predicate authorizes that transition?
3. Is the candidate universe finite or open-world?
4. If finite, where does that universe come from and can candidates be omitted before counting begins?
5. Can any candidate disappear through `not-applicable`, duplicate, inherited, already-covered, no-work, or similar omission?
6. What minimum explicit state proves the semantic predicate was evaluated?
7. Does the transition consume that state, or can it still proceed without it?
8. Can every current check pass while the underlying claim is still false?
9. Are we hardening the generic invariant rather than encoding the last defect we happened to see?
10. Can the same safety be achieved with less state or fewer concepts?

## Definition of Done for a Hardened Invariant

A common-sense invariant is considered transition-bound when:

* the authoritative candidate universe is recoverable or its open-world boundary is explicitly defined;
* every material candidate receives an explicit disposition;
* escape states cannot be represented by omission;
* the reasoning result needed for the consequential transition is explicit enough to audit;
* the transition checks/consumes that state;
* quantified inner domains are closed recursively or by an independently checkable exhaustive mechanism;
* semantic transition authority is independently checkable rather than self-certified by the actor requesting the transition;
* missing, ambiguous, or contradictory state fails closed when correctness requires it;
* the design does not persist private reasoning transcripts or redundant derivable state;
* the hardening remains generic and is not merely a patch for one historical symptom.

## Expected Outcome

The desired workflow progression is:

```text
ordinary implementation defects
        ↓ caught by implementation/targeted verification
cross-surface contract omissions
        ↓ caught before ticket/Spec completion
review
        ↓ focuses on difficult integration, architecture, and genuinely novel defects
```

Review should not repeatedly rediscover ordinary obligations that were already explicit upstream. When it does, the default response should be to inspect whether an upstream common-sense invariant was prose-only or whether its universe was incompletely constructed, then harden the earliest authoritative transition rather than adding a special-case rule for the latest symptom.

## Hardening Execution Status

As of 2026-08-29, the hardening sequence defined by this audit is implemented on `main`.

* `$spec-contract` source-universe closure landed first, including deterministic Source Unit Inventory hashing.
* The remaining proof, decomposition, semantic-mutation, route/audit-completeness, migration-safety, and cleanup gates were hardened together in `91cb99fa7f58f5e145050126b764d1f34792ff7c` (`fix(workflow): enforce transition-bound invariants`).
* The coordinated commit changes only the 17 intended skill contracts: the 16 remaining audit targets plus the `$spec-contract` caller integration required by `$to-tickets`.
* The audit principles remain design guidance; each `SKILL.md` is the executable enforcement point.
* `$verify-spec` additionally uses proof-object-granular certification reuse and semantic-first final-gate ordering: fresh independence remains mandatory for stale proof, while certifier-approved immutable proof survives only through deterministic fail-closed invalidation.

A subsequent full `$verify-spec` rerun of Spec #240 exposed a false PASS despite the first hardening: the parent verifier created/declared complete proof state while durable cell evidence did not establish the direct subject of several claims. That demonstrated that explicit state can still be self-certifying and that outer-universe closure does not close nested quantified domains.

The second-stage model therefore adds **No Self-Certifying Semantic Transition** and **Nested Universe Closure**. `$verify-spec` now binds semantic proof to durable Proof Objects and genuinely fresh non-mutating proof certification before a cell may derive `proven` or `not-applicable`.

Future defects should first be evaluated against Transition-Bound Reasoning, Universe Closure, Nested Universe Closure, Explicit Escape Disposition, No Self-Certifying Semantic Transition, falsification-first proof, and evidence entailment before adding any defect-specific rule.

## Post-Audit Derived Hardening Principles

A 2026-09-01 evaluation of `$verify-code` and `$verify-spec` exposed three additional ways an otherwise hardened workflow can still authorize an invalid PASS without requiring any defect-specific rule. These are refinements of the existing universe, omission, self-certification, and local-enforcement principles.

### Close the Transition Universe Before Dependent Universes

A dependent universe can be perfectly dispositioned and still be incomplete when the upstream transitions that create that universe were never completely identified.

Example shape:

```text
recognized contract transition A
    ↓
all consumers of A dispositioned
    ↓
consumer closure = complete

omitted contract transition B
    ↓
its consumers never become candidates
```

The stronger rule is:

> **When a nested proof universe exists because an upstream transition, event, contract change, or semantic-owner change exists, close and disposition the upstream transition universe before deriving the dependent universe. Completeness of the child universe cannot compensate for an omitted parent transition.**

This is a recursive form of Nested Universe Closure. For shared-contract verification, for example:

```text
complete contract-transition universe
        ↓
every consumer-bearing transition
        ↓
complete consumer universe per transition
        ↓
contract-impact closure
```

Searching for obsolete symbols, new type names, or known caller patterns may help discover candidates but cannot define the transition universe unless the authoritative transition predicate itself is exactly that lexical pattern.

When completeness of the upstream transition universe is semantic rather than mechanically decidable, the same actor that wants PASS must not self-certify that completeness; use a fresh non-mutating semantic certifier or another independently checkable exhaustive mechanism.

### Observed Failures Remain Until Causally Dispositioned

A failure produced by an executed required check is evidence that exists even if a later command uses a narrower scope and passes.

The dangerous escape shape is:

```text
broad required check observes failure
        ↓
verifier narrows scope or relabels surface
        ↓
smaller rerun passes
        ↓
original failure disappears from final state
```

The stronger rule is:

> **Once a required gate, test, preflight, or delegated check exposes a failure, that failure becomes a candidate in the verification universe and remains there until it receives an explicit causal disposition. A later narrower rerun cannot erase the observation.**

`Inherited`, `unchanged`, or similar ownership classifications do not by themselves prove causal independence. A report-only exclusion requires an independently checkable witness, such as reproduction at the immutable baseline, deterministic delta analysis that excludes interaction with the active change, or fresh semantic certification when causality is not mechanically decidable.

This principle does not require retaining duplicate transcript noise. It requires retaining the minimum explicit state needed to prove why an observed failure may or may not block the transition.

### Delegated Gate Ownership

Local Enforcement also applies across skill boundaries.

If a parent workflow says another skill owns an audit, classification, proof, or gate, the child skill's current contract defines what execution is required and what terminal result can authorize the parent transition.

The stronger rule is:

> **When a transition owner delegates a correctness gate to another skill, the delegated skill owns the gate procedure and terminal result. The parent may not substitute an ad hoc approximation, partial shell recreation, or same-named script search and then claim the delegated gate passed.**

If the delegated skill cannot be executed, the delegated gate is unresolved unless the owning contract explicitly defines another valid route. Unavailability does not transfer semantic ownership back to the parent by default.

This prevents a hardened child skill from being bypassed by a less-complete parent approximation while preserving the existing principle that enforcement belongs at the transition owner: the parent must consume the child's valid result, and the child remains responsible for its own internal audit universe.

### Hardening Placement Rule

When downstream verification or review rediscovers an ordinary obligation that should already have been enforced upstream, first identify the earliest authoritative transition at which the obligation escaped.

Prefer this sequence:

```text
observed defect
    ↓
identify generic invariant that should have prevented it
    ↓
locate earliest transition owner that can enforce that invariant
    ↓
harden its universe / disposition / certification state
```

Do not add a rule named after the latest symbol, test file, option, helper, sink, or historical incident unless that named concept is itself the durable authoritative domain. Historical symptoms are evidence for the hardening analysis, not normally the vocabulary of the resulting invariant.

### Additional Hardening Review Questions

When modifying an already-hardened workflow, also ask:

11. Does the workflow close the universe of **transitions/events that create downstream candidate universes**, or only the candidates beneath transitions it happened to notice?
12. Can a failure observed by an earlier required command disappear after scope narrowing, ownership reclassification, or a later passing rerun without an explicit causal disposition?
13. Is surface ownership being used as a substitute for causal evidence that a failure is unrelated?
14. When a gate is delegated to another skill, does the parent consume the child's valid terminal result, or can it approximate the child procedure and self-declare the gate passed?
15. If a new defect fits an existing hardening principle, can the existing transition state be strengthened instead of adding a new defect-specific concept?

### 2026-09-01 Implementation Note

The derived principles above were applied generically in `266f891a921ecc1a958949e0da7ddc613091157a` (`fix(workflow): harden verification invariants`):

* `$verify-code` now closes a Contract Transition Manifest before per-transition Consumer Closure and fails closed when semantic transition-universe completeness lacks independent support;
* `$verify-spec` now retains every observed failure until explicit causal disposition and requires valid delegated-skill terminal results rather than parent-authored substitutes;
* no rule was added for a particular removed helper, test file, command-line option, or same-named script assumption.