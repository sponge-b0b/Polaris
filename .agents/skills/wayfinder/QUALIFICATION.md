# Wayfinder Project-Delivery Focus Qualification

These scenarios verify `$wayfinder` integration with `$project-delivery-management` without requiring Polaris application-runtime code.

Use synthetic issue/tracker state or a disposable tracker fixture. Do not mutate production delivery state merely to run qualification.

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Chart while another map is focused | focus `{A}`; human charts new Wayfinder B | B and its decision graph are created; focus remains `{A}`; no synthetic A→B blocker |
| Chart during parallel focus | focus `{A,B}` authorized; human charts C | C is captured but does not join focus or parallel authorization |
| Chart-time research | A focused; charting new B requires research to form the map | chart-time research may run; B is not substantively worked and focus does not change |
| Focused map advancement | focus `{A}`; human invokes `$wayfinder` on A/decision under A | reconcile + guard return allowed before claim; normal Wayfinder HITL lifecycle proceeds |
| Guard before claim | focus `{A}`; human invokes decision under B | B decision is not assigned/claimed before focus guard result is known |
| Empty focus activation accepted | focus `{}`; B eligible; human invokes `$wayfinder` on B and answers `yes` to focus gate | `$project-delivery-management focus B` is authorized by the explicit human response, persisted, then guard is rerun before claim |
| Empty focus activation declined | focus `{}`; B eligible; human answers `no` | focus remains empty; decision is not claimed or mutated |
| Existing different focus | focus `{A}`; B eligible; human invokes `$wayfinder` on B | fail closed before claim; surface `switch-focus B` and exact `parallel-focus` choices; no implicit switch |
| Exact parallel authorization | focus `{A,B}` with matching authorization; human invokes decision under B | guard allows B; work proceeds |
| Non-member of parallel set | focus `{A,B}`; C later becomes eligible; human invokes C | guard returns focus required; C is not auto-admitted |
| Direct map blocker appears | focus `{A}`; A gains an open direct map blocker before/after a Wayfinder transition | reconciliation removes A from focus and selects no replacement |
| Lower-level blockers only | focus `{A}`; A remains map-eligible; all open A decisions are blocked | retain A focus and report `PROJECT DELIVERY: FOCUSED-BUT-STALLED` with exact decision blockers |
| Decision completion | A focused; decision under A is durably closed and map updated | project-delivery reconciliation runs only after authoritative Wayfinder mutation succeeds |
| Reconciliation failure | Wayfinder mutation succeeds but project-delivery state cannot be reconciled | authoritative Wayfinder mutation remains durable; no downstream lifecycle handoff depending on focus is presented |
| Route clear to Specs | A focused; final decision resolves and Post-Resolution Gate passes | hand off `$to-specs` for A; focus remains on A across the handoff |
| Independent decision frontier | A focused; multiple unblocked A decisions remain | emit multiple `$wayfinder` handoffs; map-level WIP does not serialize independent work inside A |
| Focus is not dependency | A focused; B eligible but unfocused | no blocker edge is created merely because B is queued |

## Acceptance Coverage

The scenarios cover:

* chart/capture while another Wayfinder is focused without stealing focus;
* chart-time research as part of the capture exception;
* focus authorization before any durable decision claim/mutation;
* explicit empty-focus establishment with a human yes/no gate;
* rejection of silent focus switching;
* exact parallel-focus membership and no automatic expansion;
* deterministic focus removal after direct map ineligibility with no successor selection;
* focused-but-stalled retention for lower-level blockers;
* strict separation of dependency eligibility from focus/WIP policy;
* post-transition reconciliation ordering;
* preservation of existing Wayfinder HITL/frontier behavior;
* focus continuity across the `$to-specs` handoff.
