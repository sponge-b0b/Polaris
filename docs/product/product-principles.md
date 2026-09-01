# Polaris Product Principles

**Status:** Defined  
**Purpose:** Preserve the durable decision rules used to evaluate Polaris product, architecture, roadmap, and experience choices when more than one plausible implementation or product direction could satisfy the Product Definition.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). The principles are intentionally stronger than a values list: each should be capable of rejecting an otherwise plausible feature, architecture, workflow, or user-experience choice.

## Umbrella principle

> **Every Polaris product, architecture, and roadmap decision should strengthen the quality, trustworthiness, continuity, or learning value of the portfolio decision lifecycle—or have a clear supporting reason for existing.**

The twelve principles below make that rule operational.

## 1. Decisions before features

> **Optimize the portfolio decision lifecycle before optimizing individual features.**

A new capability is justified by how it improves a portfolio decision, explanation, evaluation, or future decision quality—not merely because it is technically interesting or adjacent to finance.

This applies equally to analytical features, AI techniques, interfaces, infrastructure, and integrations. A sophisticated agent topology, charting system, or workflow engine is not product progress unless it strengthens the defined decision lifecycle.

**Decision rule:** When feature sophistication and decision quality compete, decision quality wins.

## 2. Trust by structure, not confidence

> **Do not ask the user to trust AI because it sounds confident; construct the system so important claims, decisions, and authority can be inspected.**

Trust should come from attributable evidence, decision-appropriate freshness, explicit uncertainty, meaningful challenge, deterministic constraints, authority provenance, human judgment, operational reality, and historical integrity.

A confidence score may be useful evidence about a model output. It is not a substitute for the surrounding trust structure.

**Decision rule:** Prefer architecture that reduces how much blind trust must be placed in the model.

## 3. Preserve truth before convenience

> **Never simplify the user experience by silently destroying meaningful truth.**

Polaris may summarize, progressively disclose, and reduce cognitive load. It must not collapse distinctions that matter to later inspection or learning.

Examples include preserving the difference between:

* recommendation and human decision;
* policy evaluation and final recommendation;
* intended action and observed execution;
* expected state and authoritative external state;
* what was knowable at decision time and what became known later.

The product may present a concise summary while preserving the complete evidence and authority path underneath it.

**Decision rule:** Progressive disclosure may hide detail temporarily; it must not erase semantic distinctions.

## 4. AI initiative without AI sovereignty

> **Give Polaris broad freedom to observe, investigate, reason, challenge, prepare, and recommend—but not to silently acquire authority over consequential investment action or its own governing constraints.**

Polaris should not require the human to initiate every useful piece of analysis. It should be capable of detecting material change, investigating it, reassessing affected decisions, and bringing prepared work to the user.

That initiative stops at the consequential authority boundary. Human judgment remains required for investment decisions and material governance changes, and external specialist systems retain market-facing action authority.

**Decision rule:** Automate analytical work aggressively; escalate consequential judgment explicitly.

## 5. Risk shapes the decision

> **Risk is part of forming a recommendation, not an approval stamp applied afterward.**

Investment interpretation, portfolio state, analytical risk, and deterministic policy should jointly shape the preferred action.

A plausible investment thesis may imply different actions in different portfolios because concentration, exposure, strategy, horizon, existing risk, and policy differ. That is not risk interfering with the strategy; it is the portfolio decision itself.

**Decision rule:** A recommendation that has not incorporated portfolio risk is unfinished.

## 6. Be attentive, not noisy

> **Optimize for attention quality, not information volume or interaction frequency.**

Polaris should not measure usefulness by the number of alerts, recommendations, reports, messages, generated insights, or agent outputs it produces.

A mature system should absorb immaterial changes quietly and treat conclusions such as "nothing materially changed" or "no action warranted" as successful outcomes.

When Polaris interrupts the user, it should preferably bring prepared decision work rather than merely announce that something happened.

**Decision rules:** Interrupt for materiality, not novelty. When interrupting, bring analysis rather than assigning analysis back to the user.

## 7. Current enough for the decision

> **Freshness is relative to the decision contract, not to a universal definition of real time.**

The evidence freshness required for a rapid portfolio reassessment may differ substantially from the freshness required for a long-horizon strategic judgment.

Polaris should neither accept stale evidence merely because it exists nor adopt exchange-engine latency as a universal product requirement. It should understand how current the evidence must be for the decision it is claiming to support.

When required evidence is too stale, the appropriate response may be to qualify, degrade, withhold, or invalidate the recommendation.

**Decision rule:** If evidence is too stale to support the claimed decision, reduce the claim—not the standard.

## 8. Memory should change future behavior

> **Do not preserve decisions merely so they can be retrieved later; preserve them so they can improve future attention, reasoning, evaluation, and learning.**

Decision memory is active product state, not a passive archive.

Past decisions may contain active theses, assumptions, invalidation conditions, deferred decisions, catalysts, review conditions, risk expectations, and lessons. Those facts should be capable of changing what Polaris notices and how future decisions are formed.

A prior decision such as "maintain the position unless condition X occurs" should make condition X materially relevant later without requiring the user to reconstruct the earlier context manually.

**Decision rule:** If durable decision state never influences future decisions, it is an archive, not decision memory.

## 9. Reality wins

> **When Polaris's expectation conflicts with authoritative external reality, reality wins.**

Polaris may identify an inconsistency, question the reliability of a source, or preserve conflicting evidence. It must not silently promote its expected state over an authoritative operational source merely because the external result differs from the recommendation or intended action.

This applies to facts such as fills, positions, portfolio state, published economic releases, and other externally authoritative observations within their responsibility domains.

**Decision rule:** Model the world Polaris actually observes, not the world its previous decision expected to exist.

## 10. Integrate before absorbing

> **Prefer integrating with specialist systems over casually assuming their responsibilities.**

Polaris owns the portfolio decision lifecycle, not everything that lifecycle touches.

Before expanding into an adjacent product category, Polaris should ask whether a specialist system can continue to own the underlying operational or factual responsibility while Polaris consumes, reconciles, interprets, or projects the necessary state.

This is especially important for execution, brokerage operations, official accounting, custody, settlement, comprehensive market-data vending, generalized charting, generalized quantitative development, and other specialist responsibilities.

Expansion may still be justified, but it should carry an explicit burden of proof when it creates a new primary job, authority domain, latency contract, operational responsibility, regulatory burden, or product identity.

**Decision rule:** Own the decision responsibility; integrate the surrounding specialist responsibility when practical.

## 11. Opinionated domain, flexible process

> **Make investment processes configurable while keeping the portfolio decision lifecycle and its domain concepts opinionated.**

Polaris should allow users to vary portfolios, strategies, evidence sources, models, risk policies, horizons, review conditions, asset universes, and analytical preferences.

That flexibility should operate inside recognizable investment-domain concepts such as evidence, thesis, portfolio, risk, recommendation, authority, decision, action, outcome, and evaluation.

If users must reconstruct those concepts from generic nodes, graphs, prompts, or arbitrary workflows in order to use the product, Polaris has surrendered too much product opinion.

**Decision rule:** Make the investment process configurable; keep the decision lifecycle opinionated.

## 12. Learn from process, not outcome alone

> **Judge decisions by the quality of the process and the information available at the time, not merely by whether the outcome made money.**

Investing is probabilistic. A sound decision can produce a loss, and a weak decision can produce a gain.

Polaris should therefore preserve enough information to evaluate evidence quality, reasoning quality, risk reasoning, policy effects, recommendation quality, human judgment, execution fidelity, and realized outcome separately where useful.

Historical evaluation should use what was knowable at decision time. Later facts are valid inputs to evaluation and learning, but they must not be used to rewrite what the original decision supposedly knew.

**Decision rule:** Evaluate the decision using what was knowable then; use what happened afterward to learn, not to rewrite the past.

## Principle hierarchy

The principles reinforce the major parts of the Product Definition:

```text
PRODUCT CENTER
1. Decisions before features

        ↓

TRUST MODEL
2. Trust by structure, not confidence
3. Preserve truth before convenience

        ↓

AUTHORITY MODEL
4. AI initiative without AI sovereignty
5. Risk shapes the decision

        ↓

EXPERIENCE MODEL
6. Be attentive, not noisy
7. Current enough for the decision

        ↓

CONTINUITY MODEL
8. Memory should change future behavior
9. Reality wins

        ↓

SCOPE MODEL
10. Integrate before absorbing
11. Opinionated domain, flexible process

        ↓

LEARNING MODEL
12. Learn from process, not outcome alone
```

This hierarchy is conceptual rather than a precedence order. When principles appear to conflict, the Product Definition should be interpreted as a whole, with Purpose, Authority Model, and Scope Boundaries providing the strongest constraints.

## Why some plausible principles are not separate principles

### "Prefer deterministic software where possible"

Polaris already uses deterministic software where explicit rules, invariants, freshness requirements, hard constraints, and guarantees matter. AI remains valuable where interpretation, synthesis, challenge, and probabilistic reasoning are required.

A blanket deterministic preference would be less useful than the more precise distinction already established by the Authority Model and the trust principles.

The stronger question is:

> Does this responsibility require interpretation or enforcement?

Interpretation may justify AI. Enforceable constraints should generally be deterministic where practical.

### "Keep it simple"

Simplicity remains an important engineering value, but it is not sufficient as a Polaris product principle.

A superficial appeal to simplicity could otherwise justify deleting provenance, authority distinctions, or historical context that the product requires for trustworthiness.

The Polaris-specific rule is stronger:

> **Simplify presentation without simplifying away truth.**

## Applying the principles

The principles should function as rejection and refinement tests for future proposals.

For a proposed feature, architecture, roadmap item, or user experience, useful questions include:

* Does this strengthen the decision lifecycle or merely add feature surface?
* Does it reduce blind trust in AI or increase it?
* Does it preserve meaningful evidence and authority distinctions?
* Does it increase useful analytical initiative without crossing the authority boundary?
* Does risk shape the recommendation itself?
* Does it spend user attention only when materially justified?
* Does it respect decision-appropriate freshness?
* Does preserved memory change future product behavior?
* Does authoritative operational reality remain authoritative?
* Can an external specialist system continue to own the adjacent responsibility?
* Is flexibility expressed in investment-domain terms rather than generic workflow primitives?
* Can later evaluation distinguish process quality from outcome?

A proposal need not maximize every principle independently. It should not casually violate one in order to gain convenience elsewhere.

## Examples of doctrine resolving product choices

### Automatic trade placement above a confidence threshold

A proposal that allows Polaris to place trades automatically whenever model confidence exceeds a threshold conflicts with several principles:

* **Trust by structure, not confidence:** model confidence is not sufficient authority.
* **AI initiative without AI sovereignty:** consequential investment judgment remains human.
* **Integrate before absorbing:** market-facing execution remains a specialist responsibility under the current Product Definition.

The product doctrine therefore rejects the proposal without requiring a feature-by-feature debate.

### Comprehensive adjacent product expansion

A proposal to build a full generalized charting or execution product because Polaris already contains some charting or execution-aware capability should be tested against:

* **Decisions before features:** what decision job requires the expansion?
* **Integrate before absorbing:** can a specialist product continue to own the broader responsibility?
* **Opinionated domain, flexible process:** would the expansion make Polaris a generalized terminal rather than a portfolio decision system?

A narrower Polaris-native capability may still be justified if it materially improves the decision experience.

### Inferring approval from silence

A proposal to infer that policy approval occurred merely because no policy failure was recorded conflicts with:

* **Trust by structure, not confidence.**
* **Preserve truth before convenience.**

The authority decision should be positively recorded when it is material.

### Persisting only the final recommendation

A proposal to store only the final recommendation for simplicity conflicts with:

* **Preserve truth before convenience.**
* **Memory should change future behavior.**
* **Learn from process, not outcome alone.**

The final recommendation cannot substitute for the material evidence, reasoning, authority, human decision, and subsequent lifecycle needed for trustworthy evaluation.

## Relationship to roadmap and architecture

Product Principles should constrain both roadmap selection and architecture choices.

Roadmap work should prefer milestones that deepen the end-to-end decision system over disconnected feature accumulation. Architecture work should prefer designs that preserve the defined authority, provenance, continuity, and historical-integrity contracts even when a simpler local implementation would erase those semantics.

At the same time, the principles do not prescribe particular models, languages, databases, agent topologies, workflow engines, interfaces, or package boundaries. Those implementation choices remain subordinate to the product contract.

## Consequences

The Product Principles imply:

* product progress is measured by stronger portfolio decision capability rather than feature count;
* trustworthy structure matters more than persuasive model confidence;
* user simplicity must not erase meaningful truth;
* analytical autonomy should be broad while consequential authority remains bounded;
* risk is part of recommendation formation;
* human attention is a scarce resource to be spent selectively;
* freshness requirements follow the supported decision;
* durable memory must influence future behavior;
* authoritative operational reality outranks expected state;
* external specialist responsibilities should normally remain external;
* configurability should stay grounded in investment-domain concepts;
* evaluation should distinguish decision-process quality from realized outcome.

Together these principles provide durable decision rules for building Polaris after the Product Definition is complete.