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

**Status: pending local whole-repository runs.**

| Measure | Production | Tests | Notes |
| --- | ---: | ---: | --- |
| Python files | pending | pending | Exact audited corpus will be recorded. |
| Physical/source lines | pending | pending | Tool/version recorded with result. |
| Arid duplicate groups | pending | pending | Production and tests measured separately. |
| Arid duplicate effective lines | pending | pending | Python-aware normalized metric. |
| Arid duplication % | pending | pending | Do not compare directly to jscpd percentage. |
| jscpd clones | pending | pending | Independent cross-check. |
| jscpd duplicated lines/tokens | pending | pending | Exact reporter/version recorded. |
| Ruff C90 violations | pending | — | Repository threshold = 10. |
| Mypy result | pending | — | Repository configuration. |
| Pytest result | pending | — | Full suite unless a deterministic blocker prevents it. |
| Coverage | pending | — | Repository floor = 75%. |
| High-risk/hotspot files | pending | — | Repowise/structural evidence. |
| Dead-code candidates | pending | pending | Must be verified before finding status. |
| God-class/divergent-responsibility candidates | pending | — | Requires responsibility/coupling review. |

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

## Findings

**Status: audit in progress. No candidate is considered an accepted finding until its evidence is cross-checked.**

| ID | Area | Finding | Evidence | Impact | Route | Status |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | Quantitative and structural analysis pending. | — | — | — | In progress |

## Exit criteria

The audit is complete when:

1. baseline lint/type/test/coverage results are recorded or a deterministic blocker is documented;
2. production and test duplication are independently measured by Arid and jscpd;
3. complexity/hotspot evidence is collected and material candidates are inspected;
4. God-class/divergent-responsibility candidates are confirmed or rejected from responsibility/coupling evidence;
5. dead/stale-code candidates are cross-checked for dynamic reachability and compatibility ownership;
6. material findings are consolidated so one root cause is not reported as many symptoms;
7. every material finding has a recommended route (`Direct cleanup`, `Refactor Spec`, `Wayfinder`, or `Accept`);
8. the audit clearly distinguishes measured facts from architectural inference;
9. a follow-up re-audit plan identifies which metrics should be compared after cleanup.

The audit is not complete merely because tools produced reports.
