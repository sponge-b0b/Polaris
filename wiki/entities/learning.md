# Learning (Entity ID: learning)

**Boundary Rationale:** This boundary owns Outcome, Decision Evaluation, Lesson, retrospective criteria, and attributable evaluation judgment. It is distinct because observed consequence, retrospective process judgment, and durable learning must remain separate so favorable or unfavorable outcomes do not automatically certify or condemn the quality of the original decision process.
(source: owner-approved entity boundary determination)

### Strict Invariants

* R3 persists Outcome, Decision Evaluation, and Lesson as separate durable facts: observed consequence never determines process quality, evaluation preserves ex-ante versus ex-post knowledge boundaries, and Lesson remains scoped learning rather than authority or an automatic future-behavior rule. (source: docs/adr/0010-learning-separate-r3-outcome-evaluation-and-lesson.md)
* Outcome is a decision-relative observed consequence and does not by itself establish causality or decision quality. (source: docs/current/platform-architecture-0.2.0.md)
* Decision Evaluation is an attributable retrospective judgment against explicit criteria and a historically faithful basis; it is distinct from Outcome and from generic AI evaluation. (source: docs/current/platform-architecture-0.2.0.md)
* Lesson is a durable scoped learning proposition and does not silently become Policy, Mandate, Formal Constraint, or authority. (source: docs/current/platform-architecture-0.2.0.md)
* Historical Decision Memory used for evaluation must preserve what was actually knowable at the relevant time rather than projecting later facts backward. (source: docs/current/platform-architecture-0.2.0.md; docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md)


### Planned

* **R3 retrospective learning contract** — accepted, implementation pending. The first SPY slice will preserve durable Outcome observations, attributable criterion-based Decision Evaluations with hindsight-safe knowledge separation, and scoped Lessons supported by Evaluation/Evidence. Decision Evaluation and Lesson judgments admitted as Evidence targets will own complete versioned catalogs for explicitly declared material claims and owner-issued root-local judgment revisions; claim identity never migrates automatically across judgment roots. A materially used Outcome fact will expose its typed root-local version to the retrospective Evidence basis. R3 will expose Lessons without yet making them alter future Attention or Decision Context; that behavior remains R6. (source: docs/adr/0010-learning-separate-r3-outcome-evaluation-and-lesson.md; docs/adr/0013-evidence-complete-r3-claim-requirements-and-current-support-basis.md; docs/adr/0015-evidence-complete-r3-target-and-context-version-basis.md)
