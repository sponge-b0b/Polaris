# Decision Evidence Packets (Entity ID: decision-evidence-packets)

**Boundary Rationale:** The canonical decision evidence packet has independent semantic invariants: materiality, conflict blocking, durable audit record semantics, and a ban on parallel evidence stores in reports/RAG/MCP.
(source: owner-approved entity promotion)

### Strict Invariants

* `DecisionEvidencePacket` is the canonical typed packet for Enhanced and Vigilant risk-authority outputs requiring durable evidence, because material decisions need one auditable evidence contract. (source: docs/adr/0009-decision-evidence-packets-canonical-semantics.md)
* Each packet binds output identity, `RiskAuthorityContract`, material claims, supporting and conflicting evidence, reconstruction references, retention, and schema constraints, because reviewers must be able to reconstruct why the output was allowed. (source: docs/adr/0009-decision-evidence-packets-canonical-semantics.md)
* The packet audit record in PostgreSQL is durable authority; workflow outputs and completed runs are runtime evidence, while RAG chunks, Qdrant, Neo4j, rendered files, reports, artifacts, and MCP responses are projections or views. (source: docs/adr/0009-decision-evidence-packets-canonical-semantics.md)
* Material claims fail closed unless packet support, reconstruction references, and correctness checks pass, because unsupported or conflicted claims must not be presented as governed facts. (source: docs/adr/0009-decision-evidence-packets-canonical-semantics.md)
