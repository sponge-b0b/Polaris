# Polaris Product Principles

**Status:** Defined  
**Purpose:** Preserve the durable decision rules used to evaluate Polaris product, architecture, roadmap, and experience choices when more than one plausible implementation or product direction could satisfy the Product Definition.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). The principles are intentionally stronger than a values list: each should be capable of rejecting an otherwise plausible feature, architecture, workflow, or user-experience choice.

## Umbrella principle

> **Every Polaris product, architecture, and roadmap decision should strengthen the quality, trustworthiness, continuity, or learning value of the portfolio decision lifecycle—or have a clear supporting reason for existing.**

The twelve principles below make that rule operational.

## 1. Decisions before features

> **Optimize the portfolio decision lifecycle before optimizing individual features.**

A new capability is justified by how it improves an Investment Decision, explanation, Decision Evaluation, or future decision quality—not merely because it is technically interesting or adjacent to finance.

This applies equally to analytical features, AI techniques, interfaces, infrastructure, and integrations. A sophisticated agent topology, charting system, or workflow engine is not product progress unless it strengthens the defined decision lifecycle.

**Decision rule:** When feature sophistication and decision quality compete, decision quality wins.

## 2. Trust by structure, not confidence

> **Do not ask the user to trust AI because it sounds confident; construct the system so important Claims, judgments, decisions, and authority can be inspected.**

Trust should come from attributable Evidence, decision-appropriate freshness, explicit Investment Uncertainty, meaningful challenge, deterministic rule results, power-specific authority provenance, Human Investment Decision, operational reality, and historical integrity.

A model-specific confidence or calibrated score may be useful analytical information when its subject and meaning are explicit. It is not universal Judgment Confidence and is not a substitute for the surrounding trust structure.

**Decision rule:** Prefer architecture that reduces how much blind trust must be placed in the model.

## 3. Preserve truth before convenience

> **Never simplify the user experience by silently destroying meaningful truth.**

Polaris may summarize, progressively disclose, and reduce cognitive load. It must not collapse distinctions that matter to later inspection or learning.

Examples include preserving the difference between:

* Investment Recommendation and Human Investment Decision;
* Policy or Formal Constraint result and Approval;
* Proposed Action and Action Intent;
* Action Intent and authoritative external activity;
* expected or projected Portfolio State and authoritative observed Portfolio State;
* what was available to a judgment at the time and what became known later.

The product may present a concise summary while preserving the complete Evidence, judgment, authority, and continuity path underneath it.

**Decision rule:** Progressive disclosure may hide detail temporarily; it must not erase semantic distinctions.

## 4. AI initiative without AI sovereignty

> **Give Polaris broad freedom to observe, investigate, reason, challenge, prepare, and recommend—but not to silently acquire authority over consequential investment action or its own governing constraints.**

Polaris should not require the human to initiate every useful piece of analysis. It should be capable of detecting Investment-Relevant material change, investigating it, reassessing affected unresolved work or prior judgments, and bringing prepared work to the user.

That initiative stops at the applicable consequential authority boundary. The Investment Authority Regime determines who may form a Human Investment Decision, grant Approval, authorize a Mandate Exception, accept Governed Residual Risk, or exercise execution authority. External specialist systems retain market-facing action authority.

**Decision rule:** Automate analytical work aggressively; escalate the specific consequential authority act explicitly.

## 5. Portfolio Risk shapes the decision

> **Portfolio Risk is part of forming an Investment Recommendation, not an approval stamp applied afterward.**

Investment View, Portfolio State, Portfolio Risk, Projected Portfolio Consequences, applicable Formal Constraints, and Policy should jointly shape the preferred economic disposition while preserving their distinct semantic roles.

A plausible Investment Thesis may imply different Investment Recommendations in different Portfolios because concentration, Exposure, Investment Strategy, Investment Horizon, current Portfolio Risk, Investment Mandate, and Policy differ. That is not Portfolio Risk interfering with the strategy; it is the Portfolio decision itself.

Formal Constraint results and Policy results are deterministic boundaries, not Portfolio Risk and not Approval.

**Decision rule:** An Investment Recommendation that has not incorporated Portfolio Risk and the applicable deterministic boundaries is unfinished.

## 6. Be attentive, not noisy

> **Optimize for attention quality, not information volume or interaction frequency.**

Polaris should not measure usefulness by the number of alerts, Investment Recommendations, reports, messages, generated insights, or agent outputs it produces.

A mature system should absorb irrelevant or immaterial changes quietly and treat conclusions such as "nothing materially changed" or "no Portfolio action is warranted" as successful outcomes.

When Polaris interrupts the user, it should preferably bring prepared decision work rather than merely announce that something happened.

**Decision rules:** Interrupt for Investment Materiality, not novelty. When interrupting, bring analysis rather than assigning analysis back to the user.

## 7. Current enough for the decision

> **Freshness is relative to the investment use, not to a universal definition of real time.**

The Evidence freshness required for a rapid Portfolio reassessment may differ substantially from the freshness required for a long-horizon strategic judgment.

Polaris should neither accept stale Evidence merely because it exists nor adopt exchange-engine latency as a universal product requirement. It should understand how current the Evidence must be for the judgment or consequential use it is claiming to support.

When required Evidence is too stale, the appropriate response may be to qualify or withhold a current Investment Recommendation or consequential use. The historical Investment Recommendation remains part of Durable Decision Memory; staleness does not erase that prior judgment.

**Decision rule:** If Evidence is too stale to support the current claim or use, reduce the current claim—not the standard and not the historical record.

## 8. Durable Decision Memory should change future behavior

> **Do not preserve Investment Decisions merely so they can be retrieved later; preserve their material meaning so it can improve future Attention, reasoning, Decision Evaluation, and learning.**

Durable Decision Memory is active product context, not a passive archive and not a requirement for one `Decision Record` entity.

Past Investment Decisions may contain active Investment Theses, Investment Assumptions, Invalidation Conditions, deferred decisions, Catalysts, Review Conditions, Portfolio Risk expectations, authority relationships, and Lessons. Those facts should be capable of changing what Polaris notices and how future decisions are formed.

A prior Human Investment Decision such as "maintain the Position unless condition X occurs" should make condition X materially relevant later without requiring the user to reconstruct the earlier context manually. If the prior decision was substantively resolved, condition X causes Attention to evaluate whether a renewed Decision Need exists; it does not reopen and rewrite the old decision.

**Decision rule:** If durable decision history never influences future behavior, it is an archive, not Durable Decision Memory.

## 9. Reality wins

> **When Polaris's expectation conflicts with authoritative external reality, reality wins.**

Polaris may identify an inconsistency, question the reliability of a source, or preserve Conflicting Evidence. It must not silently promote its expected state over an authoritative operational source merely because the external result differs from an Investment Recommendation or Action Intent.

This applies to facts such as fills, Positions, Portfolio State, published economic releases, and other externally authoritative observations within their responsibility domains.

**Decision rule:** Model the world Polaris actually observes, not the world its previous judgment expected to exist.

## 10. Integrate before absorbing

> **Prefer integrating with specialist systems over casually assuming their responsibilities.**

Polaris owns the portfolio decision lifecycle, not everything that lifecycle touches.

Before expanding into an adjacent product category, Polaris should ask whether a specialist system can continue to own the underlying operational or factual responsibility while Polaris consumes, reconciles, interprets, or presents the necessary state.

This is especially important for execution, brokerage operations, official accounting, custody, settlement, comprehensive market-data vending, generalized charting, generalized quantitative development, and other specialist responsibilities.

Expansion may still be justified, but it should carry an explicit burden of proof when it creates a new primary job, authority domain, latency contract, operational responsibility, regulatory burden, or product identity.

**Decision rule:** Own the decision responsibility; integrate the surrounding specialist responsibility when practical.

## 11. Opinionated domain, flexible process

> **Make investment processes configurable while keeping the portfolio decision lifecycle and its domain concepts opinionated.**

Polaris should allow users to vary Portfolios, Investment Strategies, Evidence sources, models, Policies, Investment Mandates, Investment Horizons, Review Conditions, asset universes, and analytical preferences.

That flexibility should operate inside recognizable investment-domain concepts such as Evidence, Investment Thesis, Portfolio State, Portfolio Risk, Investment Recommendation, Investment Authority Regime, Human Investment Decision, Action Intent, Outcome, and Decision Evaluation.

If users must reconstruct those concepts from generic nodes, graphs, prompts, or arbitrary workflows in order to use the product, Polaris has surrendered too much product opinion.

**Decision rule:** Make the investment process configurable; keep the decision lifecycle opinionated.

## 12. Learn from process, not Outcome alone

> **Judge decisions by the quality of the process and the information available at the time, not merely by whether the Outcome made money.**

Investing is probabilistic. A sound judgment can produce an unfavorable Outcome, and a weak judgment can coincide with a favorable one.

Polaris should therefore preserve enough information to evaluate Evidence quality, reasoning quality, Portfolio Risk reasoning, Policy and Formal Constraint effects, Investment Recommendation quality, Human Investment Decision, implementation fidelity, and observed Outcome separately where useful.

Historical Decision Evaluation should respect Judgment-Time Availability. Later facts are valid Evidence for retrospective evaluation and learning, but they must not be treated as though they were available to an earlier judgment.

**Decision rule:** Evaluate the judgment using what was available then; use what happened afterward to learn, not to rewrite the past.

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
5. Portfolio Risk shapes the decision

        ↓

EXPERIENCE MODEL
6. Be attentive, not noisy
7. Current enough for the decision

        ↓

CONTINUITY MODEL
8. Durable Decision Memory should change future behavior
9. Reality wins

        ↓

SCOPE MODEL
10. Integrate before absorbing
11. Opinionated domain, flexible process

        ↓

LEARNING MODEL
12. Learn from process, not Outcome alone
```

This hierarchy is conceptual rather than a precedence order. When principles appear to conflict, the Product Definition should be interpreted as a whole, with Purpose, Authority Model, and Scope Boundaries providing the strongest constraints.

## Why some plausible principles are not separate principles

### "Prefer deterministic software where possible"

Polaris already uses deterministic software where explicit rules, invariants, Freshness Requirements, Formal Constraints, Policy, and guarantees matter. AI remains valuable where interpretation, synthesis, challenge, and probabilistic reasoning are required.

A blanket deterministic preference would be less useful than the more precise distinctions already established by the Authority Model and the trust principles.

The stronger question is:

> Does this responsibility require investment interpretation, deterministic rule evaluation, or a power-specific authority act?

Interpretation may justify AI. Deterministic rule evaluation should be deterministic where practical. Authority remains governed by the applicable Investment Authority Regime rather than by implementation technique.

### "Keep it simple"

Simplicity remains an important engineering value, but it is not sufficient as a Polaris product principle.

A superficial appeal to simplicity could otherwise justify deleting provenance, authority distinctions, or historical context that the product requires for trustworthiness.

The Polaris-specific rule is stronger:

> **Simplify presentation without simplifying away truth.**

## Applying the principles

The principles should function as rejection and refinement tests for future proposals.

For a proposed feature, architecture, roadmap item, or user experience, useful questions include:

* Does this strengthen the Investment Decision lifecycle or merely add feature surface?
* Does it reduce blind trust in AI or increase it?
* Does it preserve meaningful Evidence, judgment, and authority distinctions?
* Does it increase useful analytical initiative without crossing a power-specific authority boundary?
* Does Portfolio Risk shape the Investment Recommendation itself?
* Does it spend user Attention only when materially justified?
* Does it respect the applicable Freshness Requirements?
* Does Durable Decision Memory change future product behavior?
* Does authoritative operational reality remain authoritative?
* Can an external specialist system continue to own the adjacent responsibility?
* Is flexibility expressed in investment-domain terms rather than generic workflow primitives?
* Can later Decision Evaluation distinguish process quality from Outcome?

A proposal need not maximize every principle independently. It should not casually violate one in order to gain convenience elsewhere.

## Examples of doctrine resolving product choices

### Automatic trade placement above a confidence threshold

A proposal that allows Polaris to place trades automatically whenever model confidence exceeds a threshold conflicts with several principles:

* **Trust by structure, not confidence:** a model-specific score is not sufficient authority.
* **AI initiative without AI sovereignty:** consequential investment and execution authority must come from the applicable authority regime and external action system.
* **Integrate before absorbing:** market-facing execution remains a specialist responsibility under the current Product Definition.

The product doctrine therefore rejects the proposal without requiring a feature-by-feature debate.

### Comprehensive adjacent product expansion

A proposal to build a full generalized charting or execution product because Polaris already contains some charting or execution-aware capability should be tested against:

* **Decisions before features:** what decision job requires the expansion?
* **Integrate before absorbing:** can a specialist product continue to own the broader responsibility?
* **Opinionated domain, flexible process:** would the expansion make Polaris a generalized terminal rather than a portfolio decision system?

A narrower Polaris-native capability may still be justified if it materially improves the decision experience.

### Inferring Approval from silence

A proposal to infer Approval merely because no Policy denial, Formal Constraint violation, or other failure was recorded conflicts with:

* **Trust by structure, not confidence.**
* **Preserve truth before convenience.**

Policy allow, Formal Constraint satisfaction, and Approval are distinct facts. If Approval is materially required, the attributable authority act should be positively recorded.

### Persisting only the final Investment Recommendation

A proposal to store only the final Investment Recommendation for simplicity conflicts with:

* **Preserve truth before convenience.**
* **Durable Decision Memory should change future behavior.**
* **Learn from process, not Outcome alone.**

The final Investment Recommendation cannot substitute for the material Evidence, reasoning, Decision Alternatives, authority acts, Human Investment Decision, Action Intent where applicable, external activity, Outcome, Decision Evaluation, and Lessons needed for trustworthy reconstruction.

## Relationship to roadmap and architecture

Product Principles should constrain both roadmap selection and architecture choices.

Roadmap work should prefer milestones that deepen the end-to-end decision system over disconnected feature accumulation. Architecture work should prefer designs that preserve the defined authority, provenance, continuity, and historical-integrity contracts even when a simpler local implementation would erase those semantics.

At the same time, the principles do not prescribe particular models, languages, databases, agent topologies, workflow engines, interfaces, or package boundaries. Those implementation choices remain subordinate to the product contract.

## Consequences

The Product Principles imply:

* product progress is measured by stronger Portfolio decision capability rather than feature count;
* trustworthy structure matters more than persuasive model confidence;
* user simplicity must not erase meaningful truth;
* analytical autonomy should be broad while consequential authority remains bounded and power-specific;
* Portfolio Risk is part of Investment Recommendation formation;
* human Attention is a scarce resource to be spent selectively;
* Freshness Requirements follow the supported investment use;
* Durable Decision Memory must influence future behavior;
* authoritative operational reality outranks expected state;
* external specialist responsibilities should normally remain external;
* configurability should stay grounded in investment-domain concepts;
* Decision Evaluation should distinguish decision-process quality from Outcome.

Together these principles provide durable decision rules for building Polaris after the Product Definition is complete.
