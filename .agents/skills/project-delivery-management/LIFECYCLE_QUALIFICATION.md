# Project Delivery Lifecycle Qualification

These scenarios verify downstream project-delivery authorization, completion, re-entry, and bootstrap-cutover semantics without requiring Polaris application-runtime code.

Use synthetic tracker state or a disposable tracker fixture. Do not mutate production delivery state merely to run qualification.

## Bootstrap cutover

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Pre-bootstrap eligible guard | canonical activation label absent; Wayfinder A open with no direct blocker | `guard A` returns `ALLOWED` with `Mode: pre-bootstrap`; no focus state is inferred or persisted |
| Pre-bootstrap blocked guard | activation label absent; A has an open direct map blocker | `guard A` returns `BLOCKED`; compatibility mode does not bypass dependency eligibility |
| Pre-bootstrap reconcile | activation label absent | report derivable frontier; perform no focus mutation |
| Partial activation | canonical label exists but no valid singleton exists | fail closed as invalid activated state; do not fall back to pre-bootstrap mode |
| Activated empty focus | canonical label + one valid singleton; focus `None`; A eligible | `guard A` returns `FOCUS REQUIRED` |
| Bootstrap lifecycle activates mid-run | an implementation lifecycle entered with `ALLOWED / Mode: pre-bootstrap` and that same atomic migration creates the activation label + singleton with empty focus | the current cutover lifecycle may finish under its captured pre-bootstrap authorization; it cannot use that authorization for a new downstream lifecycle |
| Post-cutover next lifecycle | bootstrap ticket completed; singleton active with empty focus | next human lifecycle must obtain explicit focus through `$project-delivery-management`; no pre-bootstrap authorization is reused |
| Bootstrap focus operations | activation label absent; human requests focus/switch/parallel | operation unavailable because no durable focus owner exists yet |
| Pre-bootstrap cross-map dependency | activation label absent; exact cross-Wayfinder edge is otherwise valid | dependency semantic validation/mutation may proceed because native dependency truth is independent of focused-set activation |

## Human-entry actionability

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Focused implementation ticket | parent Spec open/unblocked; governed by focused Wayfinder A | `$implement-ticket` passes project-delivery guard before Ticket-baseline persistence or mutation |
| Unfocused implementation ticket | parent Spec open/unblocked; governed only by eligible unfocused A | `$implement-ticket` fails closed before Ticket-baseline persistence and surfaces explicit `$project-delivery-management` focus/switch/parallel choices |
| Reopened Spec blocker during implementation | dependent Spec S has an existing native blocker B that was closed and is reopened | existing tickets under S become non-actionable immediately; no duplicate blocked state is written |
| Multi-governor implementation | Spec S governed by source A and remediation B; B focused | implementation is authorized because one current governor is allowed |
| Focused verification | Spec S open/unblocked; one governor focused | `$verify-spec` may run; it revalidates before persisting a passing verification receipt |
| Verification loses authorization | focus/dependency state changes before receipt persistence | verification does not persist a passing receipt under stale authorization |
| Focused review | verified Spec S open/unblocked; one governor focused | `$review-spec` may dispatch reviewers; it revalidates before Pending Review Remediation or Exit Receipt persistence |
| To-Specs remediation helper | authorized `$to-specs` invokes `$to-remediation-specs` for an existing governed Spec | child inherits the parent lifecycle authorization; no second focus Human Handoff is introduced |
| To-Tickets remediation helper | authorized `$to-tickets` invokes `$to-remediation-tickets` | child inherits the parent lifecycle authorization; no second focus Human Handoff is introduced |
| Review internal remediation | `$review-spec` is authorized and invokes `$review-spec-remediation` | child inherits parent authorization; no redundant project-focus Human Handoff |
| Root-closure verifier | authorized `$implement-ticket` remediation lifecycle dispatches independent verifier | verifier inherits parent lifecycle authorization and does not make a separate focus decision |
| Focused cleanup | reviewed Spec S open/unblocked; one governor focused | `$spec-merge-cleanup` may merge/close only after its own fresh human-entry guard |
| Intentionally non-Wayfinder Spec | no durable Wayfinder governance exists by design | existing implementation/verification/review/cleanup lifecycle proceeds without fabricating a governor |
| Ambiguous governance | durable provenance/handoff evidence cannot establish the current governor set | affected human-entry lifecycle fails closed rather than selecting a map heuristically |

## Completion and dependency satisfaction

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Spec closes | Spec S is authoritatively closed by reviewed cleanup | existing native dependents observe S as satisfied; no parallel satisfaction marker is written |
| Blocking Spec reopens | previously closed blocker S reopens with dependency edge unchanged | native dependents become ineligible again on their next frontier/actionability read |
| One governor, all work complete | Wayfinder A has no open decisions/fog and all governed Derived/Remediation Specs closed | cleanup comments and closes A, then project-delivery reconciliation removes A from focus |
| Open Remediation Spec remains | A's original Derived Specs are closed but one Remediation Spec governed by A remains open | A stays open; no completion comment claiming delivery complete |
| Open Derived Spec remains | one Derived Spec under A remains open | A stays open |
| Decision remains | all governed Specs closed but one Wayfinder decision remains open | A stays open |
| Fog remains | all governed Specs closed but `Not yet specified` contains unresolved in-scope fog | A stays open |
| Multi-governor Spec completion | completing Spec S is governed by A and B | cleanup independently reconciles both A and B against each map's full governed Spec set |
| Governor complete, sibling governor incomplete | S governed by A/B; A's full scope complete; B still governs another open Spec | A may close while B remains open |
| Closed inconsistent governor | map already closed while durable evidence shows open governed work | cleanup reports inconsistency and does not pretend completion or silently reopen during merge cleanup |
| Post-transition ordering | Spec/map closure is required | authoritative close is persisted first; `$project-delivery-management reconcile` runs afterward |
| Direct map blocker after transition | focused A gains an open direct map blocker | reconciliation removes A from focus and selects no replacement |
| Lower-level stall only | A remains map-eligible but current Spec/ticket frontier is blocked | focus remains on A; report focused-but-stalled rather than manufacturing a map blocker |

## Architecture re-entry

| Scenario | Canonical state / action | Expected result |
| --- | --- | --- |
| Closed source Wayfinder re-entry | unresolved architecture belongs unambiguously to closed source map A | `$architecture-remediation` reopens A before creating/reusing decision work; then reconciles project delivery |
| Closed remediation Wayfinder re-entry | Spec source is A but blocker belongs to remediation governor B, which is closed | reopen B, preserve `wayfinder-source: A`, and route the decision under B |
| Reopen does not focus | A reopens while focus is empty or on B | A is not auto-focused; later `$wayfinder` entry requires explicit focus/switch/parallel authorization as applicable |
| Already-open governor | blocker belongs to open A | no synthetic close/reopen cycle; create/reuse decision under A |
| Existing authority resolves blocker | blocker is fully determined by current accepted authority | create no decision and do not reopen a closed map merely to restate authority |
| Ambiguous re-entry owner | multiple governors plausibly own blocker and durable context cannot distinguish one | fail closed; no map reopen and no duplicate decision creation |
| Reopen persistence failure | closed map cannot be reopened or verified open | halt before decision creation/reuse |
| Decision persistence then reconcile | reopened/open map receives new unresolved decision ticket | durable tracker mutation happens first, project-delivery reconciliation second; no focus is invented |

## Acceptance Coverage

The scenarios cover:

* explicit pre-bootstrap versus activated focus enforcement and fail-closed partial cutover;
* the atomic bootstrap lifecycle exception without reusable post-cutover authorization;
* focus/dependency guards at implementation, verification, review, and cleanup human-entry boundaries;
* authorization inheritance for `$to-remediation-specs`, `$to-remediation-tickets`, `$review-spec-remediation`, and the independent Root Closure verifier;
* no lifecycle-local focus mutation;
* authoritative transition-before-reconciliation ordering;
* Spec closure as native dependency satisfaction and reopen as automatic re-blocking;
* completion across all currently governed Derived and Remediation Specs;
* reconciliation of every Wayfinder governing a completing Spec;
* unresolved decision/fog preventing Wayfinder delivery completion;
* direct map ineligibility versus lower-level focused-but-stalled behavior;
* closed-map architecture re-entry without automatic focus;
* source-versus-remediation governor preservation;
* ambiguous/non-resumable re-entry failure semantics.
