# Governance & Authority (Entity ID: governance-authority)

**Boundary Rationale:** This boundary owns Policy semantics applicable to Polaris boundaries, Investment Authority Regime, Admissibility, Approval, Authority Denial, Mandate Exception, Residual-Risk Acceptance, Human Investment Decision, and materially required review/contest/override relationships. It is distinct because authentication, deterministic rule evaluation, analytical judgment, and power-specific human authority must not collapse into one generic approval mechanism.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Deterministic Policy/Formal Constraint results and power-specific authority acts are separate semantic facts; one must not be inferred from the other. (source: docs/current/platform-architecture-0.2.0.md)
* Authentication, application authorization, and Investment Authority Regime powers are distinct layers, and an authenticated actor may exercise only powers established by the applicable authority regime. (source: docs/current/platform-architecture-0.2.0.md)
* Human Investment Decision is an explicit attributable durable business fact and does not retroactively rewrite an Investment Recommendation. (source: docs/current/platform-architecture-0.2.0.md)
* Model/provider output cannot self-declare Approval, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, or another authority act. (source: docs/current/platform-architecture-0.2.0.md)

### Planned

* **Deferral and substantive-resolution seams** — canonical Deferral remains a Governance-owned Human Investment Decision; the Decisions boundary records only the resulting deferred-work consequence from a trusted human-decision basis. Substantive resolution likewise consumes a trusted Governance-owned resolution basis rather than allowing the Decisions module or arbitrary caller to fabricate human authority. (source: docs/proposed/platform-domain-interaction-map.md; docs/proposed/application-use-cases-investment-decision-lifecycle.md)
