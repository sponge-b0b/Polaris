# Polaris 0.2.0 Requirements Specification

**Status:** Proposed  
**Release:** 0.2.0  
**Purpose:** Define the greenfield product requirements Polaris 0.2.0 must satisfy before architecture or implementation choices are allowed to constrain the solution.

## Authority and derivation

This specification is derived from the current non-legacy product and domain authority set, principally:

- [`../../CONTEXT.md`](../../CONTEXT.md) — canonical domain vocabulary;
- [`domain-model.md`](./domain-model.md) — frozen domain invariants, lifecycle semantics, temporal semantics, and pressure-test scenarios;
- [`domain-discovery-definition-of-done-audit.md`](./domain-discovery-definition-of-done-audit.md) — GREEN authorization to begin 0.2.0 requirements and architecture;
- [`product-definition.md`](./product-definition.md) — product purpose, users, jobs, identity, ecosystem position, and core experience;
- [`product-core-capabilities.md`](./product-core-capabilities.md) — durable core capabilities;
- [`capability-model.md`](./capability-model.md) — capability relationships and cross-cutting contracts;
- [`product-authority-model.md`](./product-authority-model.md) — separation-of-powers authority model;
- [`product-execution-continuity.md`](./product-execution-continuity.md) — continuity across externally authoritative execution;
- [`product-scope-boundaries.md`](./product-scope-boundaries.md) — ownership and external-specialist boundaries;
- [`product-principles.md`](./product-principles.md) — product decision rules.

The pre-greenfield implementation under `legacy/v0_1/` is **not** a requirements source. It may be inspected only after requirements and greenfield architecture independently establish a current need and architectural owner.

If implementation convenience, legacy behavior, or later architecture conflicts with this specification or the frozen product/domain doctrine, the conflict must be surfaced rather than resolved by silently weakening the product semantics.

## Requirement language

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** express normative strength.

- **MUST / MUST NOT** — required for 0.2.0 acceptance.
- **SHOULD / SHOULD NOT** — strong default that may be deferred only with an explicit, durable justification that does not violate a MUST requirement.
- **MAY** — permitted but not required for 0.2.0.

Requirement IDs are stable references for architecture, Specs, tests, and release verification. Later wording may be refined without changing an ID's semantic intent.

## Release objective

Polaris 0.2.0 MUST establish the first coherent greenfield baseline of Polaris as an **AI-assisted portfolio decision system** centered on durable Investment Decisions rather than workflows, reports, model outputs, or trades.

The release is intentionally allowed to be **narrow in breadth but complete in semantics**.

0.2.0 MAY initially support a limited asset universe, a limited set of Evidence providers, a limited set of interaction surfaces, and a limited set of external integrations. It MUST NOT obtain delivery speed by collapsing or omitting load-bearing domain distinctions such as Investment Decision, Investment Recommendation, Human Investment Decision, Action Intent, authoritative external activity, Outcome, Decision Evaluation, or the applicable authority acts.

A coherent 0.2.0 release therefore means:

```text
narrow supported breadth
        +
complete decision semantics for that breadth
        +
trustworthy historical reconstruction
        +
explicit authority boundaries
        +
closed-loop continuity where applicable
```

It does **not** mean every long-term Polaris feature or adjacent financial capability must ship in 0.2.0.

---

# 1. Greenfield and product-center requirements

### GF-001 — Investment Decision is the product center

Polaris MUST organize consequential portfolio decision work around first-class **Investment Decisions** and their lifecycle rather than around workflow runs, model calls, reports, conversations, jobs, or externally observed trades.

### GF-002 — Architecture neutrality

This specification MUST NOT require a particular package topology, service decomposition, workflow engine, agent topology, event architecture, database, retrieval technique, model provider, orchestration framework, interface protocol, or deployment shape.

Architecture MAY choose such mechanisms later if they independently satisfy the product requirements.

### GF-003 — Legacy independence

Current Polaris code, tests, configuration, migrations, tools, and runtime paths MUST NOT import, wrap, extend, execute through, or otherwise depend on `legacy/`.

### GF-004 — Reuse is transplant, not inheritance

A legacy implementation MAY be reused only after a current requirement and architectural owner independently exist. Reuse MUST mean deliberate transplantation into the current greenfield boundary; runtime dependency on `legacy/` is prohibited.

### GF-005 — Decision semantics outrank implementation convenience

No implementation mechanism MAY become the source of business identity merely because it is operationally convenient. In particular, workflow identity, job identity, report identity, model identity, and persistence-row identity MUST NOT substitute for canonical Investment Decision identity.

### GF-006 — Supporting mechanisms remain subordinate

AI, retrieval, reports, observability, jobs, workflows, simulations, Backtests, messaging, and other supporting mechanisms MUST justify themselves through decision quality, trustworthiness, continuity, explanation, Decision Evaluation, or future learning rather than becoming independent product centers.

---

# 2. Investment Decision identity and lifecycle

### DEC-001 — Durable Investment Decision identity

Every Investment Decision MUST have a durable identity representing one coherent unresolved portfolio-relevant choice.

That identity MUST be independent of its Subject, Decision Scope, Evidence set, Recommendation, workflow execution, conversation, report, mutable Portfolio State, or external activity.

### DEC-002 — Decision Need precedes or justifies decision work

An Investment Decision MUST be grounded in an attributable **Decision Need** that explains why deliberate investment judgment is required.

### DEC-003 — Subject, Scope, Context, and Decision are distinct

Polaris MUST preserve the distinction among Decision Subject, Decision Scope, Decision Context, and Investment Decision identity.

A change to one of those elements MUST NOT automatically manufacture a new Investment Decision unless the coherent unresolved choice itself changes.

### DEC-004 — Same unresolved choice remains the same decision

Additional Evidence, changed Portfolio State, changed Portfolio Risk, a new Investment View, or a changed Investment Recommendation MUST NOT by themselves create a new Investment Decision while the same coherent investment choice remains unresolved.

### DEC-005 — Iterative decision work

An unresolved Investment Decision MUST be able to move iteratively among Evidence gathering, reasoning, challenge, Portfolio consequence analysis, Portfolio Risk reasoning, and recommendation formation without losing identity or history.

### DEC-006 — Deferral preserves unresolved identity

A **Deferral** MUST leave the same Investment Decision unresolved and resumable. Deferral MUST NOT be represented as substantive resolution or as a new Investment Decision.

### DEC-007 — Deliberate hold/no-action may resolve

A Human Investment Decision to hold or deliberately take no action MAY substantively resolve an Investment Decision when that judgment answers the coherent choice. No synthetic Action Intent is required solely to represent that resolution.

### DEC-008 — External Resolution is distinct

Polaris MUST support **External Resolution** when circumstances eliminate the Decision Need before substantive human resolution. External Resolution MUST NOT invent a Human Investment Decision.

### DEC-009 — Resolved decisions do not reopen

Once an Investment Decision is substantively resolved, later renewed judgment MUST create a new causally linked Investment Decision rather than reopen and rewrite the resolved one.

### DEC-010 — Review Conditions do not reopen history

A satisfied Review Condition MAY cause Attention and a new or resumed Decision Need as appropriate. It MUST NOT reopen a resolved Investment Decision merely because review was anticipated.

### DEC-011 — Supersession preserves both histories

When one Investment Decision supersedes another, Polaris MUST preserve both Investment Decisions and their relationship. Supersession MUST NOT destructively replace prior history.

### DEC-012 — Historical lifecycle states remain reconstructable

Polaris MUST preserve enough temporal information to reconstruct the material lifecycle state of an Investment Decision at relevant historical times.

---

# 3. Attention and decision initiation

### ATT-001 — Multiple initiation paths

Polaris MUST support Decision Needs arising from at least user initiation, scheduled review, and Polaris-detected Investment-Relevant material change.

### ATT-002 — Investment Relevance and Materiality are distinct

Attention MUST distinguish whether new information is Investment Relevant from whether it is Investment Material to a Portfolio-relevant matter.

### ATT-003 — Quiet absorption of immaterial change

Polaris SHOULD absorb irrelevant or immaterial information without demanding user Attention.

"Nothing material changed" MUST be a valid successful outcome.

### ATT-004 — Memory-grounded Attention

Attention MUST be able to consider unresolved Investment Decisions, active Investment Theses, Investment Assumptions, Invalidation Conditions, Catalysts, Review Conditions, deferred work, relevant Portfolio State, Portfolio Risk, and durable Lessons when determining whether new information matters.

### ATT-005 — Prepared work over raw alerting

When Polaris interrupts a user for a material investment matter, it SHOULD surface prepared Decision Context or decision work rather than merely report that an event occurred.

### ATT-006 — Renewed judgment obeys decision identity rules

Attention MUST determine whether material change should resume the same unresolved Investment Decision or create a new causally linked Investment Decision after prior substantive resolution.

### ATT-007 — Attention does not imply action

A material event MAY produce Attention without producing an Investment Recommendation, Human Investment Decision, or Portfolio action.

---

# 4. Decision Context and Evidence

### EVD-001 — Information is not automatically Evidence

Polaris MUST distinguish available information from Evidence actually used or preserved in support of a material judgment, claim, authority decision, or later evaluation.

### EVD-002 — Attributable source provenance

Material Evidence MUST preserve attributable source provenance sufficient to identify where the relevant fact or assertion came from.

### EVD-003 — Temporal provenance

Material Evidence MUST preserve enough temporal metadata to distinguish observation time, applicable as-of time, and **Judgment-Time Availability** where relevant.

### EVD-004 — Judgment-Time Availability

For a material judgment, Polaris MUST be able to determine what Evidence was available to that judgment at the relevant time.

Later-acquired Evidence MUST NOT be retroactively represented as available to the earlier judgment.

### EVD-005 — Use-specific Freshness Requirements

Freshness MUST be evaluated relative to the investment judgment or consequential use being supported rather than by one universal real-time threshold.

### EVD-006 — Stale Evidence changes current support, not historical existence

When required Evidence becomes too stale, Polaris MUST qualify or withhold the affected current judgment or consequential use as appropriate. It MUST NOT erase the historical judgment or pretend it never existed.

### EVD-007 — Evidence sufficiency

Polaris MUST be able to determine and preserve whether required Evidence is sufficient for a material judgment or governed consequential use.

### EVD-008 — Missing Evidence remains missing

Absent, unavailable, unknown, disputed, or indeterminate material Evidence MUST remain represented as such. Polaris MUST NOT replace missing facts with plausible-looking values solely to complete a decision path.

### EVD-009 — Conflicting Evidence remains visible

Material Conflicting Evidence MUST remain inspectable and MUST NOT be silently removed when Polaris forms a preferred Investment View or Recommendation.

### EVD-010 — External factual authority is preserved

Where an external specialist source owns factual authority for a fact, Polaris MUST preserve that authority boundary when normalizing, caching, deriving, interpreting, or presenting the fact.

### EVD-011 — Operational reality outranks expectation

When an authoritative external fact conflicts with a Polaris expectation, Recommendation, Action Intent, cache, or derived state, the authoritative external fact MUST remain authoritative within that source's responsibility domain.

### EVD-012 — Material Signals remain reconstructable

When a Signal materially contributes to a judgment, Polaris MUST preserve enough information to reconstruct its subject, as-of basis, method or calculation identity, material parameters, and provenance. Transient Signals need not all become durable business entities.

---

# 5. Investment reasoning and challenge

### RSN-001 — Reasoning produces attributable judgment

Material Polaris investment judgments MUST be attributable to the reasoning operation and supporting Evidence from which they were formed.

### RSN-002 — Hypothesis, View, and Thesis remain distinct

Polaris MUST preserve the canonical distinctions among Investment Hypothesis, Investment View, and Investment Thesis where those concepts materially apply.

### RSN-003 — Meaningful challenge is required

Before a consequential Investment Recommendation is treated as adequately developed, Polaris MUST meaningfully consider why the preferred Investment View may be wrong.

### RSN-004 — Challenge content

Material reasoning SHOULD be capable of representing, where applicable:

- supporting Evidence;
- Conflicting Evidence;
- competing Investment Hypotheses or alternative explanations;
- Investment Assumptions;
- Investment Uncertainty;
- Invalidation Conditions;
- Catalysts;
- Investment Horizon.

### RSN-005 — Challenge is topology-independent

The challenge requirement MUST NOT mandate Bull/Bear/Sideways agents, multiple models, debate rounds, or any other fixed agent topology.

### RSN-006 — Decision Alternatives emerge before recommendation finality

Reasoning MUST be capable of producing or informing meaningful Decision Alternatives rather than forcing a single predetermined action path.

### RSN-007 — Uncertainty is not generic confidence

Polaris MUST NOT use a bare generic confidence value as a universal substitute for Investment Uncertainty or attributable Judgment Confidence.

### RSN-008 — Reasoning may remain inconclusive

Polaris MUST be allowed to conclude that material uncertainty or contradiction prevents a responsible current preference.

### RSN-009 — Supporting analytical techniques are optional means

Historical analogs, RAG, Investment Simulation, Backtest, model ensembles, deterministic analytics, and similar techniques MAY support reasoning, challenge, or evaluation but are not individually required product mechanisms.

---

# 6. Portfolio consequence and Portfolio Risk

### PRT-001 — Portfolio context is load-bearing

A consequential Investment Recommendation MUST be formed in the context of the applicable Portfolio rather than as an isolated security or market opinion.

### PRT-002 — Portfolio identity is not holdings identity

Polaris MUST treat Portfolio identity as a continuing investment responsibility rather than as a synonym for a current holdings snapshot or Account Boundary.

### PRT-003 — Portfolio State is distinguishable from projected state

Current authoritative Portfolio State and projected Portfolio State MUST remain distinguishable.

### PRT-004 — Position, Exposure, Allocation, and Portfolio Risk remain distinct

Polaris MUST preserve the canonical distinctions among Position, Exposure, Allocation, and Portfolio Risk.

### PRT-005 — Projected Portfolio Consequence

Polaris MUST be able to express the projected effect of a Decision Alternative or Proposed Action on the Portfolio without representing that projection as authoritative future reality.

### PRT-006 — Portfolio Risk is multidimensional

Portfolio Risk MUST be capable of representing materially adverse possibilities and objective shortfall in a portfolio-, horizon-, and scenario-relative way. A single generic Risk Score MUST NOT be the universal Portfolio Risk representation.

### PRT-007 — Portfolio Risk shapes recommendation formation

Portfolio Risk MUST participate in forming the Investment Recommendation rather than being applied only as a post-hoc approval stamp.

### PRT-008 — Investment Strategy and Trading System remain distinct

Polaris MUST preserve the distinction between Investment Strategy and Trading System where either concept applies.

### PRT-009 — Mandate semantics remain precise

Polaris MUST distinguish Investment Objective, Investment Principle, Formal Constraint, Investment Mandate, and Mandate Exception.

### PRT-010 — Formal Constraints are deterministic where evaluable

Applicable machine-evaluable Formal Constraints MUST produce explicit satisfied, violated, or indeterminate results rather than being replaced by model judgment.

### PRT-011 — Policy is distinct from Portfolio Risk and Formal Constraint

Platform Policy results MUST remain semantically distinct from Portfolio Risk, Formal Constraint results, Approval, and Human Investment Decision.

### PRT-012 — Unknown consequence remains unknown

If a material Projected Portfolio Consequence or Portfolio Risk cannot be established with adequate support, Polaris MUST preserve the unresolved state rather than manufacture precision.

---

# 7. Recommendation formation

### REC-001 — Recommendation is decision-bound

Every Investment Recommendation MUST be attributable to an Investment Decision and the Decision Context in which it was formed.

### REC-002 — Recommendation is not the Investment Decision

Investment Recommendation identity MUST remain distinct from Investment Decision identity and Human Investment Decision identity.

### REC-003 — Zero, one, or multiple recommendations

An Investment Decision MAY contain zero, one, or multiple Investment Recommendations over its unresolved lifecycle.

### REC-004 — Recommendation may be withheld

Polaris MUST be able to withhold a current Investment Recommendation when Evidence, freshness, reasoning, Portfolio Risk, or other required support is insufficient.

### REC-005 — No-action is valid

A responsible Recommendation MAY prefer hold, wait, Deferral, or deliberate no-action when supported by the Decision Context.

### REC-006 — Recommendation explains its basis

A consequential Investment Recommendation MUST preserve enough support to inspect its material rationale, Evidence, Portfolio context, Portfolio Risk, meaningful Decision Alternatives, material uncertainty, and conditions that would change the judgment.

### REC-007 — Proposed Actions remain candidates

A Proposed Action within a Recommendation MUST remain a candidate implementation and MUST NOT be treated as a Human Investment Decision, Action Intent, Order, or execution authorization.

### REC-008 — Recommendation remains contestable

The user or an authorized reviewer MUST be able to inspect and challenge a consequential Investment Recommendation and its material supporting basis before or during the relevant authority process.

---

# 8. Authority and Human Investment Decision

### AUT-001 — Separation of powers

Polaris MUST preserve the distinction among:

- authoritative external facts;
- deterministic Policy and Formal Constraint results;
- Polaris investment judgment;
- Admissibility;
- Approval and Authority Denial;
- Mandate Exception;
- Residual-Risk Acceptance;
- Human Investment Decision;
- external execution authority.

### AUT-002 — Capability does not imply authority

A component's ability to produce an output or perform an internal operation MUST NOT imply authority for consequential investment use or external capital action.

### AUT-003 — Model text cannot manufacture authority

A model, provider, tool, workflow, prompt, or generated output MUST NOT grant Approval, authorize a Mandate Exception, accept Governed Residual Risk, create execution authority, or reduce the authority requirements governing its own output merely by declaring those effects.

### AUT-004 — Investment Authority Regime

Polaris MUST be able to represent which attributable actors or authorized processes possess the relevant power-specific authority for a Portfolio or Investment Decision.

### AUT-005 — Human Investment Decision is attributable

A Human Investment Decision MUST be explicitly attributable and durably preserved as a distinct human judgment even when it adopts a Polaris Investment Recommendation unchanged.

### AUT-006 — Human judgment may differ from Recommendation

The Human Investment Decision MUST be able to adopt, modify, reject, defer, or choose a disposition different from the current Investment Recommendation.

### AUT-007 — Human Investment Decision may exist without Recommendation

Polaris MUST NOT require a prior Investment Recommendation in order to preserve an attributable Human Investment Decision when a human legitimately forms one.

### AUT-008 — Recommendation rejection does not imply resolution

Rejecting a Recommendation MUST NOT by itself determine whether the Investment Decision is resolved, deferred, or remains open.

### AUT-009 — Power-specific acts remain separate even for one actor

If one human performs multiple authority acts, such as Approval, Human Investment Decision, Mandate Exception, or Residual-Risk Acceptance, Polaris MUST preserve those acts separately when their semantics materially differ.

### AUT-010 — Positive authority provenance

Material positive authority acts and satisfied deterministic conditions MUST be durably reconstructable when required. Absence of a recorded denial or failure MUST NOT be treated as proof that every required authority act occurred.

### AUT-011 — Fail closed at governed boundaries

When a consequential use requires Evidence, deterministic rule results, or authority acts that are missing, stale, indeterminate, denied, or otherwise unsatisfied, Polaris MUST NOT represent the governed use as admissible merely because an output exists.

### AUT-012 — Authority decisions remain immutable historical facts

Attributable Approval, Authority Denial, Mandate Exception, Residual-Risk Acceptance, and Human Investment Decision facts MUST remain historical facts. Later change MUST be represented through new attributable acts, supersession, correction, or other non-destructive history rather than silent mutation of what occurred.

### AUT-013 — Contestability and review history

Where consequential Governance requires human review, Polaris MUST preserve attributable review outcomes and materially relevant rationale, denial, requested changes, contest, override, or explicit residual-risk acceptance where those acts occur.

### AUT-014 — Actor attribution is distinct from technical provenance

Actor identity and authority MUST remain distinct from model/provider/tool/workflow provenance. A model or workflow identifier MUST NOT be treated as the responsible human or organizational actor.

---

# 9. Action continuity and external reconciliation

### ACT-001 — No execution authority

Polaris 0.2.0 MUST NOT submit, route, modify, cancel, or otherwise exercise market-facing execution authority as part of its defining product responsibility.

### ACT-002 — Action Intent is post-human

An **Action Intent** MUST exist only when an attributable Human Investment Decision establishes an externally observable implementation consequence or control.

### ACT-003 — Action Intent cardinality follows intended consequence

A Human Investment Decision MAY establish zero, one, or multiple Action Intents. Action Intent cardinality MUST follow coherent intended external consequence rather than instrument count, Proposed Action count, Order count, or fill count.

### ACT-004 — No synthetic Action Intent for Deferral or no-action

Deferral and deliberate hold/no-action MUST NOT require a synthetic Action Intent merely to duplicate the Human Investment Decision.

### ACT-005 — Action Intent is not an Order

Action Intent MUST remain distinct from Order, fill, routing instruction, broker instruction, and externally authoritative execution fact.

### ACT-006 — Observe authoritative external activity

Polaris MUST be able to ingest or otherwise preserve authoritative external activity relevant to an Action Intent or resulting Portfolio State without claiming authorship of that external activity.

### ACT-007 — Supported reconciliation may be automatic

When the relationship between an Action Intent and external activity is sufficiently supported, Polaris SHOULD reconcile it automatically without requiring duplicate manual bookkeeping.

### ACT-008 — Material ambiguity remains unresolved

When multiple external activities could plausibly satisfy an Action Intent and the distinction materially changes meaning, Polaris MUST preserve the ambiguity and request lightweight confirmation or leave the association unresolved rather than silently guess.

### ACT-009 — Unassociated external activity remains external

External activity with no supported originating Polaris relationship MUST remain identifiable as externally initiated activity. Polaris MUST NOT retroactively manufacture a Recommendation, Human Investment Decision, or Action Intent to explain it.

### ACT-010 — Partial and divergent implementation are preserved

Partial execution, modified activity, abandoned implementation, failed implementation, or other material divergence from Action Intent MUST remain representable rather than being flattened into a binary success state.

### ACT-011 — Resulting Portfolio State is authoritative reality

When authoritative Portfolio State differs from the state expected by an Action Intent, the observed authoritative Portfolio State MUST determine what actually exists.

### ACT-012 — Execution divergence may cause Attention without rewriting history

Implementation divergence MAY cause Attention to evaluate whether unresolved work should resume or a renewed Decision Need exists. It MUST NOT reopen and rewrite a substantively resolved Investment Decision.

---

# 10. Durable Decision Memory

### MEM-001 — Cross-lifecycle responsibility

Durable Decision Memory MUST span the Investment Decision lifecycle rather than exist only as a final archive step.

### MEM-002 — Memory preserves semantics, not runtime artifacts

Durable Decision Memory MUST preserve material decision meaning and relationships independently of any one workflow execution, report, conversation, model call, job, or storage representation.

### MEM-003 — Historical reconstruction

For material judgments and decisions, Polaris MUST be able to reconstruct enough of the historical basis to answer, where applicable:

- what Decision Need existed;
- what Decision Context applied;
- what Evidence was available;
- what Polaris judged and why;
- what meaningful uncertainty or challenge existed;
- what Portfolio Risk and Projected Portfolio Consequences were understood;
- what deterministic rules applied;
- what Recommendation existed;
- which authority acts occurred;
- what the human decided;
- what Action Intent existed, if any;
- what external activity actually occurred;
- what Outcome was later observed;
- how the decision was evaluated;
- what Lessons were derived.

### MEM-004 — What was known then remains distinguishable from what is known now

Polaris MUST preserve the distinction between present knowledge and the Evidence available to a historical judgment.

### MEM-005 — History is non-destructive

Later corrections, new Evidence, changed judgments, evaluation, supersession, or renewed decisions MUST NOT silently rewrite the attributable historical facts that actually existed.

### MEM-006 — Supported relationships only

Causal, attribution, authority, and continuity relationships MUST be represented only to the strength supported by Evidence. Material ambiguity MUST remain explicit.

### MEM-007 — Durable memory is active context

Durable Decision Memory MUST be usable by future Attention, Decision Context, reasoning, Governance, and Decision Evaluation rather than serving only as passive archival storage.

### MEM-008 — Decision memory is not one mandated entity

Lowercase `decision record` MAY be used as product shorthand for an assembled representation of decision history. The requirements MUST NOT imply one canonical storage object named `DecisionRecord`.

### MEM-009 — Business truth is direct

Durable business meaning MUST be persistable or reconstructable directly from authorized decision-domain state. It MUST NOT depend on replaying a legacy workflow graph or interpreting generic runtime output as the sole source of business truth.

### MEM-010 — Decision memory remains queryable after runtime details change

Replacing models, providers, orchestration, reports, or other implementation mechanisms MUST NOT inherently destroy the ability to inspect prior Investment Decision history.

---

# 11. Outcome, Decision Evaluation, and Lesson

### EVA-001 — Outcome is decision-relative

An **Outcome** MUST represent an observed consequence relevant to an Investment Decision without implying that the decision caused the Outcome or that the decision was good or bad.

### EVA-002 — Decision Evaluation is attributable judgment

A **Decision Evaluation** MUST be an attributable retrospective judgment formed against explicit or reconstructable criteria and a historically faithful basis.

### EVA-003 — Outcome does not determine decision quality

Polaris MUST NOT equate profitable or favorable Outcome with good decision quality, nor unfavorable Outcome with poor decision quality.

### EVA-004 — Evaluate process dimensions separately where useful

Decision Evaluation SHOULD be capable of distinguishing, where Evidence permits:

- Evidence quality;
- reasoning quality;
- Investment Thesis quality;
- Portfolio Risk reasoning;
- Policy and Formal Constraint effects;
- Investment Recommendation quality;
- Human Investment Decision;
- implementation fidelity and Trade Implementation Risk;
- observed Outcome.

### EVA-005 — Retrospective evaluation respects Judgment-Time Availability

Later Evidence MAY inform evaluation and learning but MUST NOT be treated as though it was available to an earlier judgment.

### EVA-006 — Lesson is scoped learning, not authority

A **Lesson** MUST be preserved as a scoped learning proposition. It MUST NOT automatically become Policy, Investment Mandate, Formal Constraint, or another authority-bearing rule without the applicable separate change process.

### EVA-007 — Lessons may influence future behavior

Durable Lessons SHOULD be usable by future Attention, reasoning, evaluation criteria, or proposals for Policy/Mandate review where relevant.

### EVA-008 — Evaluation may remain uncertain

When Evidence cannot support a strong retrospective conclusion, Decision Evaluation MUST be allowed to preserve uncertainty rather than overstate causality or process quality.

---

# 12. Interaction and presentation

### UX-001 — Shared decision semantics across surfaces

Every supported interaction or presentation surface MUST operate over shared decision semantics rather than reconstructing an independent version of the Investment Decision.

### UX-002 — At least one complete human decision surface

0.2.0 MUST provide at least one human-usable surface capable of inspecting material Decision Context and recording an attributable Human Investment Decision for the supported release path.

The specific surface is an architecture/product-delivery choice, not a requirement for web, CLI, MCP, email, PDF, or any other named protocol.

### UX-003 — Concise first, inspectable underneath

The normal experience SHOULD summarize material decision state concisely while preserving deeper Evidence, reasoning, uncertainty, authority, and history for inspection on demand.

### UX-004 — Material effects are prominent

Material stale Evidence, conflicting Evidence, Portfolio Risk, Formal Constraint or Policy effects, denied or missing authority, unresolved ambiguity, and implementation divergence MUST NOT be hidden behind optional detail when they materially change the decision or its admissibility.

### UX-005 — Human correction and contestability

The supported human surface MUST allow a user to provide material correction, context, challenge, or human judgment without requiring the system to overwrite historical machine judgment.

### UX-006 — Surface breadth is not a release criterion

0.2.0 does not require multiple equivalent presentation surfaces merely for breadth. Additional surfaces MAY be added later if they preserve the same shared decision semantics.

---

# 13. Integration and external-system requirements

### INT-001 — Integrate without absorbing specialist authority

Polaris MUST be able to consume required external Evidence and state while preserving the specialist system's factual authority for the responsibilities it owns.

### INT-002 — Provider choice is not business identity

Provider, vendor, model, hosting, transport, or adapter identity MUST NOT become the canonical identity of the business capability or Investment Decision.

### INT-003 — Minimum coherent external state

The supported 0.2.0 release path MUST have access to sufficiently trustworthy Decision Context, Evidence, and Portfolio State to exercise the decision lifecycle honestly.

The requirement does not mandate a particular vendor or number of integrations.

### INT-004 — Source failures remain visible

When an external source is unavailable, stale, contradictory, or otherwise unfit for the intended use, Polaris MUST preserve that condition rather than silently substituting an unqualified cached or guessed value.

### INT-005 — Read/observe integration does not imply write authority

Integration with brokerage, execution, accounting, or other operational systems for observation or reconciliation MUST NOT imply authority to perform the corresponding external action.

### INT-006 — Integration breadth follows decision value

The number of integrations is not itself evidence of product completeness. 0.2.0 MAY intentionally support a small integration set if it is sufficient for a coherent decision path.

---

# 14. Configuration and extensibility

### CFG-001 — Configure investment-domain concepts

Polaris MUST allow the supported release path to express the domain configuration necessary for its Investment Decisions, including the applicable Portfolio and relevant Investment Horizon, Investment Strategy, Investment Mandate, Formal Constraints, Policy, and Review Conditions where those concepts materially apply.

### CFG-002 — Domain configurability, not generic workflow construction

User-facing configurability MUST be grounded in investment-domain concepts. Users MUST NOT be required to construct arbitrary nodes, graphs, prompts, or generic agent workflows merely to express the normal Polaris decision lifecycle.

### CFG-003 — Analytical implementation remains replaceable

Models, Evidence providers, analytical techniques, and other supporting mechanisms SHOULD be replaceable without redefining canonical Investment Decision semantics.

### CFG-004 — No speculative extensibility mandate

0.2.0 MUST NOT add a generic plugin framework, universal workflow builder, or broad extension API solely because legacy Polaris had one or future users might want one.

Extensibility MUST be justified by a current requirement.

---

# 15. Reliability and observability

### REL-001 — Failures are visible

A failure to obtain required Evidence, form a supported judgment, persist required durable state, apply a deterministic rule, execute a required authority transition, or reconcile material external activity MUST NOT be silently converted into success.

### REL-002 — Durable transitions survive process boundaries

Material committed decision-domain state MUST survive ordinary process restart and MUST NOT exist only in transient model, workflow, or in-memory state.

### REL-003 — Retry does not duplicate business truth

Where the implementation retries work, retry behavior MUST NOT create duplicate authoritative Investment Decisions, Recommendations, authority acts, Human Investment Decisions, Action Intents, or other durable business facts.

### REL-004 — Observability is supporting Evidence, not business identity

Operational telemetry MUST be sufficient to diagnose and inspect execution of the supported release path, but runtime traces, events, or workflow output MUST NOT replace canonical business state.

### REL-005 — Sensitive information is sanitized

Logs, traces, diagnostics, and operational telemetry MUST NOT expose secrets or other protected information unnecessarily.

### REL-006 — Decision provenance remains available when runtime provenance is partial

A failure or omission in optional telemetry MUST NOT destroy the independently required decision-domain provenance for material business facts.

### REL-007 — Recovery preserves historical truth

Recovery from interruption or failure MUST preserve already-committed attributable history and MUST NOT silently regenerate it as though the regenerated judgment were the original one.

---

# 16. Security and operational trust

### SEC-001 — Secrets remain outside durable product content

Credentials, tokens, passwords, and full authenticated connection strings MUST NOT be stored in decision history, model prompts, reports, test fixtures, logs, or other product content except through an explicitly secure secret-management boundary.

### SEC-002 — Authority-sensitive actions require attributable identity

Material authority acts and Human Investment Decisions MUST be attributable to an actor identity sufficient for the applicable product maturity and authority regime.

### SEC-003 — Authentication is distinct from authorization and investment authority

Identity/authentication, platform authorization, and investment-domain authority MUST remain distinct. Successful authentication MUST NOT by itself grant investment authority.

### SEC-004 — Model input cannot rewrite governing authority

Untrusted or externally supplied content, including model-generated text and retrieved Evidence, MUST NOT silently alter Policy, Formal Constraints, Investment Authority Regime, or other governing rules.

### SEC-005 — Small-team design center

0.2.0 MAY use an appropriately simple identity and operations model for sophisticated individual users and small teams. It MUST NOT assume enterprise multitenancy, institution-wide IAM, or broad compliance machinery unless a separate current requirement justifies those responsibilities.

### SEC-006 — Sensitive Portfolio information is protected

Portfolio State, decision history, authority history, and other sensitive investment information MUST be handled according to explicit access and operational boundaries appropriate to the supported deployment model.

---

# 17. Temporal and performance requirements

### TMP-001 — Decision time, not exchange-engine time

Polaris MUST be designed for portfolio decision time and analytical time, not as a low-latency execution engine.

### TMP-002 — No exchange-speed execution guarantee

0.2.0 MUST NOT claim exchange-speed decisioning, order protection, market-speed kill switches, or similar execution guarantees.

### TMP-003 — Material-change triage may precede full reasoning

During fast-moving conditions, Polaris MUST be able to recognize that prior Decision Context or current support has become unsafe or stale without waiting for a full AI reasoning cycle.

The exact mechanism is architectural.

### TMP-004 — Unsupported prior recommendations cannot masquerade as current

When a material change or freshness failure invalidates current support, Polaris MUST prevent a prior Recommendation from being presented as currently supported merely because it remains historically stored.

### TMP-005 — Exact latency objectives are operational, not domain identity

Architecture and release planning MUST define measurable latency/SLO targets for the chosen supported path, but this specification does not mandate exchange-oriented numeric thresholds before the implementation shape is known.

---

# 18. Explicit scope boundaries for 0.2.0

### SCP-001 — No autonomous execution

Automated capital execution is outside the defining scope of 0.2.0.

### SCP-002 — No generic AI/workflow platform

0.2.0 is not required to expose a general-purpose agent framework, workflow builder, orchestration platform, or arbitrary financial automation environment.

### SCP-003 — No comprehensive market-data or charting terminal

Polaris requires Investment-Relevant market Evidence but is not required to become a comprehensive market-data vendor or generalized charting platform.

### SCP-004 — No official portfolio accounting mandate

Polaris requires trustworthy Portfolio State but is not required to become the official books-and-records, custody, settlement, tax-accounting, or NAV system.

### SCP-005 — No generalized quantitative-development environment

Investment Simulation, Backtest, historical analog analysis, and other quantitative capabilities MAY support decision work. 0.2.0 is not required to become a general-purpose systematic-strategy development environment.

### SCP-006 — No broad regulatory-compliance platform

Decision Governance is in scope. Institution-wide regulatory filing, employee surveillance, generalized preclearance, and broad compliance operations are not automatically 0.2.0 responsibilities.

### SCP-007 — No feature-count acceptance

Release acceptance MUST be based on coherent decision capability and trustworthy semantics rather than the number of agents, providers, reports, integrations, dashboards, or analytical features present.

---

# 19. 0.2.0 acceptance scenarios

The release MUST demonstrate the following scenarios through executable tests, product-level verification, or equivalent acceptance evidence. One test may satisfy multiple requirements.

## AS-001 — New material Decision Need

New Investment-Relevant and material information creates Attention and a new Investment Decision with a durable identity, attributable Decision Need, Decision Context, and Evidence.

## AS-002 — Same unresolved decision resumes

New Evidence materially changes the reasoning or Recommendation for an unresolved Investment Decision without creating a new Investment Decision merely because the Evidence or Portfolio State changed.

## AS-003 — Deferral and later resumption

A human Deferral leaves the same Investment Decision unresolved; a later Review Condition or material event resumes that same coherent unresolved choice.

## AS-004 — Resolved decision followed by renewed judgment

A substantively resolved Investment Decision remains immutable history. Later renewed judgment creates a new causally linked Investment Decision rather than reopening the old one.

## AS-005 — External Resolution

Circumstances eliminate the Decision Need before substantive human judgment. Polaris records External Resolution without inventing a Human Investment Decision.

## AS-006 — Stale Evidence blocks current support

Required Evidence exceeds its applicable Freshness Requirement. Polaris preserves the historical Recommendation but qualifies or withholds current support and does not represent the stale state as current.

## AS-007 — Conflicting Evidence and meaningful challenge

Material Conflicting Evidence and a credible alternative explanation remain visible after Polaris forms a preferred Investment View and Recommendation.

## AS-008 — Portfolio Risk changes the recommendation

The same investment thesis applied to materially different Portfolio State or Portfolio Risk produces different Projected Portfolio Consequences or a different Recommendation where appropriate.

## AS-009 — Rules and authority remain distinct

A scenario demonstrates that Formal Constraint result, Policy result, Admissibility, Approval, Human Investment Decision, and execution authority are separately represented and cannot be inferred from one another.

## AS-010 — Positive authority provenance

A governed consequential use requiring positive authority demonstrates that required Evidence readiness, applicable deterministic rule results, and required authority acts are positively reconstructable rather than inferred from the absence of failure.

## AS-011 — Human modifies or rejects Recommendation

A human modifies or rejects a Polaris Recommendation. Polaris preserves both the Recommendation and Human Investment Decision without rewriting either, and the resolution state is determined independently of mere Recommendation rejection.

## AS-012 — Human decision without Recommendation

An attributable Human Investment Decision can be recorded when no Polaris Recommendation was supportable or available, without fabricating a Recommendation.

## AS-013 — Hold/no-action with zero Action Intents

A deliberate hold/no-action Human Investment Decision resolves a decision where appropriate and establishes zero synthetic Action Intents.

## AS-014 — Action Intent and partial external implementation

A Human Investment Decision establishes an Action Intent; authoritative external activity only partially implements it. Polaris preserves the difference between intended consequence and observed Portfolio State.

## AS-015 — Ambiguous reconciliation

Two plausible external activities could correspond to one Action Intent. Polaris keeps the association unresolved or requests lightweight confirmation rather than silently guessing.

## AS-016 — Unrelated external activity

Polaris observes external Portfolio activity with no supported originating Polaris relationship and preserves it as externally initiated rather than manufacturing a Recommendation, Human Investment Decision, or Action Intent.

## AS-017 — Historical reconstruction without hindsight

A later Decision Evaluation can reconstruct what Evidence was available to the original material judgment and separately use later Evidence without retroactively changing Judgment-Time Availability.

## AS-018 — Favorable Outcome from weak process

Polaris can preserve a favorable Outcome while forming a Decision Evaluation that identifies weak Evidence, reasoning, or implementation without treating profitability as proof of decision quality.

## AS-019 — Unfavorable Outcome from sound process

Polaris can preserve an unfavorable Outcome while forming a Decision Evaluation that does not automatically classify the earlier decision as poor.

## AS-020 — Lesson affects future Attention

A durable Lesson or prior Invalidation Condition influences later Attention or Decision Context without silently becoming Policy, Mandate, or a Formal Constraint.

## AS-021 — Operational reality overrides expectation

A Polaris expectation or Action Intent conflicts with authoritative external Portfolio State. Polaris preserves the conflict and uses the authoritative external state as operational reality.

## AS-022 — Legacy isolation

The current production/test/runtime path can be verified to have no import or execution dependency on `legacy/`.

---

# 20. Release acceptance gate

Polaris 0.2.0 is not complete merely because each requirement has a corresponding type, table, endpoint, service, workflow, or unit test.

The release is acceptable only when all of the following are true:

1. **Coherent lifecycle:** At least one supported investment-decision path can progress through the applicable lifecycle from Attention/Decision Need through Human Investment Decision and, where applicable, Action Intent/external reconciliation, Outcome, Decision Evaluation, and Lesson.
2. **Durable semantics:** The path preserves first-class Investment Decision identity and Durable Decision Memory independently of runtime execution identity.
3. **Historical fidelity:** Material Evidence, Judgment-Time Availability, judgments, authority acts, human decisions, and later evaluation remain reconstructable without hindsight rewriting.
4. **Authority integrity:** Polaris judgment, deterministic rules, human power-specific authority, and external operational authority remain non-collapsed.
5. **Portfolio grounding:** Recommendation formation incorporates actual Portfolio context, Projected Portfolio Consequences, and Portfolio Risk.
6. **Challenge:** Consequential Recommendation formation demonstrates meaningful challenge and material uncertainty rather than only preferred-view generation.
7. **Withholding:** The system can responsibly withhold or qualify a current Recommendation when required support is insufficient.
8. **Reality continuity:** Where an Action Intent exists in the supported path, authoritative external activity and resulting Portfolio State can be preserved and reconciled without execution authority; where no Action Intent exists, the lifecycle remains valid.
9. **Evaluation:** Outcome, Decision Evaluation, and Lesson remain separate concepts, and evaluation is not reduced to P&L.
10. **Supporting capability sufficiency:** Integration, interaction, configuration, reliability/observability, and security/operations are sufficient to make the supported path trustworthy, even if breadth is intentionally narrow.
11. **Greenfield isolation:** Current runtime and tests do not depend on `legacy/`.
12. **No architecture laundering:** Acceptance evidence demonstrates the product requirements themselves rather than treating the existence of an inherited legacy mechanism as proof that the requirement is satisfied.

## Approval consequence

Approval of this requirements specification authorizes **greenfield architecture work**, not implementation.

The next sequence after approval is:

```text
approved 0.2.0 requirements
        ↓
greenfield architecture
        ↓
required component boundaries
        ↓
selective donor inspection / salvage
        ↓
implementation lifecycle
```

Architecture MUST derive ownership and dependency direction from this specification and the frozen domain model before legacy components are evaluated for reuse.
