# Polaris Testing Guide

This guide is the current operational map for testing the greenfield Polaris platform.
It is intentionally lightweight and must evolve with the test suite.

## Authority

`AGENTS.md` owns mandatory agent testing policy, including the **Pytest Service
Preflight**, secret handling, locked `uv` execution, and broad-verification
authorization rules. This guide supplements that policy with the current test-suite
inventory and service/prerequisite map; it does not override `AGENTS.md`, Specs,
accepted architecture, or an owning verification skill.

`legacy/v0_1/docs/process/testing-guide.md` is historical donor material only. Do not
use its test paths, services, environment variables, or commands as current Polaris
authority unless they are deliberately re-established in the greenfield platform.

When this guide and current tests/fixtures disagree about a prerequisite, inspect the
selected tests and fixtures and treat the discrepancy as documentation drift. Do not
use a stale guide entry to bypass the `AGENTS.md` preflight.

## Current test surface

The greenfield suite is currently small and infrastructure-free.

| Scope | Purpose | External services |
| --- | --- | --- |
| `tests/domain/decisions/` | Investment Decision domain behavior and invariants | None |
| `tests/test_architecture_guard.py` | Repository architecture invariants | None |
| `tests/test_architecture_guard_identity_aliases.py` | Identity-alias architecture invariants | None |
| `tests/test_architecture_guard_legacy_loaders.py` | Greenfield/legacy-boundary invariants | None |

No current greenfield pytest scope requires PostgreSQL, Qdrant, Neo4j, a model
provider, or another external service. This statement is an inventory fact, not a
permanent architectural constraint.

The owning workflow determines the smallest complete test scope for a change. Do not
run the entire suite merely because this guide lists it, and do not omit a directly
affected scope merely because it is not listed as a routine command here.

## Standard commands

Use the committed environment for project-owned Python tooling:

```bash
uv run --locked pytest -q <selected-test-scope>
```

When the owning workflow requires `POLARIS_BROAD_VERIFY_AUTHORIZED`, set it only on
that individual command with the workflow-specific value required by the owner.
Never export it globally.

Current focused Decision-domain verification is:

```bash
uv run --locked pytest -q tests/domain/decisions/
```

The repository-wide architecture suite is owned by `$verify-architecture`. When that
skill is applicable, follow its current contract rather than reconstructing its suite
from this guide.

Coverage configuration is owned by `pyproject.toml`. When coverage is required by the
active workflow, use the current project configuration rather than copying a threshold
into another command or process document:

```bash
uv run --locked pytest --cov <selected-test-scope>
```

## Service preflight

Before every pytest invocation, follow the **Pytest Service Preflight** in
`AGENTS.md` for the exact selected scope. In particular:

1. inspect the selected tests, active root configuration, and fixtures;
2. classify the complete selected scope as service-free or service-backed using the
   union of its prerequisites;
3. for service-backed scopes, identify required configuration without exposing
   secrets and verify each required service is ready before pytest starts;
4. do not use a pytest failure, timeout, connection exception, or skip as a readiness
   probe;
5. if required prerequisites cannot be established safely, leave verification
   unresolved rather than launching the tests.

This guide should make step 2 cheaper by recording stable service mappings as they
become part of current Polaris. The selected tests and fixtures remain necessary
boundary evidence because service requirements can change with the code.

## How this guide should grow

Add operational detail only when the greenfield platform actually introduces the
corresponding test boundary. Useful future sections include:

- unit, integration, database/migration, end-to-end, property, and evaluation suites;
- PostgreSQL and projection-store integration tests;
- model/provider and evaluation tests, including explicit live/non-live separation;
- observability and telemetry integration tests;
- API, CLI, MCP, or other interface contract tests;
- deterministic replay/backtesting or simulation tests;
- CI-only or release-only verification gates.

For each service-backed test family, add the smallest stable operational record that
lets a developer or verification workflow prepare it safely:

```text
Test scope: <path/marker/stable family>
Service(s): <required external services>
Required configuration: <variable/config names, never secret values>
Readiness evidence: <health/status/application probe appropriate to the contract>
Normal command: <locked project command>
Notes: <live opt-in, isolation, cleanup, or CI-specific behavior>
```

Do not add speculative service matrices, endpoints, environment variables, or test
categories before the greenfield implementation establishes them. Prefer updating
this guide in the same change that introduces or materially changes a stable test
family's external prerequisites.

## Maintenance invariant

Treat this file as an operational index, not a second testing-policy source of truth.
It should answer two questions efficiently:

1. **Which current test scope proves the behavior I need to verify?**
2. **What must be ready before that scope can run safely?**

If Polaris matures to the point where those answers require a larger matrix, expand
this guide incrementally. Keep mandatory cross-repository testing policy in
`AGENTS.md` and keep subsystem-specific semantic acceptance criteria in their owning
Specs, tests, and verification skills.