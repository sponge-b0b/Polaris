---
name: spec-contract
description: Build or validate the deterministic ticket/verification contract of one CCL-backed Spec without semantically reinterpreting Spec prose.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Contract

`$spec-contract` is a deterministic helper. It does **not** decide what the Spec means.

The Spec's material semantics were already frozen by exact CCL addresses in its
`spec-contract-ccl:v1` manifest. This helper converts that projection plus explicitly
identified private implementation, testing, and exclusion cells into one reproducible
contract universe for ticketing, verification, and review.

## Contract cells

A CCL-backed software Spec exposes only these contract-cell families:

* `OBL-*` — material semantic obligations, taken mechanically from
  `spec-contract-ccl:v1`; their semantic payload is the exact ordered CCL address set;
* `IMP-*` — private/mechanical implementation obligations from stable-ID bullets in
  `## Implementation Decisions`;
* `TEST-*` — explicit proof/test obligations from stable-ID bullets in
  `## Testing Decisions`;
* `EXC-*` — exclusions from stable-ID bullets in `## Out of Scope`.

Problem/Solution prose, User Stories, Architecture Impact explanation, Further Notes,
headings, provenance markers, and other narrative text are not contract cells.
Mandatory-sounding prose outside these four cell families does not create a hidden
implementation obligation. If material behavior is actually missing, the Spec must be
reconciled through `$to-specs` and CCL first.

Do not rebuild source-unit inventories, classify prose as normative/non-normative, invent
`NORM-*` cells, or infer architecture obligations from ADR/wiki/code prose.

## Deterministic builder

Use:

```bash
python -m scripts.spec_contract build <issue-json> <handoff-output>
python -m scripts.spec_contract validate <issue-json> <expected-handoff>
python -m scripts.spec_contract check-coverage <contract-json> <coverage-json>
```

The issue JSON must come from one exact tracker snapshot, for example:

```bash
gh issue view <spec> --json body > "$SPEC_ISSUE_JSON"
```

Before building, also require the same body to pass the CCL projection validator:

```bash
python -m scripts.ccl_spec check <spec-body-file> contracts/ccl/transactions
```

If the Spec lacks a valid CCL manifest or exact generated Canonical Contract Obligations
section, return `SPEC CONTRACT: INVALID`; for an active software Spec the owning repair
path is `$to-specs`, not prose reconstruction here.

## Identity

The helper returns two distinct hashes:

```text
SPEC_BODY_HASH
    SHA-256 of the exact current Spec body bytes.

SPEC_CONTRACT_HASH
    deterministic hash of the exact ordered contract-cell universe.
```

Narrative-only prose may change `SPEC_BODY_HASH` without changing
`SPEC_CONTRACT_HASH`.

Changing any of the following changes `SPEC_CONTRACT_HASH`:

* an `OBL-*` ID or its exact CCL address set;
* an `IMP-*`, `TEST-*`, or `EXC-*` ID;
* the exact text of an `IMP-*`, `TEST-*`, or `EXC-*` cell.

Every cell also carries its own deterministic `cell_hash`. Downstream reconciliation uses
`cell + cell_hash`; matching IDs alone never hide changed contract content.

## Build handoff

Build mode writes one compact JSON handoff containing at least:

```json
{
  "spec_body_hash": "...",
  "spec_contract_hash": "...",
  "source_counts": {
    "user_stories": 0,
    "implementation_decisions": 1,
    "testing_decisions": 1,
    "out_of_scope": 1,
    "other_normative": 2
  },
  "manifest": [
    {
      "cell": "OBL-001",
      "source": "Canonical Contract Obligations / OBL-001",
      "requirement": "Exact CCL assertions: <addresses>"
    }
  ],
  "cells": [
    {
      "cell": "OBL-001",
      "kind": "material-contract",
      "cell_hash": "...",
      "ccl": ["contract@1#assertion"]
    }
  ],
  "contract_identity": {
    "source_units": [["SU-0001", "<cell-hash>", "normative-new", ["OBL-001"]]],
    "manifest": [["OBL-001", ["SU-0001"]]]
  }
}
```

`manifest`, `source_counts`, and `contract_identity` remain compatibility projections for
existing verification/review consumers during migration. They are mechanically derived
from the exact cells and contain no semantic classification judgment.

The `cells` array is authoritative for new decomposition work.

A caller may add invocation metadata such as Spec issue, fixed baseline, branch, HEAD,
default branch/head, and handoff digest around this exact helper result. Those values do
not alter the contract-cell semantics.

## Change provenance

When a caller needs repository change provenance, the existing mechanical
`classify_ownership.py` helper remains available. Git provenance answers where changes
occurred; it does not add contract cells or semantic ownership.

## Build isolation

No independent semantic builder is required because construction is deterministic.
A caller that already uses a fresh builder context may continue to do so during
migration, but freshness is not semantic proof and must not cause another prose
interpretation pass.

For compatibility with callers that still record isolation evidence, a deterministic
build may truthfully report:

```text
Build isolation: PASS
Prior contract representations supplied or inspected: 0
Pre-existing scratch contract artifacts inspected: 0
Handoff path existed before build: no
```

provided those mechanical facts are true. They are transport/recovery evidence only.

## Coverage validation

For ordinary CCL-backed ticketing, `$to-tickets` supplies one coverage object:

```json
{
  "schema": "polaris.ticket-coverage/v2",
  "spec_contract_hash": "...",
  "routes": [
    {
      "cell": "OBL-001",
      "cell_hash": "...",
      "destination": "T1"
    }
  ],
  "exclusions": [
    {
      "cell": "EXC-001",
      "cell_hash": "..."
    }
  ]
}
```

`check-coverage` mechanically requires every non-exclusion cell exactly once, every
exclusion exactly once outside ticket routing, no unknown cells, and exact current cell
hashes.

It proves exhaustive routing identity. It does not judge whether a human-selected ticket
slice is aesthetically ideal.

## Return

Build mode returns:

```text
SPEC CONTRACT: VALID | INVALID
Spec Body Hash: <sha256>
Spec Contract Hash: <sha256>
Contract cells: <n>
Material CCL cells: <n>
Implementation cells: <n>
Testing cells: <n>
Exclusion cells: <n>
Semantic prose classification performed: 0
```

Any malformed/missing stable-ID section, duplicate cell, malformed CCL manifest, or
projection drift is `INVALID`.
