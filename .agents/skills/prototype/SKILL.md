---
name: prototype
description: Build minimal throwaway code to answer one concrete design question quickly, expose the relevant state or UI alternatives, and preserve only durable conclusions. Keeps prototype evidence separate from production implementation and Living Entity Wiki authority.
compatibility: product=codex product=claude-code system=git network=none
---

# Prototype

A prototype is **throwaway code that answers one question**.

The question determines the prototype's shape.

A prototype is not:

* production implementation;
* architecture authority;
* a speculative framework;
* a place to build reusable abstractions;
* proof that a design belongs in the final system.

Its purpose is:

```text
question
   ↓
smallest useful experiment
   ↓
observable evidence
   ↓
validated | invalidated | inconclusive
```

---

# 1. Identify the Question

Determine the single question the prototype is intended to answer.

Use:

* the user's request;
* surrounding implementation context;
* an existing issue/spec;
* the current architecture discussion.

If the question is genuinely unclear and resolving it would materially change the prototype, ask the user when appropriate.

If the surrounding task makes the intended branch clear, proceed without unnecessary clarification.

---

# 2. Choose the Prototype Branch

## Logic / State Prototype

For questions such as:

> Does this logic feel right?

> Does this state model behave correctly?

> Are these transitions understandable?

use the logic-prototype guidance in:

```text
LOGIC.md
```

Build the smallest interactive terminal program capable of exercising the difficult cases.

Favor scenarios that expose:

* state transitions;
* invalid transitions;
* branching behavior;
* temporal ordering;
* edge conditions;
* competing interpretations of the model.

---

## UI Prototype

For questions such as:

> What should this look like?

> Which interaction model communicates this best?

use:

```text
UI.md
```

Create several **meaningfully different** UI directions on one prototype route.

Make variants easy to switch between according to the project's existing routing conventions.

Do not create cosmetic variants that differ only in:

* spacing;
* colors;
* icon choices;
* typography.

The variants should explore different interaction or information-architecture ideas.

---

## Ambiguous Question

If no user clarification is available and the context clearly leans one way:

```text
backend/domain/state concern
→ logic prototype

page/interaction/visual concern
→ UI prototype
```

State the assumption clearly in the prototype.

Do not silently choose a prototype form that answers a different question.

---

# 3. Consult Existing Architectural Memory

Before building, inspect whether this experiment has effectively already been run or deliberately rejected.

If the Living Entity Wiki exists:

1. start with `wiki/index.md`;
2. route the affected area to the relevant entity;
3. read its Rejected Approaches;
4. inspect any applicable `Reconsider when:` condition.

This is a **read-only consult**.

Do not invoke `$wiki-sync` merely because a prototype is being considered.

---

## Existing Rejection Still Applies

If the exact approach, or a materially equivalent one, is already rejected and its reasoning still applies:

surface it before building.

Do not silently spend time reproducing an experiment whose durable conclusion is already known.

---

## Circumstances Changed

If:

* the rejection has a `Reconsider when:` condition that appears satisfied; or
* concrete circumstances have materially changed;

surface that context and explain why re-prototyping may now be useful.

Do not automatically erase or override the existing Rejected Approach.

---

## Unclear

If it is unclear whether the prior rejection applies, surface the ambiguity.

Do not manufacture certainty merely to continue with the prototype.

---

# Rules That Apply to Every Prototype

## 1. Throwaway From the Start

Make prototype status obvious from:

* filename;
* route;
* directory;
* comments where useful.

Examples:

```text
prototype_*.py
*_prototype.py
/prototype-*
```

Follow existing repository conventions where they exist.

Do not let experimental code look production-ready.

---

## 2. Keep It Near the Relevant Context

Place prototype code close enough to the real module/page that its purpose is obvious.

Do not invent a new repository-wide architecture merely to house prototypes.

For UI prototypes, follow the project's existing routing convention.

---

## 3. One Command to Run

The prototype must have one obvious invocation using the project's existing tooling.

Examples:

```text
uv run python <prototype>
pnpm <script>
bun <script>
```

Do not build a new runner or task framework merely for the experiment.

---

## 4. No Persistence by Default

Keep state in memory unless persistence is **the thing being tested**.

Do not introduce:

* PostgreSQL;
* Qdrant;
* Neo4j;
* production files;
* external services

merely to make the prototype resemble the real system.

If the question specifically concerns persistence, use an isolated disposable target such as:

* a scratch database;
* isolated schema;
* clearly named local prototype file.

Mark destructive scratch state clearly.

Never point experimental destructive operations at production or data-preserving environments.

---

## 5. Skip Production Polish

Do not add:

* comprehensive error handling;
* reusable abstractions;
* framework layers;
* extensive configuration;
* production observability;
* generalized extension points;
* full test suites.

Implement only what is needed to make the experiment trustworthy enough to answer its question.

"Throwaway" does not mean deliberately incorrect.

The experiment must still exercise the behavior being evaluated.

---

## 6. Surface the Relevant State

For logic prototypes, show the relevant state after every meaningful action.

For UI prototypes, make each variant's important state and behavior inspectable.

The user should be able to understand:

```text
input
→ transition
→ resulting state
```

without mentally reconstructing hidden internals.

---

## 7. Do Not Smuggle Production Architecture Into the Prototype

A prototype may deliberately simplify architecture.

Do not conclude that temporary prototype structure should become production structure merely because the experiment worked.

Examples:

```text
prototype uses one file
≠
production should use one file
```

```text
prototype skips DI
≠
production should bypass Dishka
```

```text
prototype uses in-memory state
≠
production persistence is unnecessary
```

The prototype validates the **question being tested**, not every incidental implementation choice used to test it.

---

# 4. Run the Experiment

Exercise the cases required to answer the question.

For logic/state prototypes, include the scenarios that are hardest to reason about on paper.

For UI prototypes, compare the intended alternatives directly.

Do not expand the experiment simply because additional questions become interesting.

Record new questions separately.

Keep the prototype focused on the original decision.

---

# 5. Determine the Verdict

At the end, classify the result as:

```text
validated
invalidated
inconclusive
```

Do not force a binary result when the experiment did not produce enough evidence.

---

## Validated

The prototype provided sufficient evidence that the tested idea is worth carrying forward.

This means:

> the tested design question received a positive answer.

It does **not** mean:

> production implementation is complete.

It also does not independently create Living Entity Wiki knowledge.

A successful implementation technique is not itself a wiki write trigger.

---

## Invalidated

The prototype produced concrete evidence that the tested approach should not be used under the tested conditions.

Capture:

* the question;
* the observed failure;
* why the result matters;
* relevant conditions.

Distinguish:

```text
experiment failed for architectural/domain reason
```

from:

```text
prototype code was buggy
```

Only the former establishes meaningful rejection evidence.

---

## Inconclusive

The prototype did not answer the question reliably.

Report:

* what was learned;
* why the evidence was insufficient;
* what unknown remains.

Do not turn an inconclusive experiment into either an accepted or rejected architectural conclusion.

---

# 6. Validated Prototype Lifecycle

If validated and the user wants the design implemented in production:

**stop treating the prototype as the implementation.**

Hand the validated direction into the normal implementation workflow.

Production implementation must independently follow applicable repository policy, including:

* `$wiki-sync` pre-change audit;
* `$coding-standards`;
* `$tdd` where appropriate;
* `$database-migrations` where applicable;
* `$verify-code`;
* post-change `$wiki-sync`.

The prototype's earlier read-only wiki consultation does not satisfy the production pre-change `$wiki-sync` audit.

---

## No Automatic Wiki Write for Validation

Do not add an entity entry merely because the prototype succeeded.

A validated approach becomes durable wiki knowledge only if the resulting workflow produces a qualifying outcome such as:

* a real architectural decision;
* an accepted ADR;
* a realized architectural invariant;
* resolution of an existing Open Question;
* entity topology change.

Let the owning lifecycle record that outcome.

Do not create a generic:

```text
Validated Approaches
```

section.

---

# 7. Invalidated Prototype Lifecycle

A failed experiment may contain exactly the kind of causal knowledge the Living Entity Wiki exists to preserve.

If the Living Entity Wiki exists and the experiment produced a **durable architectural rejection**, invoke `$wiki-sync`.

Use provenance:

```text
source: session experiment, undocumented
```

This provenance means:

* a real experiment occurred;
* the experiment produced concrete evidence;
* no authoritative document currently records the result.

Do not use:

```text
source: session decision, undocumented
```

for experimental evidence.

---

## Qualifying Rejection

Record the result only when a future agent could plausibly repeat the same failed approach without this memory.

The entry should preserve:

* the rejected approach;
* the causal reason it failed;
* the conditions under which it failed.

If the rejection depends on conditions that might later change, add:

```text
Reconsider when:
```

only when the condition is supported by the experiment or established by the owner.

Do not invent a reconsideration condition.

---

## Non-Qualifying Failure

Do not create a Rejected Approach for:

* syntax bugs;
* bad prototype implementation;
* missing local dependency;
* temporary environment failure;
* arbitrary preference;
* lack of time;
* "didn't like it";
* agent speculation unsupported by the experiment.

---

# 8. Architectural Decisions Discovered by the Prototype

Sometimes the experiment does more than answer an implementation question.

If the resulting conclusion satisfies `$to-adr-doc`'s ADR criteria, use `$to-adr-doc`.

Examples might include:

* selecting one difficult-to-reverse state model over another;
* establishing a durable architectural ownership decision;
* rejecting an architectural direction for a load-bearing reason.

Do not convert every prototype verdict into an ADR.

---

# 9. Domain Discoveries

If the prototype reveals that the domain vocabulary or meaning itself was wrong or ambiguous, use `$domain-modeling`.

Examples:

* two supposedly identical states are actually different domain concepts;
* one term represents multiple lifecycle stages;
* a transition reveals an unstated domain distinction.

Update `CONTEXT.md` only when domain semantics genuinely changed or crystallized.

Do not put prototype implementation details into the glossary.

---

# 10. Open Questions

If the prototype exposes a meaningful unresolved architectural question:

* preserve it through `$wiki-sync` when it qualifies under the normal Open Questions rules;
* use appropriate provenance.

For an unresolved concern surfaced by the agent during the experiment:

```text
source: agent-observed during session, unresolved
```

For a question explicitly raised by the owner:

```text
source: owner-raised session question, undocumented
```

Do not turn every interesting follow-up into durable wiki knowledge.

---

# 11. Prototype Branch and Preservation

Prototype code must not land on the main production branch as normal implementation.

How the code is preserved depends on the surrounding workflow.

---

## Inside a Managed Ticket / Spec Workflow

If another workflow owns the active branch, such as `$implement-ticket`:

* do not switch branches automatically;
* do not violate its Ticket branch guard;
* do not create a hidden branch transition with uncommitted work.

The parent workflow owns branch safety.

The prototype may remain temporary working-tree material until its verdict is known.

Before the parent workflow commits production work:

* remove throwaway prototype code unless explicit preservation was requested;
* or preserve it through a separately approved prototype-history mechanism that does not contaminate the ticket's production commit.

---

## Standalone Prototype

If the user wants the experiment preserved for future reference, use a clearly throwaway branch rather than committing prototype code to the main production history.

Before creating or switching branches:

* ensure doing so will not violate an active parent workflow;
* ensure the working tree can be handled safely;
* do not silently move unrelated uncommitted work.

If branch creation/switching is unsafe, report that instead of forcing it.

---

## Prototype Preservation Is Optional

Do not preserve throwaway code merely because it exists.

Often the useful durable artifact is the **verdict**, not the implementation used to discover it.

If the prototype itself has ongoing diagnostic value, preserve it deliberately.

Otherwise delete it after its knowledge has been captured.

---

# 12. Issue / Ticket Context

When the prototype is associated with an implementation issue, preserve a concise outcome there when appropriate:

```text
Question:
...

Verdict:
validated | invalidated | inconclusive

Evidence:
...

Prototype location/branch, if preserved:
...
```

Issue history may retain experimental context.

It does not replace authoritative ADRs or Living Entity Wiki knowledge when those are warranted.

---

# 13. Cleanup

Before considering the experiment complete, decide explicitly what survives.

Possible surviving artifacts:

```text
nothing
issue/ticket verdict
CONTEXT.md vocabulary change
ADR
Rejected Approach
Open Question
prototype branch
```

Do not allow prototype files to remain accidentally mixed into production code after the verdict is known.

---

# 14. Handoff

Report:

* question tested;
* prototype branch:

  * logic; or
  * UI;
* prototype path;
* command to run;
* scenarios/variants exercised;
* verdict:

  * validated;
  * invalidated;
  * inconclusive;
* evidence supporting the verdict;
* whether prototype code was removed or preserved;
* prototype branch/location if preserved;
* domain vocabulary changes via `$domain-modeling`;
* ADR activity via `$to-adr-doc`;
* Rejected Approach recorded via `$wiki-sync`;
* Open Question recorded via `$wiki-sync`;
* production implementation status.

Clearly distinguish:

```text
prototype validated
```

from:

```text
production implementation completed
```

---

# Out of Scope

`$prototype` does not:

* treat experimental code as production code;
* bypass the production `$wiki-sync` audit because a prototype was already reviewed;
* write successful experiments into the wiki merely because they succeeded;
* turn agent opinion into a Rejected Approach;
* use owner-decision provenance for experimental evidence;
* automatically change entity topology;
* implement production architecture as part of the verdict step;
* leave throwaway files in production history by accident;
* violate branch ownership of `$implement-ticket` or another parent workflow;
* add production-grade abstractions, observability, persistence, or error handling unless they are specifically what the experiment is testing.

Its job is to answer **one question with the smallest experiment capable of producing useful evidence**.
