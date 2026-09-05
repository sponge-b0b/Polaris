# Configuration (Entity ID: configuration)

**Boundary Rationale:** This boundary owns the separation between product configuration expressed in Polaris domain concepts and replaceable technical/provider configuration. It is distinct because configuration must make the decision system operable without turning vendor settings, workflow graphs, or arbitrary prompt pipelines into the product model.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Product configuration is expressed through investment-domain concepts such as Portfolio, supported universe, Investment Strategy and Horizon, Mandate and Formal Constraints, Policy, Investment Authority Regime, Freshness Requirements, and Review Conditions. (source: docs/current/platform-architecture-0.2.0.md)
* Provider and technical configuration remain outside domain objects when they are not themselves investment semantics. (source: docs/current/platform-architecture-0.2.0.md)
* Polaris 0.2.0 does not use a generic workflow builder, plugin graph, or arbitrary prompt pipeline as its product configuration model. (source: docs/current/platform-architecture-0.2.0.md)
* Technology-specific adapter configuration must remain at infrastructure boundaries rather than leaking vendor identity into inward-owned contracts. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
