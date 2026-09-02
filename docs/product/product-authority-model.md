# Polaris Authority Model

**Status:** In progress  
**Purpose:** Preserve the product reasoning for how authority is separated, exercised, recorded, and exposed across the Polaris decision lifecycle.

This document refines the Product Definition recorded in [`product-definition.md`](./product-definition.md). It defines a product-level separation of powers rather than an implementation architecture or permission schema.

## Decision

Polaris uses a **separation-of-powers authority model**.

Different parts of the decision lifecycle have different kinds of authority:

```text
EVIDENCE AUTHORITY
Authoritative evidence sources
"What is true?"
        ↓
DETERMINISTIC AUTHORITY
Rules, invariants, freshness requirements, configured constraints
"What is admissible and trustworthy?"
        ↓
ANALYTICAL AUTHORITY
AI and analytical machinery
"What does this mean and what should we consider?"
        ↓
DECISION AUTHORITY
Human
"What will we do?"
        ↓
ACTION AUTHORITY
External operational systems
"Carry it out."
        ↓
EVIDENCE RETURNS
Observed execution and resulting state
"What actually happened?"
```

Capability does not imply authority. Polaris may be capable of observing, researching, reasoning, challenging, recommending, reconciling, and evaluating without acquiring authority to move capital.

Every material authority decision across this chain must be **durably preserved and inspectable whether the authority layers agree or disagree**. The final result must not erase the authority path that produced it.

## Evidence authority

Authoritative evidence sources establish the operational facts for which they are responsible.

Examples include:

* market-data sources establishing observed market values;
* economic-data sources establishing published releases;
* brokerage and execution systems establishing orders, fills, cancellations, stops, exits, and execution state;
* portfolio or accounting systems establishing authoritative holdings or other portfolio state where they own that responsibility.

Polaris may normalize, reconcile, contextualize, and reason over those facts. It must distinguish source evidence from interpretation and must not rewrite authoritative evidence merely because it conflicts with a recommendation, expected action, or preferred narrative.

The governing rule is:

> **Operational reality outranks expectation.**

A human may reject a Polaris recommendation, but neither the human nor Polaris should make the historical record claim that an authoritative external event occurred differently from what the responsible source reports.

## Deterministic authority

Deterministic software should govern explicit rules, invariants, trust conditions, and configured constraints whenever those questions can be answered reliably without discretionary model judgment.

Examples include:

* whether required portfolio state is fresh enough;
* whether a hard risk threshold is exceeded;
* whether required evidence is missing;
* whether an execution matches a configured tolerance;
* whether a recommendation has become stale or superseded;
* whether a configured review condition has been reached;
* whether required decision evidence is complete enough to support a governed transition.

Deterministic authority may have blocking power inside Polaris. If a decision contract requires current portfolio state and the available state is too stale, the analytical layer may still have useful observations, but Polaris may be prohibited from presenting them as a current actionable recommendation.

Human-defined policy can therefore become deterministic authority through explicit configuration:

```text
Human governance decision
        ↓
Explicit policy / constraint
        ↓
Deterministic evaluation
        ↓
Automatic enforcement
```

The software is enforcing the policy; the governing authority behind the policy remains human.

## Hard and soft constraints

Polaris should distinguish hard constraints from soft decision guidance.

A **hard constraint** is an enforceable condition that cannot be reasoned away by the analytical layer. Examples may include a required freshness threshold, a configured maximum exposure, or a requirement not to treat unverified execution as confirmed.

A **soft constraint** influences reasoning without absolutely prohibiting an outcome. Examples may include preferring lower concentration, exercising caution before a known catalyst, or treating high model disagreement as a reason for conservatism.

AI may weigh soft constraints. It must not silently reinterpret hard constraints out of existence.

If the analytical layer believes a hard policy is inappropriate, it may surface that concern for human governance review. It may not change the policy and then approve its own preferred action.

## Analytical authority

AI and other analytical machinery should have broad **epistemic and analytical authority**.

Polaris may autonomously:

* interpret and synthesize evidence;
* identify competing explanations;
* challenge active theses;
* search for disconfirming evidence;
* assess uncertainty;
* compare scenarios and alternatives;
* identify relevant historical cases;
* infer portfolio implications;
* reason about risk;
* develop candidate actions;
* recommend among admissible alternatives;
* explain conclusions;
* evaluate previous reasoning;
* identify which analytical avenues deserve further investigation;
* recognize material change and initiate reassessment;
* proactively surface a decision that deserves human attention.

This authority is intentionally broad because the attentive Polaris experience should not require a human to initiate every useful piece of analytical work.

The boundary is:

> **AI authority is analytical, not capital authority.**

Polaris may determine what it believes, why it believes it, what could make the view wrong, and what it recommends. It may not convert that analytical conclusion into an external capital action on the user's behalf.

## Human decision and governance authority

Humans retain authority over consequential investment judgment.

A user may:

* accept a Polaris recommendation;
* modify it;
* reject it;
* defer it;
* take a different action that Polaris did not recommend.

The decision record must preserve the human decision separately from the Polaris recommendation rather than rewriting history to make them appear identical.

Humans also retain authority over material governance choices such as the investment mandate, risk appetite, hard risk limits, permitted universe, consequential operating policy, and the authority boundaries themselves.

Polaris may recommend changes to those policies. It should not silently grant itself broader authority or weaken the constraints governing its own reasoning.

Human authority does **not** imply human initiation. Polaris may observe, investigate, reassess, recommend, and escalate proactively. The human boundary applies when consequential investment judgment or a material governance change is required.

## Action authority

External operational systems retain authority for market-facing and other operational actions that Polaris does not own.

For trading activity this includes responsibilities such as:

* order submission;
* routing;
* fills;
* stops and targets;
* cancellations and modifications;
* execution-time controls;
* resulting operational portfolio state.

Polaris may preserve an action intent and observe the external evidence afterward, but the external system remains authoritative for the action actually performed.

This preserves the product boundary:

```text
Polaris recommends
        ↓
Human decides
        ↓
External system acts
        ↓
Polaris observes and reconciles
```

## Internal autonomy

Not every autonomous action is a consequential investment action.

Polaris should be able to perform governed internal analytical and decision-state work without human approval for every transition. Examples may include:

* refreshing evidence;
* detecting staleness;
* recalculating risk;
* marking a thesis or recommendation as requiring reassessment;
* scheduling or initiating evaluation;
* associating unambiguous execution evidence with a decision;
* updating internal recommendation or observation state;
* surfacing a material change for attention.

The relevant distinction is not simply automatic versus manual. It is:

```text
Internal informational / analytical action
                versus
Consequential external investment action
```

Polaris should be highly autonomous in the first category and constrained by the human/external-system boundary in the second.

## Confidence-bounded internal decisions

Polaris may autonomously update internal decision state when authoritative evidence and deterministic rules make the meaning sufficiently unambiguous.

For example, if an action intent expects a sale of 150 shares and the authoritative execution source reports a matching sale of 150 shares in the relevant context, automatic reconciliation may be appropriate.

If several executions could plausibly satisfy the intent, Polaris should not silently select one. It should preserve the ambiguity and request lightweight confirmation where the distinction materially affects meaning.

The governing rule is:

> **Uncertainty that materially changes meaning escalates rather than being silently guessed away.**

This applies beyond execution reconciliation. The product should prefer explicit unresolved state over false certainty.

## Authority to withhold a recommendation

Polaris is not required to always produce an actionable recommendation.

A recommendation may be withheld for deterministic reasons, such as stale required evidence or violated hard constraints.

It may also be withheld for analytical reasons, such as unresolved contradiction or uncertainty too high to support a responsible preference among actions.

A trustworthy system should be able to conclude:

> The evidence is insufficient for a current recommendation.

The human may still inspect the evidence and exercise their own judgment.

## Risk has analytical and deterministic authority

Risk participates in more than one authority layer.

Analytical risk reasoning asks questions such as:

> What risks exist, how have they changed, and what do they imply for this portfolio?

Deterministic risk authority asks questions such as:

> Does this candidate action violate an explicit configured constraint?

The two combine before an admissible recommendation is presented:

```text
Analytical risk reasoning
        +
Deterministic risk policy
        ↓
Admissible risk-aware recommendation
```

The analytical layer may challenge the wisdom of a hard constraint, but it may not silently override it. A material change to that constraint belongs to human governance authority.

## Preserve every material authority decision

Polaris must preserve and expose the material authority decisions made across the decision chain **even when all layers agree**.

A fully aligned decision might include:

```text
Evidence authority
Market and portfolio state accepted as current and sufficient.
        ↓
Deterministic authority
Required policies evaluated; action permitted.
        ↓
Analytical authority
Polaris recommends increasing exposure by 10%.
        ↓
Human authority
Recommendation accepted.
        ↓
Action authority
External system executes the intended action.
        ↓
Observed reality
Execution reconciles with the decision.
```

The historical record should not collapse that sequence into only:

> Exposure increased by 10%.

Agreement, approval, satisfied constraints, acceptance, successful reconciliation, and faithful execution are themselves meaningful decision evidence.

Likewise, a policy that evaluated and permitted an action is different from a policy that was never evaluated or was bypassed. Silence is not proof that authority was correctly exercised.

A durable rule follows:

> **Absence of an authority failure is not evidence that authority was exercised correctly; material authority decisions should be positively recorded.**

## Authority trace as a product concept

The working product concept is an **authority trace**: the durable provenance of which authority evaluated each material transition, what decision that authority made, and how that decision affected the lifecycle.

Conceptually, an authority trace may make visible:

```text
Evidence authority
──────────────────
Facts accepted
Sources
Freshness / sufficiency
Unresolved evidence conflict

Deterministic authority
───────────────────────
Policies evaluated
Constraints applied
Checks passed / failed
Candidate actions permitted / rejected

Analytical authority
────────────────────
Interpretation
Alternatives
Challenge
Recommendation
Uncertainty

Human authority
───────────────
Accepted / modified / rejected / deferred
Human rationale where supplied

Action authority
────────────────
Observed external action
Execution differences from intent

Observed reality
────────────────
Resulting portfolio state
Outcome
```

`Authority trace` is product language at this stage, not a commitment to a particular database entity, event schema, audit table, or UI component.

## Authority trace and the evidence model

The authority trace complements Polaris's evidence model rather than replacing it.

The evidence model answers questions such as:

* What evidence existed?
* Where did it come from?
* When was it observed?
* What did it say?
* Was it current and attributable?

The authority trace answers a different set of questions:

* Which authority evaluated that evidence or decision state?
* What did that authority decide?
* Which rules or constraints were applied?
* Was a candidate action permitted, constrained, rejected, or left unresolved?
* What did the analytical layer recommend?
* What did the human decide?
* What did the external action system actually do?
* How did each authority decision affect the eventual outcome?

Together they provide two complementary forms of provenance:

```text
Evidence provenance
What was known and where it came from

        +

Authority provenance
Who or what evaluated it and what authority decision followed

        ↓

Trustworthy decision provenance
```

This is intentionally a conceptual alignment. The Product Definition does not prescribe how the current evidence implementation must represent authority decisions.

## Always preserved, progressively exposed

"Always expose" does not mean every default screen should dump the complete authority trace onto the user.

The Core Experience still requires concise-first, deep-on-demand interaction.

The authority contract is therefore:

* **always preserved** for material authority decisions;
* **always inspectable** through an appropriate product surface;
* **material effects surfaced prominently** in the normal decision experience;
* **full authority trace available on demand**.

For example, if analytical reasoning recommends a 20% increase but a hard concentration policy limits the admissible recommendation to 10%, that constraint should be visible in the primary decision explanation. If all policies were evaluated and satisfied without changing the recommendation, the affirmative policy decisions may be summarized by default while remaining inspectable in full.

The governing principle is:

> **Polaris must never reduce a multi-authority decision to only its terminal outcome.**

## Preserve agreement and disagreement

Disagreement remains important, but it is not the only authority information worth keeping.

Polaris should preserve:

* agreement;
* disagreement;
* approval;
* rejection;
* constraint;
* override;
* abstention or unresolved state;
* recommendation withholding;
* human modification;
* faithful execution;
* execution divergence;
* later outcome.

This supports evaluation of questions such as:

* Do decisions where analytical, policy, and human authority align perform differently?
* Do particular hard constraints improve or degrade outcomes?
* When do human overrides help?
* When does execution divergence explain outcome differences?
* Are recommendations frequently blocked because a policy is poorly calibrated?
* Does a particular evidence sufficiency decision correlate with later error?

Authority history is therefore not merely audit metadata. It is learnable decision information.

## Separation of powers as a trust mechanism

No single component should own facts, rules, interpretation, consequential decision, and execution simultaneously.

The desired structure is:

```text
FACTS
Authoritative evidence sources

RULES
Deterministic governance

REASONING
AI and analytical machinery

DECISION
Human

ACTION
External operational system
```

The point is not that AI becomes perfectly trustworthy.

The stronger trust property is:

> **Polaris is structured so that AI does not have to be trusted with everything.**

That preserves the earlier product doctrine: use AI where reasoning and synthesis add value while making the surrounding decision system more deterministic, inspectable, attributable, and accountable than the AI itself.

## Consequences

The Authority Model implies:

* capability must not be confused with authority;
* authoritative sources own operational facts within their responsibility domains;
* deterministic mechanisms should enforce explicit rules, invariants, freshness requirements, and hard constraints;
* AI should have broad analytical initiative without capital-action authority;
* humans retain consequential investment and material governance authority;
* external operational systems retain market-facing action authority;
* human authority does not require human initiation of the analytical process;
* AI may challenge a hard policy intellectually but cannot silently change or bypass the constraint governing itself;
* Polaris may autonomously perform governed internal analytical and decision-state actions;
* uncertainty that materially changes meaning should escalate instead of being silently resolved by guesswork;
* Polaris may qualify, withhold, or invalidate a recommendation when the decision contract cannot be satisfied;
* risk combines analytical reasoning with deterministic policy authority;
* every material authority decision must be positively preserved whether it agrees or conflicts with adjacent layers;
* approvals and satisfied constraints are authority evidence, not merely the absence of failure;
* terminal outcomes must not erase the authority path that produced them;
* authority provenance should complement evidence provenance;
* the full authority path should remain inspectable while the user experience remains concise-first and progressively disclosed;
* agreement, disagreement, policy effects, human overrides, execution fidelity, and outcomes should all remain available for later evaluation and learning.

## Relationship to later Product Definition work

This Authority Model establishes constraints for the remaining Product Definition work:

* **Scope Boundaries** should formalize which external responsibilities Polaris observes, integrates with, or explicitly does not own.
* **Differentiation** should evaluate whether durable evidence plus durable authority provenance is part of Polaris's distinctive value.
* **Core Capabilities** should include the minimum product capabilities necessary to enforce, preserve, inspect, and evaluate the authority model without prematurely prescribing implementation.
* **Product Principles** should capture separation of powers, positive authority provenance, progressive exposure, uncertainty escalation, and the refusal to confuse AI capability with authority.
