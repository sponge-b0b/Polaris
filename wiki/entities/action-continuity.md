# Action Continuity (Entity ID: action-continuity)

**Boundary Rationale:** This boundary owns Action Intent and the reconciliation relationship between attributable intended consequence and authoritative external activity, including partial, divergent, abandoned, failed, ambiguous, or unrelated implementation. It is distinct because preserving decision-to-reality continuity must not grant Polaris market-facing execution authority.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Action Intent is a post-human continuity fact and remains distinct from Proposed Action, Order, fill, broker instruction, admissibility, approval, and execution authority. (source: docs/current/platform-architecture-0.2.0.md)
* Polaris 0.2.0 observes and reconciles external execution/activity facts but defines no outbound `place_order`, `cancel_order`, or equivalent execution command port. (source: docs/current/platform-architecture-0.2.0.md)
* Authoritative external activity and resulting Portfolio State remain externally owned facts; Polaris records associations and support strength rather than rewriting external reality to match expectation. (source: docs/current/platform-architecture-0.2.0.md)
* Unrelated or ambiguous external activity must remain explicit and must not be retroactively converted into a Polaris Action Intent or Investment Decision. (source: docs/current/platform-architecture-0.2.0.md)

### Planned

* **Portfolio-State reconciliation seam** — Action Continuity consumes authoritative external activity and owns intent-to-observation association/support, while Portfolio & Risk owns the decision meaning of resulting Portfolio State. The same external change may affect several Investment Decisions differently; no reconciliation association may manufacture Portfolio truth or automatically determine Decision lifecycle semantics. (source: docs/proposed/platform-domain-interaction-map.md)
