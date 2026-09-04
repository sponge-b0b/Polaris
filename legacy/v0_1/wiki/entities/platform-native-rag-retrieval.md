# Platform-Native RAG & Retrieval (Entity ID: platform-native-rag-retrieval)

**Boundary Rationale:** This boundary owns the derived retrieval pipeline: curated-record ingestion, document/chunk/job lifecycle, vector/graph projections, retrieval/reranking/security/generation flow, and the rule that RAG cannot become a parallel source of authority.
(source: owner-approved entity boundary determination)

### Strict Invariants

* PostgreSQL is the only canonical authority for RAG documents, chunks, ingestion jobs, and retrieval source records, because retrieval indexes are derived views rather than durable truth. (source: docs/current/platform-native-rag-retrieval-pipeline.md)
* Only curated records are eligible for canonical RAG ingestion; raw runtime dumps, vendor responses, arbitrary JSON, and transient web pages do not become canonical RAG documents merely because they were retrieved. (source: docs/current/platform-native-rag-retrieval-pipeline.md)
* Qdrant vector collections and Neo4j graph projections are rebuildable from PostgreSQL records, because retrieval acceleration must not become a second system of record. (source: docs/current/platform-native-rag-retrieval-pipeline.md)
* RAG, reports, MCP tools, rendered files, and graph/vector projections must not create parallel decision-evidence stores or declare rendered text to be the source of truth, because governed decisions require canonical evidence packets and durable audit records. (source: docs/adr/0009-decision-evidence-packets-canonical-semantics.md)

### Planned

* **Expanded RAG layer capabilities such as advanced chunking, reranking, security filtering, and guard integration** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
