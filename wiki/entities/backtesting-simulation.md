# Backtesting & Simulation (Entity ID: backtesting-simulation)

**Boundary Rationale:** This boundary owns deterministic simulation over the canonical runtime: scenario/provider selection, simulated portfolio ledger, backtest metrics, and the invariant that backtesting does not fork runtime execution or place live trades.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Backtests execute through the same application and runtime boundaries as live workflows, because simulation validity depends on exercising the canonical runtime path. (source: docs/adr/0005-backtesting-simulation-deterministic-canonical-runtime.md)
* The runtime remains unaware of live versus simulated mode; provider profile, simulation time, runtime state, and metadata select simulated or historical behavior at the application/composition boundary, because runtime branches would create a second engine. (source: docs/current/backtesting-simulation-system.md)
* Backtesting must not introduce a backtesting-specific runtime engine or runtime branches; simulation logic belongs in backtest application services, provider wiring, simulated providers, persistence, and reporting, because the runtime contract must stay common. (source: docs/current/backtesting-simulation-system.md)
* Backtest scenarios require deterministic timestamps, seeds, fixtures, and expected outcomes and exclude wall-clock time, unseeded randomness, and live network dependency, because replayed simulation results must be reproducible. (source: docs/adr/0005-backtesting-simulation-deterministic-canonical-runtime.md)
* Backtesting does not place live orders, because simulation is advisory/replay behavior rather than trading execution. (source: docs/current/backtesting-simulation-system.md)

### Planned

* **Future walk-forward testing, Monte Carlo analysis, parameter sweeps, and richer simulation reporting** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
