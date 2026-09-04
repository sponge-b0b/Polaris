# Polaris Execution Continuity

**Status:** In progress  
**Purpose:** Preserve the product reasoning for how Polaris maintains Durable Decision Memory when a Human Investment Decision establishes an external implementation consequence that is carried out by another system.

This document refines the Product Identity and ecosystem position recorded in [`product-definition.md`](./product-definition.md) and [`product-ecosystem.md`](./product-ecosystem.md). It does not make Polaris an execution system. It defines how authoritative external activity returns to the Investment Decision lifecycle so later Attention, Decision Evaluation, and learning are grounded in what actually happened.

## Decision

Polaris does not own execution, but it **does own continuity of the Investment Decision lifecycle across external execution**.

When a Human Investment Decision establishes an externally observable implementation consequence, Polaris should preserve that consequence as one or more Action Intents, observe authoritative external evidence of what actually occurred, reconcile that evidence to the applicable Action Intents where supportable, and preserve the resulting Portfolio State, Outcome, Decision Evaluation, and learning relationships through time.

The governing relationship is:

```text
Investment Recommendation
        ↓
Human Investment Decision
        ↓
Action Intent where an external consequence exists
        ↓
External execution system
        ↓
Authoritative external activity / execution Evidence
        ↓
Resulting Portfolio State
        ↓
Outcome
        ↓
Decision Evaluation
        ↓
Lessons
```

External trading, brokerage, portfolio, and accounting systems remain authoritative for the operational facts they own. Polaris should not require the user to manually recreate those facts when an authoritative source can provide them.

## Why this matters

Durable Decision Memory is incomplete whenever a Human Investment Decision is intended to produce an external Portfolio consequence but the later external activity is not connected back to that decision.

Without execution continuity, the lifecycle becomes:

```text
Investment Recommendation
     ↓
Human Investment Decision
     ↓
    ???
     ↓
Outcome / Decision Evaluation
```

That gap prevents Polaris from knowing whether the intended Portfolio consequence was implemented, how it was implemented, whether external activity differed materially from the Action Intent, whether intended external controls were established or changed, and which part of the overall process materially contributed to the observed Outcome.

The closed-loop product requires:

```text
Investment Recommendation
     ↓
Human Investment Decision
     ↓
Action Intent where applicable
     ↓
observed external activity
     ↓
resulting Portfolio State
     ↓
Outcome
     ↓
Decision Evaluation
     ↓
Lessons
```

This is a product-level requirement even though its implementation will eventually depend on integrations and operational data sources.

## Action Intent as the continuity concept

An **Action Intent** is the attributable post-human-decision continuity state describing an externally observable implementation consequence or control established by a Human Investment Decision so Polaris can reconcile later authoritative external activity and Portfolio State without acquiring execution authority.

A Human Investment Decision may establish zero, one, or multiple Action Intents. Action Intent cardinality follows coherent intended external consequence rather than Financial Instrument count, Proposed Action count, Order count, fill count, or execution mechanics.

Examples may include:

* establish a Position or Exposure through an external action;
* reduce an existing Position or Exposure by an intended amount;
* close an existing Position;
* establish a coherent hedge consequence;
* rebalance several holdings when those changes jointly express one intended Portfolio consequence;
* establish or maintain an externally implemented protection condition where that control is genuinely part of the Human Investment Decision.

Conceptually, an Action Intent may express enough investment meaning for later reconciliation, such as:

```text
Human Investment Decision: reduce Portfolio equity risk
Action Intent: reduce SPY Exposure by approximately 25%
Expected consequence: lower Portfolio equity Exposure
Relevant implementation meaning: reduction should be externally observable
```

An Action Intent is not an Order, fill, routing instruction, or authorization for Polaris to execute. It may be specific enough for reconciliation without becoming the externally authoritative execution fact.

Deferral and deliberate hold/no-action do not require synthetic Action Intents merely to duplicate the Human Investment Decision. The same Human Investment Decision may still establish a separate Action Intent if it also establishes an externally observable consequence or control.

A Proposed Action also remains distinct. A Proposed Action is a candidate implementation considered during the Investment Decision; Action Intent exists only after attributable human judgment establishes an intended external consequence.

## Execution evidence is observed, not authored

Polaris should treat authoritative external systems as authoritative for operational facts such as:

* Orders;
* partial fills;
* completed fills;
* execution prices;
* quantities;
* cancellations;
* Order modifications;
* protective Orders;
* targets or contingent Orders;
* resulting Positions;
* later Position changes;
* exits;
* realized results where available.

This creates an asymmetric relationship:

```text
External execution systems → Polaris
Orders / fills / Positions / changes / Outcomes
```

without implying:

```text
Polaris → External execution systems
place / modify / cancel / liquidate
```

under the current product identity.

Read or observation integration is not execution authority.

## Automatic reconciliation is the preferred experience

The user should not be responsible for copying trade details from a broker into Polaris merely to keep Durable Decision Memory complete.

The preferred experience is:

```text
Polaris forms an Investment Recommendation
        ↓
Human forms a Human Investment Decision
        ↓
Action Intent is established when applicable
        ↓
Human/external process acts through the normal execution system
        ↓
Polaris observes authoritative external Evidence
        ↓
Polaris associates it with the Action Intent where supportable
        ↓
Durable Decision Memory continues
```

A representative product interaction might be:

> I observed the SPY reduction associated with this morning's Action Intent. The Position was reduced by 24.7% across three fills. I preserved the execution Evidence and updated the Portfolio State used for subsequent decision work.

The user should experience this as continuity, not bookkeeping.

## Reconciliation confidence and ambiguity

Automatic reconciliation must not become silent invention.

A useful product hierarchy is:

```text
Sufficiently supported association
→ reconcile automatically

Plausible but materially ambiguous association
→ preserve ambiguity and ask for lightweight confirmation

No credible association
→ preserve as unassociated external activity
```

If several external actions could plausibly satisfy the same Action Intent, Polaris should ask a narrow question such as:

> I observed two SPY reductions that could correspond to this Action Intent. Was the 10:14 sale the activity associated with it?

The desired friction is **confirmation**, not duplicate data entry.

Polaris should never attach external activity to an Action Intent merely because doing so would make the historical record look complete.

## External activity can originate outside Polaris

The Portfolio is reality; Polaris's decision history is an interpretation of and participation in that reality.

A user may make trades or Portfolio changes that did not originate from a Polaris Investment Recommendation, Human Investment Decision recorded in Polaris, or Action Intent. Polaris should observe those changes without fabricating an originating Polaris decision.

A mature product may say:

> I observed a new Position without a corresponding Polaris Action Intent or attributable Investment Decision relationship.

The user may then provide context if useful, or the activity may remain explicitly external.

External activity does not retroactively create an Investment Recommendation, Proposed Action, Human Investment Decision, or Action Intent merely because its economic result resembles one.

## One Human Investment Decision can establish several Action Intents

A Human Investment Decision may establish zero, one, or multiple externally observable consequences.

For example:

```text
Human Investment Decision: reduce Portfolio Risk

Action Intent 1: reduce SPY Exposure
Action Intent 2: close a high-beta Position
Action Intent 3: raise cash Allocation through the resulting Portfolio changes
```

Whether those consequences should be represented as one composite Action Intent or several follows coherent intended consequence rather than the number of Orders or Financial Instruments mechanically.

Each Action Intent may later be associated with zero, one, or multiple external activities:

```text
Action Intent
   ↓
external activity observed
   ↓
partial implementation
   ↓
further activity / modification
   ↓
implemented / not implemented / unresolved association
```

These labels are conceptual rather than a prescribed state machine.

The important distinction is that later Decision Evaluation should know whether the intended consequence was implemented and, if only partially, which assumptions about resulting Portfolio State were or were not realized.

## Stops, targets, and continuing external controls

Execution continuity may extend beyond an initial fill when the Human Investment Decision establishes an intended externally maintained control.

Suppose a human decides to implement a Polaris trade setup that included a suggested protective condition. Only the human judgment that establishes the external control creates Action Intent semantics; a suggested stop or target in an Investment Recommendation is not automatically an Action Intent or an Order.

When such an Action Intent exists, an external execution system may later report:

```text
entry activity
   ↓
Position established
   ↓
protective Order established
   ↓
contingent Order modified
   ↓
Position closed
```

Material external facts should remain associated with the applicable Action Intent and Investment Decision when that causal relationship is supported.

If the user manually closes the Position before a contingent Order executes, that should be preserved as observed reality rather than forced into the previously expected implementation path.

## Recommendation, human judgment, intent, external activity, and Outcome are distinct facts

Polaris should preserve the conceptual distinction:

```text
Investment Recommendation
        ≠
Human Investment Decision
        ≠
Action Intent
        ≠
Authoritative external activity
        ≠
Outcome
```

This distinction is essential for trustworthy Decision Evaluation.

For example:

```text
Investment Recommendation:
Enter around 641

Human Investment Decision:
Accept the economic disposition

Action Intent:
Establish the Position

Authoritative external activity:
Position established at 656

Outcome:
Position later closed at a loss
```

Calling that simply "a losing Polaris recommendation" would erase material information about how the recommendation, human judgment, intended implementation, actual activity, and Outcome differed.

The inverse is also possible: a poor Investment Recommendation may coincide with a favorable Outcome because of later human judgment, implementation differences, or chance.

Outcome alone therefore cannot answer whether the Investment Recommendation or decision process was sound.

## Separate dimensions of later evaluation

Execution continuity allows Polaris to form more faithful Decision Evaluations across dimensions such as:

```text
Investment Recommendation quality
Human Investment Decision
Implementation fidelity
Trade Implementation Risk and execution quality
Portfolio Risk management
Observed Outcome
```

The system can ask better questions:

* Was the original Investment Thesis reasonable given the Evidence available to the relevant judgment?
* How did the Human Investment Decision relate to the Investment Recommendation?
* Was an Action Intent established?
* Was the intended Portfolio consequence actually implemented?
* Did authoritative external activity materially differ from the Action Intent?
* Were intended externally maintained controls actually established?
* Were they later modified?
* Did implementation divergence materially affect Outcome?
* Did an Invalidation Condition occur, did another event intervene, or did an adverse Outcome occur despite reasonable reasoning?

This makes the learning loop about decision and implementation quality rather than simple profit/loss attribution.

## Portfolio State is the ultimate operational reality

Action Intent describes an intended external consequence. Authoritative Portfolio State tells Polaris what actually exists.

If an Action Intent called for a 25% reduction but the authoritative source shows only a 10% reduction, Polaris should not assume completion merely because the human previously formed the corresponding Human Investment Decision.

It should preserve that the intended consequence is only partially reflected in observed reality and that current Portfolio State still differs from the state expected by the Action Intent.

That divergence may itself cause Attention:

> The risk-reduction Action Intent appears only partially implemented. Current Exposure remains above the level assumed by the decision.

Attention then determines whether the same unresolved Investment Decision should continue or, if the earlier investment judgment was already substantively resolved, whether a renewed Decision Need warrants a new causally linked Investment Decision. Execution divergence does not reopen and rewrite a resolved Investment Decision.

This is consistent with the attentive Core Experience: Polaris notices when intended consequence and operational reality diverge without taking control of the execution system.

## External system failures remain external responsibilities

Polaris may understand that an external control was intended and later observe whether it existed or triggered.

That does not make Polaris responsible for enforcing the control.

Conceptually:

```text
Human Investment Decision / Action Intent:
Establish an external protective control.

Execution system:
Owns Order acceptance and execution.

Polaris:
Observes whether the intended control existed,
what happened to it, and how the result affected the decision lifecycle.
```

If an execution system fails to carry out an operational instruction correctly, that remains an execution-system failure. Polaris's responsibility is to preserve the Evidence accurately and incorporate the result into subsequent Portfolio reasoning and Decision Evaluation.

## The closed ecosystem loop

Execution continuity completes the ecosystem model:

```text
             ┌────────── external world ──────────┐
             │                                     │
             ↓                                     │
           SENSE                                   │
             ↓                                     │
          POLARIS                                  │
      reason / recommend                           │
             ↓                                     │
           HUMAN                                   │
            decide                                 │
             ↓                                     │
      ACTION INTENT                                │
        if applicable                              │
             ↓                                     │
      EXECUTION SYSTEM                             │
             ↓                                     │
      EXTERNAL ACTIVITY                            │
             ↓                                     │
      OBSERVED RESULT ─────────────────────────────┘
             ↓
          POLARIS
        reconcile
        attend
        evaluate
        learn
```

Polaris is therefore not merely a recommendation generator. It is a closed-loop portfolio decision system whose lifecycle crosses external operational systems without taking over their authority.

## Product contract

The durable contract is:

> **Polaris does not own execution, but it owns continuity of the Investment Decision lifecycle across execution.**

And:

> **External operational systems remain authoritative for actions and resulting Portfolio State. When a Human Investment Decision establishes an Action Intent, Polaris should observe and reconcile authoritative external Evidence against that intent wherever supportable, requiring human input primarily for material ambiguity or context that cannot be established otherwise.**

The product should prefer system-to-system continuity over user-maintained duplicate records whenever an authoritative source can supply the relevant Evidence.

## Consequences

This decision implies:

* a Human Investment Decision may establish zero, one, or multiple Action Intents;
* Action Intent represents an externally observable consequence or control established by human judgment, not a generic synonym for Proposed Action, Order, or execution mechanics;
* Deferral and deliberate hold/no-action do not require synthetic Action Intents;
* authoritative external execution and Portfolio systems should be observed rather than duplicated as factual authority;
* Polaris should automatically reconcile external activity to Action Intents when the association is sufficiently supported;
* materially ambiguous associations should trigger explicit unresolved state or lightweight confirmation rather than silent guessing or full manual data entry;
* externally initiated trades and Portfolio changes must remain identifiable as such and must not retroactively manufacture Polaris decision history;
* one Action Intent may correspond to zero, one, or multiple external activities, and one Human Investment Decision may establish several Action Intents;
* partial fills, later modifications, protective Orders, exits, and other material execution Evidence may remain associated with the Investment Decision when the relationship is supported;
* Investment Recommendation, Human Investment Decision, Action Intent, authoritative external activity, and Outcome must remain separately identifiable;
* authoritative Portfolio State determines what actually exists even when it differs from the Action Intent;
* implementation divergence may cause Attention but does not reopen a substantively resolved Investment Decision;
* Decision Evaluation should be able to distinguish Investment Recommendation quality, Human Investment Decision, implementation fidelity, Portfolio Risk reasoning, Trade Implementation Risk, and Outcome;
* execution-system failures do not become Polaris execution failures merely because Polaris observed them;
* the preferred user experience is automatic observation and reconciliation, with manual input reserved primarily for material ambiguity or missing context;
* the Authority Model must preserve Polaris reconciliation responsibility without confusing it with authority to act on capital;
* Scope Boundaries should preserve inbound execution Evidence as product-relevant integration without making outbound execution control part of Polaris's defining responsibility.
