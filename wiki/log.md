# wiki/log.md

## [2026-09-07] Independent R2 correction remediation | support and temporal semantics completed

Resolved restoration support-ID membership and cross-root compatibility for #296, then completed six additional owner-guided decisions covering recursive independent activation, minimal whole-result support, strict-prefix historical validation, explicit observation boundaries and posture ordering, replay versus distinct correction support, and unsupported-Need initiation-lineage eligibility. Current support excludes defeated/unrelated ancestry, terminal conflicts cannot be resolved by recency, and append/version/clock consequences are distinct. Reconciled the correction authority and its foundation/lifecycle/application/persistence consumption, updating Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`. This is architecture completion for Independent Spec #278, not implementation certification.

## [2026-09-07] R2 temporal cardinality completion | zero-claim lifecycle state made explicit

Closed the remaining Ticket #296 temporal-result gap after implementation entry exposed a legitimate zero-effective-claim boundary. Historical querying now distinguishes a Decision not yet known at `known_at=K` from a known Decision whose initiation/lifecycle claim is not yet effective at `T`: the former is a not-found-at-knowledge-cutoff outcome outside lifecycle interpretation, while the latter is explicit `NOT_YET_EFFECTIVE`. The known-Decision lifecycle result universe is now `NOT_YET_EFFECTIVE | DETERMINATE | CONTESTED`; not-yet-effective Decisions have no work posture and cannot authorize ordinary Decision work. Correction/version semantics now include transitions to/from `NOT_YET_EFFECTIVE`, while wall-clock passage across future effective time still creates no synthetic fact or `DecisionVersion`. Updated Planned knowledge for `investment-decisions`.

## [2026-09-07] R2 lifecycle correction bounded closure | disposition-only correction contract finalized

Replaced the too-broad Ticket #296 correction model after a bounded adversarial closure pass. R2 lifecycle correction now targets only lifecycle-disposition claims contributed by `DecisionInitiated`, substantive/external resolution facts, or prior lifecycle corrections; Subject, Scope, work-posture, and relationship correction are explicitly outside #296. Unsupported-Need retraction is a qualification of the initial disposition claim, work posture is independently reconstructed when corrected lifecycle returns to `UNRESOLVED`, historical acts remain valid under what was known when recorded, contested interpretation is explicit/queryable, lifecycle sequence may advance without `DecisionVersion`, and clock passage never manufactures a version. Older R2 wording implying Scope correction is currently available is explicitly superseded; erroneous historical Scope/Subject correction is deferred to a future purpose-specific contract rather than a generic correction framework. Updated Planned knowledge for `investment-decisions`.

## [2026-09-07] R2 lifecycle correction reconciliation | correction chains made deterministic

Closed the Ticket #296 implementation-entry design gap by freezing explicit lifecycle-correction target/effect/reconciliation semantics: corrections target one earlier same-Decision lifecycle fact/correction; `QUALIFY` supplies a complete replacement claim; `DISCONFIRM` withdraws support; disconfirming a correction restores the interpretation immediately preceding it on that branch; equivalent surviving claims coalesce while incompatible support remains contested; knowledge-time filtering precedes effective-time correction application; and lifecycle sequence remains distinct from current-state `DecisionVersion`. Also synchronized that the post-#299 foundation public contract is complete and surviving older “foundation unresolved” wording is not implementation authority. Updated Planned knowledge for `investment-decisions`.

## [2026-09-07] R2 unresolved lifecycle work posture | #295 implementation

Implemented the Decisions-domain forward lifecycle/work-posture slice: distinct supported lifecycle disposition, unresolved `ACTIVE`/`DEFERRED`/`WITHDRAWN` posture, trusted Human Investment Decision Deferral/substantive-resolution effects, work withdrawal/resumption, External Resolution, operative-applicability guards, immutable lifecycle facts, and resolved-state fail-closed behavior. Corrected the derived Investment Decisions wiki wording to match the already-frozen no-`ActorKind` Actor Attribution contract.

## [2026-09-06] R2 foundation public contract completion | implementation-time design gaps closed

Closed the post-#294 foundation design gaps before further R2 implementation: established canonical UUIDv4-backed `PortfolioId` ownership under Portfolio & Risk without requiring a full Portfolio implementation; completed Decision/Need/Operation identity contracts; made Decision Scope membership unordered and unique over canonical Portfolio identity; fixed Decision Subject, lifecycle-fact naming, common metadata naming, Actor/trigger/technical provenance typing, fact-specific business-basis rules, and the behavior-oriented public Decision construction/reconstruction surface. Updated Planned knowledge for `portfolio-risk`, `investment-decisions`, `application-use-cases`, and `durable-persistence`.

## [2026-09-06] R2 foundation contract audit | public identity and design gaps surfaced

Re-opened R2 foundation design completeness after Ticket #294 exposed implementation-selected public contracts that upstream authority had not frozen. Added UUIDv4-backed opaque `InvestmentDecisionId`, `DecisionNeedId`, and `OperationId` contracts; restored explicit lifecycle-fact vocabulary including separate Scope establishment/revision and qualified `DecisionLifecycleFactMetadata`; and recorded unresolved public-contract questions for Decision Subject, canonical Portfolio identity/reference, Scope ordering/equality, Actor/provenance/business references, and the public Decision construction/export surface. Updated Planned/Open Question knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence`.

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

Added proposed R2 design authority beneath the approved R2 component-boundary plan: a cross-entity interaction map plus detailed Investment Decision lifecycle, application-use-case, and durable-persistence designs. Recorded the resulting Planned knowledge for `investment-decisions`, `application-use-cases`, and `durable-persistence` without changing current implementation state.

## [2026-09-04] greenfield wiki bootstrap completion | supporting boundaries registered

Completed the owner-approved greenfield entity registry by adding the explicit Application, Infrastructure, and Interfaces boundaries already established by the approved R1 architecture. All supporting entities begin `pending` with no implementation routing anchors; no legacy entity topology was carried forward.

## [2026-09-04] greenfield wiki reboot | seven domain entities initialized

Re-established the active Living Entity Wiki at the repository root from the approved 0.2.0 greenfield architecture. Initialized seven pending domain entities matching the R1 owner-approved semantic boundaries, retained the pre-greenfield wiki only under `legacy/v0_1/wiki/`, and normalized newly created current/proposed/ADR document naming to the active entity registry and `platform-` cross-cutting convention.
