---
status: accepted
---

# Make asynchronous and multi-core execution first-class runtime capabilities

## Context

Polaris performs provider access, persistence, scheduling, durable follow-up, model calls, Decision Memory queries, analytical preparation, and later background/Attention work. Much of that surface is naturally asynchronous, while analytical and evaluation workloads can also benefit from CPU parallelism. Ordinary GIL-enabled CPython threads cannot provide unrestricted Python CPU parallelism, and code that is accidentally safe only because the GIL serializes execution would become incorrect under free-threaded Python.

Python 3.14 makes free-threaded CPython a supported runtime and provides mature async and subinterpreter options. Polaris is still early enough that concurrency safety can be established as an architectural invariant before shared mutable runtime state and a large native-extension dependency graph accumulate.

## Decision

Polaris adopts CPython 3.14 as its minimum supported Python baseline. The repository's default Python request is the free-threaded 3.14 variant; standard GIL-enabled CPython 3.14 remains a required compatibility target.

Asynchronous I/O and multi-core execution are first-class platform capabilities. Async is preferred at real I/O/waiting boundaries. CPU parallelism uses free-threaded threads when safe shared memory is useful, subinterpreters when interpreter isolation is preferable, and processes only when a concrete hard-isolation or dependency requirement earns them. Pure deterministic domain work remains synchronous unless it actually owns concurrency.

No Polaris correctness guarantee may depend on incidental GIL serialization. Shared mutable state must be protected by explicit synchronization, ownership, immutability, isolation, optimistic concurrency, or another race-safe invariant. Domain and application contracts remain independent of event-loop, thread, subinterpreter, and process choices.

Free-threaded qualification is executable. The supported free-threaded runtime must report a free-threaded CPython build and a disabled GIL after importing the supported Polaris runtime surface. A native dependency that re-enables the GIL fails that target instead of silently degrading it.

The next CPython minor release is qualified during its release-candidate window when practical and becomes the new baseline only after dependencies, tests, static analysis, and free-threaded qualification pass.

## Rationale

This gives Polaris efficient I/O concurrency and true shared-memory CPU parallelism without coupling domain semantics to a particular executor. Establishing GIL-independent correctness now is cheaper and safer than retrofitting thread safety after runtime state and integrations proliferate. Keeping standard CPython as a compatibility target also prevents the architecture from depending on free-threading-specific behavior for correctness.

## Consequences

- new I/O-heavy provider/client boundaries should be async unless an authoritative constraint requires otherwise;
- code must remain correct under genuinely parallel thread execution;
- runtime/native dependency changes must preserve or explicitly re-qualify the free-threaded target;
- concurrency mechanisms stay outside domain identity and application business contracts;
- `.python-version` requests free-threaded 3.14 for ordinary repository work, while explicit standard-CPython qualification remains required;
- Python baseline changes require synchronized `pyproject.toml`, `uv.lock`, tool target versions, and runtime qualification.
