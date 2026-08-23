# Project Delivery Management Qualification

These scenarios verify the deterministic project-delivery control contract in `SKILL.md` without requiring Polaris application-runtime code.

Use synthetic issue states or a disposable tracker fixture. Do not mutate production delivery state merely to run qualification.

## Focus-control scenarios

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Missing singleton after bootstrap | zero issues with `project-delivery:management` | `INVALID STATE`; no focus mutation |
| Duplicate singleton | two issues with `project-delivery:management` | `INVALID STATE`; no heuristic selection |
| Empty focus, several eligible maps | focus `None`; frontier contains A/B/C; `status` | reports A/B/C as eligible-unfocused; no map auto-focused |
| Explicit focus | empty focus; A eligible; human `focus A` | authorization comment persisted; focus becomes `{A}` |
| Silent switch attempt | focus `{A}`; B eligible; internal `guard B` | `FOCUS REQUIRED`; focus remains `{A}` |
| Explicit switch | focus `{A}`; B eligible; human `switch-focus B` | focus becomes `{B}`; no synthetic A→B blocker |
| Exact parallel focus | A/B eligible; human `parallel-focus A B` | focus `{A,B}` plus matching authorization comment |
| No automatic parallel expansion | focus `{A,B}`; C later becomes eligible | focus remains `{A,B}` |
| Direct blocker invalidates focus | focus `{A,B}`; A gains open direct blocker | reconcile removes A, retains B, clears current parallel authorization |
| Focused map completes | focus `{A}`; A closes | reconcile removes A; no successor auto-selected |
| Blocked activation | B has open direct blocker; human `focus B` | reject activation and list blocker |
| Focused-but-stalled | A remains map-eligible; authoritative lower-level frontier has only blocked work | retain `{A}` and report `FOCUSED-BUT-STALLED` |
| Project metadata changes | Priority/Project status/assignee changes with canonical tracker state unchanged | frontier/focus result unchanged |
| Invalid parallel state | focus `{A,B}` but no matching parallel authorization | `INVALID STATE`; do not choose a member |
| Closed singleton | exactly one labeled singleton but it is closed | `INVALID STATE`; do not create/select replacement |

## Cross-Wayfinder dependency scenarios

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Same-lineage decision edge | decisions D1/D2 resolve to Wayfinder A | `$project-delivery-management` declines semantic ownership; existing Wayfinder owner handles the edge |
| Cross-lineage decision edge | D-A under Wayfinder A requires D-B under Wayfinder B | exact D-A `blocked by` D-B accepted when closure of D-B satisfies the prerequisite |
| Cross-lineage Spec edge | Spec A under Wayfinder A requires completed Spec B under Wayfinder B | exact Spec A `blocked by` Spec B accepted |
| Cross-lineage ticket edge | ticket A requires ticket B from another Wayfinder lineage | exact ticket relationship accepted when ticket completion is the narrowest sufficient boundary |
| Cross-level edge | downstream decision requires completion of an upstream Spec | decision→Spec accepted when it is narrower and more accurate than a map-level edge |
| True whole-map prerequisite | every part of Wayfinder B destination requires Wayfinder A delivery completion | B `blocked by` A accepted only after no narrower authoritative blocker is sufficient |
| Over-broad whole-map proposal | some work under downstream map can proceed independently | reject map→map edge; require narrower placement |
| Cycle | blocker transitively depends on proposed consumer | reject before mutation with cycle failure |
| Ambiguous lineage | consumer or blocker has multiple plausible governing Wayfinders with no exact relationship context | reject without choosing a lineage |
| Ambiguous placement | prerequisite is real but no evidence establishes the narrowest completion boundary | reject without mutation |
| Unsupported inference | relationship proposed from title similarity, labels, Project state, or broad prose only | reject without mutation |
| Existing exact edge | authorized cross-lineage edge already exists | verify and return idempotent success; no duplicate write |
| Closed blocker | exact native dependency remains and blocker closes | dependency is satisfied; do not delete the edge merely because it is currently satisfied |
| Reopened blocker | previously closed blocker reopens with edge unchanged | native relationship becomes blocking again automatically |
| Verified removal | authoritative evidence says an exact cross-lineage prerequisite no longer applies | remove only that edge and verify absence |
| Mutation verification failure | helper command returns but relationship cannot be re-read as requested | report invalid dependency state; do not write duplicate text state |
| Hierarchy protection | cross-Wayfinder dependency reconciliation is requested | `$project-delivery-management` may use only dependency mechanics; parent/sub-issue hierarchy remains untouched |
| #188/#194 migration shape | broad prose says #194 consumes #188 semantics; #195 independent; #196 requires #189/#190; #198 requires #193 | preserve/reconcile narrow #196→#189/#190 and #198→#193 candidates; never create blanket #194→#188 map blocker |

## Acceptance Coverage

The scenarios cover:

* singleton discovery and zero/one/multiple behavior;
* direct-blocker Wayfinder frontier reduction;
* explicit focus, switch, and exact parallel focus;
* rejection of silent switching;
* automatic focus shrink after completion/direct ineligibility;
* focused-but-stalled retention;
* prevention of automatic admission of newly eligible maps;
* independence from GitHub Project, Priority, assignee, recency, and branch metadata;
* sole project-level semantic ownership of cross-Wayfinder dependency edges while preserving same-lineage owners;
* narrow same-level decision/Spec/ticket relationships and legitimate cross-level relationships;
* the strict whole-map dependency gate;
* cycle, lineage, placement, and unsupported-inference fail-closed behavior;
* idempotent add/remove semantics and post-mutation verification;
* reuse of `$github-issue-dependencies` without transferring hierarchy ownership;
* the #188/#194 narrow dependency shape without a blanket map-to-map edge.
