---
name: coding-standards
description: "Apply the repository's Python coding standards whenever creating, modifying, refactoring, fixing, or reviewing Python source code. Enforce repository-configured Ruff and Mypy rules, modern typing, simple Pythonic design, minimum total complexity, root-cause fixes, sufficient verification, and advisory code-smell review. Use this skill for any task that writes or changes Python files."
---

# Coding Standards

Apply these standards whenever creating, modifying, refactoring, fixing, or reviewing Python source code.

The objective is correct, readable, maintainable Python with the **minimum total complexity necessary** to satisfy the actual requirement.

## Scope and Precedence

These rules apply to Python (`*.py`) source files, including Python test files.

Markdown documents, configuration files, generated assets, and other non-Python files are outside this skill's coding-style scope unless the current task explicitly requires changing them.

Before applying defaults from this skill:

1. Read applicable repository instructions such as `AGENTS.md`.
2. Inspect the repository's actual Python/tool configuration, especially `pyproject.toml`, `ruff.toml`, `mypy.ini`, or equivalent files.
3. Follow repository-configured Ruff, Mypy, Python-version, test, and formatting settings when they differ from defaults stated here.

Do not modify lint, formatting, typing, or test configuration merely to make an implementation pass unless changing that policy is itself part of the task.

A direct user requirement or documented repository rule overrides a design preference in this skill. Do not, however, remove required security, data-integrity, or trust-boundary protections in the name of simplicity.

---

## Required Workflow

Before writing code:

1. Understand the requested behavior.
2. Read the code directly involved.
3. Trace the real execution and data flow far enough to identify the correct change point.
4. Inspect relevant callers, models, helpers, tests, and established repository patterns.
5. Apply the Coding Ladder below.
6. Implement the smallest correct change.
7. Perform the subtraction review.
8. Run sufficient existing checks and focused tests.

Do not begin designing abstractions before understanding the affected code path.

---

## Code Style and Layout

Use Ruff and the repository's configured formatter/linter as the source of truth.

Unless repository configuration states otherwise:

* Use exactly 4 spaces per indentation level. Never use tabs.
* Use a maximum target line length of 88 characters.
* Prefer double quotes (`"`) unless single quotes avoid unnecessary escaping.
* Use trailing commas in multiline collections, calls, and signatures where supported by the formatter.
* Group imports into standard-library, third-party, and local/application sections.

Use Ruff's lint/import-sorting functionality when import sorting is configured. Do not assume the formatter itself sorts imports.

Do not manually reformat unrelated files or produce large formatting-only diffs outside the requested change.

---

## Typing and Type Safety

Use modern Python typing consistently with the repository's configured Python version and Mypy policy.

### Function Signatures

Public functions and methods must have explicit parameter and return types, including `-> None`.

Also type private functions when required by repository Mypy settings or when annotations materially improve correctness or understanding.

Do not add noisy annotations where the type checker already infers an obvious local type unless repository policy requires them.

```python
# Bad
def calculate_total(price, tax):
    return price + (price * tax)

# Good
def calculate_total(price: float, tax: float) -> float:
    return price + (price * tax)
```

### Optional Values

Represent nullable values explicitly.

For Python 3.10+ code, prefer union-pipe syntax:

```python
def find_user(user_id: int) -> User | None:
    ...
```

Do not claim a value is non-nullable when `None` is a valid domain outcome.

### Collections

Prefer built-in generic collection syntax:

```python
def process_data(items: list[str]) -> dict[str, int]:
    ...
```

Do not introduce legacy `typing.List`, `typing.Dict`, or similar aliases when the configured Python version supports built-in generics.

### `Any`

Avoid uncontrolled propagation of `Any`.

Use the most precise type that accurately describes the value, but do not manufacture unnecessary `Protocol`, generic, wrapper, or abstraction machinery merely to eliminate an `Any`.

`Any` is acceptable when genuinely required at a dynamic or untyped boundary. Contain it there and narrow or validate it before allowing it to spread into typed domain logic.

### Type Suppressions

Treat `# type: ignore` as a last resort.

When required, specify the exact error code:

```python
import untyped_library  # type: ignore[import-untyped]
```

Prefer correcting the type model or narrowing the value when that can be done cleanly.

Do not use `cast()` merely to silence a legitimate type error. A cast communicates information to the type checker; it does not validate anything at runtime.

---

## Pythonic Practices

### Naming

Use:

* `snake_case` for variables, functions, methods, modules, and packages.
* `PascalCase` for classes and exception classes.
* `UPPER_SNAKE_CASE` for module-level constants.
* Conventional concise names such as `T`, `T_co`, or descriptive equivalents for type variables where appropriate.

Choose names that communicate domain meaning. Do not encode implementation trivia into names.

### Exception Handling

Catch the narrowest exception that the current layer can meaningfully handle.

Do not:

* use bare `except:`;
* silently swallow exceptions;
* catch broad exceptions merely to continue execution;
* convert every exception into a generic fallback value;
* log an exception and then pretend the operation succeeded.

A deliberate `except Exception` is acceptable at a genuine top-level application, CLI, worker, task, or integration boundary when that layer owns failure reporting, translation, cleanup, or isolation.

When translating exceptions, preserve the original cause when useful:

```python
try:
    data = fetch_api()
except ConnectionError as err:
    raise DataSourceUnavailable("API connection failed") from err
```

Use `pass` in an exception handler only when intentionally ignoring that specific condition is correct and the reason is non-obvious enough to justify a comment.

### Resource Management

Give files, connections, streams, locks, transactions, and similar resources an explicit and deterministic lifecycle.

Prefer context managers when the resource supports them:

```python
with open("config.json", encoding="utf-8") as file:
    config = json.load(file)
```

Do not wrap long-lived application resources in artificial per-call context managers when their lifecycle is intentionally owned elsewhere.

---

## Efficient Coding

The best code is the code never written. The simplest complete solution is the right solution.

Optimize for **minimum total complexity**, not minimum line count.

Every new abstraction, type, configuration option, state representation, execution path, dependency, indirection layer, and file carries a maintenance cost.

### The Coding Ladder

After understanding the problem and affected code path, evaluate this ladder sequentially.

Stop at the first rung that cleanly satisfies the actual requirement.

1. **Does this need to exist at all?**

   If it serves only a speculative or hypothetical future requirement, do not implement it.

   Explain the omission in the response when relevant rather than leaving speculative code, TODOs, hooks, or scaffolding in the repository.

   Apply YAGNI.

2. **Does the codebase already solve it?**

   Search for existing helpers, utilities, types, models, services, and established patterns before introducing another implementation.

   Reimplementing behavior the repository already owns is code slop.

3. **Does Python already express it directly?**

   Prefer built-ins and clear standard-library primitives when they reduce custom code without obscuring intent.

   Do not replace an obvious loop or conditional with clever `itertools`, `functools`, comprehension, or expression machinery merely to save lines.

4. **Does an already-installed dependency naturally own the problem?**

   Reuse an existing dependency when it eliminates meaningful custom logic without introducing disproportionate coupling.

   Do not invoke a heavyweight or unrelated dependency merely because it can replace a few obvious native lines.

   Never add a new dependency solely to avoid writing a few lines of clear native Python.

5. **Can the requirement be solved directly?**

   Prefer straightforward control flow and existing domain objects over new helpers, wrappers, configuration, layers, or abstractions.

6. **Only then, write custom machinery.**

   Write only the custom code necessary to satisfy the current requirement.

The ladder is a behavioral reflex, not a research project.

If multiple approaches are equally correct, choose the one with fewer concepts and less machinery.

---

## Defeating Bloat and Structural Slop

### No Clever Compression

Efficient means simple and readable, not structurally crushed.

Avoid dense comprehensions, nested ternaries, excessive chaining, and other compression that hides control flow.

### No Unrequested Abstractions

Do not introduce:

* an interface with one implementation;
* a factory for one product;
* a base class for one subclass;
* a strategy object for one strategy;
* an adapter that merely renames another API;
* a configuration variable for a value that never varies.

An abstraction must solve a current structural problem, not advertise theoretical flexibility.

### No Premature Extensibility

Do not add hooks, callbacks, strategies, plugin points, generic frameworks, optional parameters, registries, extension interfaces, or configuration surfaces for hypothetical future consumers.

Implement requirements that exist now.

### No Pass-Through Layers

Do not create wrappers, services, managers, adapters, or helper functions that merely rename or forward an existing operation.

A layer must justify itself by doing at least one meaningful thing such as:

* enforcing a real architectural boundary;
* owning a domain responsibility;
* translating representations;
* applying policy or invariants;
* coordinating behavior that belongs together.

If it only delegates, remove it.

### One Concept, One Representation

Do not create another DTO, model, wrapper, context object, enum, state container, or intermediate representation when an existing type adequately represents the same concept.

Convert representations at genuine boundaries, not ceremonially between internal layers.

### No Scaffolding

Do not generate placeholder implementations, empty framework classes, unused extension points, speculative schemas, or skeleton files "for later."

Future requirements can introduce what they actually require.

### Replace, Don't Accumulate

When a change supersedes existing behavior and backward compatibility is not required, remove the obsolete implementation in the same change.

Remove related:

* dead branches;
* compatibility shims;
* stale aliases;
* stale comments;
* unused imports;
* obsolete configuration;
* unreachable code.

Do not leave both old and new architectures operating in parallel without a real compatibility requirement.

### Deletion Over Addition

Actively look for code made unnecessary by the requested change.

Prefer the implementation that leaves the resulting system simpler, even when that requires a slightly larger diff than adding another workaround.

The goal is not minimum diff size.

### Fewest Files Within Responsibility Boundaries

Keep related changes localized and avoid unnecessary file churn.

Do not create a new module for a trivial helper that naturally belongs in an existing cohesive module.

Do not combine genuinely unrelated responsibilities merely to reduce file count.

### Root-Cause Defect Fixing

A bug report usually identifies a symptom, not necessarily the defect location.

Before changing shared behavior:

1. identify the violated invariant;
2. inspect relevant callers;
3. determine which layer owns that invariant;
4. fix it at the narrowest authoritative point.

Prefer one root-cause correction over repeated guards or patches at downstream call sites.

Do not move a boundary-specific rule into a shared function merely to reduce line count.

### Validate at Boundaries, Trust Internals

Validate untrusted, external, serialized, or loosely typed data where it enters the trusted system.

Once an invariant has been established, do not repeatedly revalidate the same condition throughout internal code unless the domain model permits that invariant to become invalid again.

Do not scatter defensive checks for states that validated internal types cannot represent.

### No Narration Comments

Comments should explain non-obvious:

* constraints;
* invariants;
* tradeoffs;
* compatibility requirements;
* reasons.

Do not narrate mechanics already made obvious by readable code.

Do not leave comments documenting speculative features that were intentionally not implemented.

---

## When Not to Optimize for Less Code

Never simplify away required correctness.

Preserve all necessary:

1. **Trust boundaries** — validation, sanitization, authentication, authorization, and typing at public or untrusted boundaries.
2. **Data integrity** — transaction semantics, rollback behavior, idempotency, concurrency control, and failure handling necessary to prevent loss or corruption.
3. **Security and accessibility** — security controls, permission checks, audit requirements, and accessibility fundamentals.
4. **Domain invariants** — explicit rules necessary to keep the domain model valid.
5. **Protocol or external-contract requirements** — behavior required by APIs, schemas, persistence formats, interoperability, or backward compatibility.
6. **Explicit requirements** — architecture or capabilities explicitly required by the task or repository even when a leaner alternative exists.

Efficient code is minimal code that remains correct, robust, and understandable.

---

## Architectural Design Standards

Architectural principles are **decision heuristics, not abstraction quotas**.

Do not introduce machinery solely to demonstrate compliance with SOLID, DRY, dependency injection, design patterns, or another named principle.

When a direct implementation and an abstract implementation are both correct for current requirements, prefer the direct implementation.

### DRY: One Source of Truth

DRY applies primarily to duplicated **knowledge, policy, invariants, and business rules**, not merely similar-looking syntax.

Keep one authoritative representation for:

* domain rules;
* constants;
* configuration schemas;
* shared invariants;
* canonical data definitions.

Do not extract two superficially similar code fragments if they represent different concepts or are likely to evolve independently.

A small amount of obvious duplication is cheaper than the wrong abstraction.

Extract shared behavior when there is a genuine shared concept or demonstrated repetition, not merely because two blocks currently look alike.

### Single Responsibility Principle

A function, class, or module should own one coherent responsibility and have a clear reason to change.

Do not interpret SRP as "one tiny operation per function."

A cohesive function may perform several sequential steps when those steps together implement one domain operation and splitting them would only introduce indirection.

Split code when responsibilities genuinely differ, independently change, or obscure one another.

Avoid God Objects and modules that accumulate unrelated responsibilities.

### Open/Closed Principle

Do not pre-build extensibility.

Use polymorphism, protocols, strategies, registries, or other extension mechanisms only when the system has:

* multiple real implementations;
* an established extension boundary;
* repeated changes along the same variation axis; or
* an explicit requirement for pluggability.

For a small fixed set of behavior, a clear conditional or mapping is often simpler and preferable.

Do not replace a straightforward `if`, `match`, or lookup table with a class hierarchy merely to satisfy OCP.

### Interface Segregation and Dependency Inversion

Keep genuine interfaces narrow and cohesive.

Introduce an abstract boundary when it provides real value, such as:

* isolating infrastructure from domain logic;
* supporting multiple actual implementations;
* defining a stable external boundary;
* replacing an unstable dependency;
* enabling a necessary test seam that cannot be achieved cleanly otherwise.

Do not create a `Protocol`, ABC, adapter, or interface merely because a concrete class is referenced by another class.

Depending directly on a stable concrete implementation is acceptable when no meaningful abstraction boundary exists.

### Composition Over Inheritance

Prefer composition when combining independent capabilities.

Use inheritance when there is a genuine substitutable `is-a` relationship and the subtype satisfies the behavioral contract of its parent.

Do not create inheritance hierarchies merely for code reuse.

### Tell, Don't Ask

Prefer placing invariant-preserving behavior with the object or component that owns the relevant state.

Avoid repeatedly retrieving another object's internal state, making decisions externally, and then pushing mutations back into that object.

Treat this as an encapsulation heuristic, not a requirement to turn simple data structures into behavior-heavy objects or create pass-through methods.

---

## Testing and Verification

Test code should be as intentional and lean as production code.

### Minimum Sufficient New Tests

For non-trivial changed behavior, add the **smallest number of tests necessary to prove the behavior and its important failure boundary**.

Prefer extending an existing appropriate test module instead of creating new testing infrastructure.

A defect fix should ordinarily include a focused regression test that would have failed before the correction.

Do not generate:

* elaborate fixture hierarchies;
* unnecessary mock frameworks;
* broad per-function suites;
* redundant permutations;
* tests for implementation details;
* ceremonial tests for trivial mechanical changes.

Do not enforce an arbitrary "one test only" rule when materially different behavior requires more than one assertion or case.

### Test at the Correct Level

Choose the lowest-cost test level that proves the real contract.

Use unit tests for isolated behavior when appropriate.

Use integration tests when the behavior fundamentally depends on component interaction, persistence, external boundaries, framework behavior, or wiring.

Do not distort production architecture solely to make everything unit-testable.

### Pure Logic

Keep business rules deterministic and side-effect-free where that naturally matches the domain.

Do not split cohesive operations into unnecessary helper functions merely to manufacture pure functions.

### Dependency Injection

Inject external or replaceable dependencies when doing so creates a meaningful architectural boundary.

Typical candidates include database gateways, API clients, clocks, randomness sources, and external services.

Do not introduce dependency injection for trivial utilities, ordinary value objects, or module loggers merely to make mocking easy.

### Test Isolation

Tests must not depend on execution order or accidentally retain persistent state between cases.

Clean up state they create when the test environment does not already provide isolation.

Prefer real lightweight collaborators over mocks when doing so is simpler and more representative.

---

## Verification Workflow

Minimalism applies to **new test code**, not to whether existing quality checks should be run.

After modifying Python:

1. Run the repository-configured formatter or formatting check for the touched code.
2. Run the repository-configured Ruff lint checks relevant to the change.
3. Run the repository-configured Mypy/type checks relevant to the changed package or project.
4. Run the smallest focused existing test set that exercises the change.
5. Run broader tests when the change is cross-cutting, affects shared infrastructure, or repository instructions require them.

Prefer repository-provided commands from `Makefile`, task runners, package scripts, project documentation, or CI configuration over inventing parallel commands.

Do not add dependencies or new test infrastructure merely to perform verification.

When a check cannot be run, state exactly which check was not run and why.

When a failure appears unrelated or pre-existing, distinguish it from failures introduced by the current change rather than modifying unrelated code to make the suite green.

---

## Code-Smell Review

Use the following as this project's **selected Fowler-inspired code-smell heuristics**.

They are diagnostic signals, not automatic violations.

Three rules govern smell review:

* **Repository standards win.** If an established repository design intentionally uses a pattern that resembles a smell, do not report it solely because it matches the heuristic.
* **Smells are advisory by default.** Report them as possible design concerns unless the task explicitly asks for strict enforcement.
* **Skip tooling-enforced issues.** Do not duplicate findings that Ruff, Mypy, the formatter, or tests already reliably identify unless the tooling cannot reasonably detect the architectural problem.

Never apply a smell's textbook refactoring mechanically.

A refactoring is worthwhile only when it leaves the code clearer and simpler for the actual system.

### Mysterious Name

A function, variable, type, or module name does not communicate what it represents or does.

Prefer renaming it to reveal intent.

If no honest concise name exists, inspect whether the underlying responsibility is itself unclear.

### Duplicated Code

The same business rule, invariant, or meaningful logic is implemented independently in multiple places.

Consider centralizing the authoritative behavior.

Do not extract incidental syntactic similarity into an abstraction without a real shared concept.

### Feature Envy

A method depends substantially more on another object's internal data or behavior than on the state owned by its current object.

Consider whether the behavior belongs closer to the data it operates on.

Do not move it when doing so would violate a real boundary or responsibility.

### Data Clumps

The same coherent group of values repeatedly travels together through the system.

Consider introducing a type only when the group represents a real concept with enough repeated meaning to justify one.

Do not create a wrapper merely to reduce parameter count.

### Primitive Obsession

A primitive value carries meaningful domain semantics, invariants, or behavior that repeatedly has to be reconstructed by callers.

Consider a domain type when doing so centralizes real rules.

Do not create value-object classes for ordinary strings, numbers, or IDs that have no behavior or invariants worth encapsulating.

### Repeated Switches

The same conditional dispatch over the same variation axis appears repeatedly.

Consider centralizing the dispatch with a mapping, strategy, polymorphism, or another appropriate mechanism.

Do not introduce polymorphism for a single small conditional that has no demonstrated extension pressure.

### Shotgun Surgery

One conceptual change requires unrelated-looking edits across many locations.

Investigate whether ownership of the changed concept is fragmented.

Move responsibility only when a clearer authoritative boundary actually exists.

Do not gather unrelated code into a monolithic module merely to reduce file count.

### Divergent Change

One module changes repeatedly for multiple genuinely independent reasons.

Consider separating those responsibilities when they have distinct ownership or change lifecycles.

Do not split a cohesive module solely because it performs several steps of the same operation.

### Speculative Generality

An abstraction, parameter, hook, configuration option, or extension point exists for requirements that do not exist.

Delete or inline it unless a current requirement justifies it.

### Message Chains

A caller navigates deeply through another component's internal object graph.

Consider hiding navigation when the chain leaks ownership or implementation details.

Do not create a pass-through method solely to shorten syntax.

### Middle Man

A class, function, service, or method mostly delegates calls without adding policy, transformation, ownership, or boundary semantics.

Remove it and call the actual owner directly when no meaningful boundary would be lost.

### Refused Bequest

A subtype cannot honor significant portions of its parent's contract or must neutralize inherited behavior.

Reconsider whether the relationship is genuinely substitutable.

Prefer composition when inheritance does not represent a valid `is-a` relationship.

---

## Before Finishing: Subtract

After implementation and before finalizing, perform one deliberate subtraction pass.

Ask:

* Can any newly added function, class, file, abstraction, option, representation, branch, comment, dependency, wrapper, or test be removed without losing required behavior?
* Did the change duplicate something the codebase already owns?
* Did it introduce another representation of an existing concept?
* Is every new layer performing meaningful work?
* Did it leave obsolete or superseded code behind?
* Did defensive checks spread past the boundary where the invariant was already established?
* Did a named design principle cause more machinery than the current requirement needs?
* Can the same behavior be expressed with fewer concepts while remaining clear and correct?

If yes, simplify before finishing.

Do not use this pass as justification for unrelated cleanup or broad aesthetic refactoring.

The goal is not the smallest diff.

The goal is the **smallest correct resulting system**.
