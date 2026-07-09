# Total Test Code Coverage Plan

## Goal
* Achieve 70-80% Total Test Code Coverage

## Current State Analysis
- **Overall Coverage: 87%** (but with 155 failing tests)
- **Passing Tests: 1,218** | **Failing: 155** | **Skipped: 2**
- **Key Issue**: Many "low coverage" modules are actually 0% because they're DI/config wiring or example files
- **Real Coverage Gaps**: Business logic in intelligence agents, integration clients, attribution engine

---

## Phase 1: Fix Failing Tests (Critical - Must Do First)

### 1.1 Fix Technical Agent Tests (2 failures)
**Root Cause**: `TechnicalAnalysisResult` has `result: dict[str, Any]` field, not `analysis`
- Line 118 in `technical_agent.py`: `tech_snapshot = technical_result.result.analysis`
- Should be: `tech_snapshot = technical_result.result.result`

**Action**:
- [ ] Fix `technical_agent.py` line 118: change `.analysis` to `.result`
- [ ] Verify test payload structure matches expected keys

### 1.2 Fix Portfolio State Builder Test (1 failure)
**Root Cause**: `PortfolioAnalysisResult` has `result: dict[str, Any]` field, not `state`
- Line 114 in `portfolio_state_builder.py`: `portfolio = portfolio_result.result.state`
- Should be: `portfolio = portfolio_result.result.result`

**Action**:
- [ ] Fix `portfolio_state_builder.py` line 114: change `.state` to `.result`

### 1.3 Fix Remaining Failures (52 failures)
- [ ] Application persistence exports (5) - contract test updates
- [ ] Service runner telemetry (2) - context propagation
- [ ] Morning report integration (1) - real node execution
- [ ] Telemetry coverage audit (1) - trace identity
- [ ] Application telemetry (1) - service started emission

---

## Phase 2: Increase Coverage on Core Business Logic (Target: +5-10%)

### 2.1 Intelligence Analysts (Current: 27-34% → Target: 70%+)
**Files to Test**:
| File | Current | Lines | Priority |
|------|---------|-------|----------|
| `intelligence/analysts/technical/technical_agent.py` | 27% | 142 | HIGH |
| `intelligence/analysts/fundamental/fundamental_agent.py` | 30% | 82 | HIGH |
| `intelligence/research/news/news_agent.py` | 32% | 79 | HIGH |
| `intelligence/research/sentiment/sentiment_agent.py` | 34% | 68 | HIGH |

**Test Strategy**:
- [ ] Create unit tests for each agent's `_execute` method
- [ ] Mock `ServiceRunner`, `LLMService`, `IntelligenceTelemetry`
- [ ] Test signal generation, risk flags, recommendations
- [ ] Test LLM context building
- [ ] Test edge cases (missing data, errors, fallbacks)

### 2.2 Attribution Engine (Current: 20% → Target: 70%+)
**File**: `intelligence/attribution/attribution_engine.py` (61 lines, 49 missed)

**Test Strategy**:
- [ ] Test performance attribution calculations
- [ ] Test signal contribution analysis
- [ ] Test decision outcome tracking

### 2.3 Risk Signal Builder (Current: 31% → Target: 70%+)
**File**: `intelligence/risk/aggregation/risk_signal_builder.py` (35 lines, 24 missed)

### 2.4 Strategy Evolution & Weighting (Current: 0-13% → Target: 70%+)
**Files**:
- `intelligence/strategy/evolution/strategy_evolution_engine.py` (0%)
- `intelligence/strategy/weighting/adaptive_weighting_engine.py` (13%)

---

## Phase 3: Integration Client Coverage (Target: +3-5%)

### 3.1 External API Clients (Current: 14-47% → Target: 60%+)
**Priority Files** (highest impact):
| File | Current | Lines | Risk |
|------|---------|-------|------|
| `integration/clients/market_data/yfinance_data_client.py` | 14% | 153 | HIGH |
| `integration/clients/market_data/massive_data_client.py` | 30% | 33 | MEDIUM |
| `integration/clients/macro/fred_macro_client.py` | 21% | 42 | MEDIUM |
| `integration/clients/news/finnhub_news_client.py` | 23% | 57 | MEDIUM |
| `integration/clients/sentiment/alphavantage_sentiment_client.py` | 18% | 78 | MEDIUM |

**Test Strategy**:
- [ ] Create mock HTTP responses for each client
- [ ] Test authentication, rate limiting, retries
- [ ] Test response parsing and normalization
- [ ] Test error handling (timeouts, 4xx, 5xx)
- [ ] Use `respx` or `httpx_mock` for HTTP mocking

---

## Phase 4: Core Runtime Artifacts (Target: +2-3%)

### 4.1 Artifact Serialization & Storage (Current: 40-44% → Target: 70%+)
**Files**:
- `core/runtime/artifacts/artifact_serializers.py` (40%)
- `core/runtime/artifacts/artifact_store.py` (44%)

**Test Strategy**:
- [ ] Test serialization/deserialization of various types
- [ ] Test artifact store CRUD operations
- [ ] Test artifact references and metadata

---

## Phase 5: DI/Config Modules (Decision Needed)

### 5.1 Zero-Coverage Modules (DI Wiring)
These are dependency injection configuration files - typically not unit tested:
- `core/di.py`, `core/bootstrap/di_providers.py` (0%)
- `config/di.py`, `backtesting/di.py`, `integration/di.py` (0%)
- `core/telemetry/decorators/*.py`, `core/telemetry/lifecycle/*.py` (0%)
- `core/workflow/examples/*.py` (0% - example code)
- `domain/portfolio/portfolio_decision_engine.py` (0%)
- `domain/strategy/models/strategy_signal_result.py` (0%)

**Decision**: 
- [ ] **Exclude from coverage** via `.coveragerc` or `pyproject.toml` - these are wiring/config
- [ ] OR add minimal smoke tests to verify DI container builds

**Recommendation**: Exclude DI/config/example files from coverage requirements.

---

## Phase 6: Coverage Configuration & Reporting

### 6.1 Configure Coverage Exclusions
Add to `pyproject.toml`:
```toml
[tool.coverage.run]
omit = [
    "*/di.py",
    "*/di_providers.py",
    "*/workflow/examples/*",
    "*/prompts/system/*",
    "scripts/*",
    "migrations/*",
]
```

### 6.2 Set Coverage Thresholds
```toml
[tool.coverage.report]
fail_under = 70
precision = 1
show_missing = true
```

---

## Success Criteria

- [ ] All 155 failing tests fixed or properly skipped
- [ ] Overall coverage ≥ 70% (currently 87% but with failures)
- [ ] Core business logic (intelligence agents) ≥ 70% each
- [ ] Integration clients ≥ 60% each
- [ ] No critical paths < 50% coverage
- [ ] CI passes with coverage gate

---

## Next Steps

1. **Immediate**: Fix the 3 AttributeError bugs (Phase 1.2, 1.3)
2. **Immediate**: Skip migration contract tests with clear TODOs (Phase 1.1)
3. **Immediate**: Write tests for 4 intelligence analysts
4. **Immediate**: Write tests for integration clients
5. **Immediate**: Configure coverage exclusions and thresholds
6. **Immediate**: Exclude DI/config/example files from coverage requirements

---

# New Codex Proposed Implementation Plan

## Summary

The current coverage target is already nominally exceeded in the latest observed run: **86% total line coverage**. However, the test suite is not currently acceptable because the same run produced **18 failing tests**. Therefore, the recommended objective is not simply to add more tests, but to make coverage **stable, enforceable, and meaningful**.

Primary success criteria:

- Full test suite is green.
- Coverage is measured consistently through project configuration.
- CI/local coverage gate is set initially to **75% total coverage**.
- Coverage exclusions are limited to non-business glue or generated-style files.
- High-value uncovered business/runtime modules are improved only after failing tests are resolved.
- Implementation proceeds one step at a time, with step results documented below.

## Key Decisions and Interface Changes

- Add or normalize project coverage configuration in `pyproject.toml`.
  - Recommended initial threshold: `fail_under = 75`.
  - Use package-level source coverage for platform code.
  - Exclude only low-value/non-business paths such as DI wiring, examples, migrations, prompt constant files, and generated/cache artifacts.
- Do not chase higher coverage until the suite is green.
- Do not use live vendor/network calls to improve coverage.
  - Use deterministic fakes, monkeypatching, and typed fixtures.
- Socket-bound Prometheus tests should not fail in restricted local environments.
  - Prefer mocking server start behavior for unit/bootstrap tests.
  - Keep true socket behavior in explicitly isolated integration coverage where safe.
- Fix current regressions before adding new tests:
  - `TechnicalAgent` must consume the canonical `TechnicalAnalysisResult` contract.
  - `PortfolioStateBuilder` must consume the canonical `PortfolioAnalysisResult` contract.
  - Telemetry tests must align with the canonical event payload and trace propagation behavior.
  - Application persistence export tests must reflect the current public export contract.

## Step-by-Step Implementation Plan

Each step is intended to be small enough for review before continuing.

### Step 1 — Append the Codex Plan and Step Results Section

- Append this plan under `# New Codex Proposed Implementation Plan`.
- Add `## Step Results` at the bottom of this file if missing.
- Confirm the original plan remains separate and unchanged.

Verification:

- Confirm this section exists.
- Confirm future progress can be recorded under `## Step Results`.

### Step 2 — Record the Current Coverage/Test Baseline

Run the current full suite with coverage and save the observed result in this plan file.

Recommended command shape:

```bash
UV_CACHE_DIR=/tmp/uv-cache COVERAGE_FILE=/tmp/polaris_coverage uv run pytest -q \
  --cov=application \
  --cov=core \
  --cov=domain \
  --cov=integration \
  --cov=intelligence \
  --cov=interfaces \
  --cov=config \
  --cov-report=term-missing:skip-covered
```

Verification:

- Document total coverage.
- Document current failure count.
- Do not treat coverage as valid until failures are resolved.

### Step 3 — Fix Canonical Typed Result Contract Regressions

Fix the failing intelligence nodes that still read legacy attributes.

Targets:

- `intelligence/analysts/technical/technical_agent.py`
- `intelligence/portfolio/management/portfolio_state_builder.py`

Expected corrections:

- Replace legacy `.analysis` access with the canonical technical analysis result field.
- Replace legacy `.state` access with the canonical portfolio analysis result field.
- Preserve typed-object internal flow and serialize only at runtime boundaries.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/unit/intelligence/analysts/technical/test_technical_agent.py \
  tests/unit/intelligence/portfolio/test_portfolio_state_builder.py \
  tests/integration/workflow/test_morning_report_real_nodes.py
```

### Step 4 — Fix Service Validation Contract Test Drift

Resolve the failing `ServiceRunner` validation tests.

Recommended approach:

- Inspect whether the canonical service validation behavior should return all validation errors or only custom validation errors.
- Prefer deterministic multi-error reporting if the implementation already consistently returns both required-field and custom validation errors.
- Update tests or code so the service validation contract is explicit and stable.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/unit/application/services/base/test_service_runner.py
```

### Step 5 — Normalize Application Persistence Export Contract Tests

Resolve export contract failures in:

```text
tests/unit/application/persistence/test_application_persistence_exports.py
```

Recommended contract:

- Root `application.persistence` exports stable public service/filter/config contracts.
- Domain modules may expose domain-owned constants/configs where intentional.
- Internal constants should not be forced into root exports unless they are part of the public application API.
- Include the current backtesting persistence exports if they are now canonical.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/unit/application/persistence/test_application_persistence_exports.py
```

### Step 6 — Fix Application Telemetry Payload Regression

Resolve the failing application telemetry test expecting `operation`.

Recommended approach:

- Preserve the canonical telemetry payload field if it is useful for auditability.
- Ensure service-started telemetry includes the operation name in a stable location.
- Do not remove trace/correlation identifiers.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/unit/telemetry/test_application_telemetry.py
```

### Step 7 — Fix Trace Audit Provider Event Coverage

Resolve the missing `integration.provider.call` trace audit event.

Recommended approach:

- Confirm `record_provider_call` emits the canonical provider telemetry event under the active trace context.
- Ensure async provider calls propagate trace identity.
- Update tests only if the event name or audit shape has intentionally changed.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/integration/telemetry/test_telemetry_coverage_audit.py
```

### Step 8 — Make Prometheus Tests Stable in Restricted Environments

Resolve Prometheus tests that fail due local socket restrictions.

Recommended approach:

- Unit tests should mock or fake HTTP server startup rather than binding a real socket.
- Bootstrap/integration tests should validate that Prometheus startup is requested and shutdown is wired.
- True socket-serving tests may be skipped only when a capability probe confirms local socket creation is blocked.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q \
  tests/unit/telemetry/test_prometheus_metrics_exporter.py \
  tests/integration/telemetry/test_bootstrap_observability.py
```

### Step 9 — Run the Full Suite Without Enforcing Coverage Gate

Run the full suite after current failures are addressed.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache COVERAGE_FILE=/tmp/polaris_coverage uv run pytest -q \
  --cov=application \
  --cov=core \
  --cov=domain \
  --cov=integration \
  --cov=intelligence \
  --cov=interfaces \
  --cov=config \
  --cov-report=term-missing:skip-covered
```

Acceptance:

- Test suite passes.
- Coverage remains above 75%.
- Any remaining skipped tests are intentional and documented.

### Step 10 — Add Project Coverage Configuration

Add canonical coverage configuration to `pyproject.toml`.

Recommended defaults:

- Source packages:
  - `application`
  - `core`
  - `domain`
  - `integration`
  - `intelligence`
  - `interfaces`
  - `config`
- Initial threshold:
  - `fail_under = 75`
- Omit only:
  - migrations
  - examples
  - DI-only glue modules where direct coverage adds little value
  - prompt constant files
  - generated/cache artifacts

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q --cov
```

### Step 11 — Add High-Value Coverage Only If Needed

If the suite is green but the configured coverage gate is not stable, add deterministic tests for high-value low-coverage modules.

Priority order:

1. Runtime artifact serializers/store.
2. Technical and portfolio intelligence branches not covered by existing tests.
3. Risk signal builder and attribution behavior.
4. Integration clients using mocked HTTP/vendor responses.
5. Strategy weighting/evolution deterministic calculations.

Verification:

- Run targeted tests for each touched area.
- Re-run the full coverage command.

### Step 12 — Run Required Quality Gates

After code and test changes are complete, run the project verification workflow.

Recommended order:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix
UV_CACHE_DIR=/tmp/uv-cache uv run ruff format . --check
UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q --cov
```

If code files changed, also refresh Graphify:

```bash
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .
```

Acceptance:

- Ruff passes.
- Mypy passes, except for explicitly deferred unrelated errors if the user reconfirms deferral.
- Pytest passes.
- Coverage gate passes.

## Test Scenarios

Required scenarios:

- Full suite passes with coverage enabled.
- Coverage gate fails below 75% and passes at or above 75%.
- Intelligence nodes consume canonical typed service result contracts.
- Application telemetry emits stable operation/trace payloads.
- Provider telemetry propagates trace identity.
- Prometheus observability tests do not fail merely because the local sandbox blocks socket creation.
- Persistence export tests protect the intended public API without forcing internal constants into root exports.

## Assumptions

- The initial enforced coverage threshold should be **75%**, because it sits inside the requested 70–80% range and leaves room to stabilize the suite before ratcheting upward.
- The current observed 86% coverage is not accepted as complete until the full suite is green.
- Coverage work should prioritize platform-critical behavior over superficial line coverage.
- No production code should be weakened solely to satisfy tests.
- No live vendor/network calls should be introduced for coverage.
- The implementation will proceed one step at a time, and each completed step will be recorded below.

---

## Step Results

### Step 1 Result

- Appended the `# New Codex Proposed Implementation Plan` section while preserving the original plan content.
- Added the `## Step Results` section at the bottom of the file for incremental execution notes.
- No code or test files were changed in this step.

### Step 2 Result

- Ran the current full-suite coverage baseline with package coverage enabled.
- Result: **18 failed, 1207 passed, 6 skipped, 2 warnings**.
- Observed total coverage: **86%** across 27,286 statements with 3,917 missed lines.
- Coverage remains above the requested 70-80% target range, but is not yet acceptable because the suite is red.
- Current failure clusters match the plan: Prometheus socket tests, trace audit provider event, morning report real-node execution, application persistence exports, service runner validation contract, technical/portfolio result contract regressions, and application telemetry payload drift.
- No production code or tests were changed in this step.

### Step 3 Result

- Fixed canonical typed result contract regressions in intelligence nodes.
- Updated `TechnicalAgent` to read `TechnicalAnalysisResult.result` through the canonical result payload.
- Updated `PortfolioStateBuilder` to read `PortfolioAnalysisResult.result` through the canonical result payload.
- The morning report real-node verification exposed the same legacy result-access pattern in two additional downstream nodes, so this step also updated:
  - `FundamentalAgent` to read `MacroAnalysisResult.result` through the canonical result payload.
  - `SentimentAgent` to read `SentimentSnapshotResult.result` through the canonical result payload.
- Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/intelligence/analysts/technical/test_technical_agent.py tests/unit/intelligence/portfolio/test_portfolio_state_builder.py tests/integration/workflow/test_morning_report_real_nodes.py`.
- Result: **4 passed, 1 warning**.
- Ran `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`; no code-graph topology changes were detected.

### Step 4 Result

- Resolved the `ServiceRunner` validation contract drift by updating the unit tests to match the canonical runner behavior.
- Confirmed `ServiceRunner` intentionally returns both envelope-level request validation errors and service-specific validation errors in deterministic order.
- Updated the failed-event payload assertion and result validation assertion to expect:
  - `payload is required.`
  - `payload is invalid.`
- Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/services/base/test_service_runner.py`.
- Result: **6 passed**.
- Ran `GRAPHIFY_VIZ_NODE_LIMIT=10000 uv run graphify update .`; graphify refreshed `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md` because the graph changed.

### Step 5 Result

- Normalized the application persistence export contract around the current canonical persistence surface.
- Updated `application.persistence` root exports to remain sorted and to expose only public service/filter/config contracts; retention result/summary types remain domain-module exports rather than root exports.
- Sorted the retention domain module `__all__` and updated the export contract tests to allow intentional domain-owned support exports such as retention defaults and the backtesting mapper.
- Added backtesting persistence to the contract audit and added result-envelope list APIs to `BacktestPersistenceService` so it conforms to the same list/read envelope pattern as the other application persistence services.
- Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/persistence/test_application_persistence_exports.py`.
- Additional verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/persistence/backtesting/test_backtest_persistence_service.py tests/unit/application/persistence/test_application_persistence_exports.py`.
- Static checks passed for touched files: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check application/persistence/__init__.py application/persistence/retention/__init__.py application/persistence/backtesting/backtest_persistence_service.py tests/unit/application/persistence/test_application_persistence_exports.py`.
- Targeted mypy passed: `UV_CACHE_DIR=/tmp/uv-cache uv run mypy application/persistence/backtesting/backtest_persistence_service.py tests/unit/application/persistence/test_application_persistence_exports.py --explicit-package-bases`.
- Ran `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`; graphify refreshed `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`.

### Step 6 Result

- Resolved the application telemetry operation payload regression.
- Added an optional canonical `operation` argument to `ApplicationTelemetry` service-started, service-completed, and service-failed emissions.
- Normalized operation propagation so, when provided, the same trimmed operation value is written to both telemetry attributes and payload for metric labeling, persistence, and audit readability.
- Updated `ServiceRunner` to propagate a request-level operation from `ServiceRequest.metadata["operation"]` into application telemetry events without changing the canonical service request contract.
- Updated telemetry and service-runner tests to verify operation propagation through both direct application telemetry emission and runner-mediated service execution.
- Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_application_telemetry.py tests/unit/application/services/base/test_service_runner.py`.
- Additional telemetry verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_domain_metrics_mapper.py tests/unit/telemetry/test_application_telemetry.py tests/unit/application/services/base/test_service_runner.py`.
- Static checks passed for touched files: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check core/telemetry/emitters/application_telemetry.py application/services/base/service_runner.py tests/unit/telemetry/test_application_telemetry.py tests/unit/application/services/base/test_service_runner.py`.
- Format check passed for touched files: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format core/telemetry/emitters/application_telemetry.py application/services/base/service_runner.py tests/unit/telemetry/test_application_telemetry.py tests/unit/application/services/base/test_service_runner.py --check`.
- Targeted mypy passed: `UV_CACHE_DIR=/tmp/uv-cache uv run mypy core/telemetry/emitters/application_telemetry.py application/services/base/service_runner.py tests/unit/telemetry/test_application_telemetry.py tests/unit/application/services/base/test_service_runner.py --explicit-package-bases`.
- Ran `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`; graphify refreshed `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`.

### Step 7 Result

- Resolved the trace audit provider event coverage gap in the integration telemetry audit fixture.
- Confirmed `record_provider_call` already emits the canonical `integration.provider.call` event and captures the active telemetry context before awaiting provider work.
- Updated `TraceAuditRuntimeNode` in `tests/integration/telemetry/test_telemetry_coverage_audit.py` to exercise the provider telemetry path through `record_provider_call` under `telemetry_context_scope`, without passing an explicit context, so active trace context propagation is verified directly.
- Added the provider result to node outputs only to keep the simulated provider call observable and used by the fixture.
- Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/telemetry/test_telemetry_coverage_audit.py`.
- Additional provider telemetry regression verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/providers/test_provider_telemetry.py tests/integration/telemetry/test_telemetry_coverage_audit.py`.
- Static checks passed for the touched test file: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/integration/telemetry/test_telemetry_coverage_audit.py`.
- Targeted mypy passed: `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/integration/telemetry/test_telemetry_coverage_audit.py --explicit-package-bases`.
- Ran `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`; graphify refreshed `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`.

### Step 8 Result

- Stabilized Prometheus telemetry tests for restricted local environments.
- Updated the direct HTTP exporter test to capability-probe loopback socket binding before attempting to start a real local server; the real socket-serving test now skips only when local socket binding is unavailable.
- Updated bootstrap/infrastructure Prometheus tests to use a lightweight fake `PrometheusMetricsExporter`, so they verify startup/shutdown wiring without binding a socket.
- Preserved bootstrap assertions that Prometheus startup is requested, `running` state is set, a server address is exposed, and shutdown is idempotent.
- Verification passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py`.
- Current environment result: **19 passed, 1 skipped**; the skipped test is the real HTTP-serving smoke test because the local socket capability probe reported socket binding unavailable.
- Static checks passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py`.
- Format check passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff format tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py --check`.
- Targeted mypy passed: `UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/unit/telemetry/test_prometheus_metrics_exporter.py tests/integration/telemetry/test_bootstrap_observability.py --explicit-package-bases`.
- Ran `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .`; graphify refreshed `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`.

### Step 9 Result

- Ran the full project test suite with package coverage enabled and without enforcing a coverage gate.
- Verification command: `UV_CACHE_DIR=/tmp/uv-cache COVERAGE_FILE=/tmp/polaris_coverage uv run pytest -q --cov=application --cov=core --cov=domain --cov=integration --cov=intelligence --cov=interfaces --cov=config --cov-report=term-missing:skip-covered`.
- Result: **1224 passed, 7 skipped, 2 warnings**.
- Observed total coverage: **88%** across 27,338 statements with 3,353 missed lines.
- Acceptance status: suite is green and coverage remains above the Step 9 target threshold of 75%.
- Remaining skips are intentional/environmental based on the current suite configuration; the newly stabilized Prometheus HTTP smoke test skips when local socket binding is unavailable.
- Warnings observed:
  - `websockets.legacy` deprecation warning from the installed `websockets` dependency.
  - SQLAlchemy warning in `tests/unit/core/storage/persistence/test_postgres_portfolio_state_repository.py` about extra compile-time columns `cash_ratio` and `risk_signals` not matching `portfolio_state_latest`; this warning is pre-existing test/schema drift to address separately if desired.
- No source or test files were modified in this step beyond documenting these results.

### Step 10 Result

- Added canonical project coverage configuration to `pyproject.toml`.
- Configured `coverage.py` source packages for: `application`, `core`, `domain`, `integration`, `intelligence`, `interfaces`, and `config`.
- Added a conservative coverage gate with `fail_under = 75`.
- Limited omissions to low-value/non-business paths: migrations, examples, package-level DI glue, the workflow module bootstrap helper, system prompt constants, and generated cache paths.
- Enabled missing-line reporting and skipped fully covered files in the default coverage report.
- Initial verification inside the restricted sandbox failed because changing `pyproject.toml` caused `uv` to rebuild the local package and fetch `setuptools`, but network/DNS access was unavailable.
- Re-ran verification with approved `uv run` escalation for dependency resolution.
- Verification passed: `UV_CACHE_DIR=/tmp/uv-cache COVERAGE_FILE=/tmp/polaris_coverage_config uv run pytest -q --cov`.
- Result: **1225 passed, 6 skipped, 2 warnings**.
- Configured coverage result: **88.77%**, satisfying the new required threshold of **75.0%**.
- Warnings remained the same as Step 9: installed `websockets.legacy` deprecation warning and the pre-existing SQLAlchemy compile warning in `test_postgres_portfolio_state_repository.py`.

### Step 11 Result

- Re-ran the configured project coverage command to determine whether additional high-value coverage tests were necessary.
- Verification command: `UV_CACHE_DIR=/tmp/uv-cache COVERAGE_FILE=/tmp/polaris_coverage_step11 uv run pytest -q --cov`.
- Result: **1224 passed, 7 skipped, 2 warnings**.
- Configured coverage result: **88.56%**, satisfying the required threshold of **75.0%** with a stable margin.
- Determination: no additional coverage-only tests are needed in this step because the suite is green and the configured gate remains stable above target.
- No source or test files were modified in this step beyond documenting these results.
- Warnings remained the same as prior full-suite runs: installed `websockets.legacy` deprecation warning and the pre-existing SQLAlchemy compile warning in `test_postgres_portfolio_state_repository.py`.

### Step 12 Result

- Ran the required project quality gates for the total test coverage plan.
- `ruff check . --fix` passed with no fixes required.
- `ruff format . --check` passed: **908 files already formatted**.
- Initial full-project mypy found one type error in `interfaces/cli/services/backtest_command_service.py`: `_list_persisted_backtests()` was annotated to return `tuple[BacktestRunRecord, ...]` while directly returning the `Sequence[BacktestRunRecord]` from `BacktestPersistenceService.list_runs()`.
- Fixed the mypy regression by converting the awaited `list_runs()` result to a tuple at the CLI service boundary. This preserves the public CLI service contract without changing persistence service behavior.
- Targeted regression test passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/interfaces/cli/test_backtest_command.py`.
- Re-ran full-project mypy: `UV_CACHE_DIR=/tmp/uv-cache uv run mypy . --explicit-package-bases`.
- Mypy result: **Success: no issues found in 905 source files**.
- Re-ran full-suite coverage: `UV_CACHE_DIR=/tmp/uv-cache COVERAGE_FILE=/tmp/polaris_coverage_step12 uv run pytest -q --cov`.
- Full-suite result: **1224 passed, 7 skipped, 2 warnings**.
- Configured coverage result: **88.56%**, satisfying the required threshold of **75.0%**.
- Ran `GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache uv run graphify update .` because a Python code file changed; graphify refreshed `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`.
- Warnings remained the same as prior full-suite runs: installed `websockets.legacy` deprecation warning and the pre-existing SQLAlchemy compile warning in `test_postgres_portfolio_state_repository.py`.
