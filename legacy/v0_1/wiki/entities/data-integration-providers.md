# Data Integration & Providers (Entity ID: data-integration-providers)

**Boundary Rationale:** This boundary owns external-system access through provider protocols and vendor clients, including transport, retry/auth/config concerns, and normalization before data enters typed services.
(source: owner-approved entity boundary determination)

### Strict Invariants

* External data enters through application services, provider protocols, and vendor clients before reaching domain and intelligence logic, because vendor transport concerns must not leak into analytical ownership. (source: docs/current/platform-architecture-and-operations.md)
* Provider implementations own transport, retry, authentication, configuration, and vendor normalization at the edge, because internal services should consume typed provider contracts rather than raw vendor APIs. (source: docs/current/platform-architecture-and-operations.md)
* Backtesting selects simulated or historical providers through application/composition boundaries while the runtime remains unaware of live versus simulated execution, because provider substitution must not fork runtime semantics. (source: docs/adr/0005-backtesting-simulation-deterministic-canonical-runtime.md)

### Planned

* **Broader provider coverage, cache and failover behavior, and additional external data sources** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
