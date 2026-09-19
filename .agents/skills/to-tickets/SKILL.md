---
name: to-tickets
description: Break an explicit plan, Spec, review, or other invocation source into tracer-bullet tickets while proving exhaustive obligation coverage and validating proposal readiness before human approval.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

Create tracer-bullet tickets using the publication workflow below, with hard boundaries for exhaustive source coverage, deterministic proposal readiness, independent semantic decomposition certification, human approval of the substantive decomposition, and exact publication readback.

This `SKILL.md` is the single authoritative procedure for `$to-tickets`. The preserved procedure later in this file remains normative for session recovery, project-delivery guards, codebase exploration, mode routing, `$to-remediation-tickets`, vertical slicing, user approval, Spec Branch Rule, tracker publication, native hierarchy/dependencies, ticket baseline/branch semantics, and handoff.

The hardening sections immediately below add the fresh-Spec obligation-coverage gate, parent-owned proposal readiness validation, one independent semantic decomposition-verification boundary, exact Spec provenance on ordinary tickets, conditional/deferred obligation routing, architecture/design obligation coverage, the design-delegation guard, and exact post-publication readback. On conflict with older wording later in this file, these hardening sections win.

The remediation path remains owned by `$to-remediation-tickets`; do not replace its Root Blocker delta contract with the fresh-Spec mapping below.

## Mandatory Mode Preflight — Run Before All Other Composition

Resolve the cheapest legally sufficient workflow mode **before** loading remediation logic, closing architecture/design source universes, running `$attention`, building Ticket Semantic Carry, or dispatching `$verify-ticket-decomposition`.

This preflight is the first substantive operation after recovering the source artifact identity.

### Minimal current-state recovery

Recover only the current durable facts needed to classify mode:

```text
Source type/title/state
Current branch/head and required Spec baseline metadata
Existing linked implementation-ticket identities/states
Whether exactly one current Ticket Coverage Manifest exists
Parent Spec body/contract identity fields when a TCM exists
Whether a current decomposition-defects:v1 record applies
```

Do not inspect historical commits, old issue generations, prior ticket proposals, or unrelated architecture sources merely to classify mode.

### Parent Spec Contract Coherence Gate

Before mode routing, whenever the originating/parent Spec already has a Ticket Coverage Manifest — including when the public source is a `Spec Review: ...` — build the exact current `$spec-contract` once in the owning `$to-tickets` context and reconcile its current identity with the current TCM.

Require the fresh contract to return:

```text
Spec Body Hash: <hash>
Spec Contract Hash: <hash>
```

Require the TCM to persist the same two fields. Then require exact equality of body hash and contract hash.

When the TCM identity is stale, one narrow deterministic current-contract reconciliation is permitted before mode routing only when current authority independently proves all of the following:

```text
Fresh current $spec-contract: VALID
Source/TCM Spec-cell ID sets equal: yes
Existing source-derived Spec routing still valid: yes
Existing Architecture/Design routing still valid: yes
Legitimate routing changes required: 0
Ticket semantic mutations required: 0
Ticket lifecycle/native-relationship mutations required: 0
Only current contract identity metadata differs: yes
```

This witness does not infer equivalence from the stale hash. It proves that the TCM's decomposition semantics are still current, then updates only the TCM identity metadata to the freshly rebuilt current contract. Update the existing current TCM in place with the fresh `Spec Body Hash` and `Spec Contract Hash`; GET that exact comment and require exact readback before continuing. No human decomposition approval or independent semantic verifier is needed for this identity-only normalization because ticket/routing semantics are unchanged.

If any witness row is false, unknown, or requires semantic rerouting, do not normalize the hash and do not continue to proposal readiness. Fall through to the applicable substantive decomposition/remediation path with the identity conflict explicit; no PASS may infer equivalence from matching subsets.

Reuse the same freshly built contract for later decomposition steps while the Spec body/baseline/branch/HEAD remain unchanged.

### Manifest-reconciliation fast-path probe
### Manifest-reconciliation fast-path probe

When the source is an ordinary Spec with existing linked implementation tickets **and** exactly one current Ticket Coverage Manifest:

1. attempt **Existing-Spec Manifest Reconciliation** before invoking `$to-remediation-tickets`;
2. build the exact current `$spec-contract` once in the owning context;
3. parse the exact current TCM Spec-cell ID set;
4. compute mechanically:

```text
missing = SOURCE_SPEC_CELL_IDS - TCM_SPEC_CELL_IDS
extra   = TCM_SPEC_CELL_IDS - SOURCE_SPEC_CELL_IDS
```

5. snapshot only the current linked-ticket bodies, Spec/Architecture obligation provenance, lifecycle states, native parents, blocking relationships, branch/baseline metadata, labels/status, and other state required by **Existing-Spec Manifest Reconciliation** to prove zero ticket-semantic/lifecycle delta;
6. test the complete `MANIFEST RECONCILIATION READINESS` witness.

If that witness passes, set:

```text
Mode: manifest-reconciliation
```

and execute **Existing-Spec Manifest Reconciliation** directly.

In `manifest-reconciliation` mode, skip all machinery whose only purpose is substantive ticket decomposition:

* do **not** invoke `$to-remediation-tickets`;
* do **not** construct a new ticket proposal;
* do **not** rediscover/close the full architecture/design source universe when the current valid TCM/source identities needed for zero-delta proof are sufficient;
* do **not** build a Ticket Semantic Carry Matrix for unchanged closed-ticket contracts;
* do **not** run the proposal-oriented `$attention` checkpoint;
* do **not** dispatch `$verify-ticket-decomposition`;
* do **not** request human decomposition approval.

The current-state deterministic reconciliation/readback contract is the proof boundary for this mode.

If the manifest-reconciliation witness fails because any required value is non-zero, unknown, stale, or semantically changed, leave the fast path and continue through the normal existing-ticket remediation path. Do not weaken the witness to stay on the cheap path.

### Anti-archaeology rule

For manifest reconciliation, current authoritative state is sufficient unless a current-state ambiguity prevents one of the required readiness fields from being decided.

Once exact current `$spec-contract` identity, exact TCM identity, exact linked-ticket snapshots, and the set differences establish the mismatch and zero semantic/lifecycle delta:

* do not run `git log`, `git show`, commit searches, old issue searches, or historical text searches merely to determine who/when introduced the bad row;
* do not rebuild adjacent source-unit inventories with ad hoc scripts when the canonical `$spec-contract` already supplies the required source-cell universe;
* do not search for historical occurrences of the bad cell ID merely to gain confidence;
* do not broaden into architecture/document history unless current authority is genuinely ambiguous and that ambiguity blocks a required reconciliation field.

Historical causation is not required to repair current decomposition metadata.

### Budget guard

Efficiency is a correctness constraint for this fast path.

If an execution/token/time budget warning appears after manifest-reconciliation eligibility is plausible, stop optional investigation immediately and complete only the deterministic current-state proof/mutation/readback steps required by this mode.

Do not spend the remaining budget on provenance archaeology, repeated equivalent queries, or confidence-seeking searches.

## Execution Budget and Independence Boundary

For **substantive fresh-ticket or existing-ticket remediation decomposition**, `$to-tickets` has exactly one independent semantic certification boundary over the frozen final proposal.

Automatic semantic subagents for substantive decomposition: **1 verifier context**.

Automatic semantic subagents for `manifest-reconciliation`: **0**.

Only after the **Mandatory Mode Preflight** selects substantive fresh/remediation decomposition must the owning `$to-tickets` agent close the bounded architecture/design obligation universe, draft ticket slices, validate proposal mechanics, run proposal-oriented `$attention`, build the Ticket Semantic Carry Matrix, and produce the parent-owned `TICKET PROPOSAL READINESS: PASS`. The owning agent may not certify the semantic completeness of its own substantive proposal as the final authority.

After parent-owned readiness PASS for a substantive proposal, automatically dispatch exactly one genuinely fresh, non-mutating `$verify-ticket-decomposition` verifier for the exact proposal identity. The verifier independently re-reads the supplied durable authority within the already-bounded source universe and returns one `TICKET DECOMPOSITION: PASS | FAIL` verdict. It does not redesign, mutate, publish, or spawn another model/subagent.

`manifest-reconciliation` is explicitly exempt from that proposal/verifier boundary because eligibility requires zero ticket/routing semantic change and its proof is deterministic current-state reconstruction plus exact readback.

When `$to-tickets` invokes `$spec-contract` solely for decomposition, use the explicit `$to-tickets` decomposition exception in that skill and execute it in the owning context. Do not create a separate fresh `$spec-contract` builder merely for ticketing.

A verifier FAIL returns control to the owning `$to-tickets` context. Correct the candidate, rerun all affected parent-owned checks, and send the revised exact proposal back to the **same verifier context** when that context remains available. If that verifier context is genuinely lost or unavailable, create one fresh replacement verifier and perform the full certification again. Do not create a cascade of fresh challengers that each inspect one successive repair.

Any second concurrent or additional independent semantic reviewer/challenger beyond the required `$verify-ticket-decomposition` verifier requires **explicit human authorization in the current invocation**.

Downstream `$implement-ticket`, `$verify-spec`, and `$review-spec` retain their own independent implementation/spec/review boundaries; the ticket-decomposition verifier does not replace them.

Efficiency is part of correctness here:

0. resolve **Mandatory Mode Preflight** first and skip every later phase that does not apply to the selected mode;
1. recover lifecycle/governance state once and reuse it while its durable identities are unchanged;
2. establish the Spec branch/baseline needed by the final contract before final decomposition;
3. build the complete `$spec-contract` universe before final ticket prose;
4. close the bounded architecture/design obligation universe before final ticket prose;
5. freeze one structured routing model from Spec cells and `ARCHSRC-*` obligations to ticket aliases/destinations;
6. render ticket bodies, dependency edges, and the parent coverage manifest from that closed routing model;
7. run deterministic proposal checks before `$attention` and before independent verification;
8. do not expand exact requirement text into giant duplicate scratch artifacts when the canonical contract/manifest already carries that text; retain exact source text by stable ID/hash and render only the durable/human-facing forms required by this workflow;
9. dispatch one independent verifier context only after the proposal is parent-ready, reuse that verifier context across repaired candidates when possible, and do not poll or emit status-noise loops for verifier work.

A failed deterministic query is corrected against the actual schema. It does not justify broad alternate searches or repeated repository archaeology.

## Architecture Source-Closure and Ticket Semantic-Carry Gate

This section is authoritative for fresh-Spec architecture/design completeness and proposal semantic fidelity. It strengthens the later **Architecture / Design Obligation Coverage**, **Proposal Readiness Validation**, **Parent Coverage Artifact**, **Independent Ticket Decomposition Gate**, and **Publication Integrity** sections. Where later wording could permit the proposal, proposed ticket `Architecture context`, or already-noticed `ARCHSRC-*` rows to define their own completeness denominator, this section wins.

The core rule is:

> **Do not prove only that every obligation you happened to find was routed. Prove first that the complete bounded authoritative source universe was closed, then prove that every materially normative obligation in that universe was dispositioned, then prove that the rendered tickets faithfully carry every routed semantic predicate.**

Ticket wording is an output of this gate. It is never an input for discovering the authoritative architecture/design universe.

### 1. Close the Architecture / Design Source Inventory

Before extracting final `ARCHSRC-*` obligations or writing final ticket prose, construct one working **Architecture / Design Source Inventory**.

Seed the inventory from durable authority, not from the draft proposal. Include every current non-legacy architecture/design source that is materially reachable through at least one of these routes:

1. explicitly named by the originating Spec's Architecture Impact, readiness state, normative body, accepted decision references, or governing architecture links;
2. the current architecture source that owns a platform/domain boundary materially consumed by the Spec or by an already-included design source, when that ownership is established by current authority;
3. explicitly referenced by an included architecture/design source where that reference is required to interpret or implement a material obligation for the Spec;
4. cited by a current durable `decomposition-defects:v1` record applicable to this decomposition.

Do **not** recursively crawl unrelated documentation or include a source merely because it exists. Follow only current authority relationships needed to interpret the affected boundary. Conversely, do not omit the current owning architecture source merely because a more specific design document or Spec cell already describes part of the behavior.

For every candidate source record exactly one row:

```text
Architecture source: <durable path/ADR/doc/tracker identity>
Discovery authority: <exact Spec/source/defect reference that makes it a candidate>
Relevant anchors: <section(s)/anchor(s) | whole source when genuinely required>
Source identity: <stable blob/hash/tracker identity at the current candidate state>
Disposition: included | excluded
Reason/authority: <why included, or exact authority proving exclusion>
```

Rules:

* every discovered candidate appears exactly once;
* `excluded` requires positive scope authority; "seems duplicated", "not mentioned by the draft", or "probably covered by the Spec" is not exclusion authority;
* if an included source references another current source for the ownership, contract, runtime, dependency, persistence, transaction, testing, or other material boundary being implemented, evaluate that referenced source as a candidate before closing the inventory;
* a source that is fully represented by Spec cells still remains in the inventory; duplication affects obligation disposition, not source discovery;
* missing/unreadable candidate authority or ambiguous source ownership fails closed;
* once the inventory is closed, do not broaden it merely to seek extra confidence unless a concrete source reference, conflict, or Attention finding falsifies the closure.

Before obligation extraction require:

```text
Architecture/design source candidates: <n>
Included architecture/design sources: <n>
Excluded architecture/design sources: <n>
Unclassified architecture/design sources: 0
Included sources without stable identity: 0
Excluded sources without reason/authority: 0
```

### 2. Close Normative Source-Unit Coverage

For every **included** source, inspect the relevant anchors and create one working source-unit row per materially distinct normative obligation. Group clauses only when they establish the same semantic predicate/owner and grouping cannot hide a condition, negative rule, temporal boundary, failure state, or separate implementation destination.

Use:

```text
Architecture source unit: ARCSU-<n>
Source/anchor: <durable source + exact section/anchor>
Requirement: <compact faithful normative requirement>
Representation: spec-cell | ARCHSRC | not-applicable
Mapping: <Spec cell(s) | ARCHSRC-* | None>
Reason/authority: <required for not-applicable; explain complete Spec-cell representation when non-obvious>
```

Rules:

* every materially normative source unit in every included anchor receives exactly one representation;
* `spec-cell` is legal only when the referenced Spec cell(s), taken together, completely preserve the source unit's predicate, conditions, negative semantics, temporal meaning, and failure boundary;
* if a source unit is only partially represented by Spec cells, create an `ARCHSRC-*` obligation for the uncovered material semantics rather than declaring duplication;
* `not-applicable` requires exact source/scope authority, not implementation convenience;
* implementation shape, current code, existing tests, and draft ticket prose do not define whether a source unit is normative or already covered;
* omission is never a representation.

Only after this source-unit universe is complete may the later **Architecture / Design Obligation Disposition Manifest** be finalized.

Before final `ARCHSRC-*` routing require:

```text
Included normative architecture/design source units: <n>
Represented completely by Spec cells: <n>
Represented by ARCHSRC obligations: <n>
Authoritatively not applicable: <n>
Unclassified normative source units: 0
Partially represented source units treated as complete: 0
Not-applicable source units without authority: 0
```

The source inventory and source-unit coverage are the denominator proof. A result such as `Architecture obligations: 9/9` is not readiness evidence unless these preceding closure counts also pass.

### 3. Prove Ticket Semantic Carry

After Spec-cell and `ARCHSRC-*` routing is frozen and final ticket bodies are rendered, build one working **Ticket Semantic Carry Matrix** for every obligation with an `implementation-ticket` disposition.

Use:

```text
Obligation: <Spec cell | ARCHSRC-*>
Authoritative requirement: <source-bound requirement>
Mapped ticket(s): <ticket aliases/identities>
Carry evidence: <What to build / acceptance / preservation criterion references>
Carry disposition: complete | incomplete | ambiguous
```

For `complete`, the rendered ticket contract must preserve every materially significant predicate required by the obligation. Check explicitly for, where applicable:

* conjunctions, exhaustive sets, cardinality, identity, and uniqueness;
* conditions, triggers, eligibility predicates, and deferred activation rules;
* effective-time / known-at / recording-time boundaries and evaluation order;
* positive versus negative field/claim semantics, including fields or meanings that **must not** be present;
* attribution, provenance, basis-role, ownership, and authority distinctions;
* atomicity, concurrency, expected-version, idempotency/replay, and conflict semantics;
* typed failure states, fail-closed behavior, contested/ambiguous states, and forbidden fallback/recency rules;
* correction/replacement ancestry and restoration semantics;
* required preservation/non-regression behavior;
* explicit exclusions and prohibited technologies/dependencies/representations;
* required proof modality when authority specifically requires real-service, architecture, runtime, negative-path, or concurrency qualification.

Compression and paraphrase are allowed only when semantic entailment is preserved. An obligation ID listed under `Spec obligations` or `Architecture obligations` is provenance, **not** proof that the ticket wording carries the obligation. A broad Architecture context citation is likewise insufficient.

When an obligation intentionally spans multiple tickets, the approved mapping must make that split explicit and the union of those ticket contracts must preserve the whole obligation without leaving a material choice between tickets. If one mapped ticket is required to enforce the obligation independently, its own contract must say so.

Before proposal readiness require:

```text
Implementation obligations requiring semantic carry: <n>
Complete semantic-carry rows: <n>
Incomplete semantic-carry rows: 0
Ambiguous semantic-carry rows: 0
Mapped implementation obligations with no carry evidence: 0
```

Any semantic or metadata edit to the rendered proposal invalidates affected carry rows and requires rechecking them before approval.

### 4. Readiness, Durable Coverage, and Publication Consequences

The parent-owned **Proposal Readiness Validation** must additionally require:

```text
Architecture/design source inventory complete: yes
Unclassified architecture/design sources: 0
Normative architecture/design source-unit coverage complete: yes
Unclassified normative architecture/design source units: 0
Ticket semantic carry complete: yes
Incomplete semantic-carry rows: 0
Ambiguous semantic-carry rows: 0
```

A readiness PASS must report the compact denominator proof, not only `ARCHSRC-*` routing counts:

```text
Architecture source closure: <included>/<candidates>; excluded <n>; unclassified 0
Architecture normative source units: <accounted>/<total>; unclassified 0
Ticket semantic carry: <complete>/<required>; incomplete 0; ambiguous 0
```

The durable parent `## Ticket Coverage Manifest` must include a compact **Architecture / Design Source Inventory** subsection containing every candidate source's durable identity, relevant anchors, and included/excluded disposition, plus the source/source-unit closure counts above. Do not persist duplicated raw source text merely to prove coverage.

Immediately before publication, revalidate that:

* the source identities used to close the Architecture / Design Source Inventory are still current for the approved proposal state;
* no newly discovered authoritative reference or Attention finding invalidates source closure;
* Spec/`ARCHSRC-*` routing still matches the approved ticket IDs;
* all semantic-carry rows for the exact approved ticket bodies remain complete.

If any of those checks fail, the prior parent readiness PASS and independent decomposition PASS are stale and the workflow returns to source closure, obligation routing, proposal validation, and independent certification as applicable. Human approval never waives this gate.

## Design Delegation Guard

`$to-tickets` decomposes a frozen implementation-ready contract. It does not design the behavior that `$implement-ticket` will later choose.

Before proposal-readiness validation for every software ticket set:

1. require the source Spec/remediation authority to be currently implementation-ready under its own durable readiness state;
2. inspect every proposed ticket for material choices left to implementation;
3. apply the `AGENTS.md` materially-different-implementations test;
4. invoke `$attention` as prescribed internal composition before freezing the proposal.

For each material candidate choice classify:

```text
Choice: <public/domain/downstream choice>
Authority: <exact source>
Disposition: frozen-upstream | semantically-equivalent-mechanic | unresolved-design
```

`unresolved-design` is never a legal ticket handoff. If two reasonable implementations could satisfy the ticket while establishing materially different public, product, domain, architecture, persistence, or downstream contracts, return the affected scope to its owning Spec/design authority rather than drafting acceptance criteria that silently delegate the choice.

### Architecture Readiness Saturation and Remediation Human Handoff

For existing Implementation Tickets during ticket reconciliation, architecture/design readiness discovery is **saturation-based, not fail-fast**. Run this sweep before any empty-delta `$implement-ticket` handoff and before proposal-readiness validation or user approval.

Construct the complete applicable **existing-ticket reconciliation universe** from durable Spec/ticket lineage. Include every open existing Implementation Ticket whose contract belongs to the current Spec reconciliation, including tickets that currently have open native blockers. Native dependency/frontier state determines implementation actionability; it does not exempt a ticket from design-readiness evaluation. Closed or superseded tickets remain historical and are excluded unless current authority explicitly returns them to active reconciliation.

Evaluate every materially determinable design dimension for every ticket. Do not stop the sweep when the first architecture gap is found, and do not stop evaluating a ticket merely because an upstream ticket has unresolved architecture. Continue evaluating every dimension whose answer does not depend on that upstream choice.

Assign exactly one ticket-level disposition:

```text
design-ready | architecture-blocked | upstream-readiness-deferred
```

Rules:

- `architecture-blocked` when at least one determinate ticket-owned unresolved durable choice exists, even when other dimensions remain dependent on upstream architecture;
- `upstream-readiness-deferred` only when no determinate ticket-owned architecture/design gap is currently established but complete readiness cannot be decided until a specific unresolved upstream architecture choice is resolved;
- `design-ready` only when current authority freezes every material choice required by that ticket;
- incomplete/unreadable ticket-universe data or an unresolved ticket-level classification is a hard blocker, not `upstream-readiness-deferred`;
- an open native blocker is never by itself evidence of an architecture/design gap;
- never create an `architecture-blocker:v1` report solely because another ticket blocks the ticket.

Before any architecture Human Handoff require complete saturation accounting:

```text
Existing-ticket reconciliation universe: <n>
Design-ready: <n>
Architecture-blocked: <n>
Upstream-readiness-deferred: <n>
Unclassified: 0
Architecture-blocked reports required: <n>
Architecture-blocked reports persisted/read-back: <n>/<n>
Missing blocker reports: 0
```

After the complete sweep, for **every** `architecture-blocked` ticket create or update that ticket's single machine-managed `<!-- architecture-blocker:v1 -->` comment under the cross-skill contract in `.agents/skills/README.md`.

Persist at least:

- `Status: unresolved`;
- `Source workflow: $to-tickets`;
- the exact source ticket identity and parent Spec;
- every coupled unresolved question/conflict determinately established for that ticket;
- durable evidence and governing authority;
- material consequence;
- exact blocked ticket/Spec obligation.

If an active report already exists, reconcile/update that same managed comment rather than creating a competing report. Read every required report back and require the marker, unresolved status, source identity, parent Spec, and complete determinate blocker set to match. Partial report persistence is non-terminal: resume/reconcile until every required report is durable before presenting any Human Handoff. A chat summary or prior-session output is never a substitute for these persisted reports.

The saturation pass is read-only with respect to ticket contracts, baselines, dependencies, and closure state. If one or more tickets are `architecture-blocked`, do not publish, rewrite, close, or otherwise reconcile ticket semantics in that invocation after the sweep; persist/verify the blocker reports and halt ordinary ticketing.

When one or more tickets are `architecture-blocked`, terminate with one copy-ready handoff per affected ticket:

> Please continue with:
>
> ```
> $architecture-remediation - <Architecture-Blocked Ticket Title> (<Ticket URL>)
> $architecture-remediation - <Architecture-Blocked Ticket Title> (<Ticket URL>)
> ```

Use the actual ticket titles and URLs. Present every architecture-blocked ticket discovered by the saturated sweep together and let the user choose which fresh remediation session to start. Do not replace the copy-ready commands with free-form prose, do not scope the invocation to the parent Spec when an existing blocked ticket is the source artifact, and do not omit a ticket merely because it is not currently on the implementation frontier.

A ticket classified only `upstream-readiness-deferred` receives **no** architecture-blocker report and no `$architecture-remediation` handoff solely for that dependency. Report its exact upstream architecture dependency as deferred state. After the governing upstream architecture changes, a later `$to-tickets` reconciliation re-evaluates that ticket from durable authority and may then classify it `design-ready` or `architecture-blocked`.

If the saturated sweep has zero `architecture-blocked` tickets but one or more `upstream-readiness-deferred` tickets, stop ordinary ticketing and report the exact durable upstream blocker(s) preventing readiness completion; do not emit a synthetic remediation handoff for the deferred tickets.

If both `architecture-blocked` and `upstream-readiness-deferred` tickets exist, emit the complete architecture-remediation handoff set for the architecture-blocked tickets and report the deferred tickets separately as dependent follow-up state.

Do not invoke `$architecture-remediation` implicitly. For a fresh Spec with no existing Implementation Ticket, do not fabricate a ticket identity: persist any correctness-critical stopping context on the owning durable Spec/planning artifact as required by the cross-skill Fresh-Session Durability Gate, then use that owning workflow's handoff contract.

Before readiness validation require:

```text
Material design choices delegated to implementation: 0
Source implementation readiness: pass
Attention design-gap findings unresolved: 0
```

For existing-ticket reconciliation, readiness validation additionally requires:

```text
Architecture-blocked tickets: 0
Upstream-readiness-deferred tickets: 0
Unclassified ticket readiness: 0
```

Private helper decomposition, equivalent algorithms/local data structures with no contract consequence, formatting, and equivalent test mechanics remain implementation-owned and do not need Spec-level prescription.

## Conditional / Deferred Obligation Routing

This section is authoritative for every materially conditional fresh-Spec obligation and supersedes preserved disposition schemas below where they omit conditional trigger state.

A conditional requirement must retain both its trigger and its eventual destination. Do not turn an inactive condition into current implementation work merely to make decomposition complete, and do not let it disappear because the trigger has not fired.

For each materially conditional Spec cell, extend the normal disposition row with:

```text
Condition/trigger: <exact originating-Spec trigger>
Trigger state at publication: active | inactive | ambiguous
Deferred destination/owner: <durable future lifecycle/verification owner | None>
Trigger evidence: <current evidence>
```

The allowed fresh-Spec dispositions are:

```text
implementation-ticket | verification-only | no-implementation-work | authoritative-exclusion | deferred-conditional
```

Rules:

* `deferred-conditional` is legal only when the originating Spec itself makes the obligation conditional and the trigger is currently inactive;
* preserve the source trigger exactly; do not strengthen `when X, do Y` into `build machinery now that guarantees Y for all future X` unless the Spec expressly requires pre-provisioning;
* an inactive conditional obligation receives no implementation ticket merely because future work will eventually be required;
* `deferred-conditional` must name a durable future destination/owner already established by current authority; `$to-tickets` may not invent CI, automation, a workflow owner, project policy, or another mechanism solely to create that destination;
* if the trigger is active, `deferred-conditional` is invalid and the obligation must use the ordinary implementation/verification/no-work disposition that the active consequent requires;
* if trigger state is ambiguous, proposal readiness fails closed;
* if the trigger is inactive but no durable future destination can be established, decomposition remains unresolved; surface a genuine owner decision only when authoritative project sources truly leave that destination undecided;
* when a later transition observes the trigger becoming active, the deferred disposition is stale and that transition must evaluate the consequent normally;
* `verification-only` continues to mean later proof of a currently applicable obligation; it is not a substitute for an inactive future condition whose trigger has not fired.

The durable parent `Ticket Coverage Manifest` must preserve `deferred-conditional` rows with the exact trigger and destination, for example:

```text
<Cell ID> → deferred-conditional — trigger: <condition>; destination: <owner>
```

That row is routing evidence, not proof that the future consequent has already been implemented or verified.

Proposal readiness additionally requires:

```text
Conditional obligation rows: <n>
Ambiguous trigger states: 0
Inactive conditional rows without durable destination: 0
Active conditional rows misclassified as deferred: 0
```

`$to-tickets` validates those fields directly against the originating Spec and durable destination authority. Do not trust the draft's trigger classification merely because it appears internally consistent.

## Human Approval Is Not Verification

The human approval step exists to approve or reject the **substantive decomposition**: ticket granularity, meaningful scope, and product/architecture choices that genuinely require owner judgment.

It is **not** a correctness backstop for `$to-tickets` or its independent verifier.

Before the user ever sees a publication proposal, `$to-tickets` owns proving that the proposal already complies with repository ticketing authority and obtaining one independent semantic decomposition certification, including as applicable:

* authoritative source/root obligation coverage;
* required ticket fields and template semantics;
* direct native parent and durable lineage;
* `Ticket branch` semantics;
* `Ticket baseline` semantics;
* required label/status;
* preservation and verification classification;
* blocking relationships/dependency direction;
* closed-ticket preservation and duplicate prevention;
* publication-state consistency with the exact source contract;
* source implementation readiness and absence of implementation-delegated material design;
* independent certification that the exact ticket bodies faithfully carry the complete bounded source/root universe.

Do not ask the user to validate, repair, or reconstruct those mechanics or semantics.

An unqualified `approve`, `approved`, `yes`, or equivalent after a readiness-valid and independently certified proposal is presented authorizes publication of that exact proposal. The user does not need to restate its metadata, prove its coverage, or independently verify repository policy.

If a genuine unresolved product, domain, public-contract, architecture, or decomposition choice remains, surface that specific choice. Do not disguise an internal ticket-construction, semantic-certification, or policy-validation failure as a human design decision, and do not bury a real upstream design gap inside ticket acceptance wording.

## Proposal Readiness Validation

Before independent certification and Step 4 approval for any non-metadata-only proposal, freeze the exact proposed ticket set and complete this parent-owned readiness validation. This parent check is mandatory evidence for `$verify-ticket-decomposition`; it is not the final independent semantic verdict.

### Freeze the candidate

Render the exact proposal that would be shown to the user, including every proposed new/update/close action, ticket body semantics, hierarchy, dependencies, branch/baseline metadata, labels/status, and mode-specific coverage summary.

Bind the candidate to:

```text
Source artifact: <durable identity>
Ticket mode: fresh | remediation
Source contract/root state: <durable identity including Spec Contract Hash where available>
Proposal identity: <SHA-256 of the exact rendered proposal candidate>
```

Any semantic or metadata change after validation invalidates the readiness result and any independent decomposition verdict for the old candidate.

### Authoritative proposal universe

For a **fresh Spec** proposal, validate against:

* the exact current `$spec-contract` manifest;
* the Spec Obligation Disposition Manifest;
* the Architecture/Design Obligation Disposition Manifest when the Spec/tickets consume governing architecture/design sources;
* the proposed ticket `Spec obligations` and `Architecture obligations` mappings;
* the applicable parent Spec, branch, workspace metadata, and current implementation-readiness/design-completeness state.

For a **Spec Review remediation** proposal, validate against:

* the exact remediation parent Spec Review;
* the parent Spec provenance;
* every current unresolved/regressed Root Blocker and active cumulative acceptance cell;
* the complete remediation / verification / preservation partition;
* current existing-ticket lineage and closed/open state;
* the Root Delta Coverage returned under `$to-remediation-tickets` authority;
* the current parent/remediation design-readiness state where material public/domain contracts are affected.

Completeness must be defined from those authoritative universes, never from what the draft happened to mention.

### Exact Spec-cell identity

For every **fresh Spec** proposal, the parent Ticket Coverage Manifest may route and disposition only cells that exist in the exact current `$spec-contract` manifest.

Materialize both ID sets mechanically:

```text
SOURCE_SPEC_CELL_IDS = exact Spec-cell IDs emitted by the bound $spec-contract manifest
TCM_SPEC_CELL_IDS = exact Spec-cell IDs rendered in the proposed Ticket Coverage Manifest
```

Require exact bidirectional equality:

```text
SOURCE_SPEC_CELL_IDS - TCM_SPEC_CELL_IDS = ∅
TCM_SPEC_CELL_IDS - SOURCE_SPEC_CELL_IDS = ∅
SOURCE_SPEC_CELL_IDS = TCM_SPEC_CELL_IDS
source count = TCM Spec-cell count
```

The first difference detects missing source cells. The second detects **invented / non-source-derived cells**. Both are publication blockers.

A disposition such as `implementation-ticket`, `verification-only`, `no-implementation-work`, `authoritative-exclusion`, or `deferred-conditional` is a disposition **of an existing source cell**. It never creates a new cell identity.

Repository lifecycle rules, branch/baseline mechanics, publication preconditions, approval state, workflow metadata, tracker normalization, and other ticketing mechanics must remain proposal/readiness metadata unless the exact current `$spec-contract` independently emits them as Spec cells. Do not mint a `NORM-*` or any other cell merely because a mechanical condition matters to ticket publication.

Regression falsifier: a proposal that contains every real source cell **plus one synthetic cell** must fail deterministic readiness with `Extra/non-source-derived Spec cells: 1`, even when all real cells are otherwise correctly routed.

### Deterministic-first validation

Before making another semantic pass over ticket slicing, mechanically validate every mechanically decidable property. Prefer scripts, exact parsing, set equality, counts, hashes, and tracker/native relationship reads over model re-reading.

At minimum require:

```text
Source implementation readiness: pass
Parent Spec contract coherence: pass
Current/TCM Spec Body Hash equal: yes when a TCM exists
Current/TCM Spec Contract Hash equal: yes when a TCM exists
Material design choices delegated to implementation: 0
Attention design-gap findings unresolved: 0
Source obligations/root cells complete: yes
Architecture/design obligation coverage complete: yes
Architecture/design obligations missing or ambiguous: 0
Proposal coverage complete: yes
Source Spec cells: <n>
TCM Spec cells: <n>
Missing source-derived Spec cells: 0
Extra/non-source-derived Spec cells: 0
Source/TCM Spec-cell ID sets equal: yes
Ambiguous dispositions: 0
Unclassified dispositions: 0
Required remediation without ticket coverage: 0
Required preservation omitted: 0
Required verification omitted/misclassified: 0
Template/required headings and fields valid: yes
Native parent/lineage valid: yes
Ticket branch semantics valid: yes
Ticket baseline semantics valid: yes
Label/status semantics valid: yes
Dependencies/blocking edges internally valid: yes
Closed tickets reopened/rewritten: 0
Duplicate/conflicting active ticket coverage: 0
Ticket Spec-obligation sets equal routing manifest: yes
Ticket Architecture-obligation sets equal routing manifest: yes
Parent Ticket Coverage Manifest render complete: yes
Unresolved repository-policy conflicts: 0
```

The owning agent then checks the substantive slice semantics against the already-closed source/routing universes. Do not reopen unrelated architecture or rediscover the repository merely to seek additional confidence.

For new tickets, explicitly enforce the repository baseline distinction:

* `Ticket baseline: Pending` is the required **per-ticket implementation anchor** at publication;
* `$implement-ticket` later pins that ticket baseline to the exact pre-mutation HEAD;
* the fixed parent **Spec baseline is separate provenance** and must never replace a new ticket's `Ticket baseline: Pending` field.

Do not treat `Pending` as proposal shorthand.

### Verdict

Return exactly one parent-owned readiness result for the frozen proposal.

PASS:

```text
TICKET PROPOSAL READINESS: PASS
Source: <identity>
Mode: fresh | remediation
Proposal identity: <sha256>
Validation owner: $to-tickets
Required independent verifier: $verify-ticket-decomposition
Design delegation: 0
Coverage: <n>/<n>; missing 0; ambiguous 0; unclassified 0
Spec-cell identity: source <n>; TCM <n>; missing 0; extra 0; exact-set-equality yes
Mechanics: template/lineage/branch/baseline/status/dependencies valid
Repository-policy conflicts: 0
Human verification required: no
```

FAIL:

```text
TICKET PROPOSAL READINESS: FAIL
Source: <identity>
Mode: fresh | remediation
Proposal identity: <sha256>
Findings:
1. <exact violated authority / affected proposal element / required correction>
...
```

On FAIL, `$to-tickets` corrects every resolvable ticket-construction defect and reruns this validation before independent certification. Do not expose intermediate invalid proposals merely to ask the user to act as the workflow verifier.

Only surface a blocker when authoritative sources genuinely leave a substantive owner decision unresolved. Mechanical/template/lifecycle errors are `$to-tickets` responsibilities.

## Independent Ticket Decomposition Gate

After `TICKET PROPOSAL READINESS: PASS` and before showing any non-metadata-only proposal for human approval, automatically dispatch exactly one genuinely fresh non-mutating verifier context executing `$verify-ticket-decomposition` for that exact proposal identity.

Pass the verifier the complete required input defined by `$verify-ticket-decomposition`, including the exact source/root state, exact `$spec-contract` or remediation universe, source inventory and normative source-unit coverage, routing/disposition manifests, Ticket Semantic Carry Matrix, exact rendered proposal, and parent readiness result.

The owning `$to-tickets` agent must not provide the verifier with an asserted semantic conclusion beyond its explicit parent-owned artifacts, must not certify the candidate itself while the verifier runs, and must not mutate the candidate until a verdict is returned.

Require exactly one valid verdict bound to the current proposal identity:

```text
TICKET DECOMPOSITION: PASS
```

or:

```text
TICKET DECOMPOSITION: FAIL
```

On FAIL:

1. consume every returned finding;
2. return control to the owning context;
3. repair every resolvable decomposition defect without broadening scope beyond durable authority;
4. rerun every affected deterministic/semantic parent-owned check and produce a new proposal identity;
5. send the revised exact candidate back to the same verifier context when available;
6. if that context is genuinely lost, create one fresh replacement verifier for the complete revised candidate.

Do not show the user a semantically failed candidate. Do not spawn a fresh challenger merely because the first verifier found defects. A second additional independent reviewer beyond the required verifier requires explicit human authorization.

Only when both of these bind to the **same exact proposal identity** may Step 4 request approval:

```text
TICKET PROPOSAL READINESS: PASS
TICKET DECOMPOSITION: PASS
```

Then present the proposal and include one compact line:

```text
Proposal readiness: deterministic repository-policy checks are complete; the exact proposal is independently certified for semantic decomposition fidelity.
```

If the user requests any substantive proposal change, both PASS results become stale. Freeze the revised candidate, rerun parent readiness, and recheck it through the same verifier context when available before requesting approval again.

If the user requests a purely mechanical change that conflicts with authoritative repository policy, preserve the authoritative repository semantics and explain the conflict. Do not ask the user to reconstruct the correct mechanical value. Request renewed approval only when the resulting proposal changes substantive ticket scope, acceptance obligations, preservation obligations, or blocking/dependency semantics.

## Fresh Spec Contract Coverage

For a fresh Spec that does not already have linked implementation tickets, the authoritative decomposition universe is the deterministic `$spec-contract` manifest.

Do not define ticket completeness from the obligations noticed during drafting.

### Recover the manifest

Use `$spec-contract` with the exact Spec, branch/baseline/HEAD state required by that skill. Under its `$to-tickets` decomposition exception, execute this build in the owning `$to-tickets` context; do not spawn a fresh model/subagent.

If the Spec Branch Rule has not yet established the durable branch/baseline needed to build the final contract, drafting may begin from the full Spec body, but **publication may not occur** until:

1. the complete Spec Branch Rule has succeeded;
2. `$spec-contract` returns `SPEC CONTRACT: VALID` for the publication state;
3. the proposed ticket breakdown is reconciled against that exact manifest;
4. any semantic change required by that reconciliation is returned to parent validation, independent certification, and the user approval step rather than silently added during publication.

Retain the exact Spec body hash and contract hash returned by `$spec-contract` for the coverage artifact.

## Spec Obligation Disposition Manifest

Create exactly one row for every Spec contract cell:

```text
Spec obligation: <US-* | ID-* | TD-* | OOS-* | other stable ID>
Requirement: <compact exact requirement>
Disposition: implementation-ticket | verification-only | no-implementation-work | authoritative-exclusion | deferred-conditional
Tickets: <one or more proposed ticket IDs/titles | None>
Reason/authority: <required for non-ticket dispositions>
```

Rules:

* `implementation-ticket` means one or more tickets carry responsibility to realize the obligation;
* `verification-only` means no new implementation is promised, but later verification must explicitly prove the obligation; state why implementation is unnecessary;
* `no-implementation-work` requires current evidence/authority that the Spec requirement is already realized or needs no repository/tracker mutation; convenience is insufficient;
* `authoritative-exclusion` requires an explicit Spec exclusion/out-of-scope authority and does not mean the requirement was forgotten;
* `deferred-conditional` follows **Conditional / Deferred Obligation Routing** above;
* one Spec cell may map to multiple tickets when the contract genuinely spans slices;
* a ticket may carry multiple Spec cells;
* do not merge distinct Spec cells merely because one implementation change may satisfy them;
* omission is never a disposition.

Before user approval require:

```text
Spec contract cells: <n>
Disposition rows: <n>
Unmapped cells: 0
Ambiguous cells: 0
Unclassified cells: 0
Implementation cells without ticket coverage: 0
Non-ticket dispositions without reason/authority: 0
```

If reconciliation changes ticket scope, acceptance criteria, blocking edges, or disposition semantics, update the proposal and return through parent readiness plus independent certification before requesting approval again under Step 4.

## Architecture / Design Obligation Coverage

Spec cells remain the primary decomposition universe, but they are not permission to drop an explicit architecture/design obligation that materially constrains the implementation slice and is not represented by its own Spec cell. For a fresh Spec proposal, close this second bounded source universe before final ticket wording and proposal readiness validation.

### Build the bounded source set

Start from architecture/design authority explicitly named by the Spec's Architecture Impact/readiness state and by the proposed tickets' Architecture context. Reduce to the exact sections/anchors materially required to implement those ticket slices; do not sweep unrelated architecture documents merely because they are linked somewhere in the repository.

Classify every materially normative obligation in that bounded source set that is not already completely represented by a Spec Contract cell:

```text
Architecture obligation: ARCHSRC-<n>
Source: <durable path/ADR/doc + section/anchor>
Requirement: <compact normative obligation>
Disposition: implementation-ticket | verification-only | deferred-existing-owner | not-applicable
Tickets/destination: <ticket(s) | durable existing owner | None>
Reason/authority: <required for non-ticket dispositions>
```

Rules:

* `implementation-ticket` obligations must be explicit in the mapped ticket's build/acceptance/preservation contract; a broad `Architecture context` citation is not sufficient coverage;
* `verification-only` requires an explicit later proof owner;
* `deferred-existing-owner` requires a durable existing ticket/Spec/lifecycle owner already established by authority; `$to-tickets` may not invent one to close the table;
* `not-applicable` requires exact source/scope authority;
* when one obligation is already fully represented by a Spec cell, record the Spec-cell reference instead of duplicating implementation responsibility;
* implementation shape, existing tests, and proposed ticket wording do not define the architecture-obligation universe.

Before proposal-readiness validation require:

```text
Bounded architecture/design sources: <n>
Material non-duplicated architecture obligations: <n>
Architecture disposition rows: <n>
Unmapped architecture obligations: 0
Ambiguous architecture obligations: 0
Implementation architecture obligations without ticket coverage: 0
Deferred obligations without durable existing owner: 0
```

Call this the **Architecture/Design Obligation Disposition Manifest**. `$to-tickets` owns closing this bounded source universe before proposal readiness. `$verify-ticket-decomposition` then independently challenges the exact closed universe and rendered proposal before human approval. Later `$verify-ticket-closure`, `$verify-spec`, and `$review-spec` independently revalidate applicable architecture/design semantics at their own downstream implementation/spec/review boundaries.

Extend the parent `## Ticket Coverage Manifest` with a compact `Architecture / Design Obligation Coverage` subsection containing each `ARCHSRC-*` source anchor, requirement, disposition, and ticket/destination. Preserve the exact current manifest body as durable decomposition authority and record enough stable source identity for downstream consumers to detect staleness. These rows are decomposition provenance, not new Spec Contract cells and not architecture decisions.

Before publication require every proposed ticket's `Architecture obligations` IDs to match exactly the `implementation-ticket` rows routed to that ticket. Missing, extra, stale, or duplicate IDs fail proposal readiness and invalidate independent certification.

## Decomposition Defect Reconciliation

`$to-tickets` is the sole owner of architecture/design decomposition defects.

A decomposition defect means current governing architecture/design contains a material implementation obligation that is absent from, incompletely represented by, or misrouted in the current parent Spec `Architecture/Design Obligation Disposition Manifest` or active ticket mapping.

### Source-owner routing

Resolve the public source before reconciliation:

* if no active conventional Spec Review currently owns remediation for the parent Spec, the canonical `<!-- decomposition-defects:v1 -->` record must be on the parent Spec and the public invocation is `$to-tickets #<Spec>`;
* if an active conventional Spec Review owns the remediation lifecycle, the canonical record must be on that Spec Review and the public invocation is `$to-tickets #<Spec Review>`;
* if invoked with a Spec while an active conventional Spec Review already owns the remediation lifecycle, fail closed and return the canonical `$to-tickets #<Spec Review>` handoff rather than creating competing decomposition state.

The defect record and the ticket-coverage artifact intentionally have different durable owners: the current `$to-tickets` source owns the unresolved `DD-*` record; the parent Spec owns the current `Ticket Coverage Manifest` and Architecture/Design Obligation Disposition Manifest.

### Canonical record

Consume exactly one machine-managed comment per current source artifact:

```text
<!-- decomposition-defects:v1 -->
## Decomposition Defects

### DD-<n>
Status: unresolved | reconciled | rejected
Discovery workflow: $verify-ticket-closure | $verify-spec | $review-spec | $verify-ticket-decomposition | other authorized owner
Discovery artifact: <durable identity>
Governing architecture/design source: <durable source + section/anchor>
Missing/misrouted obligation: <compact exact requirement>
Current manifest state: absent | incomplete | misrouted
Affected ticket coverage: <tickets | None>
Disposition owner: $to-tickets
Reconciliation: <None | ARCHSRC-* + ticket/destination + manifest reference | rejection reason>
```

Stable `DD-*` identities are append/reconcile state; omission is not resolution.

### Independent source validation

The report is a falsifier candidate, not authority. For every unresolved `DD-*`, re-read the cited architecture/design source and the bounded surrounding authority needed to interpret it, then compare it with the current parent-Spec Architecture/Design Obligation Disposition Manifest and ticket mappings. “Independent” here means source-independent from the report itself; this reconciliation does not itself spawn another model beyond the one required proposal verifier when a new proposal is being certified.

Classify each report exactly once:

```text
confirmed-decomposition-defect
rejected-no-decomposition-defect
unresolved-source-or-ownership
```

* `confirmed-decomposition-defect` → add or reconcile the missing `ARCHSRC-*` obligation in the complete bounded architecture/design universe, map it through the normal ticket/deferred/verification dispositions, supersede the parent manifest, and mark the `DD-*` reconciled only after exact persistence/readback;
* `rejected-no-decomposition-defect` → preserve the report and mark it rejected with exact authority/reason;
* `unresolved-source-or-ownership` → fail closed; do not publish speculative ticket scope.

Do not create one ticket per report automatically. Ticket slicing remains root/tracer-bullet driven. Multiple distinct architecture obligations may share one cohesive ticket or require separate tickets; each obligation must still have its own complete `ARCHSRC-*` disposition.

Closed historical tickets remain historical evidence. Missing work is reconciled forward through current open/new remediation tickets rather than reopening or rewriting a closed ticket.

### Shared downstream contract

Every current implementation ticket must carry:

```markdown
## Architecture obligations

<comma-separated ARCHSRC-* IDs, or `None` when the current manifest proves no direct architecture/design implementation obligation>
```

The parent Spec's current Architecture/Design Obligation Disposition Manifest is the shared routing/accounting artifact reused by `$verify-ticket-decomposition`, `$verify-ticket-closure`, `$verify-spec`, and `$review-spec`. Reuse is not blind trust: each independent semantic verifier/reviewer revalidates its applicable authority before relying on the manifest.

## Ticket Provenance

Every ordinary Implementation Ticket created from a Spec must contain:

```markdown
## Spec obligations

<comma-separated stable Spec contract IDs, or `None` only when the disposition manifest proves this ticket is intentionally supporting/mechanical work with no direct Spec cell>

## Architecture obligations

<comma-separated `ARCHSRC-*` IDs, or `None` only when the Architecture/Design Obligation Disposition Manifest proves the ticket carries no direct architecture/design implementation obligation>
```

The IDs are exact provenance, not a replacement for good ticket acceptance criteria.

The ticket must still describe the end-to-end behavior it delivers and carry acceptance criteria sufficient to implement its slice without delegating material design to `$implement-ticket`.

When a ticket supports another ticket mechanically without directly realizing a Spec cell, `Spec obligations: None` requires an explicit row/reason in the coverage manifest showing why the supporting ticket exists and which covered ticket(s) depend on it.

Do not infer Spec obligation IDs later from changed files or implementation notes.

## Parent Coverage Artifact

After publishing the approved fresh ticket set and native relationships, persist one durable machine-readable-enough coverage record on the parent Spec.

Use one comment headed:

```text
## Ticket Coverage Manifest
```

Include:

```text
Spec Body Hash: <hash>
Spec Contract Hash: <hash>
Spec branch: <branch>

<Cell ID> → <implementation ticket(s) | verification-only | no-implementation-work | authoritative-exclusion | deferred-conditional> — <reason/trigger/destination when required>
...

Spec contract cells: <n>
Mapped: <n>
Unmapped: 0
Ambiguous: 0
Material design choices delegated to implementation: 0
```

Persist it once per approved decomposition state. If ticket semantics are later changed through an authorized workflow, that owner must supersede/reconcile the manifest rather than leaving contradictory active coverage records.

The manifest is provenance and coverage authority for decomposition. It is **not** proof that a ticket implementation later passed.

## Publication Integrity

Immediately before Step 5 publication, require all of the following together:

* source Spec/remediation authority is still implementation-ready;
* the Parent Spec Contract Coherence Gate still passes for the exact current contract identity and current TCM when one exists;
* exact approved ticket proposal still matches planned semantics;
* the latest `TICKET PROPOSAL READINESS: PASS` binds to the exact approved proposal identity and current source state;
* the latest `TICKET DECOMPOSITION: PASS` from `$verify-ticket-decomposition` binds to that same exact proposal identity and current source/root state;
* Spec Branch Rule passed;
* `$spec-contract` manifest still matches retained body/contract hashes when applicable;
* Spec Obligation Disposition Manifest is complete when applicable;
* Architecture/Design Obligation Disposition Manifest is complete when applicable, with missing/ambiguous obligations 0;
* every ticket's `Spec obligations` and `Architecture obligations` sets equal their approved mappings when applicable;
* material design choices delegated to implementation remain zero;
* blocking edges/hierarchy still match the approved proposal.

A changed proposal, source contract/root/readiness state, branch/baseline authority, Spec body/contract, or source identity invalidates parent readiness, independent certification, and approval as applicable.

Do not publish tickets and promise to reconcile the coverage manifest or proposal correctness afterward.

## Downstream Contract

The durable chain is:

```text
frozen planning/design contract
    ↓
Spec contract cell + architecture/design source units
    ↓
parent-owned TICKET PROPOSAL READINESS
    ↓
independent $verify-ticket-decomposition certification
    ↓
human approval of the exact publication-ready proposal
    ↓
tracker publication + exact publication readback
    ↓
Ticket Coverage Manifest + Implementation Ticket obligation IDs
    ↓
$implement-ticket Proposed Closure Evidence
    ↓
independent $verify-ticket-closure certification
    ↓
$verify-spec integrated semantic certification
    ↓
$review-spec independent adversarial review
```

Ticket decomposition certification does not certify implementation. Ticket certification does not prove the complete Spec; `$verify-spec` remains responsible for integrated closure.

## Base Template Extension

For ordinary Spec tickets, insert `## Spec obligations` and `## Architecture obligations` after `## Parent` and before Architecture context / What to build.

For remediation tickets, preserve the remediation template and Root Blocker contract. When exact originating Spec cell IDs are available from the cumulative remediation state, they may be carried as provenance, but the Root Blocker acceptance universe remains authoritative for remediation.

## Procedure

Break an explicit plan, spec, review, or other invocation source into **tickets** — tracer-bullet vertical slices, each declaring the tickets that **block** it.

The issue tracker and triage label vocabulary should have been provided — run `$setup-matt-pocock-skills` if not.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting.

Prior-session summaries or remembered conclusions are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it.

## Process

### 1. Gather Context

Work from the explicit invocation source and recover its durable tracker/repository state.

If the user passes a spec path, issue number, or URL, fetch and read its full body and comments.

If the source is a Spec, use its **Architecture Impact** as routing context. Carry forward only the affected entities and governing ADR/doc references relevant to each ticket.

If the source Spec declares itself not implementation-ready, contains an unresolved material design/public-contract question, or still contains an unresolved material architecture question, halt with a Human Handoff. Do not resolve those choices here.

Before that handoff, apply the cross-skill Fresh-Session Durability Gate. If the exact readiness blocker is not already recoverable from the invoked durable planning artifact, persist it there and verify readback before stopping.

> ⚠️ **Ticket creation is blocked by unresolved upstream design/architecture.**
>
> Return to the owning Spec/planning workflow and resolve the listed readiness blocker before `$to-tickets` continues.

A Blocking Architecture finding in a Spec Review issue is not itself unresolved architecture. `$to-remediation-tickets` owns that routing.

#### Project Delivery Actionability Guard

Before ticket drafting, remediation reconciliation, branch setup, or any tracker/repository mutation for a Wayfinder-managed Spec, prove that the underlying Spec is currently in the actionable Spec frontier.

If the invocation source is a `Spec Review: ` issue, first recover its exact `**Parent Spec:** #<n>` and apply this guard to that Spec. Otherwise use the source Spec itself.

A Spec is **Wayfinder-managed** when durable provenance/handoff evidence identifies one or more governing Wayfinders through:

* its canonical `wayfinder-source` marker;
* one or more `wayfinder-remediation` markers; or
* an unambiguous matching `Derived Spec` / `Remediation Spec` entry on a canonical Wayfinder map.

Do not invent a governing Wayfinder. An intentionally non-Wayfinder Spec continues through the existing lifecycle and is not enrolled into project focus merely because `$to-tickets` was invoked.

For a Wayfinder-managed Spec:

1. require the Spec issue to be open;
2. read its complete native `blocked by` relationship set and fail closed if blocker data is truncated/unreadable;
3. if any direct blocker is open, stop before substantive work and report the Spec as dependency-blocked;
4. recover every currently governing Wayfinder from durable provenance/handoff evidence; ambiguity in governance fails closed and routes back to `$to-specs` for reconciliation rather than guessing;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for each governing Wayfinder;
7. require at least one governing Wayfinder to return `PROJECT DELIVERY GUARD: ALLOWED`.

If no governing Wayfinder is allowed, stop before substantive work. Surface the exact governing maps, their guard results, current focus, and the explicit human `$project-delivery-management` focus/switch/parallel choices. `$to-tickets` must never establish, switch, or broaden focus itself.

A closed blocker satisfies the Spec dependency only because its authoritative Spec lifecycle is complete. Ticket completion, verification readiness, review passage, `Ready to Merge`, Priority, Project fields, issue order, or handoff order do not satisfy the dependency. If a blocker Spec is reopened, the unchanged native edge makes this guard fail again automatically.

Passing this guard does not create an active-Spec scheduler. Multiple independent open/unblocked Specs governed by the same focused Wayfinder may each be ticketed in separate sessions.

### 2. Explore the Codebase

If needed, inspect the current codebase before slicing.

Use project domain vocabulary and respect applicable ADRs.

Look for useful prefactoring: make the change easy, then make the easy change.

### Existing-Spec Manifest Reconciliation

This section is entered through **Mandatory Mode Preflight — Run Before All Other Composition**. Do not repeat already-complete preflight discovery, architecture archaeology, or historical-causation searches after entering this mode.

Before routing an ordinary Spec with existing linked implementation tickets into `$to-remediation-tickets`, first determine whether the invocation is a **manifest-reconciliation-only** repair.

This path exists for cases where implementation/ticket semantics are already complete but the parent Ticket Coverage Manifest or decomposition bookkeeping is mechanically inconsistent with the exact current `$spec-contract` universe.

It is legal only when deterministic reconstruction proves all of the following:

```text
Source artifact is an ordinary Spec: yes
Current $spec-contract: VALID
Current Ticket Coverage Manifest: exactly one
Source Spec-cell IDs recovered: <n>
Linked ticket set recovered exactly: yes
Linked ticket body/lifecycle/native-relationship snapshot complete: yes

Missing source-derived Spec cells after reconstruction: 0
Extra/non-source-derived TCM cells to remove: <n>
Legitimate source-derived routing rows changed: 0
Existing linked-ticket Spec-obligation mappings changed: 0
Existing linked-ticket Architecture-obligation mappings changed: 0
Ticket acceptance/verification/preservation semantics changed: 0
Ticket dependency/blocking semantics changed: 0
Ticket labels/status/lifecycle state changed: 0
Ticket branch/baseline metadata changed: 0
New implementation/remediation work required: 0
Tickets to create: 0
Tickets to update: 0
Tickets to close/reopen: 0
```

Reconstruct the proposed manifest from:

1. the exact current `$spec-contract` cell universe;
2. the exact existing linked-ticket `Spec obligations` / `Architecture obligations` provenance and native relationships;
3. only source-derived non-ticket dispositions that already have valid durable authority;
4. the current valid architecture/design source inventory and routing;
5. deterministic current hashes/counts/identities required by the manifest format.

For every source cell, require the reconciled destination/disposition to equal the already-valid source-derived routing. Removing a row whose ID is not in the current `$spec-contract` is allowed; inventing, reclassifying, or rerouting a real source cell is not manifest-only reconciliation.

Preserve every legitimate ticket mapping exactly. Closed tickets are immutable historical contracts for this path. Do not regenerate their bodies, create replacement tickets, reopen them, rewrite them, or translate their completed work into new remediation tickets.

When the eligibility witness above passes, the only allowed durable mutations are:

* superseding/reconciling the parent `## Ticket Coverage Manifest` so its exact Spec-cell ID set equals the current `$spec-contract`;
* deterministic manifest identities/counts/hashes needed by that reconciliation;
* reconciling the applicable `<!-- decomposition-defects:v1 -->` record after successful exact readback.

This is deterministic metadata/decomposition normalization. It does **not** invoke `$to-remediation-tickets`, does not require a new ticket proposal, does not require human approval, and does not require `$verify-ticket-decomposition` because no ticket or routing semantics may change.

Before mutation emit internally:

```text
MANIFEST RECONCILIATION READINESS: PASS
Spec: <identity>
Source cells: <n>
Reconciled TCM cells: <n>
Missing source-derived cells: 0
Extra/non-source-derived cells removed: <n>
Legitimate routing changes: 0
Ticket semantic mutations: 0
Ticket lifecycle/relationship mutations: 0
New remediation work: 0
Allowed mutation surface: parent TCM + decomposition-defect bookkeeping only
```

If **any** eligibility line is non-zero, unknown, or would require changing a real source-cell disposition, ticket body, acceptance/preservation/verification obligation, dependency, lifecycle state, or implementation destination, manifest-only reconciliation is illegal. Fall through to the normal existing-ticket remediation path and its proposal/readiness/independent-certification/human-approval rules.

After manifest-only mutation:

1. re-read the parent TCM and require exact source/TCM Spec-cell set equality and exact expected valid routing;
2. re-read every linked ticket body, lifecycle state, native parent, and blocking relationship and require equality with the pre-reconciliation snapshot;
3. require created/updated/closed/reopened tickets = 0;
4. only then mark the applicable decomposition defect reconciled;
5. re-read that defect record exactly.

A failed readback restores the defect to unresolved and blocks downstream handoff; do not convert the failure into ticket regeneration.

### 3. Resolve Ticket Mode

Before drafting:

* source title prefixed `Spec Review: ` → invoke `$to-remediation-tickets`;
* ordinary Spec with linked implementation tickets and `MANIFEST RECONCILIATION READINESS: PASS` → execute **Existing-Spec Manifest Reconciliation** above and do not invoke `$to-remediation-tickets`;
* existing Spec with linked implementation tickets that does not qualify for manifest-only reconciliation → invoke `$to-remediation-tickets`;
* otherwise → fresh vertical-slice drafting.

`$to-remediation-tickets` owns:

* remediation delta analysis;
* duplicate prevention;
* open-ticket updates;
* superseded-ticket detection;
* Root Blocker reconciliation;
* remediation, verification, and preservation obligations;
* determining which new tickets are required.

If `$to-remediation-tickets` returns one or more **architecture-blocked roots**, halt with a Human Handoff to the parent Spec review lifecycle. The returned Root Blocker state is already durable review/remediation authority; do not replace it with conversational context.

> ⚠️ **Ticket remediation is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $review-spec - <Parent Spec Title> (<Spec URL>)
> ```
>
> **Architecture blockers:**
>
> 1. **RB-<n> — <question/conflict>**
>    * Governing authority: <authority>
>    * Evidence: <concise evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/conflict>

Use the actual parent Spec title and URL. Do not continue ordinary ticket remediation while an architecture-blocked root remains.

If it returns a delta, treat each returned ticket block as the authoritative semantic input for Step 4. You may improve presentation, but do not condense, reclassify, merge, or omit any returned remediation, verification, preservation, root-complete sweep, dependency, or metadata obligation.

Do not discard or collapse Root Blocker preservation obligations merely because they require no new implementation.

If it returns an empty delta, do not hand off to implementation yet. First complete **Architecture Readiness Saturation and Remediation Human Handoff** over the full applicable existing-ticket reconciliation universe. Any `architecture-blocked` or `upstream-readiness-deferred` result supersedes the empty-delta implementation handoff and must be handled by that saturation contract.

Only when every applicable existing ticket is `design-ready` may the empty-delta path report that the current ticket set already represents the source, identify the applicable open/frontier ticket, and halt with a Human Handoff:

> ✅ **No ticket changes are required.**
>
> Please continue with:
>
> ```
> $implement-ticket - <Frontier Ticket Title> (<Ticket URL>)
> ```

If multiple frontier tickets are available, present one copy-ready `$implement-ticket` line per ticket and let the user choose.

Then stop.

#### Fresh Vertical Slices

Break the work into **tracer-bullet** tickets.

<vertical-slice-rules>

* Each slice cuts a narrow but complete path through the required layers.
* A completed slice is independently demoable or verifiable.
* Each slice fits in one fresh context window.
* Necessary prefactoring comes first.

</vertical-slice-rules>

Give each ticket its **blocking edges**.

**Wide refactors are the exception.** When one mechanical change fans across the codebase and individual vertical slices cannot stay green, use expand–contract: expand first, migrate callers in manageable batches, then contract after all migrations complete.

Before proposal freeze, perform the **Design Delegation Guard** above and require `$attention` to return no unresolved design-gap finding.

### 4. Quiz the User

Present only a proposal that has passed both **Proposal Readiness Validation** and the **Independent Ticket Decomposition Gate** above, except for deterministic metadata-only normalization allowed below.

Present the proposed fresh breakdown or remediation delta.

If the delta contains **only deterministic required ticket/decomposition metadata normalization** and does not change ticket scope, acceptance criteria, preservation obligations, blocking edges, dependencies, labels, lifecycle state, or any real source-cell routing, skip user approval and continue directly to Step 5. This includes an eligible **Existing-Spec Manifest Reconciliation** above. For a metadata-only delta, independent semantic recertification is unnecessary only when deterministic comparison proves there is no semantic candidate change.

For fresh Spec tickets, present a **publication-ready proposal**. The approval surface must show the exact semantic ticket bodies that were frozen, hashed, parent-validated, and independently certified—not a summary standing in for those bodies.

For each proposed fresh ticket show:

* **Title**;
* **Parent / native parent**;
* **Spec obligations**;
* **Architecture obligations**;
* **Architecture context**;
* **What to build**;
* **Acceptance criteria**;
* **Blocked by**;
* **Ticket branch**;
* **Ticket baseline**;
* **Required label/status**;
* any other semantic section that will actually be published for that ticket.

A compact `What it delivers` or dependency summary may precede the ticket bodies for readability, but it never substitutes for the publication-ready bodies. Do not ask the user to approve a ticket contract whose acceptance criteria, routed provenance, or other material semantic wording is hidden from the approval surface.

The fresh-ticket bodies shown for approval must be the same bodies bound to the proposal identity, Ticket Semantic Carry Matrix, and independent decomposition PASS, and must be the bodies published after approval except for deterministic alias-to-tracker-ID substitution required to realize newly created tickets. If any shown body, dependency, label/status, branch/baseline metadata, or publication action changes semantically after presentation, the prior approval and independent PASS do not cover the change; freeze and validate the revised proposal and request approval again when required by this workflow.

Keep validation machinery compact. Do not dump the complete Spec disposition table, Architecture / Design Source Inventory, normative source-unit rows, or Ticket Semantic Carry Matrix merely because the publication-ready ticket bodies must be visible. Show their required readiness/coverage summaries, while exposing the exact human-authorized ticket contracts in full.

For Spec Review remediation tickets, present a **publication-ready proposal**. For each ticket show:

* **Title**;
* **Root Blocker**;
* **Blocked by**;
* **Remediation obligations / What it delivers**;
* **Verification obligations**;
* **Preservation obligations**;
* **Root-complete sweep required for closure**;
* **Ticket branch**;
* **Ticket baseline**;
* **Required label/status**.

Use `None` where a category has no obligations. Do not summarize away, merge, reclassify, or omit any obligation returned by `$to-remediation-tickets`. The proposal must contain everything needed to publish the ticket correctly without additional semantic interpretation after approval.

For remediation, also show any:

* open tickets to update;
* open tickets to close as superseded;
* dependency changes.

Before requesting approval for Spec Review remediation, verify:

* every unresolved Root Blocker returned by `$to-remediation-tickets` has the required ticket coverage;
* every remediation obligation appears in the proposed ticket;
* every verification obligation is explicitly identified as verification rather than implementation;
* every applicable satisfied same-root cell appears under Preservation obligations;
* the root-complete sweep is explicit;
* blocking edges and dependency changes match the returned delta;
* no closed ticket is being reopened or rewritten;
* `Ticket branch`, `Ticket baseline`, and required label/status are shown;
* architecture-blocked roots, if any, halted ordinary publication instead of appearing as ordinary tickets;
* no material design/public-contract choice is delegated to implementation.

If any check fails, correct the proposal before presenting it to the user and return through independent certification. Do not rely on the user to discover omissions or repair the remediation contract during approval.

For any delta that is not metadata-only deterministic normalization, after matching parent readiness PASS and independent decomposition PASS ask only for substantive approval and end with:

> **Reply `approve` to publish exactly as proposed.** Otherwise, tell me any substantive change you want.

Iterate until approved.

An unqualified `yes`, `approved`, or equivalent approves the proposal exactly as presented.

After approval, do not add, remove, merge, split, reinterpret, or reclassify ticket semantics. If a semantic defect is discovered during publishing, return to drafting/readiness validation/independent certification/Step 4 approval instead of silently repairing it.

### Pre-Publication Spec Branch Guard

After approval and before any mutation in Step 5, execute the complete **Spec Branch Rule** below through Step 4. Treat that rule as a hard precondition to publication even though its procedure is documented later in this file.

Do not create, update, close, label, parent, or change dependencies for any ticket until branch identity, local/remote branch state, upstream tracking, GitHub Development linkage **or the qualified legacy pre-existing branch reconciliation below**, and Spec baseline metadata have all been verified or persisted as required by that rule.

If any Spec Branch Rule check fails, halt before Step 5 with zero ticket-publication mutations. Do not weaken, bypass, or defer the guard merely because an existing branch is otherwise usable.

After the guard succeeds, continue to Step 5. Do not execute branch setup a second time in the same uninterrupted invocation; reuse the verified branch/baseline state.

### 5. Publish to the Configured Tracker

Apply only the approved changes, or deterministic metadata-only normalization authorized by Step 4.

For **Existing-Spec Manifest Reconciliation**, this publication authority is narrower than the ordinary bullets below: mutate only the parent TCM and applicable decomposition-defect bookkeeping. Ticket creation/update/closure/reopen, ticket body mutation, native relationship mutation, label/status mutation, and dependency mutation are forbidden.

Otherwise:

* **Local files** → create new ticket files and update or retire existing ones as required.
* **Real issue tracker** → create new issues and apply approved updates or closures to existing open tickets.

For tracker publication, render each issue body as raw multiline UTF-8. Never assemble structural Markdown by inserting serialized escape separators such as literal `\n` where real line breaks are required. For GitHub CLI/API workflows, prefer a body file / raw-file input (`--body-file`, `jq -Rs`, or exact equivalent) over manually double-escaped body fragments.

Use native parent/child and blocking relationships where supported. For GitHub, invoke `$github-issue-dependencies` for relationship operations.

The native parent is the artifact **directly decomposed by this `$to-tickets` invocation**:

* ordinary Spec ticketing → the Spec is the native parent of its Implementation Tickets;
* Spec Review remediation → the Spec Review is the native parent of its Review Remediation Tickets.

Do not use transitive provenance as native hierarchy. In particular, the originating Spec remains the branch/baseline and lifecycle provenance owner for remediation, but it is **not** the native parent of tickets created from a Spec Review. A Spec Review is likewise lifecycle provenance for the Spec, not an implementation child of the Spec.

New tickets must:

* record lineage according to ticket mode:
  * ordinary Spec ticket → `Parent Spec: #<spec_issue_number>`;
  * Spec Review remediation ticket → `Remediation parent: Spec Review #<review_issue_number>` and `Parent Spec: #<spec_issue_number>`;
* use the direct decomposition artifact above as the native GitHub parent;
* carry applicable Architecture context;
* use the shared **Ticket branch**;
* declare **Ticket baseline** as `Pending`;
* receive correct blocking relationships;
* receive `ready-for-agent` only when the source/ticket remains implementation-ready after the final pre-publication guard.

For Spec Review remediation, publish the Root Blocker contract returned by `$to-remediation-tickets` without weakening it:

* open/regressed implementation obligations → acceptance criteria;
* verification-only obligations → explicit verification criteria when applicable;
* satisfied same-root cells → preservation obligations;
* root-complete invariant sweep → closure criterion.

Do not convert preservation obligations into new implementation requirements.

Do not omit them because prior tickets are closed or the cells are currently satisfied.

When updating an existing open ticket, preserve valid execution metadata and add `Ticket baseline: Pending` when the field is missing. Never replace an existing pinned baseline SHA.

Do not reopen or rewrite closed tickets to represent newly required work.

Do not close or modify the parent Spec issue except through the owning upstream workflow.

### Post-Publication Exact Readback Gate

After all approved ticket/body/relationship/label/coverage mutations are applied and before any implementation handoff, derive the exact expected durable tracker state from the approved proposal plus only deterministic realization substitutions required by publication, such as approved ticket aliases becoming actual issue numbers/URLs or native relationship IDs.

Re-read every created or updated ticket and every affected native relationship from the tracker. Normalize only line endings (`CRLF` → `LF`) for body comparison. Do not trim, reflow, reinterpret, or semantically normalize Markdown.

For every created/updated ticket require exact agreement with the expected durable state for:

* title;
* complete issue body after allowed deterministic alias/ID substitution;
* direct/native parent and durable lineage;
* `Spec obligations` and `Architecture obligations`;
* Architecture context;
* What to build / remediation obligations;
* all acceptance, verification, preservation, and root-complete criteria;
* `Blocked by` body text and native blocked-by set;
* `Ticket branch`;
* `Ticket baseline`;
* required labels/status/lifecycle state.

Explicitly fail readback when any structural section contains serialized escape text in place of required formatting, including literal `\n` sequences used as line separators in `Blocked by` or another Markdown section.

For a fresh Spec, re-read the parent `## Ticket Coverage Manifest` and require exactly one active current manifest for the approved decomposition state. Require its Spec/body/contract identities, ticket mappings, architecture/design source identities/anchors/dispositions, architecture-obligation routing, deferred/exclusion rows, and closure counts to equal the expected approved realization.

For **Existing-Spec Manifest Reconciliation**, additionally require:

```text
Source/TCM Spec-cell ID sets equal: yes
Missing source-derived cells: 0
Extra/non-source-derived cells: 0
Legitimate source-derived routing changes: 0
Linked ticket body/lifecycle/native-relationship mutations: 0
Tickets created/updated/closed/reopened: 0
```

Compare the linked-ticket post-state to the exact pre-reconciliation snapshot, not to a newly rendered ticket proposal.

For remediation, re-read every durable remediation/root coverage artifact changed by publication and require the same exact approved semantics.

Return one internal result:

```text
TICKET PUBLICATION READBACK: PASS
Ticket bodies: <n>/<n> exact
Native parent/lineage: valid
Blocking edges: valid
Labels/status: valid
Coverage manifest: exact
Structural escape/rendering defects: 0
```

or:

```text
TICKET PUBLICATION READBACK: FAIL
Findings:
1. <exact durable mismatch>
...
```

A deterministic publication/rendering/metadata mismatch may be repaired without renewed human approval only when exact comparison proves the repair makes durable state equal to the already approved candidate and changes no semantics, dependency meaning, lifecycle state, or ticket scope. Re-read after every repair until PASS.

If any required repair would change ticket semantics, acceptance/preservation/verification obligations, routing, dependency meaning, or another human-approved substantive element, do not silently repair it. Return to proposal construction, parent readiness, `$verify-ticket-decomposition`, and Step 4 approval for the revised candidate.

Do not emit an `$implement-ticket` handoff until `TICKET PUBLICATION READBACK: PASS` is current for the published state.

### Architecture and Design Readiness Language

Scope ticket readiness claims to what the current Spec, review state, and accepted decisions actually establish.

When architecture and material design dependencies for a ticket are resolved, prefer language such as:

> All architecture and material design decisions currently required by this ticket are accepted; no known implementation-readiness blocker remains unresolved.

Do not write absolute claims such as:

* `no architecture/design decision remains unresolved`;
* `architecture/design is fully resolved`;
* `all design is settled`;
* equivalent language implying implementation cannot expose another material blocker.

Ticket readiness means **no known architecture or material design blocker currently prevents this ticket from starting**.

It does not waive `$implement-ticket`'s obligation to halt on a newly discovered material architecture/design blocker or its proactive Attention duty.

More generally, state only what the workflow has established. Do not turn current evidence into broader or final claims.

<local-ticket-template>

# <NN> — <Ticket title>

**Root blocker:** for Spec Review remediation tickets only, `RB-<n>` and the stable root invariant this ticket closes. Omit otherwise.

**Architecture context:** affected entities and governing ADR/doc references relevant to this ticket, or "None". Do not copy invariant text. Scope any readiness statement according to **Architecture and Design Readiness Language**.

**What to build:** the end-to-end behaviour this ticket makes work. It must execute the frozen upstream contract rather than delegate a material design choice.

**Blocked by:** ticket numbers/titles, or "None — can start immediately".

**Ticket branch:** the shared branch for this Spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch, or "None".

**Ticket baseline:** Pending

**Status:** ready-for-agent

* [ ] Acceptance criterion 1
* [ ] Acceptance criterion 2
* [ ] For Spec Review remediation: the required production-path, negative/fail-closed, and root-complete invariant proof is established.

**Preservation obligations:** for Spec Review remediation only, list the satisfied same-root acceptance obligations that must remain satisfied while this ticket changes shared root surfaces. Omit otherwise.

</local-ticket-template>

<issue-template>

## Parent

For an ordinary Implementation Ticket:

```text
Parent Spec: #<spec_issue_number>
```

For a Review Remediation Ticket:

```text
Remediation parent: Spec Review #<review_issue_number>
Parent Spec: #<spec_issue_number>
```

The first line identifies immediate decomposition ownership. `Parent Spec` on a remediation ticket is transitive lifecycle provenance and branch/baseline ownership only; do not use it as the native GitHub parent.

## Spec obligations

For an ordinary Implementation Ticket, list the exact stable Spec contract IDs mapped to this ticket by the approved Spec Obligation Disposition Manifest. Use `None` only for an intentionally supporting/mechanical ticket whose no-direct-cell role is explicitly justified by that manifest.

For a Review Remediation Ticket, this section is optional provenance when exact originating Spec cell IDs are available; the Root Blocker acceptance universe remains authoritative.

## Architecture obligations

For an ordinary Implementation Ticket, list the exact `ARCHSRC-*` IDs mapped to this ticket by the current Architecture/Design Obligation Disposition Manifest, or `None` when that manifest proves this ticket carries no direct architecture/design implementation obligation.

For a Review Remediation Ticket, preserve the architecture/design obligation mapping returned by the current remediation/decomposition authority when applicable.

## Root blocker

For Spec Review remediation tickets only: `RB-<n>` and the stable root invariant this ticket closes. Omit otherwise.

## Architecture context

Affected entities and governing ADR/doc references relevant to this ticket, or "None". Do not copy invariant text. Scope any readiness statement according to **Architecture and Design Readiness Language**.

## What to build

The end-to-end behaviour this ticket makes work. Do not leave a material public/domain/downstream contract for `$implement-ticket` to choose.

## Acceptance criteria

* [ ] Criterion 1
* [ ] Criterion 2
* [ ] For Spec Review remediation: required production-path and negative/fail-closed proof is complete, and the root-complete invariant sweep establishes every active non-satisfied obligation or explicitly reports remaining `unproven` verification work.

## Preservation obligations

For Spec Review remediation only, list the currently satisfied same-root acceptance obligations returned by `$to-remediation-tickets` that must remain satisfied.

These are not new implementation work. They define established behavior that remediation must not regress.

Omit this section for ordinary tickets.

## Blocked by

References to blocking tickets, or "None — can start immediately".

## Ticket branch

The shared branch for this Spec, normally `spec-<spec_issue_number>`, an explicitly overridden shared branch, or "None".

## Ticket baseline

Pending

</issue-template>

Avoid specific file paths or code snippets unless a prototype produced a decision-rich snippet materially clearer than prose.

For Spec Review remediation, semantic Root Blocker surface/reference families and acceptance obligations are durable ticket context and should be preserved even when concrete implementation files may change.

### Ticket Baseline

`Ticket baseline` is a per-ticket verification anchor, not the Spec baseline.

Publish every new ticket with `Ticket baseline: Pending`.

`$implement-ticket` replaces `Pending` exactly once with the full current `HEAD` before the ticket's first file mutation, then reuses that persisted SHA across resumed sessions.

Never initialize a ticket baseline from the fixed Spec baseline or another ticket's baseline.

Work the frontier one ticket at a time with `$implement-ticket`, clearing context between tickets.

## Spec Branch Rule

The **Pre-Publication Spec Branch Guard** executes this complete section before Step 5. When this section is reached later in document order during the same uninterrupted invocation, reuse the already verified branch/baseline state rather than rerunning setup. On a resumed invocation, re-run the guard before any new Step 5 mutation.

All tickets for a Spec — initial, Spec Review remediation, or amended-Spec delta — use the same Spec branch and fixed Spec baseline.

Each ticket has its own `Ticket baseline`.

The Spec branch is a durable GitHub development branch, not a local-only workspace convenience. On first use, `$to-tickets` owns creating it on `origin`, linking it to the originating Spec's GitHub Development section, and establishing the local upstream. Later ticketing/remediation reuses that same linked branch. A historical Spec branch that already existed on `origin` before this linkage rule may use the narrow legacy reconciliation below when GitHub exposes no supported operation for attaching that already-existing branch; this does not weaken the first-use rule for new branches.

The originating Spec's branch/baseline ownership does not make it the native parent of Spec Review remediation tickets. Native hierarchy follows direct decomposition ownership from Step 5.

### 0. Resolve the Spec Issue Number

If the source is a `Spec Review: ` issue, recover the original Spec from its exact body line:

```text
**Parent Spec:** #<n>
```

Otherwise the source Spec issue is the Spec issue.

```bash
INPUT_ISSUE_NUMBER=<input issue number>
INPUT_ISSUE_TITLE=$(gh issue view "$INPUT_ISSUE_NUMBER" --json title -q .title)

case "$INPUT_ISSUE_TITLE" in
  "Spec Review: "*)
    spec_issue_number=$(gh issue view "$INPUT_ISSUE_NUMBER" --json body -q .body \
      | grep -oP '(?<=\*\*Parent Spec:\*\* #)\d+')

    if [ -z "$spec_issue_number" ]; then
      echo "❌ Could not resolve the parent Spec issue. Halting."
      exit 1
    fi
    ;;
  *)
    spec_issue_number="$INPUT_ISSUE_NUMBER"
    ;;
esac
```

### 1. Resolve Branch Identity

```bash
SPEC_BRANCH="spec-$spec_issue_number"
```

### 2. Capture Spec Baseline for First Use

```bash
BASELINE_COMMIT=$(git rev-parse main)
```

This value is used only if the Spec branch does not already exist.

### 3. Create or Reuse the Spec Branch

Require a clean worktree before branch setup. Do not carry unrelated work across this checkout.

Determine local and remote branch existence once:

```bash
LOCAL_BRANCH_EXISTS=false
REMOTE_BRANCH_EXISTS=false

git show-ref --verify --quiet "refs/heads/$SPEC_BRANCH" \
  && LOCAL_BRANCH_EXISTS=true

git ls-remote --exit-code --heads origin "$SPEC_BRANCH" >/dev/null 2>&1 \
  && REMOTE_BRANCH_EXISTS=true
```

On first use, neither branch exists. Require local `main` to match `origin/main`, then create the remote branch through GitHub's issue-development boundary so branch creation and Spec linkage happen together:

```bash
if [ "$LOCAL_BRANCH_EXISTS" = false ] && [ "$REMOTE_BRANCH_EXISTS" = false ]; then
  git fetch origin main
  REMOTE_MAIN=$(git rev-parse origin/main)

  if [ "$BASELINE_COMMIT" != "$REMOTE_MAIN" ]; then
    echo "❌ Local main does not match origin/main. Synchronize main before creating the Spec branch."
    exit 1
  fi

  gh issue develop "$spec_issue_number" \
    --name "$SPEC_BRANCH" \
    --base main \
    --checkout

  git push -u origin "$SPEC_BRANCH"
elif [ "$LOCAL_BRANCH_EXISTS" = true ] && [ "$REMOTE_BRANCH_EXISTS" = true ]; then
  git checkout "$SPEC_BRANCH"
  git branch --set-upstream-to="origin/$SPEC_BRANCH" "$SPEC_BRANCH"
elif [ "$LOCAL_BRANCH_EXISTS" = false ] && [ "$REMOTE_BRANCH_EXISTS" = true ]; then
  git fetch origin "$SPEC_BRANCH"
  git checkout -b "$SPEC_BRANCH" --track "origin/$SPEC_BRANCH"
else
  echo "❌ Local Spec branch exists without its required remote linked branch. Reconcile branch publication/linkage before continuing."
  exit 1
fi
```

Do not create another branch for remediation or amended-Spec ticket deltas. Do not silently fall back to a local-only branch if `gh issue develop`, the remote push, or Development linkage is unavailable.

#### Legacy pre-existing branch reconciliation

A **legacy pre-existing Spec branch** may lack GitHub Development linkage only when the exact `spec-<spec_issue_number>` branch already existed on `origin` before this invocation and current GitHub tooling exposes no supported operation for attaching that already-existing branch. This is a narrow reconciliation path for historical repository state; it is not an alternate branch-creation path.

When Development linkage is absent for an already-existing remote branch, require all of the following before publication:

* the branch name is exactly `spec-<spec_issue_number>`;
* local branch identity and upstream tracking resolve exactly to `origin/$SPEC_BRANCH`;
* the originating Spec contains exactly one `## Workspace Metadata` comment;
* that single comment records exactly `**Branch:** $SPEC_BRANCH` and one full 40-character `**Baseline Commit Hash:** <sha>`;
* the recorded baseline commit exists and is an ancestor of the current Spec branch;
* `gh issue develop --list "$spec_issue_number"` returns no conflicting linked branch;
* the remote branch existed before the current invocation.

If any condition fails, halt. Never delete/recreate, rename, or replace a durable existing Spec branch merely to manufacture Development linkage. Every newly created Spec branch continues to require `gh issue develop` so creation and linkage occur together.

Verify branch identity, upstream, and Development linkage or qualified legacy reconciliation before continuing:

```bash
if [ "$(git branch --show-current)" != "$SPEC_BRANCH" ]; then
  echo "❌ Expected Spec branch $SPEC_BRANCH is not checked out."
  exit 1
fi

if [ "$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)" != "origin/$SPEC_BRANCH" ]; then
  echo "❌ Spec branch is not tracking origin/$SPEC_BRANCH."
  exit 1
fi

LINKED_BRANCHES=$(gh issue develop --list "$spec_issue_number")
LEGACY_PREEXISTING_BRANCH=false

if grep -Fq "$SPEC_BRANCH" <<<"$LINKED_BRANCHES"; then
  :
elif [ "$REMOTE_BRANCH_EXISTS" = true ]; then
  if [ -n "$(printf '%s' "$LINKED_BRANCHES" | tr -d '[:space:]')" ]; then
    echo "❌ Parent Spec has conflicting GitHub Development linkage; expected $SPEC_BRANCH."
    exit 1
  fi

  WORKSPACE_METADATA=$(gh issue view "$spec_issue_number" --json comments -q \
    '[.comments[].body | select(contains("## Workspace Metadata"))] | if length == 1 then .[0] else "" end')

  if [ -z "$WORKSPACE_METADATA" ]; then
    echo "❌ Unlinked pre-existing Spec branch requires exactly one Workspace Metadata comment."
    exit 1
  fi

  if [ "$(printf '%s\n' "$WORKSPACE_METADATA" | grep -c '^\*\*Branch:\*\* ')" -ne 1 ] \
    || [ "$(printf '%s\n' "$WORKSPACE_METADATA" | grep -c '^\*\*Baseline Commit Hash:\*\* ')" -ne 1 ]; then
    echo "❌ Workspace Metadata must contain exactly one Branch and one Baseline Commit Hash line."
    exit 1
  fi

  RECORDED_BRANCH=$(printf '%s\n' "$WORKSPACE_METADATA" | sed -n 's/^\*\*Branch:\*\* //p')
  RECORDED_BASELINE=$(printf '%s\n' "$WORKSPACE_METADATA" | sed -n 's/^\*\*Baseline Commit Hash:\*\* //p')

  if [ "$RECORDED_BRANCH" != "$SPEC_BRANCH" ]; then
    echo "❌ Workspace Metadata branch does not match $SPEC_BRANCH."
    exit 1
  fi

  if ! [[ "$RECORDED_BASELINE" =~ ^[0-9a-f]{40}$ ]]; then
    echo "❌ Workspace Metadata baseline must be one full 40-character commit SHA."
    exit 1
  fi

  if ! git cat-file -e "$RECORDED_BASELINE^{commit}" 2>/dev/null \
    || ! git merge-base --is-ancestor "$RECORDED_BASELINE" HEAD; then
    echo "❌ Workspace Metadata baseline is not valid ancestry for the current Spec branch."
    exit 1
  fi

  LEGACY_PREEXISTING_BRANCH=true
else
  echo "❌ Spec branch is not linked to the parent Spec's GitHub Development section."
  exit 1
fi

if [ "$LOCAL_BRANCH_EXISTS" = false ] && [ "$REMOTE_BRANCH_EXISTS" = false ] \
  && [ "$(git rev-parse HEAD)" != "$BASELINE_COMMIT" ]; then
  echo "❌ Newly created Spec branch does not match the captured Spec baseline."
  exit 1
fi
```

### 4. Record Spec Baseline Metadata Once

Record the baseline on the parent Spec issue only if it has not already been recorded:

```bash
ALREADY_POSTED=$(gh issue view "$spec_issue_number" --json comments -q '.comments[].body' \
  | grep -c "## Workspace Metadata" || true)

if [ "$ALREADY_POSTED" -eq 0 ]; then
  gh issue comment "$spec_issue_number" --body "$(printf \
'## Workspace Metadata\n**Baseline Commit Hash:** %s\n**Branch:** %s\n' \
"$BASELINE_COMMIT" "$SPEC_BRANCH")"
fi
```

Never overwrite the Spec body to store workspace metadata.

The original baseline remains the fixed point for the entire Spec lifecycle.

## Implementation Human Handoff

After `TICKET PUBLICATION READBACK: PASS`, ticket publication/reconciliation, and Spec branch metadata are durable, identify every open, unblocked **implementation-ready** frontier ticket for the Spec.

If one frontier ticket is available, halt with:

> ✅ **Tickets are ready for implementation.**
>
> Please run:
>
> ```
> $implement-ticket - <Frontier Ticket Title> (<Ticket URL>)
> ```

If multiple frontier tickets are available, output one copy-ready `$implement-ticket` line per ticket and let the user choose which fresh implementation session to start.

If no ticket is implementation-ready because an upstream design/readiness blocker remains, report that blocker and stop without an `$implement-ticket` handoff.

Do not invoke `$implement-ticket` implicitly.

## Transition-Bound Decomposition Coverage

Ticket publication is authorized only after the complete source contract has been dispositioned into executable or explicitly non-executable work. A well-formed set of proposed tickets is not proof that the decomposition universe was complete or design-complete.

For an originating Spec, use the current `$spec-contract` contract as the decomposition universe. If the current invocation does not already hold a valid contract for the exact Spec body/branch/baseline/HEAD, invoke `$spec-contract` in `build` mode after branch/baseline readiness and before approval using its `$to-tickets` decomposition exception. `$spec-contract` is source parsing/contract construction here; it does not verify implementation or cure a design-readiness gap.

Build one working **Decomposition Coverage** row per manifest cell:

```text
Cell: <manifest ID>
Requirement: <authoritative requirement>
Disposition: <ticket | verification-only | no-implementation-work | out-of-scope | deferred-conditional>
Ticket: <proposed/existing ticket identity | None>
Reason/authority: <why this disposition completely carries the cell>
```

Rules:

* `ticket` requires the mapped ticket's acceptance contract to preserve the cell's full predicate/domain; several cells may map to one coherent ticket;
* `verification-only` is valid only when current implementation work is not required and the obligation still receives later proof;
* `no-implementation-work` requires direct evidence that the Spec obligation is already realized or purely declarative while remaining part of later Spec verification;
* `out-of-scope` requires the originating Spec itself to establish that disposition; do not invent scope retirement during ticketing;
* `deferred-conditional` must satisfy **Conditional / Deferred Obligation Routing** and preserve its trigger/destination;
* omission is never an escape disposition.

Before presenting the approval proposal and again before publication require:

```text
Source implementation readiness: pass
Material design choices delegated to implementation: 0
Spec contract cells: <n>
Decomposition coverage rows: <n>
Missing cells: 0
Unknown rows: 0
Ambiguous mappings: 0
Unclassified dispositions: 0
Disposition rows without reason/authority: 0
```

Human approval authorizes publication of the exact complete independently certified proposal; it does not waive decomposition or design completeness. For Spec Review remediation, `$to-remediation-tickets` owns its Root Delta Coverage and returns that complete semantic delta; preserve it without condensation or omission.