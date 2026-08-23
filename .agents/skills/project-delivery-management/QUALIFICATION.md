# Project Delivery Management Qualification

These scenarios verify the deterministic focus-control contract in `SKILL.md` without requiring Polaris application-runtime code.

Use synthetic issue states or a disposable tracker fixture. Do not mutate production delivery state merely to run qualification.

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

## Acceptance Coverage

The scenarios cover:

* singleton discovery and zero/one/multiple behavior;
* direct-blocker Wayfinder frontier reduction;
* explicit focus, switch, and exact parallel focus;
* rejection of silent switching;
* automatic focus shrink after completion/direct ineligibility;
* focused-but-stalled retention;
* prevention of automatic admission of newly eligible maps;
* independence from GitHub Project, Priority, assignee, recency, and branch metadata.
