# Learning (Entity ID: learning)

**Boundary Rationale:** This boundary owns Outcome, Decision Evaluation, Lesson, retrospective criteria, and attributable evaluation judgment. It is distinct because observed consequence, retrospective process judgment, and durable learning must remain separate so favorable or unfavorable outcomes do not automatically certify or condemn the quality of the original decision process.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Outcome is a decision-relative observed consequence and does not by itself establish causality or decision quality. (source: docs/current/platform-architecture-0.2.0.md)
* Decision Evaluation is an attributable retrospective judgment against explicit criteria and a historically faithful basis; it is distinct from Outcome and from generic AI evaluation. (source: docs/current/platform-architecture-0.2.0.md)
* Lesson is a durable scoped learning proposition and does not silently become Policy, Mandate, Formal Constraint, or authority. (source: docs/current/platform-architecture-0.2.0.md)
* Historical Decision Memory used for evaluation must preserve what was actually knowable at the relevant time rather than projecting later facts backward. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md)
