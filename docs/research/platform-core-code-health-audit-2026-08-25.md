# Polaris Core Code Health Audit — 2026-08-25

## Research status and authority

This document is **point-in-time research input only**. It records the structural health of the Polaris codebase at the repository snapshot below.

It does **not** establish architecture, authorize refactoring, supersede accepted ADRs, modify existing Specs, satisfy or close `$wayfinder` work, or imply that a finding remains current after the audited repository snapshot. Any finding promoted into architectural work must be independently revalidated against current repository state through the normal `$wayfinder` workflow.

**Audit date:** 2026-08-25

**Repository snapshot:**

```text
branch: main
commit: 37150063f77903ac58880da5ef0b68ec0381850f
```

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

In particular:

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

Inspect:

- package/module layout;
- repository quality configuration;
- empty/stale modules and package declarations;
- repeated or competing infrastructure boundaries;
- obvious abandoned compatibility/scaffolding.

### 2. Baseline quality gates

Record the current snapshot results for:

- Ruff, including configured McCabe complexity (`C90`, threshold 10);
- Mypy under repository configuration;
- Pytest;
- coverage against the repository's configured 75% floor.

These are not the whole audit; they establish whether refactoring starts from a known-green behavioral baseline.

### 3. Duplicate-code analysis

Use two independent detectors:

- **Arid 2.x** for Python-aware duplicate detection and structural context;
- **jscpd** as an independent token/text-oriented cross-check.

Production code and tests are measured separately so test-fixture repetition does not distort production-code conclusions.

Duplicate findings are triaged as:

- repeated syntax with independent ownership — usually acceptable;
- repeated construction/serialization/testing pattern — local refactor candidate;
- duplicated business rule, invariant, normalization, policy, or lifecycle behavior — high-priority ownership defect;
- duplicate competing abstraction — possible architecture/refactoring decision.

### 4. Complexity, size, and hotspot analysis

Use repository Ruff complexity checks plus structural health/risk evidence to identify:

- functions above the configured McCabe threshold;
- large or highly coupled modules;
- classes with excessive method/state breadth;
- files with high change risk or blast radius;
- repeated high-complexity patterns.

Size alone does not establish a God class. Responsibility breadth and coupling must support that conclusion.

### 5. Responsibility and God-class review

For candidate classes/modules, inspect:

- number of unrelated reasons to change;
- state owned across multiple architectural concepts;
- feature envy / extensive navigation of collaborators;
- orchestration mixed with domain policy, persistence, transport, or formatting;
- repeated internal dispatch suggesting hidden sub-responsibilities;
- dependency fan-in/fan-out and change blast radius.

A class is recorded as a God-class/divergent-responsibility finding only when responsibility evidence supports it.

### 6. Dead code and stale scaffolding

Cross-check repository search, structural tooling, and call/dependency evidence before declaring code dead.

Candidates include:

- zero-byte or placeholder modules;
- unreferenced compatibility aliases;
- packages/config entries whose implementation no longer exists;
- superseded paths left beside current architecture;
- unreachable helpers/classes/files.

### 7. Dependency and coupling review

Use graph-backed analysis selectively after hotspots are identified. The goal is to answer specific questions such as:

- Is this large class actually a high-fan-in architectural boundary?
- Do two modules form a cycle or duplicate ownership?
- Which callers would be affected by extraction or consolidation?
- Is apparent dead code reachable through dynamic dispatch?

Broad graph output is evidence, not an architecture decision.

### 8. Finding disposition

Each material finding will be assigned one recommended route:

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
| Pytest | **FAIL** | — | 33 failed, 3006 passed, 9 skipped. |
| Coverage | 90.07% | — | 47,279 / 52,489 statements; repository floor 75%. |
| High-risk/hotspot files | structural pass pending | — | Targeted Repowise analysis next. |
| Dead-code candidates | structural pass pending | structural pass pending | Must be verified before finding status. |
| God-class/divergent-responsibility candidates | structural pass pending | — | Requires responsibility/coupling review. |

### Duplicate-code interpretation

The Arid and jscpd percentages intentionally differ because the tools normalize and count clones differently. The important signal is that both independently identify substantial production duplication; neither percentage is treated as a quality score or direct refactoring target.

Arid production findings are predominantly executable by finding count (`816` executable, `301` declarative, `171` mixed), while the largest raw duplicated regions include substantial declarative model repetition. This makes blanket DRY extraction unsafe: SQLAlchemy/model declarations may repeat syntax while preserving independent schema ownership.

The first high-signal production clusters to inspect are:

1. **Database model declarations** — especially `core/database/models/telemetry.py`, `recommendations.py`, `market.py`, `runtime.py`, `reports.py`, `sentiment.py`, `rag.py`, `portfolio.py`, `agent_intelligence.py`, and `macro.py`. Both detectors repeatedly identify these files. The likely mix is intentional declarative repetition plus possible duplicated schema knowledge; structural review must separate the two.
2. **Persistence services/models/repositories** — repeated executable patterns appear across agent-intelligence, attribution, market, news, portfolio, sentiment, recommendation, projection-job, and observability persistence code. This is a stronger candidate for shared knowledge/ownership defects than model-column syntax alone.
3. **Workflow execution/bootstrap** — `core/workflow/execution/workflow_facade.py` and workflow bootstrap paths recur in executable duplicate findings, including overlap with governed-workflow execution behavior.
4. **Workflow-output projectors** — macro, market, news, portfolio, and sentiment projectors show repeated executable structures and cross-projector clone pairs.
5. **Evaluation infrastructure** — evaluation contracts, datasets, jobs, run service, model-replacement gate, provider adapters, and CLI evaluation services contain repeated blocks across representation and orchestration boundaries.

These are hotspot candidates, not instructions to introduce base classes, generic repositories, generic projectors, or other abstractions. Each cluster must first establish whether the duplicated code represents one piece of knowledge with multiple owners.

### Baseline test health

The current full-suite behavioral baseline is **not green**, despite clean Ruff/Mypy results and 90.07% aggregate coverage.

The 33 failures are not one homogeneous defect. Initial clustering shows:

- governed workflow/plugin/policy tests failing because `WorkflowFacade` now requires an execution-audit capability that several test/runtime constructions do not supply;
- a live Neo4j integration test attempting to connect to unavailable localhost Neo4j instead of cleanly skipping/failing its environment prerequisite;
- a broad telemetry/operational-logging cluster where expected emergency/error/lifecycle records are absent or static architecture checks detect direct logging/event imports outside the expected ownership boundary;
- three model-allocation-readiness tests referencing missing `docs/model_allocation_readiness.md`;
- isolated evaluation-policy, morning-report claim-audit, provider telemetry, and command-guard failures.

This is a material pre-refactor confidence issue. The failures must be separated into stale-test/configuration problems versus actual implementation regressions before cleanup implementation begins.

### Coverage risk candidates

Aggregate coverage is strong enough to support refactoring, but it hides several zero- or low-coverage production surfaces that deserve dead-code/reachability or risk review.

Notable zero-coverage non-trivial files include:

```text
intelligence/strategy/evolution/strategy_evolution_engine.py      42 statements
core/telemetry/lifecycle/telemetry_lifecycle.py                    35
domain/portfolio/portfolio_decision_engine.py                      34
core/telemetry/decorators/instrumented.py                          25
core/telemetry/decorators/timed.py                                 23
core/telemetry/decorators/trace.py                                 18
integration/contracts/execution/execution_decision.py              12
```

Notable low-coverage larger surfaces include:

```text
core/storage/persistence/repositories/postgres_ai_observability_export_job_repository.py   20.2% / 178 statements
core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py         26.5% / 211
intelligence/attribution/attribution_engine.py                                              21.0% / 62
interfaces/cli/services/workflow_control_input_service.py                                   38.0% / 108
core/runtime/artifacts/artifact_store.py                                                    46.2% / 93
```

Low coverage does not prove dead code or bad design. These files are priority inputs to the reachability/risk pass because they combine meaningful size with weak behavioral protection.

## Initial repository-inventory candidates

These are **candidates under validation**, not final findings.

### CH-CANDIDATE-001 — stale `web` package/config declaration

`pyproject.toml` declares `web` in both the wheel package list and coverage source list, while the audited repository root contains no top-level `web/` directory.

Possible interpretations:

- stale package/coverage configuration left after a removed interface;
- intentionally reserved future package (which would conflict with the repository's no-speculative-scaffolding rule);
- another build-layout convention not yet identified.

Before promotion to a finding, validate packaging/test behavior and search for any dynamic/tooling dependency on the declaration.

### CH-CANDIDATE-002 — empty bootstrap modules

The audited `core/bootstrap/` tree contains zero-byte modules:

```text
core/bootstrap/application_bootstrap.py
core/bootstrap/service_registry.py
```

Repository code search currently finds no references to either module name.

Before promotion to a finding, verify import/dependency analysis and whether they serve any packaging or external compatibility role.

### CH-CANDIDATE-003 — persistence-layer executable duplication

Both Arid and jscpd repeatedly identify executable clone families across application persistence services and core persistence models/repositories.

This candidate is higher priority than declarative ORM repetition because repeated transaction, conversion, failure, telemetry, projection, or repository lifecycle behavior may represent duplicated knowledge rather than merely similar syntax.

Next validation: targeted health/risk analysis plus inspection of representative clone families and their architectural ownership.

### CH-CANDIDATE-004 — workflow execution/bootstrap duplication and wiring drift

`core/workflow/execution/workflow_facade.py` and workflow bootstrap paths are duplicate-code hotspots, and the failing test cluster independently indicates governed-execution construction drift around the required execution-audit capability.

The duplicate and test signals may share a root cause, or they may be unrelated symptoms. Do not consolidate them until call/dependency evidence establishes ownership.

### CH-CANDIDATE-005 — observability/telemetry ownership drift

A large share of the failing suite concerns missing telemetry failure reporting, emergency logging, or static restrictions on direct telemetry/logging ownership. This intersects code-health concerns because duplicated fallback/logging behavior and competing emission paths are explicitly prohibited by `$coding-standards`.

Next validation: identify canonical emission ownership, direct callers/importers, and whether failures come from one centralized behavior change or multiple local workarounds.

### CH-CANDIDATE-006 — zero-/low-coverage potentially stale surfaces

Several non-trivial production modules have zero coverage, while larger persistence/runtime modules have materially low coverage. These are not dead-code findings yet.

Next validation: Repowise dead-code/reference analysis, followed by graph-backed reachability checks only for ambiguous/dynamic paths.

## Findings

**Status: audit in progress. No candidate is considered an accepted finding until its evidence is cross-checked, except direct baseline facts explicitly stated below.**

| ID | Area | Finding | Evidence | Impact | Route | Status |
| --- | --- | --- | --- | --- | --- | --- |
| CH-FINDING-001 | Behavioral baseline | The audited full test suite is not green. | 33 failed, 3006 passed, 9 skipped; Ruff/Mypy pass and coverage = 90.07%. | Refactoring cannot rely on a clean regression baseline until failures are classified and resolved. | Pending failure decomposition | Confirmed fact |

## Exit criteria

The audit is complete when:

1. baseline lint/type/test/coverage results are recorded or a deterministic blocker is documented;
2. production and test duplication are independently measured by Arid and jscpd, or a detector limitation is explicitly documented;
3. complexity/hotspot evidence is collected and material candidates are inspected;
4. God-class/divergent-responsibility candidates are confirmed or rejected from responsibility/coupling evidence;
5. dead/stale-code candidates are cross-checked for dynamic reachability and compatibility ownership;
6. material findings are consolidated so one root cause is not reported as many symptoms;
7. every material finding has a recommended route (`Direct cleanup`, `Refactor Spec`, `Wayfinder`, or `Accept`);
8. the audit clearly distinguishes measured facts from architectural inference;
9. a follow-up re-audit plan identifies which metrics should be compared after cleanup.

The audit is not complete merely because tools produced reports.
