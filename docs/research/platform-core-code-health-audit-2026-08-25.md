# Polaris Core Code Health Audit — 2026-08-25

## Research status and authority

This document is **point-in-time research input only**. It records the structural health of the Polaris codebase at the repository snapshot below.

It does **not** establish architecture, authorize refactoring, supersede accepted ADRs, modify existing Specs, satisfy or close `$wayfinder` work, or imply that a finding remains current after the audited repository snapshot. Any finding promoted into implementation or architectural work must be revalidated against current repository state through the applicable workflow.

**Audit date:** 2026-08-25

**Repository snapshot:**

```text
branch: main
commit: 37150063f77903ac58880da5ef0b68ec0381850f
```

**Audit status:** Complete for the audited snapshot. Structural candidate validation and behavioral-baseline classification are complete; remediation and post-remediation re-audit remain future work.

Because Polaris is actively evolving, this audit becomes historical evidence after the snapshot above. Future code-health decisions must revalidate findings against the then-current repository state.

## Purpose

Polaris has accumulated a substantial platform core. Before adding more core capability, this audit asks whether the existing code is structurally healthy enough to extend with confidence.

The audit focuses on existing-code housekeeping rather than feature completeness:

- duplicated code and duplicated knowledge;
- high-complexity functions and maintenance hot spots;
- oversized modules, classes, or methods;
- God-class / divergent-responsibility candidates;
- pass-through layers, speculative abstractions, duplicate representations, and stale compatibility/scaffolding;
- dead or orphaned code;
- dependency and coupling risks;
- refactoring candidates where responsibility or ownership is unclear;
- baseline lint, type, test, and coverage health that affects refactoring confidence.

The objective is not to maximize DRYness or minimize line count. The objective is the **smallest correct, readable, maintainable resulting system**, consistent with `$coding-standards`.

## Executive conclusion

The audited Polaris core is structurally healthier than the raw detector output initially suggested.

The multi-signal investigation rejected several tempting metric-driven conclusions:

- broad SQLAlchemy/repository repetition does not justify a generic repository abstraction;
- repeated ORM declarations largely preserve independent schema ownership;
- `WorkflowFacade` breadth is consistent with a facade and is not itself a structural defect;
- `WorkflowRuntimeAssembler` breadth is expected at a composition root;
- `ServiceRunner` remains cohesive around one application-service execution lifecycle;
- `AutomatedDecisionAuditService` is large but cohesive around one approval/governance lifecycle and is **not** supported as a God class;
- the layered telemetry model is intentional and does not have one missing canonical owner.

The confirmed production code-health work is narrower:

- stale packaging/scaffolding and a small set of verified dead symbols;
- duplicated durable-job **claim-transition** knowledge across two PostgreSQL job repositories;
- internal complexity in decision-evidence reconstruction/persistence;
- workflow-output projection orchestration concentration;
- local complexity in the fail-closed risk-authority gate;
- targeted telemetry/logging policy overlap that requires policy synchronization before cleanup.

No confirmed structural finding currently requires a Wayfinder. The desired ownership for the production refactors is sufficiently clear for direct cleanup or focused Refactor Specs.

The historical full-suite baseline is not green, but focused diagnosis found **no reproduced implementation regressions** among the currently reconstructed failures. The failures are explained by stale tests, one environment prerequisite, stale document paths, observability policy drift, and order-dependent logging-capture defects. Those baseline issues should be repaired before relying on the suite as a regression oracle for the affected refactors.

## Scope

Primary production-code scope:

```text
application/
config/
core/
domain/
integration/
intelligence/
interfaces/
mcp_server/
workflows/
```

Secondary scope:

- `tests/` where test duplication, fixture structure, coverage, or test design materially affects refactoring confidence;
- packaging, lint, typing, coverage, and runtime configuration where stale configuration or duplicate ownership affects code health;
- migrations only where structural or ownership problems are relevant to current code health.

Excluded from production-code metrics unless explicitly noted:

- `.agents/`;
- `docs/` and `wiki/`;
- generated/cache/tool-output directories;
- `audit-polaris-workflow.py` and other standalone workflow-governance tooling that is not part of the Polaris runtime/application packages.

## Evaluation principles

This audit follows repository coding policy rather than generic smell thresholds.

1. **DRY applies to duplicated knowledge, policy, invariants, and business rules — not merely similar syntax.**
2. **Smells are diagnostic signals, not automatic violations.** A large class or repeated block is a candidate for investigation, not proof that extraction is correct.
3. **No speculative abstractions.** A cleanup that adds more machinery than it removes is not automatically an improvement.
4. **One concept, one representation.** Competing models, wrappers, contexts, or state containers are higher-priority than harmless repeated syntax.
5. **Root-cause fixes beat downstream guards.** Repeated defensive logic may indicate an ownership problem.
6. **Architecture takes precedence over local metrics.** A refactor that crosses or weakens an accepted boundary is not justified by a complexity score.
7. **Current-layer correctness wins over compatibility with an incorrect implementation accident.** Downstream consumers should be repaired after the authoritative layer is corrected.

## Methodology

The audit is intentionally multi-signal. No single tool result is treated as truth.

### 1. Repository and configuration inventory

Inspect package/module layout, repository quality configuration, empty/stale modules, package declarations, repeated infrastructure boundaries, and abandoned compatibility/scaffolding.

### 2. Baseline quality gates

Record Ruff, Mypy, Pytest, and coverage under repository configuration so refactoring starts from a known behavioral baseline rather than assuming the suite is green.

### 3. Duplicate-code analysis

Use two independent detectors:

- **Arid 2.x** for Python-aware duplicate detection and structural context;
- **jscpd** as an independent token/text-oriented cross-check.

Production code and tests are measured separately.

Duplicate findings are triaged as repeated syntax, repeated construction/serialization/testing, duplicated business policy/invariants, or competing abstractions. Similar syntax is never sufficient by itself to authorize abstraction.

### 4. Complexity, size, and hotspot analysis

Use Ruff complexity checks and Repowise structural/change-risk evidence to identify functions, modules, and classes requiring inspection. Size alone does not establish a God class.

### 5. Responsibility and God-class review

Inspect actual reasons to change, collaborator/state breadth, caller groups, orchestration/policy/persistence mixing, and dependency blast radius before accepting a divergent-responsibility finding.

### 6. Dead code and stale scaffolding

Cross-check detector output against repository search, package exports, registries, CLI/MCP/plugin/config lookup, dynamic dispatch, tests, public compatibility evidence, and targeted history before declaring code dead.

### 7. Dependency and dynamic-path review

Use `$codebase-memory-mcp` for structural callers, dependencies, impact, and reachability. Use `$codegraph` selectively for event, decorator, callback, registry, plugin, and other implicit runtime paths. Graph blind spots are recorded rather than guessed through.

### 8. Behavioral-baseline decomposition

Reconstruct the historical failure areas, rerun the narrowest deterministic test set available, isolate order-dependent behavior, and classify root causes rather than treating every failed test as an independent production defect.

### 9. Finding disposition

Structural findings use these routes:

| Route | Meaning |
| --- | --- |
| `Direct cleanup` | Obvious local housekeeping with no architectural ambiguity. |
| `Refactor Spec` | Cohesive implementation/refactoring work whose desired ownership is already clear. |
| `Wayfinder` | Genuine architectural fog: competing owners, unclear boundary, contract change, or multiple materially different valid structures. |
| `Accept` | Intentional/cheaper-than-abstraction condition; document rationale if non-obvious. |

## Existing repository quality contract

At the audited snapshot, `pyproject.toml` establishes:

- Python `>=3.12`;
- Ruff linting including McCabe `C90`;
- `max-complexity = 10`;
- repository Mypy configuration;
- coverage source packages for the application/runtime code;
- coverage floor `fail_under = 75`.

The audit does not weaken these settings to make the current code look healthier.

## Quantitative baseline

Tool versions recorded for this snapshot:

```text
uv       0.11.17
Python   3.12.3
Ruff     0.15.22
Mypy     2.3.0
Pytest   9.1.1
Arid     2.0.0
jscpd    5.0.12 (CLI reports `cpd`)
Repowise 0.34.0
```

| Measure | Production | Tests | Notes |
| --- | ---: | ---: | --- |
| Python files / sources | 966 Arid files / 716 jscpd sources | 469 Arid files | Detector corpus semantics differ. |
| Physical/source lines | 186,422 Arid source lines / 185,455 jscpd lines | 125,011 Arid source lines | Do not compare detector line bases directly. |
| Arid analyzed effective lines | 99,930 | 74,221 | Comments/docstrings/imports/signatures ignored. |
| Arid duplicate groups | 1,288 | 1,512 | Complete scans; both exited `1` because findings exist. |
| Arid duplicate effective lines | 11,885 | 12,877 | Redundant normalized lines. |
| Arid duplication % | 11.89% | 17.35% | Python-aware normalized metric. |
| jscpd clones | 587 | invalid run | Test run analyzed zero files because repository config ignores `**/tests/**`. |
| jscpd duplicated lines | 10,296 | invalid run | Production = 5.55% of jscpd line basis. |
| jscpd duplicated tokens | 50,386 | invalid run | Production = 6.66% of jscpd token basis. |
| Ruff | PASS | included | No configured lint or C90 violations. |
| Mypy | PASS | included | `Success: no issues found in 1435 source files`. |
| Pytest | **FAIL** | — | Historical full-suite baseline: 33 failed, 3006 passed, 9 skipped. |
| Coverage | 90.07% | — | 47,279 / 52,489 statements; repository floor 75%. |
| Repowise health | 8.18 average / 5.95 hotspot | — | 1,066 files analyzed; worst score 1.13. |
| Dead-code candidates | 19 Repowise safe-only unused exports plus broader low-confidence candidates | — | Strong subset later verified; several detector labels rejected. |
| God-class labels | 3 Repowise-labelled candidates | — | All three rejected as class-level God-class findings after responsibility review. |

## Structural analysis

### Duplicate-code interpretation

The Arid and jscpd percentages intentionally differ because the tools normalize and count clones differently. The important signal is that both independently identify substantial production duplication; neither percentage is treated as a quality score or direct refactoring target.

Arid production findings are predominantly executable by finding count (`816` executable, `301` declarative, `171` mixed), while the largest raw duplicated regions include substantial declarative model repetition. Blanket DRY extraction would be unsafe.

Final validation produced these conclusions:

- **Database model declarations:** mostly intentional declarative repetition preserving independent schema ownership. No broad abstraction finding.
- **Persistence repositories:** broad SQLAlchemy repetition is mostly independent record-specific behavior. The supported duplicated knowledge is the narrower durable-job claim transition described below.
- **Workflow execution/bootstrap:** facade/composition-root breadth is broadly justified. The missing execution-audit-capability failures were traced to stale tests using an obsolete governed-facade path, not a confirmed production ownership defect.
- **Workflow-output projectors:** output-specific mapping remains intentionally parallel. The confirmed problem is orchestration concentration in `WorkflowOutputProjectionService`, not missing projector inheritance.
- **Telemetry:** multiple semantic emitters are intentional by layer. The confirmed issue is local reporting/policy overlap, not a missing global telemetry owner.

### Repowise structural pass

Repowise 0.34.0 analyzed 1,066 files. Repository-wide average health was `8.18/10`; hotspot health was `5.95/10`.

Repowise reported many `untested_hotspot` biomarkers because its health run did not ingest coverage. Those biomarkers are rejected as evidence of missing tests. Actual coverage for major hotspots is strong, including:

```text
application/decision_evidence/persistence.py                         88.43%
application/projections/workflow_outputs/projection_service.py       87.10%
core/workflow/execution/workflow_facade.py                            87.31%
application/evaluations/risk_authority_gate.py                        91.30%
application/governance/automated_decision_audit.py                    93.62%
config/settings.py                                                     97.61%
core/storage/persistence/governance_audit/governance_audit_models.py  89.57%
core/workflow/bootstrap/workflow_runtime_assembler.py                 96.60%
application/services/base/service_runner.py                           93.85%
```

The strongest structural hotspots were:

| File | Repowise score | Final interpretation |
| --- | ---: | --- |
| `application/decision_evidence/persistence.py` | 1.13 | Large but cohesive around durable evidence reconstruction; internal decomposition is warranted. |
| `application/projections/workflow_outputs/projection_service.py` | 1.34 | Confirmed orchestration concentration; projector ownership remains appropriate. |
| `core/workflow/execution/workflow_facade.py` | 1.80 | Broad facade surface is expected; no class-level split finding promoted. |
| `application/evaluations/risk_authority_gate.py` | 2.34 | One cohesive fail-closed domain decision with local decomposition opportunity. |
| `application/governance/automated_decision_audit.py` | 2.64 | Large but cohesive approval/governance lifecycle; God-class label rejected. |
| `core/workflow/bootstrap/workflow_runtime_assembler.py` | 4.45 | Broad composition-root construction is expected; class-level God-class label rejected. |

### God-class and responsibility conclusions

Repowise labelled `AutomatedDecisionAuditService`, `ServiceRunner`, and `WorkflowRuntimeAssembler` as God classes. Responsibility/caller analysis does not support those labels:

1. **`WorkflowRuntimeAssembler` — reject God-class finding.** It owns construction of the canonical workflow runtime object graph. High fan-out is intrinsic to the composition-root responsibility. Local method decomposition may still be useful, but architectural ownership is not divergent.
2. **`ServiceRunner` — reject God-class finding.** Validation, policy enforcement, retries, runtime metadata, telemetry context, and lifecycle emission participate in one canonical application-service execution lifecycle.
3. **`AutomatedDecisionAuditService` — reject God-class finding.** Automated policy/governance audit recording, human review tasks/decisions, residual-risk acceptance, and governed-output release form one coherent approval/governance lifecycle with a small collaborator surface.

`WorkflowFacade` also has broad surface area and low-cohesion metrics, but that is expected for a facade. Graph and behavioral analysis did not establish a competing-owner or divergent-responsibility defect.

## Candidate validation and disposition

| Candidate | Final disposition | Route / result |
| --- | --- | --- |
| `CH-CANDIDATE-001` stale `web` package/config declaration | Supported. `pyproject.toml` still names `web` in wheel packages and coverage sources while no top-level `web/` package exists. | `Direct cleanup` |
| `CH-CANDIDATE-002` empty bootstrap modules | Supported. Both modules are zero-byte, have no observed references/exports/dynamic lookup, and history shows no implemented responsibility. | `Direct cleanup` |
| `CH-CANDIDATE-003` persistence executable duplication | Partially supported. Broad repository duplication rejected; shared durable-job claim-transition invariant confirmed between projection-job and AI-observability export-job repositories. | `Refactor Spec` for narrow claim transition; otherwise `Accept` |
| `CH-CANDIDATE-004` workflow execution/bootstrap duplication and wiring drift | Structural production finding rejected. `WorkflowFacade`/composition breadth is justified; audited capability failures are stale tests bypassing `GovernedWorkflowExecutionService`. | `Accept` production structure; test remediation |
| `CH-CANDIDATE-005` observability/telemetry ownership drift | Partially supported. Layered ownership is valid; isolated semantic logging/telemetry overlap and static policy drift remain. | `Refactor Spec` after policy synchronization |
| `CH-CANDIDATE-006` zero-/low-coverage stale surfaces | Partially supported. Several zero-coverage symbols are verified stale; low coverage alone is not a finding for the remaining modules. | `Direct cleanup` for verified subset |
| `CH-CANDIDATE-007` decision-evidence persistence complexity | Supported as internal structural complexity, not ownership divergence. | `Refactor Spec` |
| `CH-CANDIDATE-008` workflow-output projection concentration | Supported as service-internal orchestration concentration. | `Refactor Spec` |
| `CH-CANDIDATE-009` risk-authority gate brain method | Partially supported. One cohesive fail-closed decision; local named decomposition is warranted without changing authority semantics. | `Refactor Spec` |
| `CH-CANDIDATE-010` approval-lifecycle service breadth | Rejected. `AutomatedDecisionAuditService` forms one coherent governance approval lifecycle. | `Accept` |
| `CH-CANDIDATE-011` safe-only dead export set | Partially supported. Detector list contained both genuinely stale and demonstrably live/test/public surfaces. | `Direct cleanup` only for verified subset |

### Verified direct-cleanup set

The following have no observed supported repository compatibility surface and are ready for direct cleanup after revalidation against the implementation branch:

```text
pyproject.toml: stale `web` wheel/coverage entries
core/bootstrap/application_bootstrap.py
core/bootstrap/service_registry.py
domain/portfolio/portfolio_decision_engine.py::PortfolioDecisionEngine
intelligence/strategy/evolution/strategy_evolution_engine.py::StrategyEvolutionEngine
integration/contracts/execution/execution_decision.py::ExecutionDecision
require_non_empty
workflow_result_to_dict
```

`build_chunks` is not included in the unconditional set. It has no current repository consumer, but its docstring explicitly claims backward compatibility. Cleanup must first make an explicit compatibility decision rather than deleting it blindly.

Repowise-labelled symbols such as `InMemoryRuntimeTelemetrySink`, `InMemoryTelemetrySink`, `sanitize_web_content`, `build_interactive_input_reader`, and `get_builtin_workflows` were found to have legitimate current roles and are not dead-code findings.

### Durable job claim-transition duplication

`PostgresWorkflowOutputProjectionJobRepository` and `PostgresAiObservabilityExportJobRepository` do **not** implement one generic durable-job repository contract. Their terminal states, retry behavior, idempotency identity, queue-status behavior, metadata, and cleanup semantics differ materially.

They do share one narrower invariant:

- select a claimable row using concurrency-safe locking;
- transition it to `RUNNING`;
- increment `attempt_count`;
- set `started_at`;
- clear prior error state;
- commit or roll back on `SQLAlchemyError`;
- return the updated typed record.

Stale-running recovery also overlaps partially, but repository-specific timestamp/retry semantics differ.

The smallest plausible consolidation boundary is therefore a claim-transition helper or similarly narrow durable-job transition utility. A generic repository abstraction would erase meaningful domain-specific queue semantics and is rejected.

### Decision-evidence persistence

`DecisionEvidencePacketPersistenceService` owns persistence and reconstruction of decision-evidence packets from canonical durable sources. Serialization, source-kind validation, RAG/evaluation/trace/domain-source reconstruction, tamper/staleness checks, and reconstruction telemetry are tied by one invariant: reconstructed evidence must match canonical durable sources.

The module is therefore large but mostly cohesive. The finding is internal decomposition of source-specific validators/parsers and reconstruction steps while preserving one canonical owner, not splitting architectural ownership.

### Workflow-output projection

`WorkflowOutputProjectionService` owns the shared projection lifecycle: eligibility, job creation/claiming, idempotency, trace context, telemetry, retry/reconcile behavior, and outcome persistence. Individual projectors own output-specific mapping and persistence.

The supported finding is service-internal orchestration concentration, especially around repeated skip/block/start/fail/succeed branches. A base-projector hierarchy or generic projector abstraction is not justified by the evidence.

### Risk-authority gate

`select_risk_authority_gate` is complex because it implements one sequential fail-closed domain decision:

```text
metadata present
→ metadata valid
→ authority consistent
→ boundary permitted
→ required packet evidence present
→ output-governance evidence present
→ decision evidence present
→ provenance evidence present
→ pass
```

The method can be decomposed into named internal checks, but graph/source evidence does not show multiple independent policy owners. Refactoring must preserve risk-authority semantics and fail-closed behavior.

### Telemetry and logging ownership

Final validation supports a layered model:

- generic observability infrastructure owns transport/mechanics;
- semantic emitters own separate application/runtime event vocabularies;
- bootstrap configuration telemetry owns canonical configuration-failure reporting;
- explicit emergency/fallback logging is permitted when observability cannot safely report itself.

There is no single telemetry root-ownership defect.

The remaining issue is local overlap and policy synchronization. Representative production paths log semantic failure/block events in addition to structured telemetry or outcomes, while static architecture tests enforce tighter direct-operational-logging restrictions. This requires deciding which direct logs are valid documented exceptions and which are production bypasses, then removing duplicate knowledge rather than broadening the architecture unnecessarily.

CodeGraph resolved representative `EventBus.emit` subscriber dispatch and telemetry decorator emitter calls. Runtime-selected decorator emitters and unnamed event-bus subscriber paths remain graph blind spots; no finding depends solely on those unresolved edges.

## Behavioral baseline classification

### Historical baseline and focused reproduction

The audited full-suite result remains:

```text
33 failed
3006 passed
9 skipped
```

The existing `.pytest_cache/v/cache/lastfailed` could not be treated as the authoritative 33-test inventory. It contained 51 entries, a missing path, and renamed/missing nodeids.

A focused reconstruction across the surviving cached failure-area files produced:

```text
32 failed
302 passed
```

This was **not** a replacement full-suite baseline; it was a targeted diagnostic reproduction. The historical 33rd failure could not be deterministically recovered from the stale cache/current test names and remains documented as a historical-count limitation.

Targeted isolation then showed that 20 of the 32 failures were order-dependent logging-capture failures: the same tests passed in focused groups.

### Root-cause groups

| Group | Failures | Classification | Root cause | Remediation owner | Refactor gate |
| --- | ---: | --- | --- | --- | --- |
| `GROUP-001` governed facade audit capability | 5 | Stale test | Tests call governed `WorkflowFacade.run_workflow` directly instead of using the current issue-only `WorkflowExecutionAuditCapability` path through `GovernedWorkflowExecutionService`. | Tests | Only affected workflow/governance area |
| `GROUP-002` live Neo4j unavailable | 1 | Environment prerequisite | Live integration test expects Neo4j on localhost:7687; service was unavailable. | Test infrastructure/environment | Only Neo4j/RAG projection work |
| `GROUP-003` model-allocation readiness path | 3 | Stale/missing repository artifact | Tests still read `docs/model_allocation_readiness.md`; the document was moved/reclassified to `docs/reference/model-gateway-profile-policy-model-allocation-readiness.md`. | Tests | No production blocker |
| `GROUP-004` evaluation job risk-authority prerequisite | 1 | Stale test | Test expects provider invocation without satisfying the current output-governance readiness prerequisite for the strategy-synthesis authority gate. | Tests | Only evaluation/gate area |
| `GROUP-005` observability static policy drift | 2 | Architecture-policy drift | Static policy forbids two noncanonical `TelemetryEvent` imports and eight direct operational logging sites; behavioral tests also expect some direct logs. | Architecture-policy synchronization | Telemetry/logging refactors |
| `GROUP-006` order-dependent `caplog` failures | 20 | Test defect | Logging capture is contaminated by test order/batch state; the same call sites emit expected logs in isolated grouped reruns. | Test infrastructure/environment | Broad regression trust until fixed |

### Behavioral assessment

For the 32 currently reproduced failures:

- implementation regressions: **0**;
- stale tests: **6**;
- environment-prerequisite failures: **1**;
- stale/missing repository artifact failures: **3**;
- architecture-policy drift failures: **2**;
- test defects: **20**.

The historical audited 33rd failure was not reproduced because the cached failure inventory was stale. This limitation is explicit rather than silently reclassifying the historical baseline.

No broad architecture re-entry is justified by the behavioral pass. `GROUP-005` requires synchronization of existing observability policy, static tests, and intentional logging exceptions; it does not currently require a Wayfinder.

## Findings

| ID | Area | Finding | Evidence | Impact | Route | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `CH-FINDING-001` | Behavioral baseline | The audited full suite is not green, but the currently reconstructable failures contain no confirmed implementation regression. | Historical 33/3006/9 baseline; focused 32-failure reconstruction decomposes into six root causes. | Baseline must be repaired before affected refactors can rely on the suite as a trustworthy regression oracle. | Pre-refactor remediation | Confirmed |
| `CH-FINDING-002` | Packaging | `web` remains in wheel/coverage configuration without a corresponding package. | `pyproject.toml`; repository inventory. | Stale configuration and misleading coverage/package intent. | `Direct cleanup` | Confirmed |
| `CH-FINDING-003` | Bootstrap scaffolding | `application_bootstrap.py` and `service_registry.py` are empty, unreferenced bootstrap scaffolding. | Repository search, Repowise, graph reachability, history. | Dead surface and misleading ownership signals. | `Direct cleanup` | Confirmed |
| `CH-FINDING-004` | Dead code | A narrow set of unused symbols has no observed static, dynamic, export, registry, CLI/MCP/plugin, test, or supported compatibility role. | Repowise safe-only + zero coverage where applicable + graph/search compatibility pass. | Unnecessary maintenance surface. | `Direct cleanup` | Confirmed subset |
| `CH-FINDING-005` | Persistence jobs | Projection and AI-observability job repositories duplicate one durable claim-transition invariant while their broader lifecycle semantics differ. | Arid/jscpd + repository semantic comparison. | Shared concurrency/state-transition knowledge has multiple owners. | `Refactor Spec` | Confirmed |
| `CH-FINDING-006` | Decision evidence | Decision-evidence persistence/reconstruction is cohesive but internally over-concentrated. | Repowise 1.13; 1,300 NLOC; graph/caller responsibility review; 88.43% coverage. | High maintenance complexity around canonical reconstruction logic. | `Refactor Spec` | Confirmed |
| `CH-FINDING-007` | Workflow projection | `WorkflowOutputProjectionService` concentrates the shared projection orchestration lifecycle. | Repowise 1.34; 814 NLOC; 21.13% duplication; graph/caller review. | High change/ripple risk and repeated lifecycle branches. | `Refactor Spec` | Confirmed |
| `CH-FINDING-008` | Risk authority | `select_risk_authority_gate` is a 130-line / CCN-19 cohesive fail-closed decision that can be locally decomposed. | Ruff/Repowise/source/caller review. | Local readability and maintainability risk in a critical decision path. | `Refactor Spec` | Confirmed |
| `CH-FINDING-009` | Observability | Layered telemetry ownership is valid, but local semantic logging/telemetry overlap and static-policy disagreement remain. | Graph-backed telemetry pass + two static architecture-policy failures. | Duplicate reporting knowledge and unreliable policy enforcement until synchronized. | `Refactor Spec` after policy synchronization | Confirmed |

## Explicitly rejected or accepted smells

The following should **not** become refactoring projects merely because a tool produced a poor score or label:

- generic repository abstraction across persistence families — **rejected**;
- generic/base projector abstraction — **rejected**;
- `AutomatedDecisionAuditService` God-class split — **rejected**;
- `WorkflowRuntimeAssembler` God-class split — **rejected**;
- `ServiceRunner` God-class split — **rejected**;
- `WorkflowFacade` class-level split based on breadth/LCOM alone — **rejected**;
- broad telemetry-owner consolidation — **rejected**;
- low coverage as proof of dead code — **rejected**;
- ORM/model declarative repetition as a blanket DRY violation — **rejected**.

These rejections are findings in the methodological sense: they prevent detector-driven cleanup from making the architecture worse.

## Recommended remediation order

Restore a trustworthy behavioral baseline before production structural refactors whose verification depends on it.

1. Isolate and repair the order-dependent logging-capture contamination (`GROUP-006`).
2. Update governed workflow/plugin/policy/telemetry tests to use the current governed execution capability path (`GROUP-001`).
3. Synchronize observability policy, static tests, valid direct-logging exceptions, and actual production bypasses (`GROUP-005`).
4. Update model-allocation readiness tests to the classified reference document (`GROUP-003`).
5. Update the evaluation metric-policy test to satisfy current risk-authority/output-governance prerequisites (`GROUP-004`).
6. Make the live Neo4j prerequisite consistently explicit in test execution/documentation (`GROUP-002`).
7. Re-establish the full-suite baseline.
8. Perform verified direct cleanup.
9. Create focused Refactor Specs for the confirmed production findings.

No Wayfinder is required by the current audit evidence. Architecture re-entry remains available if implementation revalidation later discovers genuine ownership or contract ambiguity.

## Follow-up re-audit plan

After baseline remediation and code-health changes, rerun the same signals against the then-current repository snapshot.

At minimum compare:

- Ruff and Mypy status;
- full Pytest pass/fail/skip counts;
- aggregate and affected-module coverage;
- Arid production/test duplication using the same normalization options;
- jscpd production duplication using the same repository configuration;
- Repowise repository and hotspot health;
- size/complexity for `DecisionEvidencePacketPersistenceService`, `WorkflowOutputProjectionService`, and `select_risk_authority_gate`;
- duplicate job-claim lifecycle evidence;
- dead/stale symbol count;
- observability architecture-policy tests and representative behavioral logging tests.

The objective is not to force every metric downward. A successful remediation should reduce duplicated knowledge and structural risk while preserving or improving behavioral confidence and architectural clarity.

## Exit criteria assessment

1. **Baseline lint/type/test/coverage recorded:** complete. The non-green test baseline and focused diagnostic limitation are documented.
2. **Independent duplicate measurement:** complete. Arid and jscpd production results are recorded; jscpd test-corpus limitation is explicit.
3. **Complexity/hotspot inspection:** complete.
4. **God-class/divergent-responsibility validation:** complete; detector labels were reviewed and rejected where unsupported.
5. **Dead/stale-code reachability and compatibility validation:** complete for the promoted cleanup subset; ambiguous/live symbols were not promoted.
6. **Root-cause consolidation:** complete.
7. **Finding routing:** complete; no finding currently requires a Wayfinder.
8. **Measured facts vs architectural inference:** separated throughout the audit.
9. **Follow-up re-audit plan:** documented above.

**Audit result:** Complete for the audited snapshot. Proceed to baseline remediation, then direct cleanup and focused Refactor Specs, followed by re-audit.

## Post-audit remediation discoveries

This section is additive remediation evidence discovered **after** the audited August 25 snapshot. It does not rewrite the point-in-time findings above.

### `CH-POST-001` — semantic dead API / contract ownership drift

During post-audit verification of real-node workflow and backtest behavior, Polaris exposed a governed-execution contract defect introduced after the audited snapshot: `GovernedWorkflowExecutionService.run_workflow()` still accepted a caller-supplied `execution_id` even though the service had become the authoritative owner of governed execution correlations. The implementation silently discarded the caller value while backtesting continued constructing and passing deterministic step execution IDs.

This was not conventional dead code. The parameter remained referenced and type-correct, and tests could stay behaviorally green. The defect was that the API advertised caller authority that no longer existed while downstream consumers preserved a superseded contract.

The production migration was completed by removing the obsolete caller-owned execution-ID contract from the governed boundary, backtest protocol/request path, governance tests, and stale test doubles. The remediation then exposed a standards-enforcement gap:

- internal source compatibility had been treated as an implicit reason to retain obsolete API shape;
- `$coding-standards` did not explicitly prohibit accepting and ignoring/discarding/overwriting superseded inputs or equivalent compatibility sinks;
- `$verify-code` did not require repository-wide consumer discovery/closure when an authoritative shared contract changed.

The enforcement gap was remediated by:

- `aa8a3e5ae9cfd7360c223b8cc71ad51435fe7034` — `fix(standards): enforce complete internal contract migrations`;
- `123296731a44f54b58adaeadff0bf6cad4a86b19` — `fix(verification): enforce contract impact closure`.

`$coding-standards` now establishes that internal source compatibility is not a default Polaris requirement, authoritative layers become correct first, all affected internal consumers are migrated, and obsolete compatibility residue is forbidden unless explicit authority requires a genuine compatibility boundary. `$verify-code` now requires contract-impact closure with repository-wide consumer discovery while keeping Ruff, Mypy, and Pytest execution targeted.

**Disposition:** Remediated. Treat semantic dead API / contract ownership drift as an explicit defect class in the next repository-wide code-health pass.

**Methodology consequence:** Before resuming the original direct-cleanup queue, perform an adversarial semantic/migration-completeness audit. For authoritative contracts and invariants, inspect callers, implementations, protocols, adapters, fakes, fixtures, configuration, bootstrap/registries, alternate/fallback/bypass paths, and migration history. Any newly discovered defect class must receive a repository-wide saturation sweep rather than a one-off fix.

A temporary GitHub issue (`#239`) was created directly while recording this remediation. That issue bypassed the repository's lifecycle-owning skill workflow and is explicitly **not** workflow authority; it is closed as `not planned` and retained only as historical evidence of the process defect. Durable authority for this post-audit finding is this repository record and the committed implementation/policy changes above.
