---
name: spec-contract
description: Build or validate the deterministic contract of one CCL-backed Spec without semantically reinterpreting Spec prose.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Contract

`$spec-contract` is a deterministic helper. It does **not** decide what a Spec means.

The Spec's material semantics are already frozen by exact CCL addresses in its
`spec-contract-ccl:v1` manifest. This helper converts that projection plus explicitly
identified private implementation, testing, and exclusion cells into one reproducible
contract universe for ticketing, implementation, verification, and review.

## Contract cells

A CCL-backed software Spec exposes only:

* `OBL-*` — material semantic obligations from `spec-contract-ccl:v1`; semantic payload is
  the exact ordered CCL address set;
* `IMP-*` — private/mechanical implementation obligations from stable-ID bullets in
  `## Implementation Decisions`;
* `TEST-*` — proof/test obligations from stable-ID bullets in `## Testing Decisions`;
* `EXC-*` — exclusions from stable-ID bullets in `## Out of Scope`.

Narrative sections are human context and never create hidden cells. If material behavior is
missing, route the Spec back to `$to-specs` / semantic authority instead of interpreting
prose here.

Do not build Source Unit inventories, classify prose as normative/non-normative, invent
`NORM-*`, or infer architecture obligations from ADR/wiki/code prose.

## Deterministic builder

Use:

```bash
python -m scripts.ccl_spec check <spec-body-file> contracts/ccl/transactions
python -m scripts.spec_contract build <issue-json> <contract-output>
python -m scripts.spec_contract validate <issue-json> <expected-contract>
python -m scripts.spec_contract check-coverage <contract-json> <coverage-json>
```

The canonical result schema is:

```json
{
  "schema": "polaris.spec-contract/v1",
  "spec_body_hash": "...",
  "spec_contract_hash": "...",
  "cells": [
    {
      "cell": "OBL-001",
      "kind": "material-contract",
      "cell_hash": "...",
      "ccl": ["contract@1#assertion"]
    }
  ]
}
```

There is no secondary source-unit, normative-classification, or compatibility projection.
The `cells` array is the complete contract universe.

## Identity

`SPEC_BODY_HASH` hashes exact body bytes.

`SPEC_CONTRACT_HASH` hashes the exact ordered contract-cell identity. Narrative-only prose
may change the body hash without changing the contract hash.

Every cell carries its own deterministic `cell_hash`. Downstream reconciliation uses
`cell + cell_hash`; matching IDs alone never hide changed contract content.

Changing any `OBL-*` CCL address set or the exact content of an `IMP-*`, `TEST-*`, or
`EXC-*` cell changes its cell hash and therefore the Spec Contract Hash.

## Coverage validation

For ordinary ticketing, `$to-tickets` supplies exactly one:

```json
{
  "schema": "polaris.ticket-coverage/v2",
  "spec_contract_hash": "...",
  "routes": [
    {"cell": "OBL-001", "cell_hash": "...", "destination": "T1"}
  ],
  "exclusions": [
    {"cell": "EXC-001", "cell_hash": "..."}
  ]
}
```

`check-coverage` requires every non-exclusion cell exactly once, every exclusion exactly
once outside ticket routing, no unknown cells, and exact current hashes.

## Ticket contract

For an ordinary ticket use:

```bash
python -m scripts.spec_contract build-ticket \
  <contract.json> <coverage.json> "#<ticket>" <ticket-body> <output>
```

The result is `polaris.ticket-contract/v1`: exact assigned executable cells plus every
parent exclusion as a guardrail and one deterministic Ticket Contract Hash.

## Return

```text
SPEC CONTRACT: VALID | INVALID
Spec Body Hash: <sha256>
Spec Contract Hash: <sha256>
Contract cells: <n>
Semantic prose classification performed: 0
```

Malformed/missing stable-ID sections, duplicate cells, malformed CCL projection, coverage
drift, or ticket projection drift are deterministic failures. They are not permission to
reconstruct intended meaning from prose.
