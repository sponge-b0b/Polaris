# Python Coding Standards

This document establishes the official coding standards for this project. All code added to this repository must adhere to these guidelines to ensure consistency, readability, and type safety. 

Compliance is enforced automatically during CI/CD pipelines via **Ruff** and **Mypy**.

---

## 🎯 Scope
> ⚠️ **Scope Exclusion**: Markdown documents (`*.md`), configuration files, and documentation assets are exempt from these guidelines. These rules apply strictly to Python (`*.py`) source files.

---

## 🎨 Code Style & Layout (Ruff Compliance)

Our code style is governed by PEP 8 and enforced by Ruff's formatter.

* **Indentation**: Use exactly **4 spaces** per indentation level. Do not use tabs.
* **Line Length**: Max line length is **88 characters** (matching default Ruff/Black settings).
* **Quotes**: Prefer **double quotes (`"`)** for all strings unless single quotes avoid escaping.
* **Imports Ordering**: Group and alphabetize imports automatically using Ruff. 
  1. Standard library imports
  2. Third-party library imports
  3. Local/application imports
* **Trailing Commas**: Use trailing commas in multi-line lists, dictionaries, and function arguments to minimize git diffs.

---

## 🏷️ Typing & Type Hints (Mypy Compliance)

Every public function, method, and module component must be explicitly typed. 

### 1. Function Signatures
Always provide explicit types for all inputs and the return value, even if it returns `None`.
```python
# ❌ Bad
def calculate_total(price, tax):
    return price + (price * tax)

#  Good
def calculate_total(price: float, tax: float) -> float:
    return price + (price * tax)
```

### 2. Handling Optional Values
If a variable or argument can accept `None`, you must declare it using Python 3.10+ union pipes (`|`). Do not rely on implicit optional types.
```python
# ❌ Bad
def find_user(user_id: int) -> User: ...  # Will crash if user isn't found

#  Good
def find_user(user_id: int) -> User | None: ...
```

### 3. Collection Sizing
Use standard collection classes (`list`, `dict`, `set`) instead of the deprecated `typing.List` or `typing.Dict`.
```python
# ❌ Bad (Legacy)
from typing import List, Dict
def process_data(items: List[str]) -> Dict[str, int]: ...

#  Good (Modern Python 3.10+)
def process_data(items: list[str]) -> dict[str, int]: ...
```

### 4. Bypassing Type Checks
* Avoid using `Any` wherever possible. Opt for `Protocol` or generic TypeVars (`TypeVar`) instead.
* If a third-party package lacks types, use `# type: ignore` as a last resort, always specifying the exact error code:
  ```python
  import untyped_library  # type: ignore[import-untyped]
  ```

---

## 🐍 Pythonic Best Practices

### 1. Explicit variable naming
* **`snake_case`**: Variables, functions, methods, modules, and packages.
* **`PascalCase`**: Classes, Exceptions, and TypeVars.
* **`UPPER_SNAKE_CASE`**: Constants defined at the module level.

### 2. Error & Exception Handling
* Never catch a generic, naked `Exception`. Always target specific exceptions.
* Never use `pass` in an exception block without an explanatory comment.

```python
# ❌ Bad
try:
    data = fetch_api()
except Exception:
    pass

#  Good
try:
    data = fetch_api()
except ConnectionError as err:
    logger.error("API connection failed: %s", err)
    data = {}
```

### 3. Resource Management
Always use context managers (`with` statements) when opening files, database sockets, or network streams to guarantee proper cleanup.

```python
#  Good
with open("config.json", "r", encoding="utf-8") as file:
    config = json.load(file)
```

---

## ⚡ Efficient Coding

The best code is the code never written. The simplest complete solution is the right solution.

Optimize for **minimum total complexity**, not minimum line count. Every new abstraction, type, configuration option, state representation, execution path, dependency, indirection layer, and file carries a maintenance cost.

### The Coding Ladder

Before writing, generating, or modifying code, understand the task and trace the real code path it affects. Then evaluate this ladder sequentially and stop at the first rung that cleanly satisfies the requirement:

1. **Does this need to exist at all?** If it serves only a speculative or future requirement, do not implement it. State that decision in the response rather than leaving speculative code, TODOs, or scaffolding behind. (YAGNI)
2. **Does the codebase already solve it?** Search for existing helpers, utilities, types, models, and established patterns before adding another implementation. Reimplementing existing behavior is code slop.
3. **Does Python already express it directly?** Prefer built-ins and clear standard-library primitives when they reduce code without obscuring intent. Do not replace an obvious loop or conditional with clever library composition merely to save lines.
4. **Does an already-installed dependency naturally own the problem?** Use it when it eliminates meaningful custom logic without introducing disproportionate coupling. Never add a new dependency merely to avoid a few lines of clear native code.
5. **Can the requirement be solved directly?** Prefer straightforward, flat control flow and existing domain objects over helpers, wrappers, configuration, or abstractions.
6. **Only then:** Write the minimum custom code necessary to satisfy the actual requirement.

The ladder is a behavioral reflex, not a research project. It runs only after the problem and affected code path are understood. If two approaches satisfy the requirement equally well, choose the one with fewer concepts and less machinery.

### Defeating Bloat & Structural Slop

* **No Clever Compression**: Efficient means simple and readable, not structurally crushed. Avoid dense comprehensions, nested ternaries, excessive chaining, or other compression that hides control flow.
* **No Unrequested Abstractions**: Do not introduce an interface with one implementation, a factory for one product, a base class for one subclass, or a configuration variable for a value that never varies.
* **No Premature Extensibility**: Do not add hooks, callbacks, strategies, plugin points, generic frameworks, optional parameters, or extension surfaces for hypothetical future consumers.
* **No Pass-Through Layers**: Do not add wrappers, services, managers, adapters, or helper functions that merely rename or forward an existing operation. A layer must enforce a real boundary, transform behavior or data, or own a distinct responsibility.
* **One Concept, One Representation**: Do not create another DTO, model, wrapper, context object, enum, state container, or intermediate representation when an existing one adequately represents the same concept. Convert representations only at genuine boundaries.
* **No Scaffolding**: Do not generate boilerplate, placeholder implementations, unused extension points, or skeletons "for later." Later requirements can introduce what they actually need.
* **Replace, Don't Accumulate**: When new code supersedes existing code and backward compatibility is not explicitly required, remove the obsolete implementation, compatibility shim, dead branch, stale comment, unused import, and old configuration surface.
* **Deletion Over Addition**: Actively look for redundant or superseded code that the change makes unnecessary. Prefer the solution that leaves the system smaller and simpler after completion.
* **Fewest Files Within SRP Constraints**: Keep related changes localized and avoid unnecessary file churn. Do not combine genuinely unrelated responsibilities merely to reduce file count.
* **Root-Cause Defect Fixing**: A bug report usually names a symptom. Before altering shared behavior, identify its callers and determine where the violated invariant actually originates. Prefer one root-cause correction over repeated downstream guards or patches.
* **Validate at Boundaries, Trust Internals**: Validate untrusted, external, or loosely typed data where it enters the system. Once an invariant has been established, do not repeatedly defend against impossible states throughout internal code unless the domain model permits that state to change.
* **No Narration Comments**: Comments should explain non-obvious constraints, invariants, tradeoffs, or reasons. Do not restate what readable code already says.

When two library or implementation options require roughly the same amount of machinery, choose the one that correctly handles the domain's real edge cases. Efficient code is minimal code that is correct, not minimal code that is fragile.

### When NOT To Optimize for Less Code

Never simplify away, omit, or truncate:

1. **Trust Boundaries**: Required input validation, sanitization, authentication, authorization, and data typing at public or untrusted boundaries.
2. **Data Integrity**: Error handling, transaction semantics, rollback behavior, idempotency, or failure handling needed to prevent data loss or corruption.
3. **Security & Accessibility**: Required security controls, permission checks, audit behavior, and accessibility fundamentals.
4. **Domain Invariants**: Explicit logic required to keep the domain model valid.
5. **Explicit Directives**: If the user explicitly requires a particular architecture, pattern, or capability after a leaner alternative has been considered, implement the requested design without repeatedly arguing for simplification.

### Minimal Sufficient Verification

Efficient code without sufficient verification is unfinished.

For non-trivial behavior, add the **smallest amount of verification necessary to prove the changed behavior and its important failure boundary**.

* Prefer extending an existing test file over creating new test infrastructure.
* A defect fix should ordinarily include a focused regression test that would have failed before the fix.
* Do not generate elaborate fixture hierarchies, mock frameworks, broad per-function suites, or redundant permutations unless the behavior genuinely requires them.
* Test observable behavior and important invariants rather than implementation details.
* Trivial mechanical changes do not require ceremonial tests.

### Before Finishing: Subtract

Review the completed change once specifically for removal:

* Can any new function, class, file, abstraction, configuration option, state representation, branch, comment, or dependency be removed without losing required behavior?
* Did the change duplicate an existing concept or representation?
* Is every new layer performing meaningful work?
* Did the change leave superseded code or compatibility machinery behind?
* Can the same behavior be expressed with fewer concepts while remaining clear?

If so, simplify before finishing.

The goal is not the smallest diff. The goal is the **smallest correct resulting system**.

---

## 🏗️ Architectural & Clean Code Design Standards

To ensure long-term maintainability, scalability, and code health, all contributions must respect foundational software engineering principles. While the "Code Smells" section focuses on identifying issues, these principles define how we proactively design software.

### 1. The DRY Principle (Don't Repeat Yourself)
Every piece of knowledge or business logic must have a single, unambiguous, authoritative representation within the system.
* **No Copy-Pasting**: If the same logic shape is needed in multiple places, extract it into a shared utility function, class, or module.
* **Single Source of Truth**: Constants, configuration schemas, and data structures must be defined exactly once. Do not hardcode magic strings or numbers across files.

### 2. Single Responsibility Principle (SRP)
A class, module, or function should have one, and only one, reason to change. It must perform a single focused task.
* **Functions**: Keep functions short. A function should do one thing, do it well, and do it completely. If a function contains an "and" in its mental description (e.g., `parse_and_save_data`), it must be broken down into separate, composable components.
* **Classes**: A class must manage one core domain responsibility. Avoid "God Objects" or manager classes that orchestrate completely unrelated operations (e.g., mixing database access logic with raw HTTP response parsing).

### 3. Open/Closed Principle (OCP)
Software entities should be open for extension, but closed for modification. You should be able to introduce new behavior without rewriting existing, battle-tested source code.
* **Polymorphism Over Conditionals**: Avoid growing large `if-elif-else` or structural pattern matching blocks when adding support for a new data type or strategy. Instead, use abstract base classes (`abc.ABC`), structural protocols (`typing.Protocol`), or strategy patterns to allow pluggable, isolated extensions.

### 4. Interface Segregation & Dependency Inversion (ISP & DIP)
* **Keep Interfaces Lean**: High-level modules must not depend on bloated, monolithic interfaces they only partially use. Favor small, highly targeted protocols or interfaces over giant base classes.
* **Depend on Abstractions**: Depend on abstract interfaces rather than concrete, low-level implementations. This isolates core business logic from infrastructural details (like a specific database engine, file system, or external API client) and makes unit testing via mocking trivial.

### 5. YAGNI & KISS (Keep It Simple / You Ain't Gonna Need It)
* **No Speculative Engineering**: Do not build complex abstraction layers, plugins, or configuration parameters for hypothetical future requirements. Only write code that delivers immediate, specified value.
* **Prioritize Readability**: Code is read vastly more often than it is written. Prefer explicit, readable code paths over overly clever, compact, or deeply nested one-liners.

### 6. Composition Over Inheritance
Favor composition over class inheritance whenever sharing or altering functionality.
* Use **inheritance** (`is-a` relationship) strictly when a subclass can seamlessly substitute its parent class in all contexts without breaking behavior (Liskov Substitution Principle).
* Use **composition** (`has-a` relationship) by passing instances of other classes as components to build complex behavior. This keeps components loosely coupled and easier to test.

### 7. Tell, Don't Ask
Do not query an object about its internal state to make a decision, and then modify that object's state from the outside. Instead, command the target object to perform the action directly using its own data. This encapsulates data with the logic that operates on it.

---

## 🧪 Testing Standards & Testability

Code quality is directly tied to testability. Code that is difficult to unit test is fundamentally misarchitected.

* **Pure Functions**: Isolate business logic into deterministic, side-effect-free pure functions (same inputs always produce the exact same outputs) wherever possible.
* **Dependency Injection**: Pass external dependencies (database clients, loggers, network systems) into functions or class initializers rather than instantiating or importing them globally inside the logic scope.
* **Test Isolation**: Every unit test must be completely isolated, self-contained, independent of execution order, and free of persistent state modifications to external systems.

---

## 👃Code Smells

Below is a fixed set of Fowler code smells (_Refactoring_, ch.3). Three rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it
  endorses something the baseline would flag, suppress the smell.
- **Always Advisory by default.** Each smell is a labelled heuristic ("possible
  Feature Envy"), never a hard violation unless the user explicitly promotes it.
- **Skip tooling-enforced issues.** Do not report issues already enforced by the
  normal formatter, linter, type checker, or test suite unless the tool cannot
  reasonably catch the problem in this diff.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name** — a function, variable, or type whose name doesn't reveal
  what it does or holds. → rename it; if no honest name comes, the design's
  murky.
- **Duplicated Code** — the same logic shape appears in more than one hunk or
  file in the change. → extract the shared shape, call it from both.
- **Feature Envy** — a method that reaches into another object's data more than
  its own. → move the method onto the data it envies.
- **Data Clumps** — the same few fields or params keep travelling together (a
  type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession** — a primitive or string standing in for a domain concept
  that deserves its own type. → give the concept its own small type.
- **Repeated Switches** — the same `switch`/`if`-cascade on the same type recurs
  across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits across many
  files in the diff. → gather what changes together into one module.
- **Divergent Change** — one file or module is edited for several unrelated
  reasons. → split so each module changes for one reason.
- **Speculative Generality** — abstraction, parameters, or hooks added for needs
  the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation the caller shouldn't
  depend on. → hide the walk behind one method on the first object.
- **Middle Man** — a class or function that mostly just delegates onward. → cut
  it, call the real target direct.
- **Refused Bequest** — a subclass or implementer that ignores or overrides most
  of what it inherits. → drop the inheritance, use composition.
