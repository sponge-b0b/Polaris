# Domain Contracts & Data Semantics (Entity ID: domain-contracts-data-semantics)

**Boundary Rationale:** This is the semantic contract layer that prevents runtime, application, persistence, intelligence, and interfaces from inventing ad hoc dict semantics, score meanings, precision rules, or authority metadata. It is meaningful because it preserves cross-cutting typed invariants, not because `domain/` exists.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Internal platform communication uses typed domain objects, requests, results, signals, runtime context, and persistence models rather than ad hoc dictionaries, because stable platform semantics must be reviewable and enforceable across entity boundaries. (source: docs/adr/0006-domain-contracts-data-semantics-typed-internal-contracts.md)
* `dict[str, Any]` remains valid only at untrusted external-input and explicit serialization boundaries, because boundary adapters may need shape flexibility while internal services require typed contracts. (source: docs/current/domain-contracts-data-semantics-contract-semantics.md)
* Stable business dimensions that must be queried, governed, or projected require first-class typed fields rather than being stored only in generic metadata, raw payloads, or JSON blobs, because hidden semantics cannot reliably support migrations, lineage, or downstream authority. (source: docs/current/domain-contracts-data-semantics-contract-semantics.md)
* Score-bearing fields must identify their score family, range, polarity, and conversions explicitly, because consumers must not infer meaning from the word “score.” (source: docs/current/domain-contracts-data-semantics-contract-semantics.md)
* Internal calculations and persistence preserve full numeric precision, with rounding limited to rendering or presentation boundaries, because precision loss inside the platform changes domain meaning. (source: docs/adr/0006-domain-contracts-data-semantics-typed-internal-contracts.md)
