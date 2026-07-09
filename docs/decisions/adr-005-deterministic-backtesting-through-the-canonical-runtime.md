# ADR-005: Deterministic Backtesting Through the Canonical Runtime

## Status

Accepted

## Context

Backtesting must validate that calculations, risk assessments, and recommendations are correct for deterministic inputs. A dedicated simulation runtime or backtest-only execution semantics would diverge from live behavior and invalidate those comparisons.

## Decision

Backtests execute through the existing workflow runtime and application boundaries. The runtime remains unaware of whether providers are live or simulated. Dishka provider composition selects deterministic simulated or historical providers, while workflows, services, intelligence nodes, policies, governance, telemetry, and persistence retain their normal contracts.

Backtest scenarios use explicit timestamps, seeds, fixtures, and expected outcomes. Verification compares calculated results with independently derived deterministic expectations, not only with previously captured platform output.

## Rationale

Reusing the canonical runtime tests production behavior rather than a parallel approximation. Provider inversion isolates the data source while preserving execution, policy, telemetry, and decision logic.

## Consequences

- No backtesting-specific runtime engine or runtime branches are added.
- Simulated providers must match live provider contracts.
- Identical scenarios must produce identical, independently verifiable results.
- Wall-clock time, unordered collections, network calls, and unseeded randomness are excluded from deterministic scenarios.

## Affected Modules

- `application/services/backtesting/backtest_service.py`
- `application/services/backtesting/backtest_request.py`
- `application/services/backtesting/backtest_result.py`
- `application/services/backtesting/scenario_loader.py`
- `integration/providers/backtesting/di.py`
- `integration/providers/backtesting/`
- `interfaces/cli/services/backtest_command_service.py`
