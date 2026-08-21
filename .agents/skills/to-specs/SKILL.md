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

   If one or more derived or remediation in-progress Specs exist after reconciliation, invoke `$to-remediation-specs` and do not create another spec for that handed-off scope.

   `$to-remediation-specs` owns recovery of existing specs, Wayfinder decision provenance, delta analysis, duplicate prevention, and in-place amendment.

   If no in-progress handed-off Spec exists, continue with normal spec creation.

3. **Architecture preflight.** For software work, identify the affected Living Entity Wiki entities and compare the distilled solution against their applicable invariants, decisions, rejections, boundaries, and current authoritative sources.

   Confirm that:

   * the architecture impact is understood;
   * required architecture decisions and documentation have already been reconciled;
   * no material architecture question remains unresolved;
   * the solution still agrees with the current architecture.

   If not, halt with a Human Handoff. Do not make material architectural decisions while writing the spec.

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

5. **Write and publish the spec(s)** using the template below. Apply the `ready-for-agent` triage label.

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

6. **Human Handoff Intercept.** After all creation or remediation work for the source is complete, identify every in-progress Spec handled for the source — derived or remediation — that is ready for ticket creation or reconciliation.

   Output one copy-ready handoff line per Spec:

   ```text
   $to-tickets - <Spec Title> (<Spec URL>)
   ```

   If multiple Specs exist, output all lines together. If only one exists, output one line.

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
