---
status: accepted
---

# Isolate unqualified PostgreSQL dependencies from the GIL-disabled runtime

## Context

ADR 0004 makes CPython 3.14 free-threading a first-class Polaris runtime capability while also requiring standard GIL-enabled CPython as a compatibility target. It already permits process isolation when a concrete dependency incompatibility earns the operational cost.

The R2 PostgreSQL adapter currently uses SQLAlchemy 2.0.54, greenlet 3.5.6, and asyncpg 0.31.0 from one locked dependency graph. Post-#323 Attention qualification tested that exact lock against both the #323 ticket baseline and the certified final #323 state.

The qualification established:

- the free-threaded CPython 3.14 build is genuine and the GIL remains disabled after importing SQLAlchemy and greenlet;
- the full PostgreSQL persistence suite can segfault nondeterministically under GIL-disabled execution on both the pre-#323 baseline and final #323 state;
- disabling thread-local bytecode is not a general correction: it passed 5/5 baseline trials but segfaulted 5/5 final trials;
- disabling SQLAlchemy runtime C extensions is not a reliable correction either: it passed 5/5 baseline trials but still segfaulted 1/5 final trials;
- every new or changed #323 persistence test passed 5/5 when exercised independently, and additional aggregate runs sometimes passed, so no deterministic #323 semantic/test path explains the fault;
- standard GIL-enabled CPython 3.14 passed five fresh-process full PostgreSQL suites on both refs: 46/46 tests on the baseline and 59/59 tests on the final state in every trial.

The evidence therefore establishes a current runtime/dependency incompatibility, not permission to weaken database concurrency semantics and not evidence that one #323 product transition is incorrect.

## Decision

Polaris keeps free-threaded CPython 3.14 as the repository default and keeps GIL-independent correctness as an architectural invariant.

The SQLAlchemy/greenlet-backed PostgreSQL adapter is temporarily qualified only for standard GIL-enabled CPython 3.14+ execution. A Polaris process with the GIL actually disabled must fail fast before constructing or using this adapter.

This is an **adapter/runtime compatibility boundary**, not a business or concurrency semantic:

- application/domain persistence contracts do not change;
- database atomicity, compare-and-set, idempotency, continuity, and graph/concurrency correctness must remain explicit and may not rely on GIL serialization;
- Polaris must not silently re-enable the GIL inside an otherwise free-threaded process;
- deployments that need a free-threaded application/runtime surface plus PostgreSQL persistence may isolate the persistence-owning role in a standard CPython process under the process-isolation allowance already established by ADR 0004.

The exception may be removed only after the then-current locked dependency/runtime combination is re-qualified. Requalification must include:

1. a genuine free-threaded CPython build with the GIL still disabled after importing the supported adapter/runtime surface;
2. the complete real PostgreSQL adapter contract/concurrency suite on the current persistence candidate;
3. repeated fresh-process execution sufficient to challenge the nondeterministic failure class that caused this exception; one successful suite run is not sufficient;
4. zero crashes/failures attributable to the runtime/dependency combination across that campaign;
5. continued standard-CPython qualification.

## Rationale

A silent or probabilistic segmentation fault is incompatible with durable business persistence. The currently proven safe target is standard CPython, which ADR 0004 already requires as a compatibility target.

Making the exception explicit and fail-fast is smaller and safer than:

- pretending a single green free-threaded run establishes support;
- relying on a TLBC or SQLAlchemy-C-extension workaround that the current final persistence surface has already falsified;
- weakening database concurrency behavior to reduce stress on greenlet;
- replacing the persistence technology stack without an independently justified design decision.

## Consequences

- the PostgreSQL adapter cannot currently execute inside a GIL-disabled Polaris process;
- standard CPython 3.14+ becomes the qualified runtime for the PostgreSQL-owning role until requalification succeeds;
- free-threaded Polaris development/runtime remains the default outside this adapter-scoped exception;
- PostgreSQL tests that certify adapter behavior must run on the standard compatibility target while the exception is active;
- a free-threaded attempt to construct the PostgreSQL adapter must produce an explicit configuration/runtime failure rather than entering the unsafe dependency path;
- future SQLAlchemy, greenlet, CPython, or adapter changes that may affect this boundary require explicit requalification before the exception is removed.
