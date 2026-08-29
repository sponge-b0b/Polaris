---
name: to-specs
description: Turn an explicit planning source and current codebase understanding into one or more implementation specifications and publish or update them in the configured issue tracker.
disable-model-invocation: true
---

This skill takes an explicit planning source and current codebase understanding and produces a spec or specs depending on complexity and scope. Do NOT interview the user — recover and synthesize the required context from the invocation, repository, and durable tracker artifacts.

The issue tracker and triage label vocabulary should have been provided to you — run `$setup-matt-pocock-skills` if not.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## Process

1. **Gather context.** Work from the provided source and explore the repo as needed to understand the current codebase. Use the project's domain glossary vocabulary throughout the spec.

   When the source is a Wayfinder map, treat that map and its resolved decision tickets as the planning source.

   Before any tracker/repository mutation for a Wayfinder-managed source, invoke `$project-delivery-management` `reconcile`, then `guard <Wayfinder>`. Require `PROJECT DELIVERY GUARD: ALLOWED` before reconciling handoff metadata, amending Specs, or publishing new Specs.

   If the source Wayfinder is directly blocked, report its blockers and stop. If it is eligible but unfocused, stop and surface the explicit `$project-delivery-management` focus/switch/parallel choice. `$to-specs` must not establish or change focus itself.

   Read-only context recovery and architecture inspection may happen before the guard. An intentionally non-Wayfinder planning source remains outside Wayfinder focus management; do not invent a governing Wayfinder merely to enroll it.

2. **Resolve spec mode.** When the source is a Wayfinder map, resolve the complete set of existing Spec handoffs before choosing fresh or remediation mode.

   A handoff is one of:

   * **Derived Spec** — a Spec created from this Wayfinder map; the map remains its canonical `wayfinder-source`.
   * **Remediation Spec** — an existing Spec created from another planning source that this Wayfinder is explicitly responsible for reconciling. Remediation does not change the Spec's original source provenance.

   Recover derived Specs from both:

   * explicit `Derived Spec` metadata under `Spec Handoff` on the source Wayfinder map; and
   * existing Specs whose durable tracker provenance unambiguously identifies that Wayfinder as their source, including the canonical `wayfinder-source` marker and legacy source-context references that predate that marker.

   Recover remediation Specs from both:

   * explicit `Remediation Spec` metadata under `Spec Handoff` on the source Wayfinder map; and
   * existing Specs whose `wayfinder-remediation` provenance marker unambiguously identifies that Wayfinder.

   Reconcile each set. If reverse provenance unambiguously establishes a linkage missing from the map's `Spec Handoff`, add the matching `Derived Spec` or `Remediation Spec` linkage before continuing. Do not remove existing linkages, duplicate a linkage, convert one handoff role into the other, replace original `wayfinder-source` provenance to represent remediation, or treat incomplete Wayfinder metadata as proof that no other handed-off Specs exist.

   `Spec Handoff` is additive provenance only. Entry order, issue number, publication order, and handoff role do not define execution order or priority.

   If one or more derived or remediation in-progress Specs exist after reconciliation, invoke `$to-remediation-specs` and do not create another spec for that handed-off scope. Wait for that internal child to return, then continue through dependency/frontier and Wayfinder projection reconciliation below.

   `$to-remediation-specs` owns recovery of existing specs, Wayfinder decision provenance, delta analysis, duplicate prevention, and in-place amendment.

   If no in-progress handed-off Spec exists, continue with normal spec creation.

3. **Architecture preflight.** For software work, identify the affected Living Entity Wiki entities and compare the distilled solution against their applicable invariants, decisions, rejections, boundaries, and current authoritative sources.

   Confirm that:

   * the architecture impact is understood;
   * required architecture decisions and documentation have already been reconciled;
   * no material architecture question remains unresolved;
   * the solution still agrees with the current architecture.

   If not, halt with a Human Handoff. Do not make material architectural decisions while writing the spec and do not publish placeholder Specs merely to reserve ordering or future scope.

   When an originating Wayfinder map or decision is known, use it in the handoff:

   > ⚠️ **Specification is blocked by unresolved architecture.**
   >
   > Please run:
   >
   > ```
   > $wayfinder - <Wayfinder Map or Decision Title> (<URL>)
   > ```

   If no originating Wayfinder artifact can be resolved, report that the architectural planning source must be established before specification can continue rather than guessing one.

4. **Resolve testing seams.** Prefer existing seams to new ones and use the highest practical seam. The fewer seams across the codebase, the better.

   Use seams already established by the resolved solution, durable Wayfinder decisions, or current repository state. Ask the user only when the seam remains genuinely unresolved or multiple materially different seams remain plausible.

5. **Write and publish the complete currently specifiable set** using the template below. Apply the `ready-for-agent` triage label.

   Partition the planning source into every implementation Spec that is currently decision-complete and independently specifiable. Publish that complete set up front; do not serialize Spec creation merely because one Spec depends on another. A blocked Spec may be fully specified and published while remaining non-actionable.

   Do not create a placeholder Spec for scope whose material architecture remains unresolved. Route that scope back through the Architecture preflight instead.

   When sourced from Wayfinder, include the source map and the resolved decision tickets consumed by that spec:

   ```html
   <!-- wayfinder-source: #<map>; decisions: #<decision>,#<decision> -->
   ```

   After publishing, record each newly derived spec on the source Wayfinder map using additive tracker metadata:

   ```markdown
   ## Spec Handoff
   **Derived Spec:** #<spec_issue_number>
   **Derived Spec:** #<spec_issue_number>
   ...
   ```

   An existing Spec intentionally governed by a later Wayfinder uses a distinct linkage:

   ```markdown
   ## Spec Handoff
   **Remediation Spec:** #<spec_issue_number>
   ```

   Record each linkage once. Do not overwrite the Wayfinder map body, duplicate an existing linkage, or rewrite a Spec's original source provenance to represent remediation.

6. **Publish semantic Spec dependencies and derive the frontier.** After all currently specifiable Specs for the source have been published or amended, establish every currently known semantic Spec prerequisite before any `$to-tickets` handoff.

   A dependency says the consumer Spec may not advance until the blocker Spec closes through its authoritative Spec lifecycle. Ticket completion, verification readiness, review passage, `Ready to Merge`, Priority, Project fields, issue order, or handoff order do not satisfy a Spec dependency.

   For each required Spec dependency:

   * recover the governing Wayfinder lineage of consumer and blocker from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence;
   * place the edge on the narrowest authoritative Specs whose closure expresses the prerequisite; do not promote a narrower dependency to a Wayfinder edge;
   * when both Specs belong to the same Wayfinder lineage, `$to-specs` owns the semantic relationship and invokes `$github-issue-dependencies` for the exact native `blocked by` mutation;
   * when the relationship crosses Wayfinder lineages, delegate semantic validation and mutation to `$project-delivery-management` `dependency ensure <consumer> blocked-by <blocker>`;
   * reject same-lineage cycles or incomplete blocker graphs before mutation; cross-lineage cycle/placement validation remains owned by `$project-delivery-management`;
   * re-read the consumer after mutation and require the exact native edge to exist.

   Do not maintain a parallel dependency registry in Spec bodies, handoff metadata, or Project fields. Human-readable planning prose may explain why an edge exists but never substitutes for the native relationship.

   Then re-read every in-progress Derived/Remediation Spec handled for this source, including complete native blocker data.

   The **Spec dependency frontier** is the set of open handled Specs with zero open native blockers directly on the Spec.

   For each Wayfinder-managed Spec in that frontier, recover its complete current governing Wayfinder set from durable source/remediation provenance and reconciled handoff evidence. Invoke `$project-delivery-management` `reconcile` once, then `guard <Wayfinder>` for every governing Wayfinder. The Spec belongs to the **actionable Spec frontier** when at least one governing Wayfinder returns `PROJECT DELIVERY GUARD: ALLOWED`.

   An intentionally non-Wayfinder Spec is durably outside Wayfinder delivery governance. If it is in the Spec dependency frontier, include it directly in the actionable Spec frontier according to its ordinary lifecycle without invoking or inventing a Wayfinder/project-delivery guard.

   Do not assume the invocation source remains the Spec's only or currently focused governor. If a Wayfinder-managed governing set is ambiguous or no governing Wayfinder is authorized, exclude the Spec from the actionable frontier and report the exact reason. One currently focused governing Wayfinder is sufficient.

   Do not persist an active-Spec field, queue, WIP=1 marker, or frontier snapshot. Multiple independent actionable Specs inside the same focused Wayfinder are concurrently actionable.

   A blocked Spec remains published and visible but receives no `$to-tickets` handoff. A Wayfinder-managed Spec governed only by unfocused Wayfinders also receives no handoff.

   Native dependency state is re-read on every reduction. If a blocker Spec is legitimately reopened, the unchanged edge makes the dependent Spec ineligible again automatically; do not invent replacement state.

7. **Project the source Wayfinder into Spec Delivery.** When the planning source is a Wayfinder map, re-read its reconciled Derived/Remediation Spec set after all handoff and dependency mutations above.

   If at least one durably governed Spec remains open, the Wayfinder has crossed the specification boundary. Its Project lifecycle projection is now:

   ```text
   Artifact Type: Wayfinder Map
   Workflow State: Spec Delivery
   Next Skill: None
   Work Status: In Progress
   Root Blocker: None
   Completed On: None
   ```

   `Spec Delivery` means specification has already happened and active governed Specs now own downstream execution. Never leave such a map projected as `Ready to Spec` merely because the map itself remains open.

   Re-read `$project-delivery-management` state after dependency reconciliation and include the source map's current authoritative `Project Delivery State` in the post-transition Project reconciliation set. Preserve existing Project `Area`/`Priority` presentation unless this invocation has separate authority to change them; do not derive those values from planning prose.

   Include the source map in Project reconciliation only after the Spec handoffs/provenance/dependencies are durable. Project drift never rolls back or deletes valid Spec handoffs.

   If no governed Spec remains open, do not manufacture `Spec Delivery`; let the owning completion/re-entry lifecycle project the map's resulting state.

### Mandatory Project Reconciliation

After all Spec publication/amendment, provenance, and native dependency mutations are durable, and after the source-Wayfinder state in Step 7 has been derived, invoke `$project-tracking` as prescribed internal composition **before** Step 8 or any ordinary return.

Build one reconciliation set from the durable post-transition state:

* every handled open Spec with zero open native Spec blockers → base `Spec / Ready to Ticket / $to-tickets / Ready`;
* every handled open Spec with one or more open native Spec blockers → base `Spec / Blocked / None / Blocked`;
* the source Wayfinder map when Step 7 establishes `Spec Delivery` → the exact `Wayfinder Map / Spec Delivery / None / In Progress` projection defined there;
* any other formal artifact whose base lifecycle state changed during this invocation.

Supply current authoritative Project Delivery State separately from the base lifecycle projection. Preserve existing `Area` and `Priority` unless this invocation has separate authority to change them.

Do not ask `$project-tracking` to discover affected artifacts or infer the lifecycle transition. `$to-specs` owns this set and these base states; `$project-tracking` owns validation, delivery overlay, and Project mutation.

If Project synchronization fails, report `PROJECT TRACKING: DRIFT`. Do not roll back durable Spec/Wayfinder state and do not suppress an otherwise-authorized Step 8 handoff.

8. **Human Handoff Intercept.** After all creation/remediation, dependency reconciliation, source-Wayfinder projection, and mandatory Project reconciliation are complete, output handoffs only for Specs in the actionable Spec frontier.

   Output one copy-ready handoff line per actionable Spec:

   ```text
   $to-tickets - <Spec Title> (<Spec URL>)
   ```

   If multiple independent actionable Specs exist, output all lines together and let the user choose or run independent sessions in parallel. If only one exists, output one line.

   If no handled Spec is actionable, report each blocked or unfocused Spec and its exact reason, then stop without a `$to-tickets` handoff.

   Use the actual tracker title and URL. Do not substitute issue numbers for titles.

   Do not invoke `$to-tickets` implicitly. The user chooses which Spec to continue.

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an , I want a , so that

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Architecture Impact

For software work, record:

* Affected entities
* Impact: `none | conforming | extending | changing | retiring`
* Governing architectural decisions or constraints
* Required ADRs/docs already resolved
* Unresolved architecture questions: `none`

Do not duplicate full invariants or architectural documentation into the spec.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

* The modules that will be built/modified
* The interfaces of those modules that will be modified
* Technical clarifications from the developer
* Schema changes
* API contracts
* Specific interactions

Architectural decisions belong here only as references to decisions already resolved during `$wayfinder`, not as new architecture created during specification.

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Testing Decisions

A list of testing decisions that were made. Include:

* A description of what makes a good test (only test external behavior, not implementation details)
* Which modules will be tested
* Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this spec.

## Further Notes

Any further notes about the feature.
