---
name: to-specs
description: Project decision-complete planning into implementation Specs from exact Canonical Contract Ledger semantics while preserving Independent Specs and existing Spec identity.
disable-model-invocation: true
---

# To Specs

## Authoritative procedure composition

Before executing this skill, read in full:

1. `.agents/skills/to-specs/RETAINED_SKILL.md`
2. `.agents/skills/to-specs/PROCEDURE.md`
3. `.agents/skills/to-specs/CONTROL_PLANE.md`

`RETAINED_SKILL.md` preserves the previously authoritative entrypoint, including the
execution-feasibility, durable routing-defect, reconciliation, and Human Handoff gates.
All retained requirements remain mandatory. This file is authoritative only for the
additional machine-enforced cross-Spec ownership gate below and wins on conflict.

## Cross-Spec ownership gate

A feasibility manifest must not pass because an actor omitted a sibling provider from
`unit_analysis` or claimed local completion for work owned by another Spec. Every
current material `OBL-*` and every local `IMP-*` / `TEST-*` must have explicit ownership
classification before ticketing.

Immediately after the retained preflights, require:

```bash
python -m scripts.workflow_spec_ownership preflight \
  --repo . \
  --main-ref origin/main
```

Require `TO-SPECS OWNERSHIP PREFLIGHT: VALID`.

Use the same bounded `polaris.to-specs-execution-feasibility/v1` manifest. Every
topology-bearing Spec entry must add:

```json
{
  "ownership_analysis": {
    "material": [
      {
        "cell": "OBL-001",
        "disposition": "owned",
        "role": "<local executable role>",
        "reason": "<ownership reason>",
        "basis": ["<durable source>"]
      },
      {
        "cell": "OBL-002",
        "disposition": "consumed-boundary",
        "provider_spec": 357,
        "provider_cells": ["OBL-004"],
        "reason": "<provider ownership reason>",
        "basis": ["<durable source>"]
      }
    ],
    "planning": [
      {
        "cell": "IMP-001",
        "supports": ["OBL-001", "OBL-002"],
        "reason": "<local implementation/proof responsibility>",
        "basis": ["<durable source>"]
      }
    ]
  }
}
```

The material rows must cover every and only current `OBL-*` exactly once. `owned` requires
a local executable role. `consumed-boundary` requires another Spec in the same bounded set.
For a topology-bearing provider, `provider_cells` must name material provider cells whose
combined CCL refs cover the consumed cell. For an immutable topology-less
`legacy_completed` provider, `provider_cells` must be empty.

An OPEN consumed provider must be a native prerequisite of the consumer. The same provider
must also appear in the retained `unit_analysis.provider_requirements` for the execution
unit that owns the consumed cell. A downstream or unrelated provider is blocking.

The planning rows must cover every and only current `IMP-*` / `TEST-*` exactly once. Each
planning cell must support current local `OBL-*` cells and at least one supported obligation
must be `owned`. A planning cell may not exist solely to implement or certify a consumed
sibling capability. Supported cells must be in the same unit or a transitive upstream local
unit.

Every execution unit containing material obligations must contain at least one locally
`owned` material obligation. A consumed-boundary-only unit is not an executable vertical
material-outcome slice.

Before publication/readiness mutation and again immediately before frontier handoff, run:

```bash
python -m scripts.workflow_spec_ownership check \
  --manifest <execution-feasibility.json>
```

Require:

```text
TO-SPECS CROSS-SPEC OWNERSHIP: VALID
Unprotected consumed-boundary requirements: 0
Execution units without local material ownership: 0
```

A model-authored statement that ownership is clear is not a substitute. `$attention` must
inspect the exact ownership analysis together with the retained feasibility and
routing-defect evidence.

When this gate fails and accepted authority already fixes ownership, `$to-specs` owns the
in-place projection/topology repair. Preserve Spec identity, surviving stable cell IDs,
closed delivery history, native dependency truth, and live-WIP recovery handles. Do not
implement a downstream consumer inside an upstream provider Spec merely to close a ticket.
If ownership is genuinely unresolved, fail closed to the retained planning/semantic owner.

A `$to-tickets` Human Handoff is legal only when all retained receipts and these current
receipts pass on one state:

```text
TO-SPECS OWNERSHIP PREFLIGHT: VALID
TO-SPECS CROSS-SPEC OWNERSHIP: VALID
Unprotected consumed-boundary requirements: 0
Execution units without local material ownership: 0
```
