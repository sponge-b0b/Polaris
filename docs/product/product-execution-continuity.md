# Polaris Execution Continuity

**Status:** In progress  
**Purpose:** Preserve the product reasoning for how Polaris keeps a decision record causally complete when the resulting portfolio action is executed by another system.

This document refines the Product Identity and ecosystem position recorded in [`product-definition.md`](./product-definition.md) and [`product-ecosystem.md`](./product-ecosystem.md). It does not make Polaris an execution system. It defines how execution evidence returns to the decision lifecycle so later monitoring, evaluation, and learning are grounded in what actually happened.

## Decision

Polaris does not own execution, but it **does own continuity of the decision lifecycle across execution**.

When a human decision implies an external portfolio action, Polaris should preserve the intended action, observe authoritative external evidence of what actually occurred, reconcile that evidence into the originating decision record, and continue tracking the resulting position or action through completion, exit, outcome, evaluation, and learning.

The governing relationship is:

```text
Polaris recommendation
        ↓
Human decision
        ↓
Action / execution intent
        ↓
External execution system
        ↓
Observed execution evidence
        ↓
Resulting portfolio state
        ↓
Position / action lifecycle
        ↓
Outcome
        ↓
Evaluation
        ↓
Learning
```

External trading, brokerage, portfolio, and accounting systems remain authoritative for the operational facts they own. Polaris should not require the user to manually recreate those facts when an authoritative source can provide them.

## Why this matters

A decision record that stops at the human decision is incomplete whenever the decision is meant to produce a portfolio action.

Without execution continuity, the lifecycle becomes:

```text
recommendation
     ↓
human decision
     ↓
    ???
     ↓
outcome evaluation
```

That gap prevents Polaris from knowing whether the recommendation was actually followed, how it was implemented, whether execution differed materially from the intent, whether risk controls were established or changed, how the position was eventually closed, and which part of the overall process deserves credit or blame.

The closed-loop product requires:

```text
recommendation
     ↓
human decision
     ↓
observed action
     ↓
observed result
     ↓
portfolio consequence
     ↓
outcome
     ↓
evaluation
     ↓
learning
```

This is a product-level requirement even though its implementation will eventually depend on integrations and operational data sources.

## Action or execution intent as a product concept

When the human decides to act, Polaris should know what external change it expects to observe.

The working product concept is an **action intent** or **execution intent**: a durable statement of the portfolio action implied by the human decision. It is not an exchange order and does not grant Polaris authority to transmit or execute anything.

Examples include:

* enter a position;
* reduce a position by an approximate amount;
* add to an existing position;
* close a position;
* establish or maintain a protective stop;
* establish a target or exit condition;
* hedge an exposure;
* rebalance several holdings;
* defer action until a condition is met;
* intentionally take no action.

Conceptually, the intent may express enough investment meaning for later reconciliation, such as:

```text
Decision: reduce portfolio equity risk
Action: reduce SPY exposure by approximately 25%
Expected resulting exposure: lower than current state
Relevant risk condition: concentration / volatility
Review condition: reassess after execution
```

The exact representation is intentionally unresolved. The durable point is that Polaris should know the expected portfolio consequence before attempting to associate later external events with the decision.

## Execution evidence is observed, not authored

Polaris should treat authoritative external systems as the source of truth for operational facts such as:

* orders;
* partial fills;
* completed fills;
* execution prices;
* quantities;
* cancellations;
* order modifications;
* protective stops;
* targets or contingent orders;
* resulting positions;
* later position changes;
* exits;
* realized results where available.

This creates an asymmetric relationship:

```text
External execution systems → Polaris
orders / fills / positions / changes / outcomes
```

without implying:

```text
Polaris → External execution systems
place / modify / cancel / liquidate
```

under the current product identity.

Read or observation integration is not execution authority.

## Automatic reconciliation is the preferred experience

The user should not be responsible for copying trade details from a broker into Polaris merely to keep the decision record complete.

The preferred experience is:

```text
Polaris recommends an action
        ↓
Human accepts / modifies / rejects / defers
        ↓
Human executes through the normal trading system when applicable
        ↓
Polaris observes the resulting external evidence
        ↓
Polaris associates it with the originating decision
        ↓
Decision record continues
```

A representative product interaction might be:

> I observed the SPY reduction associated with this morning's decision. The position was reduced by 24.7% across three fills. I have attached the execution evidence and updated the portfolio state used for subsequent monitoring.

The user should experience this as continuity, not bookkeeping.

## Reconciliation confidence and ambiguity

Automatic reconciliation must not become silent invention.

A useful product hierarchy is:

```text
High-confidence association
→ reconcile automatically

Plausible but ambiguous association
→ ask for lightweight confirmation

No credible association
→ preserve as unassociated external activity
```

If several trades could plausibly satisfy the same decision intent, Polaris should ask a narrow question such as:

> I observed two SPY reductions that could correspond to this decision. Was the 10:14 sale the action associated with it?

The desired friction is **confirmation**, not duplicate data entry.

Polaris should never attach an external action to a decision merely because doing so would make the record look complete.

## External activity can originate outside Polaris

The portfolio is reality; Polaris's decision records are an interpretation of that reality.

A user may make trades or portfolio changes that did not originate from a Polaris recommendation. Polaris should observe those changes without fabricating an originating Polaris decision.

A mature product may say:

> I observed a new position without a corresponding Polaris decision record.

The user may then provide context if useful, or the activity may remain explicitly external.

This allows Polaris to maintain an accurate portfolio model without requiring all human investment judgment to originate inside the product.

## One decision can produce several actions

A portfolio decision may imply zero, one, or multiple external actions.

For example:

```text
Decision: reduce portfolio risk

Action 1: reduce SPY exposure
Action 2: close a high-beta position
Action 3: raise cash allocation
Action 4: refrain from adding risk until CPI
```

Each action may have its own lifecycle:

```text
intended
   ↓
observed as initiated externally
   ↓
partially executed
   ↓
executed
   ↓
modified
   ↓
completed / closed / abandoned
```

These labels are conceptual rather than a prescribed state machine.

The important distinction is that later evaluation should know whether the decision was actually implemented and, if only partially, which assumptions about the resulting portfolio were or were not realized.

## Stops, targets, and continuing trade lifecycle

Execution continuity must extend beyond the initial fill when the decision includes ongoing risk or exit conditions.

Suppose the decision is conceptually:

```text
Enter SPY long
Entry area: around 640
Protective stop: 620
Target: 675
```

The external execution system may later report:

```text
entry submitted
   ↓
entry filled
   ↓
position opened
   ↓
stop established
   ↓
target established
   ↓
stop or target modified
   ↓
position closed
```

The relevant events should remain associated with the originating decision where they are causally connected.

If the target is eventually filled, the decision record should be able to preserve the actual entry, actual position size, actual protective stop, actual target, subsequent modifications, exit price, exit reason, holding period, and realized outcome where available.

If the user manually closes the position before either contingent order executes, that should be preserved as a different observed outcome rather than forced into the original plan.

## Recommendation, decision, execution, and outcome are distinct facts

Polaris should preserve at least four conceptual layers:

```text
Polaris recommendation
        ≠
Human decision
        ≠
Actual execution
        ≠
Realized outcome
```

This distinction is essential for trustworthy evaluation.

For example:

```text
Polaris recommendation:
Enter around 641

Human decision:
Accept

Actual execution:
Entered at 656

Outcome:
Stopped out at a loss
```

Calling that simply "a losing Polaris recommendation" would erase material information about how the decision was implemented.

The inverse is also possible: a poor recommendation may produce a favorable realized outcome because of execution luck or a later human override.

Outcome alone therefore cannot answer whether the recommendation process was sound.

## Separate dimensions of later evaluation

Execution continuity allows Polaris to evaluate the investment process more honestly across dimensions such as:

```text
Recommendation quality
Human judgment
Execution quality
Risk-management adherence
Position-management choices
Realized outcome
```

The system can ask better questions:

* Was the original thesis reasonable given what was knowable at the time?
* Did the human accept, modify, reject, or defer the recommendation?
* Was the intended portfolio action actually executed?
* Did the actual fill materially differ from the action the decision assumed?
* Were the expected stop, target, or risk conditions established?
* Were they later modified?
* Did the exit occur because the thesis failed, a risk control triggered, the human overrode the plan, or another event intervened?
* Did execution differences materially explain the realized outcome?

This makes the learning loop about process quality rather than simple profit/loss attribution.

## Portfolio state is the ultimate operational reality

Action intent describes what the decision meant to change. Observed portfolio state tells Polaris what actually exists.

If the decision called for a 25% reduction but the broker shows only a 10% reduction, Polaris should not assume completion merely because the human previously accepted the recommendation.

It should understand that the decision may be only partially implemented and that the current portfolio still differs from the state assumed by the intended action.

That may itself become decision-relevant attention:

> The risk-reduction decision appears only partially implemented. Current exposure remains above the level assumed by the recommendation.

This is consistent with the attentive Core Experience: Polaris notices when decision intent and operational reality diverge without taking control of the execution system.

## External system failures remain external responsibilities

Polaris may understand that a protective stop was expected and later observe whether it existed or triggered.

That does not make Polaris responsible for enforcing the stop.

Conceptually:

```text
Decision:
Use a protective stop.

Execution system:
Owns order acceptance and execution.

Polaris:
Observes whether the expected control existed,
what happened to it, and how the result affected the decision lifecycle.
```

If an execution system fails to carry out an operational instruction correctly, that remains an execution-system failure. Polaris's responsibility is to preserve the evidence accurately and incorporate the result into subsequent portfolio reasoning and evaluation.

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
      EXECUTION SYSTEM                             │
             ↓                                     │
           ACTION                                  │
             ↓                                     │
      OBSERVED RESULT ─────────────────────────────┘
             ↓
          POLARIS
        reconcile
        monitor
        evaluate
        learn
```

Polaris is therefore not merely a recommendation generator. It is a closed-loop portfolio decision system whose lifecycle crosses external operational systems without taking over their authority.

## Product contract

The durable contract is:

> **Polaris does not own execution, but it owns continuity of the decision lifecycle across execution.**

And:

> **External operational systems remain authoritative for actions and resulting portfolio state. Polaris should automatically observe and reconcile that external evidence into the originating decision wherever practical, requiring human input primarily for ambiguity or context that cannot be derived.**

The product should prefer system-to-system continuity over user-maintained duplicate records whenever an authoritative source can supply the relevant evidence.

## Consequences

This decision implies:

* a human decision that implies external action should leave enough intent for Polaris to recognize the expected portfolio consequence later;
* action or execution intent is a product concept, not an authorization for Polaris to place orders;
* authoritative external execution and portfolio systems should be observed rather than duplicated as operational systems of record;
* Polaris should automatically reconcile observed external actions to originating decisions when confidence is sufficient;
* ambiguous associations should trigger lightweight confirmation rather than silent guessing or full manual data entry;
* externally initiated trades and portfolio changes must remain identifiable as such;
* a decision may have zero, one, or many action threads, each with its own observed lifecycle;
* partial fills, later modifications, protective orders, exits, and other material execution evidence may remain associated with the decision lifecycle;
* recommendation, human decision, execution, and realized outcome must remain separately identifiable;
* portfolio state determines what actually exists even when it differs from the recorded intent;
* incomplete implementation of a human decision may itself become attentive decision context;
* later evaluation should be able to distinguish recommendation quality, human judgment, execution quality, risk management, and outcome;
* execution-system failures do not become Polaris execution failures merely because Polaris observed them;
* the preferred user experience is automatic observation and reconciliation, with manual input reserved primarily for ambiguity or missing context;
* the Authority Model should distinguish observation and reconciliation authority over Polaris's own records from authority to act on capital;
* Scope Boundaries should preserve inbound execution evidence as product-relevant integration without making outbound execution control part of Polaris's defining responsibility.
