---
name: spec-contract
description: Build or validate the deterministic Spec obligation manifest and classify repository change provenance without inferring semantic lifecycle ownership from Git history.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Contract

Read `SKILL.base.md` in full before execution. The preserved procedure there remains normative except where this front-door hardening section explicitly supersedes it.

## Receipt Contract Handoff Integrity

This section is authoritative for the finalizer-facing build handoff.

Keep the existing V2 `SPEC_CONTRACT_HASH` semantics unchanged: it is durable cross-run identity derived only from the exact Spec body plus deterministic Source Unit identity/classification and source-unit-to-cell mapping. Human-readable `Source`, `Requirement`, `Reason`, `Named surfaces`, or other explanatory/display prose MUST NOT participate in `SPEC_CONTRACT_HASH`.

In `build` mode, when `handoff-output` is requested, write the existing finalizer-facing fields plus exactly one additional object:

```json
"contract_identity": {
  "source_units": [
    ["SU-0001", "<text sha256>", "normative-new", ["US-1"]]
  ],
  "manifest": [
    ["US-1", ["SU-0001"]]
  ]
}
```

`contract_identity.source_units` is the exact ordered V2 identity projection `[Source Unit, Text Hash, Classification, Manifest cells]` already used to compute `SPEC_CONTRACT_HASH`. `contract_identity.manifest` is the exact ordered V2 identity projection `[Cell, Source unit IDs]` already used to compute that same hash. These rows contain no model-authored display prose and MUST NOT be independently recreated for the handoff.

Serialize the handoff compactly and atomically exactly as the base procedure requires. After the atomic replace, compute SHA-256 over the exact handoff file bytes and return:

```text
CONTRACT_HANDOFF_DIGEST: <sha256>
```

immediately after `Spec Contract Hash` in the helper result.

`CONTRACT_HANDOFF_DIGEST` is invocation-local transport binding only. It is not semantic contract identity, is not persisted as tracker authority, and MUST NOT be compared across independent `$spec-contract` builds. Two valid independent builds may have the same `SPEC_CONTRACT_HASH` and different handoff digests because their human-readable display prose may legitimately differ.

The caller must retain the exact handoff file and returned digest as one inseparable pair. If either is lost, rebuild through `$spec-contract`. Never reconstruct the handoff or digest from a prior receipt, hand-parsed Spec body, conversational state, or another representation.

After applying this override, execute the complete procedure in `SKILL.base.md`.
