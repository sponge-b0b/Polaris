# Model Access (Entity ID: model-access)

**Boundary Rationale:** This boundary owns the replaceable application-to-model capability: provider interaction, structured draft responses, technical provenance, timeout/retry behavior, and deterministic response validation before business acceptance. It is distinct because model providers and SDKs are infrastructure while investment judgment and authority remain inward-owned semantics.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Model/provider identity is technical provenance, not business capability identity or authority. (source: docs/current/platform-architecture-0.2.0.md)
* Model adapters return draft analytical results that require deterministic validation and application/domain acceptance before becoming durable business judgment. (source: docs/current/platform-architecture-0.2.0.md)
* Malformed, incomplete, timed-out, refused, or retried model operations must not create duplicate or falsely successful business judgments. (source: docs/current/platform-architecture-0.2.0.md)
* Model/provider SDK types and vendor operations must not leak into inward-owned domain/application contracts merely for convenience. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
