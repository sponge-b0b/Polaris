# Governance & Authority (Entity ID: governance-authority)

**Boundary Rationale:** This boundary owns Policy semantics applicable to Polaris boundaries, Investment Authority Regime, Admissibility, Approval, Authority Denial, Mandate Exception, Residual-Risk Acceptance, Human Investment Decision, and materially required review/contest/override relationships. It is distinct because authentication, deterministic rule evaluation, analytical judgment, and power-specific human authority must not collapse into one generic approval mechanism.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Deterministic Policy/Formal Constraint results and power-specific authority acts are separate semantic facts; one must not be inferred from the other. (source: docs/current/platform-architecture-0.2.0.md)
* Authentication, application authorization, Actor Attribution, and Investment Authority Regime powers are distinct layers. Actor Attribution establishes who performed an act; it does not grant authority. (source: docs/current/platform-architecture-0.2.0.md; docs/proposed/investment-decisions-r2-foundation-public-contract.md)
* A canonical authority-bearing domain act may be established only when the applicable Investment Authority Regime confirms that the attributable actor possesses the specific required power for the act's subject, scope, conditions, and authority-effective time. An unauthorized attempt may be auditable but must not be recorded as the corresponding canonical Human Investment Decision, Approval, Mandate Exception, Residual-Risk Acceptance, Authority Denial, or another power-specific authority act. (source: docs/proposed/investment-decisions-r2-foundation-public-contract.md)
* Human Investment Decision is an explicit attributable durable business fact and does not retroactively rewrite an Investment Recommendation. (source: docs/current/platform-architecture-0.2.0.md)
* Analytical or advisory judgment may be attributable without conferring the distinct investment-authority power required for Human Investment Decision or another authority act. (source: docs/proposed/investment-decisions-r2-foundation-public-contract.md)
* Model/provider output cannot self-declare Approval, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, or another authority act. (source: docs/current/platform-architecture-0.2.0.md)
* Historical authority validity is evaluated against the regime and authority facts applicable when the act occurred; later authority revocation or reassignment does not rewrite a valid historical authority act or its Actor Attribution. (source: docs/proposed/investment-decisions-r2-foundation-public-contract.md)

### Planned

* **Deferral and substantive-resolution seams** — canonical Deferral remains a Governance-owned Human Investment Decision; the Decisions boundary records only the resulting deferred-work consequence from a trusted human-decision basis. Substantive resolution likewise consumes a trusted Governance-owned resolution basis rather than allowing the Decisions module or arbitrary caller to fabricate human authority. (source: docs/proposed/platform-domain-interaction-map.md; docs/proposed/application-use-cases-investment-decision-lifecycle.md)
* **Authorization design** — later Governance implementation must preserve the distinct authentication, application-authorization, Actor Attribution, and Investment Authority Regime contracts. Shared policy technology may be used internally, but a generic authorization abstraction must not erase power-specific investment-authority semantics. (source: docs/proposed/investment-decisions-r2-foundation-public-contract.md)
