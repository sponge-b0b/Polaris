---
status: accepted
---

# 0024. Non-Authoritative Strategy Advisory Boundary

## Context

ADR-0007 makes structured `StrategyHypothesis` production and deterministic `StrategySynthesisDecision` selection the canonical strategy authority. The later risk-authority decision also permits model output to explain, critique, summarize, draft, retrieve, or flag while prohibiting it from deciding strategy scoring, eligibility, sizing, execution safety, governance, policy, curation, production readiness, or capital action.

Polaris still benefits from model-assisted qualitative strategy analysis such as counterarguments, missing-evidence warnings, scenario-risk narration, and reviewer questions. The architecture therefore needs a durable boundary that permits those contributions without creating a second strategy-selection path or allowing advisory output to influence canonical strategy state indirectly.

## Decision

Polaris defines Strategy Advisory as a read-only, non-authoritative AI-adjacent lane over canonical strategy evidence and already-produced strategy artifacts.

Strategy Advisory may explain canonical strategy results, critique evidence sufficiency, surface conflicting or missing evidence, frame counterarguments or alternative scenarios, narrate qualitative risks, and raise questions for human review.

Strategy Advisory must not:

- create or replace canonical `StrategyHypothesis` objects;
- mutate `StrategyEvidenceContext`, hypothesis strength/confidence/assumptions/invalidation, perspective weights, candidate scores, synthesis weights, or `StrategySynthesisDecision`;
- participate in canonical hypothesis ranking or strategy selection;
- alter portfolio posture, allocation intent, recommendation eligibility, sizing, trade packaging, execution-risk decisions, policy, governance, approval, residual-risk acceptance, release, or readiness; or
- decide whether its own output is authoritative, sufficiently evidenced, publishable, durable, or RAG-eligible.

The canonical strategy lifecycle must remain semantically complete and produce the same authoritative strategy result whether Strategy Advisory succeeds, fails, is disabled, or does not exist.

If an advisory observation later causes automated platform behavior, the relevant condition must be re-established through an appropriate typed, code-owned authority before it may affect strategy, recommendation, governance, or capital state.

Durable advisory output, when later permitted by the persistence/publication architecture, is authoritative only as a record of what the advisory component said. Its claims do not thereby become authoritative strategy facts.

Model-generated alternatives must not be represented as canonical `StrategyHypothesis` objects. Use advisory-specific concepts such as an advisory counterargument or advisory scenario unless a later accepted contract chooses more precise terminology.

## Rationale

A read-only advisory lane preserves the replayability, attribution, deterministic testing, and single comparison authority established by ADR-0007 while still allowing models to contribute qualitative reasoning that deterministic scoring may not express well.

Allowing advisory output to feed back into hypothesis construction, scoring, synthesis, or downstream capital/governance decisions would create a second strategy authority and make model availability, drift, or failure capable of changing canonical strategy behavior. Keeping the lane observational also gives later workflow, contract, model-routing, persistence, publication, and evaluation decisions a stable authority boundary to build on.

## Consequences

- Strategy Advisory is an extension of the Strategy Synthesis boundary, not a replacement for its canonical decision path.
- Later Wayfinder decisions may choose where advisory generation runs and how it is typed, evidenced, persisted, presented, and evaluated, but they may not violate this authority boundary without a new architectural decision.
- Free-form advisory critique may aid humans, but it cannot become a backdoor debate or voting mechanism for canonical strategy selection.
