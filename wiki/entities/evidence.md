# Evidence (Entity ID: evidence)

**Boundary Rationale:** This boundary owns attributable Evidence identity, source provenance, temporal meaning, fitness for judgment, and the bindings that show which Evidence materially supported a judgment or governed use. It is distinct because Polaris may reason from external facts without taking over the external system's factual authority.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Evidence preserves source provenance, observation/as-of time, Judgment-Time Availability, and the information needed to evaluate freshness and support. (source: docs/current/platform-architecture-0.2.0.md)
* External specialist systems remain authoritative for facts inside their responsibility domains; Polaris records attributable observations and derives decision meaning without silently replacing external factual authority. (source: docs/current/platform-architecture-0.2.0.md)
* Evidence sufficiency, unresolved or missing support, and conflicting Evidence must remain explicit rather than being inferred from model confidence or absence of an error. (source: docs/current/platform-architecture-0.2.0.md)
* A later change in Evidence fitness may change current support without erasing the historical Evidence observation or the fact that it supported an earlier judgment. (source: docs/current/platform-architecture-0.2.0.md)
