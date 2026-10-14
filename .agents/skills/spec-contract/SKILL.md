---
name: spec-contract
description: Build or validate the deterministic Spec obligation manifest and classify repository change provenance without inferring semantic lifecycle ownership from Git history.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Spec Contract

This `SKILL.md` is the authoritative entry point for `$spec-contract`.

Before executing the skill, read the sibling `.agents/skills/spec-contract/PROCEDURE.md` completely. That file preserves the established procedure. Apply every rule in `PROCEDURE.md` except where the overrides below conflict; these overrides win.

The purpose of this overlay is narrow: **durable hashes must be mechanical and reproducible. Model-authored classification, mapping, explanatory prose, and other semantic analysis are validation evidence, never hash input.**

## Mechanical Durable Contract Identity

`SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH` are mechanical identities derived from the exact current GitHub Spec body bytes by `.agents/skills/spec-contract/scripts/extract_source_units.py`.

The extractor is the sole authority for both fields. A builder must consume:

```text
spec_body_hash
spec_contract_hash
source_units
```

from one extractor invocation over one exact issue-body snapshot. Never hand-compute, reconstruct, or reverse-engineer either durable hash from the Source Unit Inventory, manifest, prior Ticket Coverage Manifest, prior verification receipt, scratch files, or conversational state.

The contract hash algorithm is implemented by `spec_contract_hash_from_body_hash()` in that extractor and is exactly:

```text
SPEC_BODY_HASH = SHA256(exact UTF-8 Spec body bytes)
SPEC_CONTRACT_HASH = SHA256(b"POLARIS-SPEC-CONTRACT-V2\0" + bytes.fromhex(SPEC_BODY_HASH))
```

The domain separator and byte conversion above are literal. Do not substitute JSON serialization, display text, source-unit rows, manifest rows, newline joining, shell interpolation, or an equivalent-looking custom payload.

This field remains named `SPEC_CONTRACT_HASH` for durable-artifact compatibility, but it is a **contract-source identity**, not a digest of model-authored semantic interpretation.

### Never hash semantic analysis

The following remain mandatory semantic validation evidence but are explicitly excluded from `SPEC_CONTRACT_HASH`:

- source-unit `Classification`;
- source-unit `Manifest cells`;
- reverse source-unit mappings stored under `contract_identity.manifest`;
- `Source`, `Requirement`, `Reason`, and `Named surfaces` prose;
- source counts;
- ticket/decomposition routing;
- architecture/design routing;
- repository change provenance;
- verification/review proof text;
- any other model-authored or lifecycle-authored representation.

`contract_identity.source_units` and `contract_identity.manifest` remain in the existing build-handoff schema for **internal semantic consistency validation only**. Despite the historical key name, they do not participate in the durable hash. Independent valid builds may produce different represented-summary mappings or explanatory prose while retaining the same durable contract hash.

### Reproducibility falsifiers

Every build and validation path must satisfy:

```text
same exact Spec body bytes
    -> SAME SPEC_BODY_HASH
    -> SAME SPEC_CONTRACT_HASH

same exact Spec body bytes
+ different Source/Requirement/Reason wording
    -> SAME SPEC_CONTRACT_HASH

same exact Spec body bytes
+ different but individually valid normative-represented summary mappings
    -> SAME SPEC_CONTRACT_HASH

same exact Spec body bytes
+ different semantic classification/mapping that changes the actual manifest cell universe
    -> SAME SPEC_CONTRACT_HASH
    -> semantic contract validation FAILS separately

changed Spec body bytes
    -> DIFFERENT SPEC_BODY_HASH
    -> DIFFERENT SPEC_CONTRACT_HASH
```

If two runs over the same `SPEC_BODY_HASH` produce different `SPEC_CONTRACT_HASH` values, return:

```text
SPEC CONTRACT: INVALID
Reason: mechanical contract identity is non-deterministic
```

Do not reconcile the Ticket Coverage Manifest to whichever hash happened to be produced most recently.

## Semantic Contract Validation Remains Independent

Removing semantic analysis from the hash does **not** weaken contract validation.

The complete Source Unit Inventory, classifications, manifest mappings, source counts, and Manifest Integrity Gate in `PROCEDURE.md` remain mandatory. A build with unresolved classification or mapping is still invalid.

For build/verification/decomposition coherence, compare the actual semantic artifacts directly rather than using the hash as a proxy:

- current manifest Spec-cell ID set must equal the Ticket Coverage Manifest Spec-cell ID set;
- no current source-derived cell may be missing or extra;
- source counts and manifest integrity gates must pass where required by the owning workflow;
- `contract_identity.source_units` and `.manifest` must be internally self-consistent within the current build;
- a genuine current semantic manifest change requires its normal owning reconciliation even though the body-derived contract hash is not an interpretation fingerprint.

A disagreement only about which already-existing cells best explain a redundant `normative-represented` summary is not a durable identity change. It may be challenged for semantic completeness, but it must never force hash reconciliation by itself.

## Exact Source-Byte Safety Override

Where `PROCEDURE.md` says the extractor is the mechanical authority for `SPEC_BODY_HASH`, extend that rule to `SPEC_CONTRACT_HASH` as well.

The extractor output is therefore the sole mechanical authority for:

- `SPEC_BODY_HASH`;
- `SPEC_CONTRACT_HASH`;
- ordered `SU-*` source-unit boundaries;
- normalized source-unit text used for classification/display;
- every source-unit Text Hash.

The semantic caller still owns classification and source-unit-to-cell mapping. Those semantic outputs must never be fed back into either durable hash.

## Build Handoff Override

Keep the existing build-handoff JSON schema unchanged for compatibility.

`spec_body_hash` and `spec_contract_hash` must be copied exactly from the same extractor output used for that build.

`contract_identity.source_units` and `contract_identity.manifest` are current-build semantic-consistency evidence. They must still reconcile internally with the current displayed manifest, but they are not inputs to `SPEC_CONTRACT_HASH` and are not required to be byte-identical across independent valid builds.

`CONTRACT_HANDOFF_DIGEST` continues to bind exact handoff bytes only. It may change when semantic evidence or display prose changes even when `SPEC_CONTRACT_HASH` remains stable.

## Validate-Mode Override

Replace the hash-related portions of `PROCEDURE.md` Section 4 with this sequence:

1. take one exact current Spec-body snapshot through the mandatory extractor;
2. read both `SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH` from that extractor output;
3. require those durable hashes to equal the passing receipt/TCM identities as applicable;
4. independently rebuild/classify the complete current Source Unit Inventory;
5. independently rebuild the current semantic manifest and require all integrity gates to pass;
6. compare the actual current manifest cell universe and required persisted semantic artifacts directly with the receipt/TCM; do not infer semantic equality from hash equality;
7. permit different `normative-represented` explanatory mappings when each current mapping is complete and the actual manifest obligation universe is unchanged;
8. fail `STALE` or `INVALID` on genuine body, manifest-cell, source-count, unresolved-classification, baseline, branch, or HEAD/policy-anchor violations according to the existing procedure;
9. recompute change provenance fresh as already required.

Do not canonicalize Source Unit Inventory classification/mapping rows or manifest reverse mappings to recompute `SPEC_CONTRACT_HASH`. That historical algorithm is superseded.

## Required Consumer Behavior

Any deterministic consumer that validates a contract handoff must:

1. validate the handoff's source-unit/mapping evidence for internal consistency;
2. recompute `SPEC_CONTRACT_HASH` only from `spec_body_hash` using the extractor's shared helper;
3. compare TCM/receipt semantic cell sets directly where coherence matters;
4. never use semantic mapping differences as hash mismatch evidence.

The canonical `$verify-spec` artifact helper implements this rule. Other consumers must not reintroduce the superseded structural-hash algorithm.

## Execute Preserved Procedure

After applying the overrides above, execute all remaining rules, gates, return contracts, isolation requirements, provenance requirements, and fail-closed behavior from `PROCEDURE.md` unchanged.
