# Configuration (Entity ID: configuration)

**Boundary Rationale:** This boundary owns the separation between product configuration expressed in Polaris domain concepts and replaceable technical/provider configuration. It is distinct because configuration must make the decision system operable without turning vendor settings, workflow graphs, or arbitrary prompt pipelines into the product model.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Product configuration is expressed through investment-domain concepts such as Portfolio, supported universe, Investment Strategy and Horizon, Mandate and Formal Constraints, Policy, Investment Authority Regime, Freshness Requirements, and Review Conditions. (source: docs/current/platform-architecture-0.2.0.md)
* Provider and technical configuration remain outside domain objects when they are not themselves investment semantics. (source: docs/current/platform-architecture-0.2.0.md)
* Polaris 0.2.0 does not use a generic workflow builder, plugin graph, or arbitrary prompt pipeline as its product configuration model. (source: docs/current/platform-architecture-0.2.0.md)
* Technology-specific adapter configuration must remain at infrastructure boundaries rather than leaking vendor identity into inward-owned contracts. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
* R3 Freshness and Evidence-sufficiency requirements are immutable attributable product-configuration facts with typed applicability and append-only `CORRECTS | SUPERSEDES` version history; missing, contested, unavailable, or invalid requirement authority must not be treated as no requirement. (source: docs/adr/0013-evidence-complete-r3-claim-requirements-and-current-support-basis.md)
* R3 Configuration selects values for the closed Evidence-owned `MinimumEligibleEvidence` predicate and marks each sufficiency definition `REQUIRED | NOT_APPLICABLE`; a complete zero-sufficiency-definition version and each per-requirement non-applicability state require distinct exact witnesses. Configuration does not execute Evidence semantics or expose a generic rule language. (source: docs/adr/0014-evidence-derive-r3-sufficiency-from-executable-requirements.md)

### Planned

* **R3 Evidence requirement authority** — accepted, implementation pending. Configuration will expose application-allocated requirement-set, immutable version, and dependent requirement identities through an inward Evidence-requirements contract. Sufficiency definitions will carry the typed `MinimumEligibleEvidence` predicate and explicit applicability state; Evidence will resolve and evaluate exactly one applicable historical version without taking authority to invent or rewrite configured requirements. (source: docs/adr/0013-evidence-complete-r3-claim-requirements-and-current-support-basis.md; docs/adr/0014-evidence-derive-r3-sufficiency-from-executable-requirements.md)
