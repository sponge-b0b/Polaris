# Portfolio & Risk (Entity ID: portfolio-risk)

**Boundary Rationale:** This boundary owns the decision meaning of Portfolio identity and state, Position, Exposure, Allocation, Projected Portfolio State, Projected Portfolio Consequence, Portfolio Risk, Portfolio Risk Assessment, Investment Objectives, Principles, Strategy, Horizon, Mandate, and machine-evaluable Formal Constraints. It is distinct because portfolio consequence and economic risk must remain separate from governance authority and from external books-and-records ownership.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Portfolio identity is a continuing investment responsibility rather than merely a current set of holdings, and Position, Exposure, Allocation, and Portfolio Risk remain distinct concepts. (source: docs/current/platform-architecture-0.2.0.md)
* Authoritative operational Portfolio State may come from an external specialist source; Polaris owns its decision meaning and derived consequences without claiming external books-and-records authority. (source: docs/current/platform-architecture-0.2.0.md)
* Projected Portfolio Consequence and Portfolio Risk are economic decision inputs, not approval or authority facts. (source: docs/current/platform-architecture-0.2.0.md)
* Machine-evaluable Formal Constraints are deterministic rules; their evaluation remains distinct from power-specific human authority acts. (source: docs/current/platform-architecture-0.2.0.md)

### Planned

* **Action-continuity reconciliation seam** — authoritative external activity may change Portfolio State while Action Continuity separately owns intended-vs-observed association/reconciliation. One Portfolio change may externally resolve one Decision, materially alter another unresolved Decision, and create a different Decision Need; Portfolio & Risk owns the resulting Portfolio meaning without manufacturing Action Intent causality. (source: docs/proposed/platform-domain-interaction-map.md)
