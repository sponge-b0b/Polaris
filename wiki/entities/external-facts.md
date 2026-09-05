# External Facts (Entity ID: external-facts)

**Boundary Rationale:** This boundary owns the adapter-facing observation contracts through which external specialist systems provide Evidence, authoritative Portfolio State, execution/activity observations, and related factual inputs. It is distinct because Polaris must preserve external source authority while translating those observations into internal decision meaning.
(source: owner-approved entity boundary determination)

### Strict Invariants

* External specialist systems remain authoritative for facts inside their responsibility domains; Polaris records attributable observations and preserves source authority. (source: docs/current/platform-architecture-0.2.0.md)
* External observations preserve source identity, externally meaningful identity where needed, observed/as-of time, ingestion time, and relevant source metadata. (source: docs/current/platform-architecture-0.2.0.md)
* Vendor SDK types and protocols remain in infrastructure adapters and must not leak into domain/application contracts. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md)
* Execution integration is inbound observation/reconciliation only for 0.2.0; no outbound market-execution capability is exposed through this boundary. (source: docs/current/platform-architecture-0.2.0.md)
