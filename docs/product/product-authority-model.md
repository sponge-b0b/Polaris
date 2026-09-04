# Polaris Authority Model

**Status:** In progress  
**Purpose:** Preserve the product reasoning for how factual authority, deterministic rules, Polaris judgment, human investment authority, and external execution authority remain separated, exercised, recorded, and exposed across the Polaris decision lifecycle.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). It defines a product-level separation of powers rather than an implementation architecture or permission schema.

## Decision

Polaris uses a **separation-of-powers authority model**.

The decision lifecycle contains several materially different responsibilities that must not be collapsed merely because each can constrain what happens next:

```text
AUTHORITATIVE FACT SOURCES
"What externally authoritative facts are established?"
        ↓
DETERMINISTIC RULE EVALUATION
Policy / Formal Constraints / freshness and readiness
"Which rule results apply?"
        ↓
POLARIS INVESTMENT JUDGMENT
Investment View / Portfolio Risk Assessment / Investment Recommendation
"What does Polaris judge and recommend?"
        ↓
INVESTMENT AUTHORITY REGIME
Human Investment Decision and power-specific authority acts
"Who may decide, approve, except, or accept residual risk?"
        ↓
EXTERNAL EXECUTION AUTHORITY
Orders / fills / cancellations / operational state
"What was actually carried out?"
        ↓
EVIDENCE RETURNS
Observed external activity and resulting Portfolio State
```

Capability does not imply authority. Polaris may be capable of observing, researching, reasoning, challenging, recommending, reconciling, and evaluating without acquiring authority to move capital.

Likewise, deterministic rule evaluation is not automatically an authority act. A Policy result, a Formal Constraint result, Approval, Mandate Exception, Residual-Risk Acceptance, Human Investment Decision, and external execution authority are distinct facts even when they all support the same practical outcome.

Every material authority act and materially relevant deterministic result should be **durably preserved and inspectable whether the layers agree or disagree**. The final result must not erase the authority path that produced it.

## Authoritative fact sources

External sources establish the operational facts for which they are authoritative.

Examples include:

* market-data sources establishing observed market values;
* economic-data sources establishing published releases;
* brokerage and execution systems establishing Orders, fills, cancellations, protective Orders, exits, and execution state;
* portfolio or accounting systems establishing authoritative holdings or other Portfolio State where they own that responsibility.

Polaris may normalize, reconcile, contextualize, and reason over those facts. It must distinguish external facts from Polaris interpretation and must not rewrite authoritative Evidence merely because it conflicts with an Investment Recommendation, Action Intent, or preferred narrative.

The governing rule is:

> **Operational reality outranks expectation.**

A Human Investment Decision may reject a Polaris Investment Recommendation, but neither human judgment nor Polaris reasoning changes what an authoritative external source actually reported.

## Deterministic rule evaluation

Deterministic software should evaluate explicit rules, invariants, freshness requirements, readiness conditions, Policy, and Formal Constraints whenever those questions can be answered reliably without discretionary investment judgment.

Examples include:

* whether required Portfolio State satisfies the applicable Freshness Requirement;
* whether required Evidence is missing;
* whether an externally observed implementation matches a configured reconciliation tolerance;
* whether a Review Condition is due;
* whether required decision Evidence is complete enough for a governed boundary;
* whether an applicable platform Policy allows or denies an operation;
* whether an applicable Investment Mandate Formal Constraint is satisfied, violated, or indeterminate.

These results may have blocking consequences inside Polaris. If a current Investment Recommendation requires fresh Portfolio State and that state is too stale, Polaris may still have useful analytical observations, but it must not represent the unsupported recommendation as currently admissible for the consequential use.

The semantics remain power-specific:

```text
Policy
→ deterministic platform allow / deny result

Formal Constraint
→ deterministic Mandate satisfaction / violation / indeterminate result

Approval
→ attributable positive authority act by an authorized actor/process

Human Investment Decision
→ attributable human investment judgment
```

One must not be inferred from another.

## Formal Constraints, Policy, and analytical guidance are different

Older Polaris product prose used `hard constraint` and `soft constraint` as broad categories. The canonical domain model is more precise.

An **Investment Mandate Formal Constraint** is an authoritative machine-evaluable Mandate restriction. Only Formal Constraints produce deterministic Mandate satisfaction or violation results.

A **Policy** is a deterministic platform rule governing whether an operation, output, or boundary crossing may happen. Policy does not itself store human Approval or define the underlying investment judgment.

An **Investment Principle** or other analytical consideration may influence judgment without becoming a deterministic boundary. Tension with an Investment Principle is not automatically Mandate violation and does not automatically require a Mandate Exception.

A **Freshness Requirement** or other readiness condition may block a consequential use because the required Evidence is not fit for that use. That readiness failure is not automatically a Policy denial, Formal Constraint violation, Authority Denial, or Human Investment Decision.

AI may reason about the wisdom or effects of any of these conditions. It may not silently change their authoritative meaning or claim that a deterministic or authority requirement was satisfied when it was not.

## Polaris investment judgment

AI and other analytical machinery support broad **investment reasoning and judgment** without thereby receiving consequential investment authority.

Polaris may autonomously:

* interpret and synthesize Evidence;
* form and compare Investment Hypotheses;
* challenge active Investment Theses;
* search for Conflicting Evidence;
* assess Investment Uncertainty;
* compare Investment Scenarios and Decision Alternatives;
* identify relevant historical cases;
* form Portfolio Risk Assessments;
* infer Projected Portfolio Consequences;
* develop Proposed Actions;
* form Investment Views and Investment Recommendations;
* explain conclusions;
* form Decision Evaluations;
* identify analytical avenues that deserve further investigation;
* recognize material change and cause Attention to evaluate whether a Decision Need exists;
* proactively surface investment work that deserves human attention.

This initiative is intentionally broad because the attentive Polaris experience should not require a human to initiate every useful piece of analytical work.

The boundary is:

> **Polaris may form investment judgment; that judgment does not grant capital authority.**

A model cannot grant Approval, authorize a Mandate Exception, accept Governed Residual Risk, create execution authority, or lower the authority requirements that govern its own output merely by saying those things in model text.

## Investment Authority Regime and Human Investment Decision

The **Investment Authority Regime** determines which attributable actors or processes possess particular investment-authority powers for a Portfolio or Investment Decision.

Those powers are distinct. Depending on the applicable regime, separate authority may be required to:

* form the Human Investment Decision;
* grant Approval for a governed subject or use;
* issue an Authority Denial;
* authorize a Mandate Exception;
* accept specified Governed Residual Risk;
* exercise execution authority.

One actor may possess several powers, but possession or exercise of one must not be inferred from another.

A human may form a Human Investment Decision that:

* selects an economic disposition aligned with a Polaris Investment Recommendation;
* modifies it;
* rejects it;
* defers substantive resolution;
* chooses a different disposition that Polaris did not recommend.

Human Investment Decision remains separate from the Investment Recommendation even when the economic content is identical.

A human can also perform separate authority acts when authorized—for example, granting Approval or accepting Governed Residual Risk. Those acts must not be collapsed into the Human Investment Decision merely because the same person performs them at the same time.

Humans or organizations also remain the source of authoritative changes to Investment Mandates, Investment Authority Regimes, and other governing arrangements. Polaris may recommend or analyze such changes; it does not silently grant itself broader authority.

Human authority does **not** imply human initiation. Polaris may observe, investigate, establish analytical judgments, and cause Attention to evaluate possible Decision Needs proactively. The consequential authority boundary applies to the specific power being exercised, not to every upstream analytical transition.

## External execution authority

External operational systems retain authority for market-facing and other operational actions that Polaris does not own.

For trading activity this includes responsibilities such as:

* Order submission;
* routing;
* fills;
* protective and contingent Orders;
* cancellations and modifications;
* execution-time controls;
* resulting operational Portfolio State.

Polaris may preserve an Action Intent and observe authoritative external Evidence afterward, but the external system remains authoritative for the activity actually performed.

This preserves the product boundary:

```text
Polaris forms an Investment Recommendation
        ↓
Human forms a Human Investment Decision
        ↓
Action Intent may be established
        ↓
External system acts
        ↓
Polaris observes and reconciles
```

## Internal autonomy

Not every autonomous Polaris operation is a consequential investment authority act.

Polaris should be able to perform governed internal analytical and decision-state work without human Approval for every transition. Examples may include:

* refreshing Evidence;
* detecting staleness;
* recalculating analytical measures;
* forming a new Portfolio Risk Assessment;
* recognizing that an Investment Recommendation is no longer currently supportable;
* evaluating whether a Review Condition is due;
* initiating Decision Evaluation work;
* associating unambiguous external activity with an Action Intent;
* preserving new observations or analytical judgments;
* surfacing a material change for Attention.

The relevant distinction is not simply automatic versus manual. It is whether a specific transition exercises consequential authority, and if so which power is required under the applicable Investment Authority Regime.

## Ambiguity must remain explicit

Polaris may autonomously update internal state when authoritative Evidence and deterministic rules establish the meaning sufficiently for the intended use.

For example, if an Action Intent expects an externally observable sale of 150 shares and an authoritative execution source reports one uniquely matching sale in the relevant context, automatic reconciliation may be appropriate.

If several executions could plausibly satisfy the Action Intent, Polaris should not silently select one. It should preserve the ambiguity and request lightweight confirmation where the distinction materially affects meaning.

The governing rule is:

> **Uncertainty that materially changes meaning remains unresolved or is escalated rather than silently guessed away.**

This applies beyond execution reconciliation. Unknown, absent, disputed, or unresolved material facts must remain represented as such rather than being replaced by likely-looking values.

## Authority to withhold a recommendation is the wrong framing

Polaris is not required to always produce an Investment Recommendation, but withholding is not a special investment-authority power.

A recommendation may be withheld because deterministic readiness requirements are not satisfied—for example, required Evidence is stale or insufficient.

It may also be withheld because Polaris's analytical judgment cannot support a responsible preference—for example, material Investment Uncertainty or unresolved contradiction remains too significant.

A trustworthy system should be able to conclude:

> The available Evidence does not support a current Investment Recommendation.

The human may still inspect the Evidence and exercise their own judgment, subject to the applicable Investment Authority Regime and other authority conditions for consequential use.

## Portfolio Risk and authority remain distinct

Portfolio Risk is an economic domain concept, not an authority layer.

Portfolio Risk reasoning asks questions such as:

> What materially adverse possibilities exist, how have they changed, and what do they imply for this Portfolio and the alternatives under consideration?

Deterministic Policy or Formal Constraint evaluation asks different questions such as:

> Is this operation allowed under platform Policy?

or:

> Does this candidate Portfolio condition satisfy the applicable Mandate Formal Constraint?

Approval, Mandate Exception, and Residual-Risk Acceptance ask still different authority questions.

The resulting decision process may therefore combine:

```text
Portfolio Risk Assessment
        +
Projected Portfolio Consequences
        +
Policy / Formal Constraint results
        +
applicable authority acts
        ↓
Admissibility for the intended consequential use
```

No one element silently substitutes for the others.

## Preserve every material authority act and relevant deterministic result

Polaris must preserve and expose material authority acts across the decision chain **even when all relevant actors and rules agree**.

A fully aligned decision might include:

```text
Evidence readiness
Required Evidence accepted as sufficient and fresh enough.
        ↓
Formal Constraint / Policy results
Applicable deterministic conditions satisfied.
        ↓
Polaris judgment
Investment Recommendation formed.
        ↓
Approval
Granted by an authorized actor if required.
        ↓
Human Investment Decision
Human selects the economic disposition.
        ↓
Action Intent
External consequence established if applicable.
        ↓
External execution authority
Authoritative activity occurs.
        ↓
Observed reality
Activity reconciles and resulting Portfolio State is observed.
```

The historical record should not collapse that sequence into only:

> Exposure increased by 10%.

Agreement, Approval, satisfied Formal Constraints, accepted Governed Residual Risk, Human Investment Decision, successful reconciliation, and faithful implementation are distinct facts when they materially apply.

Likewise, a Policy that evaluated and allowed an operation is different from a Policy that was never evaluated or was bypassed. Silence is not proof that a required authority act or deterministic evaluation occurred.

A durable rule follows:

> **Absence of a recorded failure is not evidence that every required rule or authority act was satisfied; material positive results should be durably reconstructable.**

## Authority trace as product shorthand

Lowercase `authority trace` may remain product shorthand for an assembled representation of the material authority acts and deterministic results associated with an Investment Decision or governed subject.

It is not a separate canonical authority power and does not imply one storage entity.

Conceptually, an authority trace may make visible:

```text
Evidence / readiness
────────────────────
Sources
Freshness / sufficiency
Unresolved Evidence conflict

Deterministic rules
───────────────────
Policy results
Formal Constraint results
Readiness checks

Polaris judgment
────────────────
Investment View
Portfolio Risk Assessment
Investment Recommendation
Investment Uncertainty

Power-specific authority acts
─────────────────────────────
Approval / Authority Denial
Mandate Exception if applicable
Residual-Risk Acceptance if applicable

Human investment judgment
─────────────────────────
Human Investment Decision
Rationale where supplied

External authority
──────────────────
Orders / fills / other authoritative activity
Resulting Portfolio State
```

The exact presentation and persistence remain implementation questions.

## Authority history and the Evidence model

Authority history complements Polaris's Evidence model rather than replacing it.

The Evidence model answers questions such as:

* What Evidence existed?
* Where did it come from?
* When was it observed?
* What did it say?
* Was it current and attributable?
* Was it available to the material judgment at the relevant time?

Authority history answers a different set of questions:

* Which authority power applied to this subject and consequential use?
* Who possessed that power under the applicable Investment Authority Regime?
* What authority act was performed?
* Which Policy or Formal Constraint results were relevant?
* Was Approval required and, if so, granted or denied?
* Was a Mandate Exception required and authorized?
* Was Governed Residual Risk accepted where required?
* What Human Investment Decision was formed?
* What did the external execution system actually do?

Together they support trustworthy reconstruction without laundering one kind of fact into another.

## Always preserved, progressively exposed

"Always expose" does not mean every default screen should dump the complete authority history onto the user.

The Core Experience still requires concise-first, deep-on-demand interaction.

The product contract is therefore:

* **always preserve** materially required authority acts and rule results;
* **keep them inspectable** through an appropriate product surface;
* **surface material effects prominently** in the normal decision experience;
* **make fuller authority history available on demand**.

For example, if Polaris prefers a 20% increase but an applicable Formal Constraint makes that resulting Portfolio condition inadmissible without a Mandate Exception, that fact should be visible in the primary decision explanation. If all applicable conditions are satisfied, the positive results may be summarized while remaining inspectable.

The governing principle is:

> **Polaris must never reduce a multi-authority decision to only its terminal outcome.**

## Preserve agreement and disagreement

Disagreement remains important, but it is not the only authority information worth keeping.

Polaris should preserve, where material:

* applicable rule results;
* Approval;
* Authority Denial;
* Mandate Exception;
* Residual-Risk Acceptance;
* unresolved authority requirements;
* Human Investment Decision;
* Polaris Investment Recommendation;
* faithful implementation;
* implementation divergence;
* later Outcome.

This supports Decision Evaluation questions such as:

* Do decisions where Polaris judgment, deterministic boundaries, and human judgment align perform differently?
* Do particular Formal Constraints or Policies improve or degrade decision quality?
* When do human departures from Polaris recommendations help?
* When does implementation divergence explain Outcome differences?
* Are recommendations frequently inadmissible because a Policy or constraint is poorly calibrated?
* Do particular Evidence sufficiency judgments correlate with later error?

Authority history is therefore not merely audit metadata. It may become Evidence in later Decision Evaluation while preserving its original semantic role.

## Separation of powers as a trust mechanism

No single component should own external facts, deterministic rules, Polaris investment judgment, human consequential authority, and market-facing execution simultaneously.

The desired structure is:

```text
FACTS
Authoritative external sources

RULES
Policy / Formal Constraints / readiness

POLARIS JUDGMENT
Investment reasoning and recommendation

HUMAN AUTHORITY
Power-specific acts under the Investment Authority Regime

ACTION
External operational system
```

The point is not that AI becomes perfectly trustworthy.

The stronger trust property is:

> **Polaris is structured so that AI does not have to be trusted with every kind of authority.**

That preserves the product doctrine: use AI where reasoning and synthesis add value while making the surrounding decision system more deterministic, inspectable, attributable, and accountable than the AI itself.

## Consequences

The Authority Model implies:

* capability must not be confused with authority;
* authoritative sources retain factual authority within their responsibility domains;
* Policy, Formal Constraints, freshness/readiness requirements, Approval, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, and external execution authority remain semantically distinct;
* deterministic mechanisms should evaluate explicit rules and invariants without being mislabeled as human or investment authority;
* Polaris should have broad analytical initiative without capital-action authority;
* the Investment Authority Regime determines who possesses each consequential authority power;
* Human Investment Decision does not automatically imply Approval, Mandate Exception, or Residual-Risk Acceptance;
* external operational systems retain market-facing execution authority;
* human authority does not require human initiation of analytical work;
* Polaris may analyze or challenge a governing rule intellectually but cannot silently change its authoritative meaning or bypass it;
* Polaris may autonomously perform governed internal analytical and decision-state operations that do not exercise a separately required consequential authority power;
* ambiguity that materially changes meaning should remain explicit instead of being silently resolved by guesswork;
* Polaris may qualify or withhold an Investment Recommendation when Evidence or analytical judgment cannot support it;
* Portfolio Risk is an economic concept and must not be collapsed into deterministic Policy or authority;
* material positive authority acts and rule results must be preserved when required, not inferred from silence;
* terminal Outcomes must not erase the authority path that produced them;
* authority history should complement Evidence provenance while preserving each fact's semantic role;
* the user experience may progressively disclose authority detail without deleting it;
* authority, rule, implementation, and Outcome history should remain available for later Decision Evaluation and learning.

## Relationship to later Product Definition work

This Authority Model constrains the other Product Definition records:

* **Scope Boundaries** should preserve which external responsibilities Polaris observes, integrates with, or explicitly does not own.
* **Differentiation** should treat durable Evidence plus power-specific authority reconstruction as part of Polaris's trust proposition.
* **Core Capabilities** should enforce, preserve, inspect, and evaluate the authority model without prematurely prescribing implementation.
* **Product Principles** should preserve separation of powers, positive authority reconstruction, progressive exposure, ambiguity preservation, and the refusal to confuse AI capability with authority.
