---
status: accepted
---

# Persist material investment judgments, not reasoning traces

## Context

R3 requires meaningful challenge, durable Recommendation history, and responsible withholding for the first coherent SPY Investment Decision slice. The architecture already separates model draft output from accepted business judgment and requires Investment View, Investment Recommendation, Human Investment Decision, and execution semantics to remain distinct.

The remaining decision is where durability begins inside Investment Intelligence. Persisting only a final Recommendation would lose the durable basis needed to reconstruct meaningful challenge and analytical uncertainty. Persisting complete prompts, model conversations, internal reasoning traces, or every candidate hypothesis would instead make implementation mechanics into canonical business truth.

## Decision

R3 persists **material business-semantic analytical judgments**, not reasoning transcripts or model topology.

A materially relied-upon **Investment View** is a durable, attributable, time-specific first-class judgment with opaque identity. It preserves the material Evidence basis, Investment Horizon, assumptions, Investment Uncertainty, materially surviving alternative explanation or dissent, and Invalidation Conditions where applicable. A materially new View appends as a new historical judgment rather than rewriting an earlier View.

An **Investment Hypothesis** becomes durable only when it materially shapes a View, challenge, Recommendation, or later Decision Evaluation. Transient hypotheses remain reasoning-local. R3 does not require an Investment Thesis for every decision.

Every Investment View used to support a consequential Investment Recommendation has a durable, attributable **meaningful-challenge result**. The result preserves the View being challenged, the strongest credible alternative explanation or competing interpretation actually considered, material Conflicting Evidence, challenged assumptions or uncertainty, and a substantive challenge disposition:

- `SURVIVES_CHALLENGE`
- `QUALIFIED`
- `REJECTED`
- `INCONCLUSIVE`

A boolean such as `challenged=true` is insufficient. The challenge contract does not require multiple models, Bull/Bear/Sideways agents, debate rounds, or any fixed reasoning topology.

Material **Decision Alternatives** that participate in Recommendation formation or materially inform a Human Investment Decision are durable. Transient brainstorming alternatives are not. For the first R3 SPY slice the minimum economic alternatives are increase exposure, hold/no-action, and reduce exposure.

An **Investment Recommendation** is a durable, attributable first-class judgment with opaque identity. It preserves the governing Investment Decision, formation time, Investment Horizon, preferred economic disposition, materially relied-upon Investment View or Views, material Decision Alternatives, material Evidence bindings, challenge result, Investment Uncertainty, applicable Portfolio/Risk consequence references, and material assumptions or invalidation references.

Investment Recommendation remains analytical judgment only. It does not establish Human Investment Decision, Approval, Admissibility, Action Intent, Order, or execution authority.

When Polaris deliberately determines that it cannot responsibly express a current preferred economic disposition, it records a durable attributable **Recommendation withholding judgment**. Withholding is not an Investment Recommendation and is not a hold/no-action Recommendation. No Recommendation attempted yet, explicit withholding, and an existing Recommendation are distinct states.

Recommendation history is append-only. Evidence refresh alone does not create a new Recommendation. Reconsideration that produces a new attributable preference creates a new Recommendation even when the economic disposition is unchanged. A later Recommendation does not rewrite an earlier one. A historical Recommendation may cease to be currently supportable, but that does not itself create a withholding judgment or reactivate an older Recommendation. Current support is derived from durable history plus current Decision applicability and current Evidence/Portfolio/Risk fitness.

Prompts, hidden/internal reasoning traces, provider-specific response fragments, retry attempts, debate turn order, discarded brainstorming, non-material hypotheses and alternatives, intermediate rankings/scores, and raw context that was not materially used as Evidence remain technical or transient unless separately promoted into a canonical business judgment.

## Rationale

This boundary preserves enough analytical history to explain what Polaris believed, how it was challenged, why a Recommendation was or was not formed, and how that judgment related to Evidence—without turning model internals or workflow mechanics into business identity.

It also preserves clean downstream ownership. Portfolio & Risk can attach projected consequences and Risk to durable alternatives and Views, while Governance can relate Human Investment Decisions to zero or more durable Recommendations without rewriting Investment Intelligence.

## Considered Options

### Persist only the final Investment Recommendation

Rejected because it cannot preserve meaningful challenge, material dissent, or the View/Portfolio distinction required to reconstruct responsible judgment.

### Persist complete prompts, model conversations, and reasoning traces

Rejected because implementation mechanics, provider topology, and transient reasoning are not canonical business truth.

### Persist every hypothesis and alternative

Rejected because transient analytical exploration does not merit durable business identity.

### Persist only materially consequential analytical judgments

Accepted because it preserves historical fidelity and explainability while keeping the durable model semantically bounded.
