# Project Tracking Focus-Aware Qualification

These scenarios verify focus-aware GitHub Project projection without making the Project authoritative.

Use synthetic tracker/Project fixtures or a disposable Project. Do not mutate production delivery state merely to run qualification.

## Base route and focus overlay

| Scenario | Base lifecycle + project-delivery context | Expected final projection |
| --- | --- | --- |
| Focused Wayfinder decision work | Wayfinder Map / Architecture Decision / base `$wayfinder` / `focused` | `Workflow State=Architecture Decision`; `Work Status=In Progress`; `Next Skill=$wayfinder` |
| Eligible-unfocused Wayfinder decision work | same base / `eligible-unfocused` | lifecycle state preserved; `Work Status=Ready`; `Next Skill=$project-delivery-management` |
| Focused Wayfinder ready to spec | Wayfinder Map / Ready to Spec / base `$to-specs` / `focused` | `Work Status=In Progress`; `Next Skill=$to-specs` |
| Eligible-unfocused Wayfinder ready to spec | same base / `eligible-unfocused` | `Work Status=Ready`; `Next Skill=$project-delivery-management` |
| Directly ineligible Wayfinder | active Wayfinder lifecycle state / `ineligible` | lifecycle state preserved; `Work Status=Blocked`; `Next Skill=None` |
| Focused-but-stalled Wayfinder | active Wayfinder lifecycle state / `focused-stalled` | lifecycle state preserved; `Work Status=In Progress`; base `Next Skill` preserved; never project false dependency blocking |
| Complete Wayfinder | Wayfinder Map / Complete / base Done+None | `Work Status=Done`; `Next Skill=None`; non-complete focus context rejected |
| Focused descendant | Spec / Ready to Verify / base `$verify-spec` / `focused` | base `Work Status` preserved; `Next Skill=$verify-spec` |
| Eligible-unfocused descendant | Spec / Ready to Verify / base `$verify-spec` / `eligible-unfocused` | `Workflow State=Ready to Verify`; `Work Status=Ready`; `Next Skill=None` |
| Ineligible descendant | Implementation Ticket / Ready to Implement / base `$implement-ticket` / `ineligible` | lifecycle state preserved; `Work Status=Blocked`; `Next Skill=None` |
| Focus restored | previously suppressed Spec becomes governed by a focused Wayfinder | next reconciliation restores validated base lifecycle `Next Skill` |
| Multiple governors, one focused | Spec governed by A/B; B focused | classify `focused`; preserve ordinary lifecycle route |
| Multiple governors, none focused | Spec governed by eligible A/B; neither focused | classify `eligible-unfocused`; suppress `Next Skill` |
| Non-Wayfinder artifact | intentional non-Wayfinder formal artifact; no project-delivery context | ordinary base projection remains unchanged |
| Pre-bootstrap | Wayfinder-managed artifact before activation; no project-delivery context | ordinary base projection remains unchanged |

## Invalid projection cases

| Scenario | Input | Expected result |
| --- | --- | --- |
| Overlay cannot repair bad base route | Spec / Ready to Verify / base `$implement-ticket` / `eligible-unfocused` | reject base route before overlay; do not normalize to `None` |
| Project delivery skill on descendant | Spec row final `Next Skill=$project-delivery-management` | reject; option is valid only for eligible-unfocused Wayfinder Map projection |
| Focused blocked lifecycle map | Wayfinder Map / Workflow State Blocked / `focused` | reject contradictory overlay |
| Eligible-unfocused blocked lifecycle map | Wayfinder Map / Workflow State Blocked / `eligible-unfocused` | reject contradictory overlay |
| Focused-stalled descendant | Spec / `focused-stalled` | reject; state is Wayfinder Map only |
| Completed artifact with active focus state | Workflow State Complete + `focused` | reject |
| Ambiguous project-delivery context | caller cannot determine current governors/focus | reject before Project mutation; do not inspect Project to guess |

## Completion contradiction

| Scenario | Durable tracker state | Requested result |
| --- | --- | --- |
| Derived Spec open | Wayfinder A governs open Derived Spec S1 | reject A `Complete` projection |
| Remediation Spec open | A's Derived Specs closed; A governs open Remediation Spec S2 | reject A `Complete` projection |
| Reverse remediation provenance only | S2 durably identifies A via `wayfinder-remediation`, forward handoff temporarily absent but unambiguous | treat S2 as governed contradiction evidence; do not claim A complete |
| Open decision remains | all governed Specs closed; A has open Wayfinder decision | reject A `Complete` projection |
| Unresolved fog remains | all governed Specs closed; `Not yet specified` still contains unresolved in-scope item | reject A `Complete` projection |
| All governed work closed | all Derived/Remediation Specs closed, no decision/fog remains, caller supplies authoritative Complete | no contradiction; helper may project Complete but does not infer it |
| Multi-governor completion | completing Spec S governed by A/B; B has another open Remediation Spec | reject B completion while allowing independently authoritative A completion when A has no contradiction |

## Schema rollout and drift

| Scenario | Project schema/action | Expected result |
| --- | --- | --- |
| Option absent before rollout | existing `Next Skill` lacks `$project-delivery-management` | one-time operator rollout appends it while preserving every existing option ID |
| Rollout rerun | option already exists exactly once | no mutation; success is idempotent |
| Duplicate option | option exists more than once | rollout fails closed; no heuristic choice |
| Missing/ambiguous Next Skill field | zero or multiple matching single-select fields | rollout fails closed |
| Steady-state missing option after activation | `$project-tracking` reads schema without required option | `PROJECT TRACKING: DRIFT`; no schema repair |
| No scheduler fields | schema has no `Active`, `Frontier`, or `Queued` fields | correct; do not create them |
| Project mutation failure | authoritative workflow/focus transition already persisted, item update fails | report `PROJECT TRACKING: DRIFT`; never roll back lifecycle/focus/dependency truth |
| Verification mismatch | item edit returned success but re-read differs | report drift; do not claim sync |

## Acceptance Coverage

The scenarios cover:

* focused=`In Progress`, eligible-unfocused=`Ready`, genuinely ineligible=`Blocked`, complete=`Done` for Wayfinder delivery projection;
* `Workflow State` remaining lifecycle truth independent of focus;
* `$project-delivery-management` only as the eligible-unfocused Wayfinder `Next Skill`;
* descendant `Next Skill` suppression and restoration;
* focused-but-stalled remaining `In Progress`;
* validation of base lifecycle route before focus overlay;
* all-governed Derived/Remediation completion contradiction checks plus unresolved decision/fog;
* one-time idempotent Project option rollout without new scheduler fields;
* steady-state refusal to repair Project schema;
* Project drift remaining downstream and non-authoritative.
