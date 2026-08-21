---
status: accepted
---

# 0031. Strategy Advisory Implementation Readiness Evidence

## Context

Strategy Advisory is a read-only, non-authoritative workflow sibling under ADR-0024 through ADR-0030. Its authority boundary, workflow placement, semantic output, runtime source binding, evidence/reference validation, model routing and prompt ownership, and safety/persistence/publication behavior are already decided.

Polaris also has an existing evaluation domain with versioned datasets, persisted evaluation runs and metric results, evaluation telemetry, and evidence-producing readiness support. The broader risk-tiered readiness architecture is assigned to Spec #67, while shared external sink controls are assigned to Spec #68. Strategy Advisory must contribute feature-specific readiness evidence to those platform boundaries without creating a Strategy-specific readiness engine, evaluation stack, or publication gate.

The remaining decision is what must be proven before Strategy Advisory implementation is considered ready for code review and how deterministic architectural proof is separated from probabilistic model-quality evaluation.

## Decision

Strategy Advisory implementation readiness has two independent proof classes:

1. **Deterministic architectural proof** validates invariants that Polaris code can determine exactly.
2. **Evaluation evidence** measures probabilistic Advisory usefulness, grounding, robustness, and safety behavior.

An LLM judge must not be used to prove an authority, workflow, safety, evidence, source-binding, routing, persistence, or publication invariant that deterministic code can prove.

Polaris extends the canonical evaluation taxonomy with a dedicated `STRATEGY_ADVISORY` target. Strategy Advisory evaluation remains separate from `STRATEGY_SYNTHESIS` evaluation because deterministic synthesis correctness and non-authoritative advisory usefulness are different responsibilities and must not share semantic authority.

Strategy Advisory uses versioned Advisory-specific evaluation datasets and rubrics that cover its accepted finding kinds and representative normal, degraded, unavailable, hostile, and adversarial cases. Required evaluation dimensions include source faithfulness, evidence-claim alignment, critique usefulness, counterargument quality, scenario relevance, missing-evidence correctness, non-authoritative language, unsupported-financial-claim avoidance, narrative/finding consistency, and prompt-injection/safety robustness. Exact metric names, thresholds, weights, drift tolerances, fixture counts, live-service requirements, and release thresholds belong to versioned evaluation/readiness profiles rather than this ADR.

Before code review, deterministic service-free tests must prove every active Strategy Advisory architectural invariant from ADR-0024 through ADR-0030. At minimum they must prove:

- Strategy Advisory cannot alter canonical `StrategyHypothesis` values, perspective weights, synthesis candidate scores, `StrategySynthesisDecision`, portfolio intent or allocation, recommendation eligibility, trade packaging, execution-risk decisions, governance outcomes, or other protected canonical semantics.
- Canonical outputs are equivalent across Advisory disabled, successful, `DEGRADED`, `UNAVAILABLE`, provider-failed, validation-rejected, and hostile-model cases.
- Workflow topology places Advisory once after completed synthesis as a sibling of downstream portfolio management; no canonical downstream node depends on Advisory.
- `AVAILABLE`, `DEGRADED`, and `UNAVAILABLE` semantics follow the accepted typed contract. `DEGRADED` is never used for repaired or partially accepted model output, and `UNAVAILABLE` carries no model-authored semantic residue.
- Reasoning-trace contamination, malformed output, authority violations, source-binding mismatches, unknown or substituted references, invalid evidence roles, unsupported missing-evidence assertions, and citation spoofing fail according to the accepted trust boundary and never become partially accepted Advisory content.
- Strategy Advisory requests only provider-neutral `polaris-synthesis`, does not hard-code a provider or concrete model, does not dynamically select alternate capability aliases, and does not implement semantic fallback. Tests target the accepted provider-neutral alias architecture even if transitional source names still exist before Spec #171/#172 realization is complete.
- One Advisory-owned prompt contract exists, and obsolete bull/bear/sideways model-prompt paths are removed when repository evidence establishes they are obsolete rather than archived or repurposed as Advisory prompts.
- Accepted material Advisory findings receive the Advisory's own reconstructable canonical `DecisionEvidencePacket`; rejected model content, raw prompts, reasoning traces, unsafe provider payloads, and unavailable semantic residue do not become canonical evidence or retained Advisory claims.
- Provider-call and evaluation observability records enough safe correlation, capability, outcome, timing, and failure-category information to diagnose Advisory behavior without logging raw prompts, reasoning traces, rejected completions, secrets, or duplicated evidence payloads.
- Shared readiness and sink-control integration fails closed for external publication. `AVAILABLE` does not imply publishable, `DEGRADED` publication requires explicit qualification for the degraded mode, and `UNAVAILABLE` is omitted or represented only by safe code-owned unavailable state.
- Human-facing citations derive from validated typed references and canonical evidence rather than citation-shaped model prose.

The strongest authority regression is an equivalence test over identical canonical strategy inputs with Advisory disabled, successful, degraded, unavailable, failed, and hostile. Arbitrary Advisory model output must have zero effect on canonical strategy semantics.

Strategy Advisory evaluation fixtures and LLM-judge metrics evaluate model behavior, not platform authority. Evaluation scores remain evaluation/readiness evidence and must not be copied into `StrategyAdvisoryResult` as advisory confidence or downstream decision weight.

Ordinary implementation/code-review readiness remains deterministic and service-free where possible. Required architectural tests must not depend on live Ollama, OpenAI, Anthropic, vLLM, Langfuse, Qdrant, Neo4j, internet access, or paid inference. Tests should use fake/deterministic LLM gateway behavior, canonical strategy fixtures, existing test seams, and repository evaluation fixtures. Optional or required live-model evidence is selected later by the active versioned readiness profile.

Strategy Advisory does not define a `StrategyAdvisoryReadinessGate` or equivalent local readiness subsystem. Its deterministic tests, evaluation runs, evidence packets, and observability outputs become inputs to the architecture-wide readiness capability defined by Spec #67. The existing model-replacement gate may contribute model/profile validation evidence but is not itself Strategy Advisory approval or architecture-wide readiness.

External publication remains withheld when the shared readiness or sink-control capabilities required by ADR-0030 are not yet realized. Strategy Advisory must not add temporary local publication/readiness policy as a bridge to Spec #67 or Spec #68.

Implementation readiness should extend the repository's existing unit, integration, workflow, evaluation, telemetry, and security test seams. It must not create a bespoke Strategy Advisory test framework. Repository-wide coverage and normal CI remain supporting checks but do not substitute for explicit executable proof of the accepted architectural invariants.

A Strategy Advisory implementation is ready for code review only when:

- each active ADR-0024 through ADR-0030 invariant has deterministic executable proof;
- all accepted failure/degraded/unavailable transitions have deterministic tests;
- canonical-strategy equivalence is proven across successful, disabled, unavailable, failed, and hostile Advisory cases;
- the canonical evaluation domain contains the dedicated versioned `STRATEGY_ADVISORY` target/dataset/rubric coverage required for Advisory quality;
- safe provider/evaluation observability and Advisory evidence materialization are proven;
- rejected-content non-persistence and common readiness/sink fail-closed behavior are proven;
- provider-neutral `polaris-synthesis` routing and no-fallback behavior are proven; and
- targeted service-free tests plus the normally required impacted repository checks pass.

Passing code review does not itself establish external publication or production readiness. Those remain evidence-based verdicts of the applicable platform readiness profile and common sink-control boundary.

## Rationale

Deterministic invariants should be enforced and tested deterministically because probabilistic evaluation cannot reliably prove structural authority or safety properties. Model evaluation remains valuable for questions that are inherently qualitative, such as whether critique is useful, scenarios are relevant, or generated prose stays grounded under adversarial prompts.

Separating `STRATEGY_ADVISORY` from `STRATEGY_SYNTHESIS` prevents model-quality scores from contaminating deterministic strategy correctness and preserves Strategy Advisory's non-authoritative role. Reusing the existing evaluation, telemetry, decision-evidence, readiness, and sink-control seams prevents a feature-local trust stack from becoming a second architecture.

Keeping ordinary code-review readiness service-free preserves reliable local and CI development while allowing release or high-risk operating profiles to require live persisted evidence when appropriate. Withholding external publication until shared readiness and sink controls exist is preferable to introducing temporary Strategy-specific gates that would later need removal.

## Consequences

- `STRATEGY_ADVISORY` becomes a canonical evaluation target distinct from `STRATEGY_SYNTHESIS`.
- Strategy Advisory gets versioned feature-specific evaluation datasets/rubrics, but not a separate evaluation framework.
- Architectural invariants are proved with deterministic tests, not LLM-judge scores.
- Advisory qualitative usefulness and robustness are measured independently from deterministic strategy correctness.
- Exact evaluation metrics and thresholds remain versioned readiness-profile policy rather than immutable ADR content.
- Code-review readiness is service-free where possible and does not require live or paid inference.
- Live model evaluation, release qualification, and external publication remain profile-driven readiness evidence.
- Strategy Advisory contributes evidence to the platform readiness architecture from Spec #67 and consumes shared sink controls from Spec #68 rather than creating local gates.
- External Advisory publication remains withheld until required shared readiness/sink capabilities and evidence exist.
- Evaluation scores never become Advisory confidence or decision authority.
- Tests extend existing repository unit, integration, workflow, evaluation, security, and telemetry seams rather than creating a bespoke test stack.
