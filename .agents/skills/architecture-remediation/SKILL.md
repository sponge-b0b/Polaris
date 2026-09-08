---
name: architecture-remediation
description: "Route unresolved architecture blockers through the parent Spec's actual governance: back into the existing governing Wayfinder effort when Wayfinder-managed, or through in-place owner-guided remediation when the Spec is intentionally Independent."
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Architecture Remediation

Use when `$implement-ticket`, `$review-spec`, `$to-remediation-specs`, or another workflow cannot continue because of unresolved or incomplete architecture.

This workflow is **governance-mode aware**:

- for a **Wayfinder-managed Spec**, it remains a routing workflow: recover the exact existing governor, reopen it when authoritative re-entry requires it, create/reuse decision work there, and hand resolution to `$wayfinder`;
- for an intentionally **Independent Spec**, do not invent a Wayfinder merely to satisfy remediation. Resolve the bounded architecture decision in place with the owner, persist the resulting authority, amend the existing Spec, and return through `$to-tickets` before implementation resumes.

Never modify implementation here. Never create a new Wayfinder map for an Independent Spec solely because architecture remediation was required.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

A blocker-driven Human Handoff must not depend on explanatory prose from the producing session. When the invoked source artifact has a durable `<!-- architecture-blocker:v1 -->` report, that report is the blocker authority for this remediation. A concise blocker summary in the invocation is supplemental only.

Independent-Spec owner-guided HITL may itself span multiple model/context sessions. Once that mode begins, the active `<!-- independent-architecture-remediation-checkpoint:v1 -->` on the remediation source artifact is the recoverable in-progress decision state. Owner answers, the semantic decision map, dependency/frontier state, and closure-discovered material choices must never exist only in agent context.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## 1. Capture the Blocker Set

First resolve the invocation mode from durable evidence:

```text
Invocation mode: blocker-remediation | explicit-readiness-audit
```

Use **blocker-remediation** when the source artifact contains an active `<!-- architecture-blocker:v1 -->` report with `Status: unresolved`. Read the complete source-artifact comment history needed to resolve that marker, require zero or one active unresolved report, and use its blocker set as the exact stopping-point input. Validate its source workflow, source artifact, parent Spec, blocker questions/conflicts, evidence, material consequences, blocked obligations, and governing-authority references against current durable state before proceeding.

Use **explicit-readiness-audit** only when the human invocation itself explicitly requests an architecture/readiness audit and states the audit scope. Do not silently convert a missing blocker report into an audit merely to keep the workflow moving.

If the invocation is presented as a blocker-remediation handoff but no recoverable active blocker report exists, halt and identify `<!-- architecture-blocker:v1 -->` as the missing durable artifact. Do not ask the human to reconstruct the prior session's finding.

A blocker includes:

* an unresolved material architecture decision;
* a blocking `[source-conflict]` among applicable authorities;
* current authority invalidating architecture required by the work;
* a required obligation that cannot be implemented without violating or changing current authority;
* a required obligation that cannot be implemented without inventing a durable architectural owner, contract, key, path, boundary, dependency direction, lifecycle rule, or authority semantic.

For each blocker capture:

* unresolved question/conflict;
* durable blocker-report evidence or explicit audit evidence;
* material consequence;
* affected owners, contracts, canonical paths, boundaries, dependencies, or lifecycle responsibilities;
* governing ADR/doc references already known;
* exact blocked requirement/acceptance obligation when applicable;
* source ticket or review finding.

Also capture:

* parent Spec;
* Spec Review issue when applicable.

Preserve durable source evidence and terminology. Do not invent a resolution while capturing the blocker set.

### Architecture blocker report lifecycle

For blocker-remediation mode, retain the source artifact and exact managed blocker-comment identity throughout the workflow.

The cross-skill contract in `.agents/skills/README.md` owns the report format and the meaning of:

```text
Status: unresolved | routed | resolved
```

Do not create a second active `<!-- architecture-blocker:v1 -->` report. When this workflow changes the blocker disposition, update that same managed comment in place and read it back before any Human Handoff or ordinary return that depends on the new disposition.

* **Wayfinder-managed unresolved work:** after the exact governing Wayfinder decision ticket(s) are durable, set the report to `routed` and record those decision references in `Disposition` before handing off to `$wayfinder`.
* **Independent Spec resolution:** after authoritative architecture, Spec amendment, remediation receipt, and required synchronization are durable, set the report to `resolved` and record the remediation receipt/authority references before handing off to `$to-tickets`.
* **Existing authority fully resolves the blocker:** set the report to `resolved` and record the exact accepted authority that removes the missing choice before returning control.

Changing blocker-report status is provenance/disposition state; it does not by itself imply a Project lifecycle transition unless this workflow separately changes the source artifact's authoritative lifecycle state.

### Decision Coupling

De-duplicate by **independent architectural decision**, not by caller bullet or symptom.

Questions belong to the same decision when they jointly define the same durable contract, lifecycle, ownership model, or canonical path and answering one materially constrains the others.

Ask:

> Can each question be resolved independently without materially changing the decision space of the others?

If **No**, combine them into one decision with multiple explicit questions.

If **Yes**, keep them independent.

Do not create separate decisions merely because the caller reported several numbered blockers.

## 2. Resolve Architecture Governance Mode

Read the parent Spec and recover its complete current Wayfinder governance from durable evidence:

* canonical source provenance:

  ```html
  <!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
  ```

* every applicable remediation provenance marker:

  ```html
  <!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision> -->
  ```

* matching `Derived Spec` / `Remediation Spec` handoff metadata on canonical Wayfinder maps;
* source ticket / Spec Review lineage supplied by the durable blocker report or explicit audit invocation.

Preserve original source provenance. Remediation governance is additive and must never replace `wayfinder-source`.

Resolve exactly one governance mode:

### Wayfinder-managed

The Spec is Wayfinder-managed when durable source/remediation provenance or reconciled `Spec Handoff` evidence establishes one or more current Wayfinder governors.

Resolve the **exact governing Wayfinder whose scope owns the architecture blocker being routed**. A Spec may have more than one governor; do not default to the original source when the blocker belongs to a later remediation Wayfinder.

If one candidate governor is established unambiguously, use it. If multiple governors plausibly own the blocker and durable context does not distinguish one, fail closed. Do not guess, create a replacement map, or duplicate the decision under several maps.

Blockers remain under that governing map unless one is genuinely outside its destination.

### Independent Spec

A Spec may intentionally exist outside Wayfinder governance.

Treat it as **Independent** only when durable recovery establishes no Wayfinder source/remediation provenance and an exhaustive reconciliation against canonical Wayfinder `Derived Spec` / `Remediation Spec` handoffs does not establish a governor.

This is a valid lifecycle mode. Do not create, infer, or require a Wayfinder merely because implementation later discovers an architecture blocker.

If evidence suggests a Wayfinder relationship should exist but provenance/handoff state is missing, contradictory, or ambiguous, fail closed as governance drift rather than silently classifying the Spec as Independent.

Record:

```text
Architecture governance mode: Wayfinder-managed | Independent Spec
Governing Wayfinder: #<map> | None
Governance evidence: <exact durable evidence>
```

## 3. Test Existing Architecture Coverage

Before creating decision work or asking the owner to decide anything, inspect relevant accepted authority and resolved architectural decisions.

A prior decision resolves the blocker only when current accepted authority **directly determines the exact durable choice the blocker report says is missing**.

For each blocker ask:

> Can the blocked work proceed from current authority without inventing another durable architectural choice?

If **Yes**:

* record the exact accepted decision/authority that determines the missing choice;
* explain concisely how it resolves that specific blocker;
* do not create or ask for a duplicate decision.

If **No**, the blocker remains unresolved.

**Related subject matter is not coverage.** Do not treat a closed decision or ADR as resolving a blocker merely because it concerns the same subsystem, owner, contract, or lifecycle.

For example, deciding **who owns** a lifecycle does not automatically determine its required inputs, durable selection key, or ordering.

If existing authority resolves only part of a blocker, preserve only the unresolved dimensions and re-apply **Decision Coupling** to them.

## 4A. Wayfinder-Managed Re-entry

Perform this section only for `Architecture governance mode: Wayfinder-managed` and only when at least one architecture blocker remains unresolved after Section 3.

Re-read the exact governing Wayfinder immediately before mutation.

If it is closed:

1. reopen that same Wayfinder issue with an explicit lifecycle-reentry reason identifying the blocked Spec/work;
2. re-read it and require state `open`;
3. invoke `$project-delivery-management` `reconcile` **after** the reopen is durable.

Reopening restores authoritative Wayfinder lifecycle state; it does **not** restore project focus. `$project-delivery-management` reconciliation must never auto-focus the reopened map or silently replace another focused map.

If the Wayfinder is already open, do not create a synthetic reopen/close cycle.

If the map cannot be reopened or its identity/state cannot be verified, halt. Do not create/reuse a decision ticket against a lifecycle state that still says delivery-complete.

## 4B. Independent-Spec Architecture Resolution

Perform this section only for `Architecture governance mode: Independent Spec` and only when at least one blocker remains unresolved after Section 3.

The existing parent Spec is the durable lifecycle owner for this bounded remediation. Do not create a Wayfinder map, Wayfinder decision ticket, Spec Review, or other new formal issue merely to host the architecture decision.

### Durable decision-map checkpoint

Before asking the owner the first architecture question, establish one durable in-progress checkpoint on the remediation **source artifact**. In blocker-remediation mode, this is the artifact carrying the active `architecture-blocker:v1` report. In explicit-readiness-audit mode, use the explicitly audited formal artifact; if the audit has no narrower tracker artifact, use the parent Spec.

Use one active machine-managed comment:

```markdown
<!-- independent-architecture-remediation-checkpoint:v1 -->
## Independent Architecture Remediation Checkpoint

**Status:** in-progress | closure | completed
**Source artifact:** <#n title + URL>
**Parent Spec:** <#n title + URL>
**Source blocker:** <architecture-blocker comment URL | explicit-readiness-audit>
**Governance mode:** Independent Spec
**Generation:** <monotonic integer>

### Decision map

| ID | Coupling group | Semantic dimension | Depends on | State | Resolution / durable reference |
| --- | --- | --- | --- | --- | --- |
| D-1 | CG-1 | <material dimension> | <D-IDs | None> | <authority-resolved | owner-resolved | ready | dependent | closure-discovered> | <decision or Pending> |

### Owner decisions

1. **D-<n> — <decision name>**
   - **Owner answer:** <explicit answer>
   - **Frozen semantic consequence:** <complete durable choice>
   - **Recorded from:** <current invocation / owner response>

### Current owner question

**State:** none | awaiting-owner
**Decision:** <D-n | None>
**Question:** <exact durable choice | None>
**Recommendation:** <recommended answer | None>
**Material alternatives/tradeoffs:** <alternatives | None>

### Bounded closure

**Reported blocker coupling groups:** <n>
**Owner-resolved coupling groups:** <n>
**New material choices discovered by closure:** <n>
**Unresolved material choices:** <n>
**Material implementation-delegated architecture choices:** <n>
**Closure notes:** <dimensions tested / Pending>

### Completion references

<None while active | architecture authority + Spec amendment + remediation receipt>
```

Checkpoint rules:

* maintain zero or one **active** checkpoint (`Status: in-progress | closure`) for the same remediation source; update it in place rather than creating competing active comments;
* a completed checkpoint remains historical provenance and is not architecture authority. A later distinct remediation may create a new active checkpoint;
* validate the checkpoint's source artifact, parent Spec, blocker/audit source, governance mode, and current authority before trusting it;
* if multiple active checkpoints exist, or the checkpoint conflicts materially with the current blocker/authority, fail closed and reconcile the durable state rather than choosing one;
* the checkpoint is recoverable workflow state, not a substitute for final architecture docs, the amended Spec, or the Independent Architecture Remediation Receipt;
* checkpoint create/update/readback is workflow-state persistence, not a formal artifact lifecycle transition and does not by itself trigger `$project-tracking`.

#### Precompute the semantic decision space

Before the first owner question, enumerate the **materially known semantic dimensions and their dependencies across the entire blocker-defined contract**, not merely the first example that triggered remediation. Use the bounded-closure dimensions below as the minimum adversarial lens.

This is a decision map, not an immutable questionnaire:

* precompute every currently identifiable material dimension and dependency;
* mark dimensions that cannot yet be formulated independently as `dependent`;
* owner answers may eliminate, split, merge, or reshape later dimensions;
* newly exposed material dimensions are added as they become identifiable;
* do not invent a final exact question before prerequisite owner decisions determine its decision space.

Persist the initial map and read the checkpoint back successfully **before** asking the first owner question.

#### Fresh-session resume

At every fresh invocation of an active Independent remediation:

1. recover and validate the source blocker/audit, parent Spec, current authority, and active checkpoint;
2. treat checkpointed `owner-resolved` decisions as durable owner inputs; do not re-ask them merely because agent context was lost;
3. if `Current owner question` is `awaiting-owner` and no durable answer exists, resume by presenting that exact pending choice;
4. if the human explicitly reaffirms, refines, or changes a prior checkpointed decision, update the checkpoint and propagate the change through the map before continuing;
5. if an older interrupted remediation predates this checkpoint contract, explicit owner decisions supplied in the current invocation may seed the initial checkpoint after durable authority/blocker validation. Do not treat unverified remembered decisions as equivalent.

### Owner-guided decision resolution

Resolve one coupled architectural decision at a time inside this workflow.

For each unresolved coupling group:

1. research every recoverable fact from repository/tracker/accepted authority rather than asking the owner;
2. propagate all checkpointed owner decisions through the decision map and identify the next materially answerable choice;
3. state the exact durable choice that remains;
4. provide the recommended answer and the material alternatives/tradeoffs;
5. **before asking**, update `Current owner question` in the checkpoint to `awaiting-owner`, persist the exact question/recommendation/alternatives, and verify readback;
6. ask the owner for one decision at a time;
7. **as the first workflow action after the owner answers**, update the corresponding decision to `owner-resolved`, record the explicit answer plus its frozen semantic consequence, recompute dependent/frontier states, clear `Current owner question`, increment `Generation`, and verify readback before doing additional analysis/research;
8. only after that successful durable readback may the workflow formulate or ask the next owner question.

An owner answer is not considered preserved merely because it is present in the current conversation or agent working state. Token exhaustion, context reset, interruption, or a fresh model session after an answer must not require the owner to reconstruct that decision.

`$grilling` and `$domain-modeling` may be used as prescribed internal composition when they materially improve the decision analysis. Their HITL is in-skill HITL, not a separate lifecycle handoff.

Do not select a materially consequential architecture choice merely to keep implementation moving.

### Bounded design-completeness closure

After the reported blockers are answered, do **not** persist immediately. Perform one bounded adversarial closure over the affected public/domain/architecture contract so the workflow does not return one example at a time.

Within the blocker-defined contract boundary, enumerate every materially relevant semantic dimension and nested universe, including where applicable:

* owners and authority/input sources;
* identity and support/reference membership;
* lifecycle/state transitions and correction/restoration semantics;
* zero / one / many cardinality cases;
* temporal knowledge/effective boundaries;
* ordering and compatibility rules;
* version/concurrency consequences;
* determinate/contested/absent states;
* failure and fail-closed behavior;
* downstream/public/persistence-visible consequences;
* correction-of-correction, competing support, or equivalent nested closure where the contract contains those structures.

Apply the repository's design-to-implementation test:

> Could two reasonable implementations satisfy the amended authority while producing materially different domain, public, persistence, temporal, authority, or downstream behavior?

If **Yes**, architecture remains incomplete. Add every newly discovered material choice to the durable decision map, assign its coupling/dependencies, update the checkpoint back to `Status: in-progress`, and verify readback **before** asking the owner about it. Re-apply Decision Coupling and continue owner-guided resolution before persistence.

When all reported blocker choices are owner-resolved, set the checkpoint to `Status: closure`, persist/read back the current closure counts and tested semantic universe, then run the adversarial closure. If closure discovers a material choice, return to `in-progress` as above. Do not let closure findings exist only in working context.

Closure requires:

```text
Reported blocker coupling groups: <n>
Owner-resolved coupling groups: <n>
New material choices discovered by closure: <n>
Unresolved material choices after closure: 0
Material implementation-delegated architecture choices: 0
```

Ordinary private helper structure, local algorithms, code organization, formatting, and equivalent test mechanics remain implementation details and do not block closure.

### Scope boundary

Independent remediation may complete or correct architecture required by the existing Spec destination. It may not silently turn the Spec into a materially broader planning effort.

If resolving the blocker reveals genuinely new destination scope that should be separately planned, halt and explain that a new planning lifecycle is required. Do not chart that Wayfinder implicitly.

## 5A. Create or Reuse Wayfinder Decision Tickets

Perform this section only for Wayfinder-managed remediation.

For every blocker still unresolved after the coverage test, inspect the governing map's open child decisions.

Reuse an open child only when it represents the same underlying unresolved decision.

Otherwise create exactly one child decision under the existing governing map using repository Wayfinding operations.

Use `wayfinder:grilling` unless the caller established another appropriate Wayfinder ticket type.

Use:

```markdown
**Parent Wayfinder:** #<wayfinder_map>
**Parent Spec:** #<spec_issue>
**Source Ticket:** #<source_ticket>
**Spec Review:** #<spec_review_issue>

## Question

<single architectural decision to resolve>

When coupled:

1. <question/dimension>
2. <question/dimension>

## Discovery Context

<durable blocker-report evidence and why current work cannot proceed>

## Blocked Obligation

<exact requirement that cannot currently be satisfied, when applicable>

## Governing Authority

<applicable ADRs/docs/contracts and what they determine or leave unresolved>
```

`Parent Wayfinder` and `Parent Spec` are required.

Omit optional relationships or sections when they do not apply.

Do not:

* propose a preferred resolution;
* rewrite the blocked obligation into a solution;
* duplicate a decision because the same blocker surfaced at multiple workflow stages;
* split one coupled contract/lifecycle into artificial separate decisions.

The ticket must preserve enough context for `$wayfinder` to determine whether authority must change, the blocked obligation must change, existing authority must be completed, or both must be reconciled.

After the required decision-ticket/map mutations are durable, invoke `$project-delivery-management` `reconcile`. This reduction may remove invalid focus but must never select, switch, or broaden focus.

For blocker-remediation mode, update the source `architecture-blocker:v1` report to `Status: routed`, record the governing Wayfinder and exact decision ticket references in `Disposition`, and verify the readback before the `$wayfinder` Human Handoff.

## 5B. Persist Independent-Spec Remediation

Perform this section only after Independent-Spec bounded design-completeness closure passes.

### Persist architecture authority

Reconcile every owner-approved architectural decision into its actual durable authority.

Use the existing documentation lifecycles rather than inventing parallel records:

* `$to-adr-doc` for durable ADR decisions when an ADR is required;
* `$to-doc` for new non-ADR architecture documentation;
* `$classify-doc` when existing documentation must be reclassified;
* `$wiki-sync` after substantive authoritative architecture/document changes that affect Living Entity Wiki knowledge.

When an existing authoritative document can be amended directly under repository policy, make the smallest coherent update rather than creating a new document solely for remediation history.

Respect repository branch/authority rules. Do not leave canonical architecture authority only on an unauthorized feature branch. When repository policy requires canonical architecture changes on another branch, persist there and synchronize the active Spec branch through the repository's normal merge/synchronization procedure before downstream ticket reconciliation.

### Amend the existing Spec in place

Update the existing parent Spec rather than creating another Spec.

Preserve:

* Spec issue identity;
* original planning/source provenance;
* branch and fixed Spec baseline lineage;
* existing ticket and Spec Review lineage;
* unaffected requirements and decisions.

Amend only what the resolved architecture requires:

* affected user stories/requirements;
* `Architecture Impact`;
* affected implementation decisions;
* affected testing decisions/acceptance obligations;
* stale contradictory design-completeness assertions.

Do not add unrelated scope or regenerate the Spec from scratch.

### Persist one remediation receipt

Add one durable comment to the parent Spec for this completed independent remediation:

```markdown
<!-- independent-architecture-remediation:v1 -->
## Independent Architecture Remediation Receipt

**Source workflow:** `$architecture-remediation`  
**Source ticket/review:** <artifact | None>  
**Governance mode:** Independent Spec

### Blockers
<exact blocker/coupling groups>

### Owner decisions
<resolved durable choices>

### Bounded closure
<closure counts + materially tested semantic universe>

### Authority changed
<ADRs/docs/wiki/Spec sections changed>

### Downstream reconciliation
**Affected existing tickets:** <#IDs | None>
**Next lifecycle:** `$to-tickets`
```

The Spec and architectural documents remain semantic authority; the receipt is durable remediation provenance, not a second architecture registry.

Do not rewrite existing Implementation Ticket bodies, Ticket baselines, dependency edges, or closure evidence here. Existing ticket contracts may now be stale; `$to-tickets` / `$to-remediation-tickets` owns their reconciliation.

If repository-side architecture changes are required, do not post the completion receipt until those changes are durably committed/pushed and the active Spec branch contains the required authority.

After the receipt and all required repository/Spec synchronization are durable, update the active Independent checkpoint to `Status: completed`, record the controlling architecture/Spec/receipt references under `Completion references`, require `Current owner question: none`, and verify readback. The completed checkpoint remains workflow provenance; final architecture authority lives in the documented/Spec surfaces named by those references.

For blocker-remediation mode, only after that completed-checkpoint readback succeeds, update the source `architecture-blocker:v1` report to `Status: resolved`, record the receipt URL and controlling authority in `Disposition`, and verify the readback before the `$to-tickets` Human Handoff.

## Mandatory Project Reconciliation

After every architecture-remediation tracker transition is durable, invoke `$project-tracking` as prescribed internal composition **before** any Human Handoff or ordinary return.

For Wayfinder-managed remediation, first perform the existing required `$project-delivery-management` reconciliation after Wayfinder mutations.

Synchronize only formal artifacts whose authoritative lifecycle state this skill actually created, reopened, or changed:

* a governing Wayfinder map reopened or kept active because unresolved architectural decision work now exists → base `Wayfinder Map / Architecture Decision / $wayfinder / Ready`;
* each newly created or lifecycle-changed open Wayfinder decision → base `Wayfinder Decision / Architecture Decision / $wayfinder / Ready`;
* an Independent parent Spec successfully amended and architecture-complete but requiring existing ticket reconciliation → base `Spec / Ready to Ticket / $to-tickets / Ready`;
* a source Implementation Ticket or review artifact only when this skill itself durably records a lifecycle change for that artifact;
* any additional formal artifact whose lifecycle state this skill durably changes.

Do not manufacture a source-artifact transition merely because the caller arrived with an architecture blocker. A blocker-report status update alone is provenance/disposition, not a Project lifecycle mutation. When existing authority fully resolves the blocker set and this skill makes no lifecycle mutation, there may be no Project reconciliation target; return control to the caller without inventing one.

Supply current Project Delivery State separately from the base lifecycle projection. Independent Specs remain outside Wayfinder delivery-focus governance. `$project-tracking` owns validation, delivery overlay, and Project mutation; it does not discover which artifacts this skill changed.

If Project synchronization fails, report `PROJECT TRACKING: DRIFT`. Do not undo durable architecture/Spec state and do not suppress an otherwise-authorized handoff or resolved-authority return.

## 6. Human Handoff Intercept

### Wayfinder-managed unresolved decisions remain

When a Wayfinder-managed blocker remains unresolved, halt after every independent decision has one corresponding open Wayfinder ticket and, in blocker-remediation mode, after the source blocker report is durably `routed`.

Present all decisions and identify the next one:

> ⚠️ **Work is blocked by unresolved architecture.**
>
> The following Wayfinder decision tickets represent the unresolved blockers:
>
> * **`<Decision Ticket Title> (<URL>)`**
>
> Please continue with:
>
> ```
> $wayfinder - <Next Decision Ticket Title> (<URL>)
> ```

When only one exists, present only that ticket.

Do not resume implementation, review remediation, or Spec amendment until the applicable decisions are resolved and the map route is clear.

`$wayfinder` owns decision sequencing and resolves one decision ticket per session. Its project-delivery focus guard applies at that substantive decision-entry boundary. If this remediation reopened a previously completed map, `$wayfinder` may require an explicit human focus/switch/parallel decision before resolution proceeds.

### Independent Spec resolution complete

After Independent-Spec architecture authority, Spec amendment, receipt persistence, blocker-report resolution when applicable, and Project reconciliation are complete, do not return directly to the previously blocked implementation ticket.

Present:

> ✅ **Independent architecture remediation is complete.**
>
> The existing Spec has been reconciled in place. Existing ticket contracts must now be reconciled against the amended Spec.
>
> Please continue with:
>
> ```
> $to-tickets - <Parent Spec Title> (<Spec URL>)
> ```

This is the next human lifecycle boundary. `$to-tickets` owns reuse/reconciliation of existing tickets and establishment of any new Ticket baselines required by the amended contract.

### Existing Authority Fully Resolves the Blocker Set

If every reported blocker is directly resolved by current accepted authority, create no Wayfinder decision and do not start Independent-Spec owner decision work solely to restate existing authority.

Report for each blocker:

* exact governing decision/authority;
* the durable choice it determines;
* why no architectural invention remains necessary.

Do not infer resolution from topic overlap.

For blocker-remediation mode, update the source `architecture-blocker:v1` report to `Status: resolved`, record the exact controlling authority in `Disposition`, and verify readback before return or any downstream handoff.

If current authority invalidates or materially changes the existing Spec/remediation obligation:

* Wayfinder-managed Spec → continue through the normal Wayfinder-to-Spec reconciliation path;
* Independent Spec → perform the bounded in-place Spec reconciliation under Section 5B, then hand off to `$to-tickets`.

Otherwise report that the blocker set is already architecturally resolved and return control to the calling workflow.

## 7. Return Path

### Wayfinder-managed Spec

After new architectural decisions are resolved, or existing accepted authority requires Spec reconciliation:

```text
$wayfinder
→ $to-specs
→ $to-remediation-specs when an existing Spec is affected
→ $to-tickets
→ $implement-ticket
```

`$to-remediation-specs` owns reconciling existing Wayfinder-managed Spec requirements and downstream ticket intent against newly resolved architecture.

### Independent Spec

After owner-guided architecture resolution and in-place Spec amendment:

```text
$architecture-remediation
→ $to-tickets
→ $implement-ticket
```

Do not insert `$wayfinder`, `$to-specs`, or `$to-remediation-specs` merely to simulate governance that the Independent Spec does not have.

For either mode, do not hand directly back to a blocked implementation ticket when architecture changes or invalidates its Spec/remediation obligation. The ticket contract must first be reconciled against the new authority.

A legitimately reopened Spec or blocker participates through the existing native dependency graph. Do not write a separate satisfaction/ineligibility flag; downstream frontier guards must re-read current open/closed blocker state.

## Completion

This skill is complete when:

* governance mode is recovered without guessing;
* blocker-remediation mode has a recoverable durable source blocker report, or explicit-readiness-audit mode is unambiguously human-requested;
* caller blockers are reduced to the minimum set of genuinely independent decisions;
* existing accepted authority is tested against the exact missing durable choices;
* no duplicate or artificially split decisions are introduced;
* every blocker-remediation report is durably `routed` or `resolved` before the corresponding handoff/return;
* mandatory `$project-tracking` reconciliation runs for every formal artifact whose lifecycle state this skill changed;
* the mode-specific completion conditions below are satisfied.

For **Wayfinder-managed** remediation:

* the exact governing Wayfinder is recovered without rewriting source/remediation provenance;
* when unresolved decision work re-enters a closed map, that same map is reopened and verified open before decision work is created/reused;
* every unresolved decision is represented by exactly one open Wayfinder ticket;
* project-delivery reconciliation runs after authoritative Wayfinder transitions without auto-focusing a map;
* the appropriate `$wayfinder` Human Handoff or resolved-authority return is presented.

`$wayfinder` owns architectural resolution and authority reconciliation for Wayfinder-managed Specs. `$to-specs` / `$to-remediation-specs` own propagating those changed decisions back into the governed Spec.

For **Independent Spec** remediation:

* the source artifact has one recoverable active checkpoint before owner-guided HITL begins;
* the checkpoint contains the blocker-wide semantic decision map and dependency/frontier state;
* every owner question is persisted/read back before it is asked;
* every owner answer is persisted/read back before the next question is formulated;
* every unresolved coupled architecture choice is explicitly owner-resolved;
* bounded design-completeness closure reports zero unresolved material choices, with closure-discovered choices checkpointed before any additional HITL;
* resulting architecture is persisted in its authoritative repository/doc/wiki surfaces;
* the existing Spec is amended in place without changing its identity or inventing Wayfinder provenance;
* one Independent Architecture Remediation Receipt is persisted;
* the checkpoint is durably `completed` with final authority/receipt references and no pending owner question;
* existing ticket bodies/baselines remain untouched here;
* the `$to-tickets` Human Handoff is presented.

## Transition-Bound Architecture Blocker Disposition

Architecture routing/resolution decisions that suppress or create durable work must be explicit working state.

After capturing the blocker set, create one **Architecture Blocker Disposition** row per reported blocker before deduplication:

```text
Blocker: AB-<n>
Caller obligation/question: <exact source>
Underlying durable choice(s): <owner/path/key/boundary/lifecycle/failure semantic>
Coupling group: <CG-<n>>
Existing authority: <resolves | partial | unresolved>
Authority/evidence: <exact accepted source and durable choice>
Governance mode: <Wayfinder-managed | Independent Spec>
Result: <return-to-caller | wayfinder-decision-work | independent-resolution>
Decision ticket: <existing/new ticket | None>
Owner decision: <resolved choice | Pending | None>
```

Decision Coupling must itself be reflected by the `Coupling group`: every blocker belongs to exactly one group, and the group must explain why its questions cannot be resolved independently. Do not silently merge caller blockers merely because they concern the same subsystem.

`Existing authority: resolves` and `Result: return-to-caller` are legal only when the recorded authority directly determines every durable choice required by that blocker. Apply this counterexample test: **could the blocked work still have to invent a durable semantic while all cited authority remains true?** If yes, the blocker is `partial` or `unresolved`, not resolved.

For Wayfinder-managed remediation, every coupling group containing any unresolved/partial blocker requires exactly one open governing Wayfinder decision unless authoritative existing tracker state already provides that exact ticket.

For Independent-Spec remediation, every coupling group containing any unresolved/partial blocker requires one explicit owner decision inside this workflow and must pass bounded design-completeness closure before persistence. No Wayfinder decision ticket is required or permitted solely for this remediation mode.

Before mode-specific Human Handoff or resolved-authority return require:

```text
Caller blockers: <n>
Disposition rows: <n>
Missing blockers: 0
Unassigned coupling groups: 0
Resolved blockers with incomplete durable-choice proof: 0
Wayfinder unresolved groups without exactly one open decision ticket: 0
Independent unresolved groups without explicit owner decision: 0
Independent unresolved material choices after bounded closure: 0
Independent active remediation without recoverable checkpoint: 0
Independent owner decisions present only in conversational/agent state: 0
Independent pending owner question at completion: 0
Active source blocker reports left unresolved at handoff/return: 0
```

These disposition rows remain working-state accounting and need not become a second architecture registry. For Independent remediation, however, every correctness-critical in-progress decision-map/frontier/owner-answer state required to resume the workflow must be represented in the managed checkpoint. The checkpoint is workflow provenance only; durable blocker reports, accepted architecture authority, the amended Independent Spec, and its remediation receipt remain the semantic truth.
