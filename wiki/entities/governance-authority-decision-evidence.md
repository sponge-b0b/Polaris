# Governance, Authority & Decision Evidence (Entity ID: governance-authority-decision-evidence)

**Boundary Rationale:** This boundary owns decision authority, reviewability, contestability, residual-risk acceptance, release disposition, and evidence/audit semantics. It is meaningful because it constrains what the system may recommend, publish, or treat as approved.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Policy determines whether an action may occur; governance determines whether it should proceed or require approval; approval and residual-risk acceptance are attributable governance lifecycle outcomes; and release or future execution remains downstream, because eligibility, authority, review, and execution are distinct concerns. (source: docs/current/platform-architecture-and-operations.md)
* Governed outputs require canonical governance and evidence semantics rather than local approval metadata in reports, interfaces, RAG, or telemetry, because publication authority must be auditable. (source: docs/adr/0010-governance-approval-lifecycle-contestability-residual-risk.md)
* Decision evidence, reviewability, contestability, residual-risk acceptance, and release disposition constrain what the system may recommend or publish, because high-impact outputs need traceable authority rather than model confidence alone. (source: docs/adr/0009-decision-evidence-packets-canonical-semantics.md)
* ADR 0008’s accepted disposition does not authorize broad unrelated core changes; future remediation touching core areas requires a clear approval trail, because risk-authority review is scoped rather than blanket permission. (source: docs/adr/0008-governance-authority-decision-evidence-risk-authority-review-disposition.md)

### Planned

* **Registry-bound workflow authority facts** — accepted, implementation pending. A registered workflow's immutable identity and Risk Authority Contract must form one platform-owned source for governed tier/evidence selection; caller metadata and transport references cannot establish those facts. (source: docs/adr/0016-dependency-composition-governed-execution-evidence-resolution-lifecycle.md)
* **Broader runtime approval and capital-allocation governance capabilities** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
