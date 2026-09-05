# wiki/log.md

## [2026-09-04] R2 Decision relationship design | lineage and contextual graph semantics separated

Added the proposed `investment-decisions` relationship model separating lifecycle-lineage edges (`RENEWED_FROM`, `SUPERSEDES`) from materially used prior-Decision context (`PRIOR_DECISION_CONTEXT`). Recorded that candidate retrieval alone does not create durable context, the lifecycle subgraph must remain acyclic, contextual influence may form richer temporal graphs, and R2 implements only lifecycle edges while preserving later many-to-many context compatibility. Updated Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`.

## [2026-09-04] R2 pre-specification design | lifecycle/application/persistence plans made explicit

Added proposed R2 design authority beneath the approved component-boundary plan: a cross-entity interaction map plus detailed Investment Decision lifecycle, application-use-case, and durable-persistence designs. Recorded the resulting Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence` without changing current implementation state.

## [2026-09-04] greenfield wiki bootstrap completion | supporting boundaries registered

Completed the owner-approved greenfield entity registry by adding the explicit Application, Infrastructure, and Interfaces boundaries already established by the approved R1 architecture. All supporting entities begin `pending` with no implementation routing anchors; no legacy entity topology was carried forward.

## [2026-09-04] greenfield wiki reboot | seven domain entities initialized

Re-established the active Living Entity Wiki at the repository root from the approved 0.2.0 greenfield architecture. Initialized seven pending domain entities matching the R1 owner-approved semantic boundaries, retained the pre-greenfield wiki only under `legacy/v0_1/wiki/`, and normalized newly created current/proposed/ADR document naming to the active entity registry and `platform-` cross-cutting convention.
