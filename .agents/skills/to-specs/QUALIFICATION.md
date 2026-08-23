# To Specs Dependency-Frontier Qualification

These scenarios verify `$to-specs` publication, dependency, and actionable-frontier behavior without requiring Polaris application-runtime code.

Use synthetic tracker state or a disposable tracker fixture. Do not mutate production delivery state merely to run qualification.

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| One independent Spec | focused Wayfinder A; one decision-complete Derived Spec S1; no blockers | publish S1 and emit one `$to-tickets` handoff |
| Multiple independent Specs | focused A; decision-complete S1/S2/S3; no Spec blockers | publish all three up front and emit three `$to-tickets` handoffs; no active-Spec selection |
| Dependency chain | focused A; S2 semantically requires S1 | publish both Specs, establish native S2 `blocked by` S1, hand off S1 only |
| Blocked-but-published | focused A; S1 has an open native Spec blocker | keep S1 published/visible and emit no handoff for S1 |
| Blocker closes | S2 `blocked by` S1; S1 closes through authoritative Spec lifecycle | S2 enters dependency frontier on next reduction without rewriting the edge |
| Blocker reopens | same edge; S1 legitimately reopens | S2 becomes ineligible again immediately; no replacement state is written |
| Unresolved architecture | source still requires a material architecture decision | publish no placeholder Spec; hand back to `$wayfinder` |
| Handoff order differs | map lists S3, S1, S2 in `Spec Handoff` | order has no scheduling meaning; native blockers + focus alone determine actionability |
| Same-lineage Spec dependency | S1/S2 governed by Wayfinder A | `$to-specs` owns semantic edge, validates cycle safety, delegates exact native mutation to `$github-issue-dependencies` |
| Cross-lineage Spec dependency | S-A governed by Wayfinder A requires S-B governed by Wayfinder B | delegate exact relationship to `$project-delivery-management dependency ensure`; `$to-specs` does not write it directly |
| Same-lineage cycle proposal | existing S1→S2 path plus proposal S2→S1 | reject before mutation |
| Source Wayfinder unfocused | A eligible but not focused; human invokes `$to-specs` for A | fail before handoff/spec mutation and surface `$project-delivery-management` focus/switch/parallel choice |
| Focused Remediation Spec | focused A governs existing Spec S from another source via remediation provenance | S participates in A's actionable frontier without rewriting original `wayfinder-source` |
| Independent remediation + derived Specs | focused A governs Derived S1 and Remediation S2; neither blocked | both may emit `$to-tickets` handoffs in the same result |
| Project metadata changes | Project/priority/assignee/order changes only | Spec dependency/actionable frontier result is unchanged |

## Acceptance Coverage

The scenarios cover:

* complete up-front publication of currently specifiable Specs;
* no placeholder Specs for unresolved architecture;
* provenance-only `Spec Handoff` ordering;
* same-lineage native Spec dependencies and cross-lineage delegation;
* dependency frontier as open Specs with zero open direct blockers;
* focus intersection for the actionable frontier;
* multiple concurrent actionable Specs with no durable Spec scheduler;
* blocked Specs remaining published without handoffs;
* Remediation Specs participating without source-provenance rewriting;
* authoritative closure/reopen dependency satisfaction;
* cycle rejection and independence from Project metadata.
