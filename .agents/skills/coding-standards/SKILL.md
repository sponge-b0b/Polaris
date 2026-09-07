---
name: coding-standards
description: Apply the repository's Python coding standards whenever creating, modifying, refactoring, fixing, or reviewing Python source code. Enforce repository configuration, project-specific data-contract, scoring, precision, async and observability requirements, modern typing, simple Pythonic design, authoritative contract migrations, minimum total complexity, and root-cause fixes. Use for any task that writes or changes Python files.
---

# Coding Standards

Apply these standards whenever creating, modifying, refactoring, fixing, or reviewing Python source code.

Optimize for **correct, readable, maintainable Python with the minimum total complexity necessary**.

## Scope and Precedence

These rules apply to Python source and tests.

Before changing code:

1. Read applicable repository instructions such as `AGENTS.md`.
2. Inspect relevant code, callers, tests, and established patterns.
3. Inspect repository configuration such as `pyproject.toml`, `ruff.toml`, and `mypy.ini`.
4. Follow repository-configured Python, Ruff, Mypy, formatting, and testing rules over generic defaults in this skill.
5. Follow authoritative ADRs and `docs/current/` sources when a coding rule depends on project architecture or semantics.

Do not modify lint, formatting, typing, or test configuration merely to make code pass unless changing that policy is itself part of the task.

A direct user requirement or documented repository rule overrides a design preference here. Required correctness, security, data integrity, domain contracts, scoring semantics, and observability are not optional simplifications.

---

## Polaris Non-Negotiables

### Data-Contract Boundaries

When changing application-service, intelligence, runtime, persistence, or other data-contract boundaries, read:

```text
docs/current/domain-contracts-data-semantics-contract-semantics.md
```

Follow its canonical classification and boundary rules.

In particular:

* exchange stable internal semantics through typed objects;
* use mappings only at approved serialization, vendor, telemetry, persistence, report, artifact, runtime, or transport boundaries;
* do not hide stable business dimensions in generic metadata or undifferentiated mappings;
* promote stabilized semantics from extension mappings into explicit typed fields;
* distinguish fallback or unavailable values from canonical observations.

For AI-adjacent outputs, preserve the applicable `RiskAuthorityContract` requirements defined by the same authoritative source.

### Score Semantics and Precision

When creating, modifying, or reviewing scoring code, read:

```text
docs/current/domain-contracts-data-semantics-contract-semantics.md
```

That document owns canonical score semantics.

Preserve those semantics exactly.

New or changed scoring code must:

* identify the canonical score family explicitly;
* validate its defined range at the typed boundary;
* convert between score families only through an explicit formula.

Do not rely on naming, convention, or implicit arithmetic to establish score semantics.

Do not infer score direction, range, sign, normalization, interpretation, or meaning from field names or incidental implementation.

Do not introduce alternate score interpretations, inversions, normalization, or representations without an authoritative contract permitting them.

Do not use `round()` in:

* application logic;
* intelligence or analysis logic;
* regime logic;
* calibration logic;
* persistence logic.

Preserve full numerical precision internally.

Round only:

* in human-facing renderers; or
* where an explicit external contract requires fixed precision.

Changing canonical score semantics is a contract/architecture change, not a local coding decision.

### Typing and Internal Models

Type public functions and methods explicitly, including return types.

Type private interfaces when repository Mypy policy requires it or when doing so materially improves correctness.

Use modern built-in typing syntax supported by the configured Python version.

Represent nullable values honestly.

Contain `Any` at genuinely dynamic or untyped boundaries and narrow it before typed domain logic.

Treat `# type: ignore` as a last resort and specify the exact error code when required.

Do not use `cast()` merely to hide a legitimate type error.

Prefer:

```python
@dataclass(frozen=True, slots=True)
```

for immutable internal models when a dataclass is the appropriate representation.

Do not introduce another model merely to satisfy this preference when an existing type already owns the concept.

### Async Boundaries

Use established asynchronous provider and client interfaces consistently.

Do not introduce:

* synchronous alternatives to canonical async boundaries;
* sync/async compatibility branches;
* duplicate execution paths;

unless a real boundary requirement exists and is supported by the applicable architecture source.

Do not preserve an incorrect synchronous path merely for compatibility.

### Observability

Observability is required operational behavior, not an optional enhancement.

When creating or modifying an operational boundary, consult the applicable current observability and platform architecture documents.

Preserve established conventions for applicable:

* structured logs;
* trace spans;
* trace-context propagation;
* metrics;
* failure visibility.

Do not:

* create parallel telemetry systems;
* duplicate lifecycle emission paths;
* create competing instrumentation ownership;
* bypass canonical telemetry boundaries;
* consider operational behavior complete when required observability has been lost.

Extend the canonical observability path instead of creating local alternatives.

Pure helpers and internal calculations do not need ceremonial telemetry. Instrument the operational boundary that owns the behavior.

---

## Core Python Standards

Use repository-configured Ruff, formatting, and Mypy rules as the source of truth.

Prefer clear, idiomatic Python over cleverness.

### Naming

Use names that communicate domain meaning:

* `snake_case` for functions, variables, methods, modules, and packages;
* `PascalCase` for classes;
* `UPPER_SNAKE_CASE` for module constants.

Do not encode incidental implementation details into names.

### Exception Handling

Catch the narrowest exception the current layer can meaningfully handle.

Do not:

* use bare `except:`;
* silently swallow failures;
* catch broad exceptions merely to continue;
* turn failures into misleading success values;
* log an exception and then pretend the operation succeeded.

A deliberate `except Exception` is appropriate only at a genuine boundary that owns failure reporting, translation, cleanup, or isolation.

Preserve the original cause when translating exceptions where useful.

### Resources

Give files, connections, transactions, locks, streams, and similar resources deterministic ownership and lifecycle.

Use context managers where appropriate.

Do not impose per-call lifecycle management on long-lived resources intentionally owned elsewhere.

---

## Efficient Coding

The best code is the code never written.

Optimize for **minimum total complexity**, not minimum line count.

Every abstraction, type, option, representation, execution path, dependency, indirection layer, and file carries maintenance cost.

### The Coding Ladder

After understanding the real execution and data flow, evaluate these in order.

Stop at the first rung that cleanly satisfies the requirement.

1. **Does this need to exist at all?**

   If it serves only a speculative future requirement, do not implement it.

   Apply YAGNI. Do not leave speculative hooks, TODOs, extension points, or scaffolding behind.

2. **Does the codebase already solve it?**

   Search for existing helpers, types, services, models, and patterns before creating another implementation.

   Do not duplicate behavior the repository already owns.

3. **Does Python already express it directly?**

   Prefer clear built-ins and standard-library primitives.

   Do not replace obvious control flow with clever expressions merely to save lines.

4. **Does an installed dependency naturally own it?**

   Reuse an existing dependency when it eliminates meaningful custom logic without disproportionate coupling.

   Do not add a dependency merely to avoid a few clear native lines.

5. **Can the requirement be solved directly?**

   Prefer existing domain objects and straightforward control flow over new wrappers, helpers, configuration, or layers.

6. **Only then write custom machinery.**

   Write only what the current requirement actually needs.

If multiple solutions are equally correct, choose the one with fewer concepts and less machinery.

### Subtract Before Finishing

Before finalizing, remove anything newly introduced that is not required.

Ask:

* Did this duplicate something the codebase already owns?
* Did it create another representation of an existing concept?
* Is every new abstraction or layer performing meaningful work?
* Did obsolete behavior remain after being superseded?
* Does every input accepted by a changed internal contract still have real semantic effect?
* Did defensive validation spread beyond the boundary that owns it?
* Can the same behavior remain clear and correct with fewer concepts?

Simplify when the answer is yes.

Do not use subtraction as justification for unrelated cleanup.

---

## Structural Design Rules

### No Speculative Abstractions

Do not introduce an interface, factory, base class, strategy, adapter, registry, plugin point, hook, configuration option, or extension mechanism for hypothetical future consumers.

An abstraction must solve a current structural problem.

### No Pass-Through Layers

Do not create wrappers, services, managers, adapters, or helpers that merely rename or forward an existing operation.

A layer should perform meaningful work such as:

* owning a domain responsibility;
* enforcing a real boundary;
* translating representations;
* applying policy or invariants;
* coordinating behavior that belongs together.

If it only delegates, remove it.

### One Concept, One Representation

Do not introduce another DTO, model, wrapper, context object, enum, state container, or intermediate representation when an existing type already represents the concept adequately.

Convert representations at genuine boundaries.

### Authoritative Contract Changes and Compatibility

Internal source compatibility is **not** a default Polaris requirement.

Compatibility exists only when an explicit user requirement, accepted architecture, versioned migration contract, or genuine external/public compatibility obligation requires it. Existing internal callers, tests, or implementation history do not by themselves establish a compatibility requirement.

When ownership, an internal contract, an API, or an invariant changes:

1. make the authoritative layer correct first, even when downstream callers break;
2. update every affected caller, implementation, protocol, adapter, fake, fixture, test, configuration surface, registry/bootstrap path, and other consumer;
3. remove the superseded internal contract and representation in the same change.

Do not preserve obsolete internal behavior by:

* accepting and ignoring, discarding, overwriting, or neutralizing obsolete inputs;
* absorbing stale calls through `*args` or `**kwargs`;
* retaining stale aliases, compatibility shims, wrappers, flags, or no-op parameters;
* maintaining parallel old/new execution paths;
* falling back to behavior that the authoritative contract replaced.

If genuine compatibility is explicitly required, isolate it at the compatibility boundary, identify the authority requiring it, and keep the canonical internal contract free of compatibility residue.

If the correct implementation is blocked by unresolved architecture or an external requirement, surface the blocker. Do not substitute a hack, workaround, bypass, compromise design, or silent behavioral degradation.

### Root-Cause Fixes

A reported symptom is not necessarily the defect location.

Before fixing shared behavior:

1. identify the violated invariant;
2. inspect relevant callers;
3. identify the layer that owns the invariant;
4. fix the narrowest authoritative point.

Prefer one root-cause correction over repeated downstream guards.

### Validate at Boundaries

Validate untrusted, serialized, external, or loosely typed data where it enters the trusted system.

Once an invariant is established, trust it internally unless the domain permits it to become invalid again.

Do not scatter defensive checks for impossible internal states.

### Comments

Comments should explain non-obvious:

* constraints;
* invariants;
* tradeoffs;
* compatibility requirements;
* reasons.

Do not narrate mechanics already clear from the code.

---

## Architecture Heuristics

Named design principles are **heuristics, not abstraction quotas**.

Do not add machinery merely to demonstrate SOLID, DRY, dependency injection, or another design pattern.

### DRY

Centralize duplicated **knowledge, policy, invariants, and business rules**, not merely similar syntax.

A small amount of obvious syntactic duplication is cheaper than the wrong abstraction.

### Responsibility

A function, class, or module should own one coherent responsibility.

Do not interpret this as one tiny operation per function. Keep sequential steps together when they form one domain operation.

### Extensibility

Do not pre-build extension mechanisms.

Use polymorphism, protocols, strategies, or registries only when there are real implementations, an established extension boundary, repeated variation, or an explicit requirement.

### Interfaces and Dependency Injection

Introduce abstract boundaries when they provide real value, such as:

* isolating infrastructure from domain logic;
* supporting multiple actual implementations;
* establishing a stable external boundary;
* replacing an unstable dependency;
* creating a necessary test seam.

Depending directly on a stable concrete implementation is acceptable when no meaningful abstraction boundary exists.

Prefer composition over inheritance unless a genuine substitutable `is-a` relationship exists.

---

## Testing Expectations

Test behavior and contracts, not implementation details.

For non-trivial changed behavior, add the **smallest number of tests necessary** to prove:

* the required behavior; and
* its important failure boundary.

A defect fix should ordinarily include a focused regression test that would have failed before the fix.

Prefer existing test modules and infrastructure.

Avoid:

* elaborate fixture hierarchies;
* unnecessary mocks;
* redundant permutations;
* ceremonial tests;
* production abstractions created solely for unit-test convenience.

Use integration tests when the real contract depends on wiring, persistence, component interaction, framework behavior, or an external boundary.

Do not distort production architecture merely to make everything unit-testable.

For procedural testing workflow, use the applicable `$tdd`, `$verify-code`, or `$verify-spec` skill rather than duplicating those workflows here.

When scoring behavior changes, verification must cover canonical score semantics and precision.

When an operational boundary changes, verification must cover required observability through the established telemetry path.

---

## Code-Smell Review

Smells are diagnostic signals, not automatic violations.

Repository architecture and explicit standards take precedence.

Smells are **Advisory by default** unless a documented rule makes the condition a violation.

Do not duplicate issues that Ruff, Mypy, formatting, or tests already reliably detect.

Watch for:

* **Mysterious Name** — names conceal domain intent.
* **Duplicated Code** — the same knowledge or business rule has multiple owners.
* **Feature Envy** — behavior appears to belong with another component's state.
* **Data Clumps** — a repeated value group may represent a real domain concept.
* **Primitive Obsession** — primitives repeatedly reconstruct meaningful domain invariants.
* **Repeated Switches** — repeated dispatch may indicate fragmented ownership.
* **Shotgun Surgery** — one concept requires changes across many unrelated locations.
* **Divergent Change** — one module owns unrelated reasons to change.
* **Speculative Generality** — abstractions exist for requirements that do not.
* **Message Chains** — callers navigate another component's internal structure.
* **Middle Man** — a layer delegates without adding meaningful responsibility.
* **Refused Bequest** — inheritance does not satisfy true substitutability.

Never apply a textbook refactoring mechanically.

Refactor only when the result is simpler and more correct for the actual system.

---

## Required Correctness

Never simplify away required:

* trust-boundary validation;
* authentication or authorization;
* security and accessibility controls;
* transaction, rollback, concurrency, or idempotency behavior;
* domain invariants;
* external contracts;
* canonical data-contract semantics;
* canonical score semantics;
* numerical precision;
* observability;
* explicitly required architecture.

The goal is not the smallest diff or fewest lines.

The goal is the **smallest correct resulting system**.
