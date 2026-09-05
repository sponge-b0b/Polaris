# wiki/log.md

## [2026-09-04] R2 temporal and identity precision | final audit invariants tightened

Tightened the proposed R2 design after final adversarial pressure testing: one Decision Need now grounds at most one Investment Decision; `ESTABLISHED` Decision Scope requires at least one Portfolio; deliberate hold/no-action versus non-resolving Recommendation rejection is explicit at the human-judgment seam; and `as_known_at(K)` is formally the state effective at K using only knowledge recorded by K, preventing future-effective known facts from applying early. Updated Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`.

## [2026-09-04] R2 final adversarial reconciliation | late correction and continuity provenance made durable

Closed two final Spec-readiness gaps: late External Resolution and unsupported-Need findings may qualify any previously recorded lifecycle disposition only through append-only correction, and every committed distinct Decision identity now preserves the continuity determination, materially considered candidate Decisions, attributable create-new basis, and revalidation knowledge/guard that explain why it was treated as a new coherent choice. Also made contested Supersession/operative applicability fail closed for ordinary work. Updated Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`.

## [2026-09-04] R2 adversarial follow-up | continuity and operative-work ambiguities closed

Closed the final Spec-readiness ambiguities exposed after the atomic lifecycle simplification: re-Deferral now appends a new trusted human-Deferral fact, ordinary unresolved work/judgment commands require the Decision to remain operative rather than supportably superseded, and R2 continuity no longer leaves matching logic to implementation—existing unresolved candidates require an explicit continue/create-new determination and missing or inconsistent determination fails closed. Updated Planned knowledge for `investment-decisions` and `application-use-cases`.

## [2026-09-04] R2 final audit correction | lifecycle disposition simplified and contested interpretation preserved

Collapsed the second-audit four-axis draft into the final three-concern model: supported lifecycle disposition (`UNRESOLVED`, `SUBSTANTIVELY_RESOLVED`, `EXTERNALLY_RESOLVED`, `NEED_RETRACTED_UNSUPPORTED`), unresolved work posture (`ACTIVE`, human-`DEFERRED`, `WITHDRAWN`), and orthogonal Supersession relationships. Preserved unresolved/partial Scope, fail-closed continuity arbitration, many-to-many lineage, append-only correction, dual temporal queries, and explicit contested lifecycle interpretation rather than last-writer-wins. Updated Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`.

## [2026-09-04] R2 second adversarial audit | Decision Need status separated from judgment resolution

Refined the proposed R2 lifecycle after the second adversarial pass found that External Resolution and unsupported-Need correction had still been conflated with substantive judgment state. Split Decision Need status, judgment-resolution status, unresolved work posture, and Supersession into independent dimensions; added zero/partial/established Scope completeness, one-Need/one-Decision integrity, explicit re-Deferral, conservative all-unresolved continuity candidates for R2, and correction semantics that preserve human acts when later Need facts change effective lifecycle understanding. Updated Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`.

## [2026-09-04] R2 pre-Spec audit remediation | lifecycle, continuity, graph, and temporal gaps closed

Reworked the proposed R2 Decision design after an adversarial documentation audit. Separated resolution disposition, unresolved work posture, and Supersession; allowed unresolved Scope at initiation; made Deferral depend on a trusted Human Investment Decision basis; added explicit decision-work withdrawal and unsupported-Need retraction semantics; added fail-closed continuity arbitration for concurrent initiation; defined non-destructive lifecycle correction plus distinct as-known-at/effective-at reconstruction; removed one-to-one Supersession assumptions; made prior-Decision context bind the target state actually used; and added the Action Continuity ↔ Portfolio & Risk interaction seam. Updated Planned knowledge for `investment-decisions`, `application-use-cases`, `durable-persistence`, `governance-authority`, `portfolio-risk`, and `action-continuity`.

## [2026-09-04] R2 Decision relationship design | lineage and contextual graph semantics separated

Added the proposed `investment-decisions` relationship model separating lifecycle-lineage edges (`RENEWED_FROM`, `SUPERSEDES`) from materially used prior-Decision context (`PRIOR_DECISION_CONTEXT`). Recorded that candidate retrieval alone does not create durable context, the lifecycle subgraph must remain acyclic, contextual influence may form richer temporal graphs, and R2 implements only lifecycle edges while preserving later many-to-many context compatibility. Updated Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`.

## [2026-09-04] R2 pre-specification design | lifecycle/application/persistence plans made explicit

Added proposed R2 design authority beneath the approved component-boundary plan: a cross-entity interaction map plus detailed Investment Decision lifecycle, application-use-case, and durable-persistence designs. Recorded the resulting Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence` without changing current implementation state.

## [2026-09-04] greenfield wiki bootstrap completion | supporting boundaries registered

Completed the owner-approved greenfield entity registry by adding the explicit Application, Infrastructure, and Interfaces boundaries already established by the approved R1 architecture. All supporting entities begin `pending` with no implementation routing anchors; no legacy entity topology was carried forward.

## [2026-09-04] greenfield wiki reboot | seven domain entities initialized

Re-established the active Living Entity Wiki at the repository root from the approved 0.2.0 greenfield architecture. Initialized seven pending domain entities matching the R1 owner-approved semantic boundaries, retained the pre-greenfield wiki only under `legacy/v0_1/wiki/`, and normalized newly created current/proposed/ADR document naming to the active entity registry and `platform-` cross-cutting convention.
