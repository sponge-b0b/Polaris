# To Tickets Project-Delivery Guard Qualification

These scenarios verify `$to-tickets` actionability gating without requiring Polaris application-runtime code.

Use synthetic tracker state or a disposable tracker fixture. Do not mutate production delivery state merely to run qualification.

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Focused actionable Spec | Spec S open/unblocked; governed by focused Wayfinder A | guard passes before drafting/publishing and normal `$to-tickets` lifecycle proceeds |
| Dependency-blocked Spec | S has any open direct native blocker | stop before drafting/branch/ticket mutation and report blocker |
| Closed blocker | S blocked by B; B closed | blocker is satisfied; continue if focus guard passes |
| Reopened blocker | same edge; B reopens | S immediately fails actionability guard again; no duplicate state written |
| Eligible but unfocused governor | S open/unblocked; governed only by eligible Wayfinder B; focus `{A}` | stop before substantive work and surface explicit `$project-delivery-management` switch/parallel choices |
| No current focus | S open/unblocked; governed by eligible A; focus `{}` | stop and require explicit `$project-delivery-management focus A`; `$to-tickets` does not focus A itself |
| Multiple governors, one focused | S governed by source A and remediation B; B focused | actionability passes because at least one current governor is authorized |
| Multiple governors, none focused | S governed by A/B; neither focused | fail closed and report both guard results |
| Directly blocked governor plus focused governor | S governed by A/B; A map-blocked; B focused and eligible | B authorization is sufficient; do not promote A's map blocker to the Spec |
| Ambiguous governance | provenance/handoff evidence cannot determine governing Wayfinder set | fail closed and route back to `$to-specs` reconciliation rather than guessing |
| Spec Review source | human invokes `$to-tickets` on a `Spec Review: ` issue | recover `Parent Spec`, apply the same Spec dependency/focus guard before remediation ticket reconciliation |
| Guard before branch setup | actionability fails | no Spec branch creation/switch, workspace metadata write, ticket proposal mutation, or ticket publication occurs |
| Intentionally non-Wayfinder Spec | no durable Wayfinder governance exists by design | preserve existing non-Wayfinder lifecycle; do not fabricate a Wayfinder or project focus |
| Project metadata changes | Project/priority/assignee/order changes only | actionability result is unchanged |

## Acceptance Coverage

The scenarios cover:

* open/unblocked Spec eligibility;
* authoritative closure and reopen behavior of native Spec dependencies;
* focused-Wayfinder intersection without focus mutation in `$to-tickets`;
* multi-Wayfinder remediation governance;
* Spec Review parent-Spec guarding;
* fail-closed ambiguity handling;
* guard ordering before substantive ticket/branch mutation;
* preservation of intentionally non-Wayfinder lifecycle paths;
* independence from GitHub Project metadata.
