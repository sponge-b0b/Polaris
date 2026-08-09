---
name: to-specs
description: Turn the current conversation context and codebase understanding into one or more implementation specifications and publish or update them in the configured issue tracker.
disable-model-invocation: true
---

This skill takes the current conversation context and codebase understanding and produces a spec or specs depending on complexity and scope. Do NOT interview the user — just synthesize what you already know.

The issue tracker and triage label vocabulary should have been provided to you — run `$setup-matt-pocock-skills` if not.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary throughout the spec.

2. **Resolve spec mode.** If the invocation references an existing in-progress spec, treat this as re-entry and update that spec rather than creating another one.

   For re-entry:

   * preserve the existing spec identity, branch, baseline, tickets, and review lineage;
   * incorporate only the requirements, Architecture Impact, implementation decisions, and testing decisions affected by the newly resolved work;
   * do not create a new spec unless the new work is genuinely separate scope.

3. **Architecture preflight.** For software work, identify the affected Living Entity Wiki entities and compare the distilled solution against their applicable invariants, decisions, rejections, boundaries, and current authoritative sources.

   Confirm that:

   * the architecture impact is understood;
   * required architecture decisions and documentation have already been reconciled;
   * no material architecture question remains unresolved;
   * the solution still agrees with the current architecture.

   If not, stop and return the issue to `$wayfinder`. Do not make material architectural decisions while writing the spec.

4. Sketch out the seams at which you're going to test the feature. Existing seams should be preferred to new ones. Use the highest seam possible. If new seams are needed, propose them at the highest point you can. The fewer seams across the codebase, the better - the ideal number is one.

   Use seams already established by the resolved solution, existing spec, or current conversation. Ask the user only when the seam remains genuinely unresolved or multiple materially different seams remain plausible.

5. Write the spec(s) using the template below.

   * **Fresh mode:** publish a new spec to the configured issue tracker and apply the `ready-for-agent` triage label.
   * **Re-entry mode:** update the existing spec in place. Do not create a second spec or reset its existing workflow lineage.

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
