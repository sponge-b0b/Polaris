---
name: to-remediation-specs
description: Invoked only by `$to-specs` when a Wayfinder map already has one or more in-progress Spec handoffs — recover derived and remediation Specs, apply new or revised accepted decision-state deltas, and amend them without duplicating previously consumed decision states.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# To Remediation Specs

Invoked by `$to-specs` when its source Wayfinder map already has one or more in-progress Spec handoffs.

Replace fresh spec creation for that handed-off scope. The Wayfinder map remains the source input for the current remediation decisions.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## 1. Recover the Existing Specs

From the source Wayfinder map, resolve every in-progress Spec identified by the reconciled `Derived Spec` and `Remediation Spec` metadata established by `$to-specs`.

For a **Derived Spec**, confirm its durable source provenance identifies the input Wayfinder.

For a **Remediation Spec**, preserve its original source provenance even when it identifies another Wayfinder. Confirm instead that the input Wayfinder explicitly names the Spec as a `Remediation Spec` or that the Spec already has a `wayfinder-remediation` marker for the input Wayfinder.

If tracker evidence reveals an additional unambiguous handed-off Spec missing from the map's `Spec Handoff`, add the matching linkage and include that Spec before continuing.

Preserve each Spec's:

* issue identity;
* original planning/source provenance;
* branch and baseline lineage;
* existing tickets;
* Spec Review lineage, when present.

If no in-progress handed-off Specs exist, return to `$to-specs` for normal spec creation.

If any candidate relationship or handoff role is ambiguous, halt rather than guessing which Specs belong to the current remediation run.

## 2. Recover Revision-Aware Decision Provenance

Existing Wayfinder provenance remains the durable membership record for which decisions a Spec derives from.

For each **Derived Spec**, read its source Wayfinder provenance marker:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
```

Confirm that `wayfinder-source` identifies the input map.

For each **Remediation Spec**, preserve its existing `wayfinder-source` marker unchanged and read the separate remediation marker for the input map when present:

```html
<!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision> -->
```

Decision IDs alone are **not sufficient consumption identity** because an accepted Wayfinder decision may later be reopened and materially revised while retaining the same issue number.

### Current accepted decision-state identity

For every resolved decision currently relevant to the input map, resolve one current terminal accepted state from durable tracker evidence.

A decision has a consumable current accepted state only when:

* the issue is currently closed through normal successful resolution, not merely retired as `not_planned` / superseded;
* exactly one latest terminal resolution anchor can be selected by comment chronology whose first non-empty line is `## Resolution` or `## Final Resolution`;
* no later semantic-change/re-entry comment begins with `## Decision Analysis`, `## Recommendation Revision`, `## Architecture Remediation Re-entry`, or `## Workflow Convergence Remediation` without a later terminal resolution anchor;
* the exact terminal resolution comment body is recoverable.

If these conditions are ambiguous or incomplete, that decision has no consumable current state and remediation fails closed. Do not infer acceptance merely from issue `closed` state, an old resolution, or a decision ID already present in Spec provenance.

For each consumable current accepted state compute:

```text
Resolution body SHA-256 = sha256(exact UTF-8 terminal resolution comment body)

Decision-state packet:
wayfinder-decision-state:v1
Decision: #<n>
Resolution comment: <numeric comment id>
Resolution body SHA-256: <sha256>

Decision State Identity = sha256(exact UTF-8 packet bytes above)
```

The terminal resolution comment remains semantic authority/provenance. The Decision State Identity is only a deterministic consumption identity.

Use bounded retrieval: locate resolution/revision/re-entry headings and fetch the selected terminal resolution body rather than loading complete unrelated comment history.

### Persisted consumed-state marker

For each Wayfinder represented on a Spec, maintain zero or one machine-managed marker:

```html
<!-- wayfinder-decision-states:v1 map=#<map>; states=#<decision>:<state_sha256>,#<decision>:<state_sha256> -->
```

Rules:

* the marker records the exact accepted decision states semantically represented by that Spec for that map;
* preserve separate markers for separate Wayfinders;
* update a map's marker in place; do not append competing markers;
* more than one state marker for the same map is ambiguous and fails closed;
* the marker is consumption provenance, not architecture authority;
* never remove a historical consumed entry merely because a later map presentation omits it; only advance/add an entry when the corresponding current accepted state is completely represented.

### Compute the per-Spec decision-state delta

For each current resolved decision applicable to a Spec, compare:

1. current accepted `Decision State Identity`;
2. existing decision-ID membership in the Spec's source/remediation provenance for this map;
3. persisted consumed state in `wayfinder-decision-states:v1`, when present.

A decision enters the Spec's **decision-state delta** when any of these is true:

* the decision is newly applicable and absent from decision-ID provenance;
* the decision ID is present but no consumed-state identity has ever been recorded and semantic representation of the current accepted state has not yet been proven;
* the persisted consumed-state identity differs from the current accepted state identity.

Classify each delta item:

```text
Delta reason: new-decision | legacy-state-bootstrap | revised-decision-state
```

A matching decision ID must never suppress `revised-decision-state`.

### Legacy ID-only bootstrap

Existing Specs created before `wayfinder-decision-states:v1` are valid historical artifacts, but their decision-ID markers cannot prove which later revision they consumed.

For every such ID already recorded:

* reconcile the current Spec semantics against the **current accepted decision state** once;
* if the current state is completely represented, authorize a `legacy-state-bootstrap` consumption record and persist the current state identity without inventing a semantic edit;
* if the current state is not completely represented, keep that decision in the state delta and amend the Spec;
* never declare the Spec synchronized solely because its decision ID appears in the old marker.

If a Derived Spec predates even source provenance metadata, first recover its map relationship under the existing compatibility rule, then perform this same state-aware bootstrap.

If a Remediation Spec has no remediation marker yet for the input map, treat this as its initial remediation from that map and apply the same state-aware reconciliation.

Do not regenerate a Spec merely to bootstrap provenance. Keep decision-state deltas independent per Spec and per Wayfinder; consumption by one Spec or one Wayfinder does not imply consumption by another.

## 3. Reconcile the Decision-State Deltas

For each Spec with a non-empty decision-state delta, read only the affected current accepted decision states and the authority they reference.

Apply that delta semantically to a candidate amendment for that Spec:

* update existing requirements or user stories when the decision changes the same behavior;
* replace or remove content invalidated by the decision;
* add content only for genuinely new behavior;
* reconcile **Architecture Impact** with newly resolved architecture;
* update affected implementation and testing decisions;
* preserve unaffected content.

For every non-empty candidate amendment, normalize the resulting `## Out of Scope` section before publication: every materially independent exclusion must be a separate Markdown bullet. Split prose or a bullet only when it contains independent exclusions; keep semantically inseparable clauses together. Preserve the exact exclusion meaning and do not add, remove, broaden, or narrow scope merely to normalize structure.

Do not duplicate:

* user stories;
* Architecture Impact entries;
* implementation decisions;
* testing decisions;
* previously consumed Wayfinder decisions.

A new decision does not imply a new spec entry when it only clarifies or supersedes an existing one.

Do not introduce architectural decisions absent from resolved Wayfinder history.

## 4. Architecture Completeness Preflight

Before applying a materially changed architecture-dependent implementation obligation to any candidate Spec, verify that accepted architecture determines enough to implement it without inventing another durable architectural choice.

Where applicable, check:

* canonical ownership;
* typed authority/input sources;
* identity, version, selection, or correlation semantics;
* lifecycle ordering;
* persistence/retrieval responsibility;
* dependency boundaries;
* failure semantics.

### Concrete Implementability Check

For each materially changed obligation, identify the existing concrete contract and production seam expected to realize it.

Inspect only enough existing source to determine whether the accepted architecture is realizable.

Where applicable, verify:

* required domain/type inputs can exist at the lifecycle point where the obligation requires them;
* the designated producer has authoritative inputs sufficient to construct the required artifact;
* required classifications or authority facts are determined or deterministically derivable from accepted authority;
* production composition can supply required dependencies without inventing new durable semantics;
* canonical consumers can obtain required typed inputs from the authoritative path.

Search before reading. Locate the affected type, producer, consumer, or composition seam and read only the surrounding code needed to answer these questions.

Do not require implementation wiring to already exist.

Missing factories, methods, configuration objects, registration calls, repository operations, DI bindings, bootstrap wiring, or similar mechanisms are implementation work when accepted architecture already determines their semantics.

If satisfying any candidate obligation would require inventing a new durable input, meaning, authority source, classification, owner, key/path, boundary, dependency direction, or lifecycle rule, architecture remains incomplete.

Ordinary implementation details are not architecture.

If satisfying any candidate obligation would require inventing unresolved architecture:

* do not amend any Spec in the current remediation run;
* do not consume any decision delta;
* do not create or modify implementation tickets;
* collect every independent architecture blocker;
* preserve coupled questions as one blocker when they jointly define the same contract or lifecycle;

Halt with a Human Handoff:

> ⚠️ **Spec remediation is blocked by incomplete architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Blocked Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```
>
> Pass the blocked obligation, concrete contract/production-seam evidence, material consequence, governing authority, and source Wayfinder decisions.

If more than one Spec is independently blocked, output one handoff per blocked Spec.

Do not propose the architectural resolution.

## 5. Update Provenance

After all candidate amendments pass the Architecture Completeness Preflight and every affected decision-state consumption record is authorized, update provenance per Spec and handoff role.

For a **Derived Spec**, keep its existing source marker as the decision-membership record and add any newly applicable decision IDs now completely represented:

```html
<!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision>,#<new-decision> -->
```

For a **Remediation Spec**, preserve its original `wayfinder-source` marker unchanged and add/update the separate remediation marker for newly applicable decisions from the input Wayfinder:

```html
<!-- wayfinder-remediation: #<map>; decisions: #<decision>,#<decision>,#<new-decision> -->
```

Then create or update the input map's single revision-aware consumed-state marker:

```html
<!-- wayfinder-decision-states:v1 map=#<map>; states=#<decision>:<state_sha256>,#<decision>:<state_sha256> -->
```

For every authorized decision-state delta item:

* add its current state identity when no prior state entry exists;
* replace only that decision's prior state identity when a revised accepted state has been completely consumed;
* leave unrelated consumed-state entries byte-for-byte unchanged.

A materially revised decision may therefore advance the state marker **without adding a new decision ID** to source/remediation membership.

A Spec may have provenance/state markers for more than one Wayfinder. Never merge a remediation Wayfinder into `wayfinder-source`, replace original source provenance, or use the state marker as architectural authority.

Decision membership, consumed-state advancement, and the semantic Spec amendment are one atomic tracker mutation. If the issue update/readback cannot prove all three agree, treat publication as failed rather than leaving provenance ahead of semantics.

Wayfinder decision tickets and their terminal resolution comments remain the durable home of the decisions themselves.

## 6. Update the Existing Specs

Write each reconciled candidate back to its existing Spec in place.

Do not:

* create new specs for handed-off scope;
* reset branch or baseline metadata;
* replace existing ticket or review lineage;
* create implementation tickets;
* reopen or close existing remediation tickets merely because a spec changed.

Return the amended Spec set to `$to-specs`.

## Completion

Report:

* existing Specs amended or already synchronized;
* source Wayfinder map;
* handoff role (`Derived Spec` or `Remediation Spec`) per Spec;
* newly consumed or advanced decision states per Spec, including delta reason and terminal resolution comment;
* spec sections changed per Spec;
* Architecture Completeness Preflight result;
* concrete contracts/production seams checked when applicable;
* whether legacy decision-state provenance was bootstrapped per Spec;
* whether any ambiguity or architecture blocker prevented amendment.

If a Spec's decision-state delta is empty, make no semantic changes to that Spec and report that it is synchronized with the current accepted decision states of the input Wayfinder.

If the Architecture Completeness Preflight fails, leave all existing Specs and provenance unchanged and present the Human Handoff.

## Transition-Bound Decision-State Consumption

Wayfinder consumption is a semantic state transition, not an issue-number set operation. A decision ID or prior consumed-state identity may not advance merely because the decision was read or a Spec was edited.

For every item in every per-Spec decision-state delta, create one working **Decision-State Consumption Record**:

```text
Decision: #<n>
Target Spec: #<n>
Delta reason: new-decision | legacy-state-bootstrap | revised-decision-state
Terminal resolution comment: <comment id>
Prior consumed state: <state identity | None>
Current accepted state: <state identity>
Affected obligations/sections: <exact mapping>
Semantic representation: <complete | incomplete>
Architecture implementability: <pass | blocked>
Evidence: <current Spec/authority/concrete-seam evidence>
Consumption authorized: <yes | no>
```

`Consumption authorized: yes` requires:

* the current accepted decision-state identity was mechanically resolved from a valid terminal resolution anchor;
* every material consequence of that exact accepted state for the target Spec is mapped to an existing or amended obligation/section, or explicitly shown already represented;
* `Semantic representation: complete`;
* `Architecture implementability: pass` under the existing completeness preflight;
* no unresolved ambiguity about the decision state's applicability to that Spec.

A decision revision that only clarifies or supersedes existing text may legitimately require no new requirement, but its record must name the exact existing representation. A partially incorporated revision remains `no` and its consumed-state identity must not advance.

Before any Spec/provenance mutation require:

```text
Current applicable resolved decisions: <n>
Current accepted state identities resolved: <n>
Decisions without consumable current state: 0
Decision-state delta items: <n>
Decision-state consumption records: <n>
Missing delta records: 0
State-identity mismatches without reconciliation: 0
Legacy ID-only decisions treated synchronized without bootstrap proof: 0
Incomplete semantic representations: 0
Architecture-blocked consumption records: 0
Unauthorized state advancements proposed: 0
Duplicate wayfinder-decision-states:v1 markers for any map: 0
```

Only after all records for the candidate amendment are authorized may the Spec body, decision-membership provenance, and consumed-state marker advance atomically. Immediately read the issue back and mechanically require:

* every authorized current decision ID is present in the proper source/remediation membership marker;
* every authorized current Decision State Identity exactly matches the single state marker for that map;
* no unauthorized decision/state entry advanced;
* the semantic sections named by every record are present in the published body.

This prevents a Spec from claiming that a reopened/revised Wayfinder decision was consumed when it contains only an older accepted state.

