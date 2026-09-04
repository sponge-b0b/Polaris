# Application Services & Output Curation (Entity ID: application-services-output-curation)

**Boundary Rationale:** This boundary owns use-case orchestration above runtime and below interfaces, including service-level policies, typed inputs/outputs, and curated projection from completed runtime outputs into durable domain records.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Application services own use-case orchestration above runtime and below interfaces, because interfaces should delegate behavior and runtime should remain execution infrastructure rather than product policy. (source: docs/current/platform-architecture-ownership-ledger.md)
* Service inputs and outputs must remain typed and persistence-aware only through explicit use-case or persistence-service boundaries, because application behavior should not smuggle durable semantics through arbitrary payloads. (source: docs/current/platform-architecture-and-operations.md)
* Completed-run archival is broad and automatic, while curated domain-record projection is narrow and policy-driven through registered projectors, because not every runtime output deserves durable product authority. (source: docs/current/application-services-output-curation-workflow-output-curation.md)
* Retrieval projections are downstream of curated PostgreSQL records and must be reproducible from them, because RAG and graph/vector stores cannot become the original source of product facts. (source: docs/current/application-services-output-curation-workflow-output-curation.md)

### Planned

* **Expanded application-service capabilities for scheduling, reporting, and user-facing workflows** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
