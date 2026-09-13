---
name: verify-spec
description: Perform authorized Spec-wide integration verification and repairs, including applicable repository-wide invariant gates, then obtain fresh independent semantic certification before persisting a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Read `SKILL.base.md` in full before execution. The preserved procedure there remains normative except where this front-door hardening section explicitly supersedes it.

## Receipt and Contract-Handoff Integrity

This section is authoritative for contract identity, semantic-certifier binding, finalization, and receipt persistence.

Keep these three identities separate:

1. `SPEC_CONTRACT_HASH` — durable cross-run semantic/structural identity. It is reproduced only from deterministic V2 structural identity and never from human-readable `Source`, `Requirement`, `Reason`, evidence, or other variable prose.
2. `CONTRACT_HANDOFF_DIGEST` — SHA-256 of the exact ephemeral `$spec-contract` handoff bytes for one certification/finalization transaction. It is invocation-local only and MUST NOT be compared across independent builds or persisted as contract authority.
3. `Verification Hash` — checksum of one finalized verification record. Because that record contains human-readable evidence, this checksum may legitimately differ across independent valid verification runs. It is not cross-run contract identity.

When `$spec-contract` builds `CONTRACT_HANDOFF`, require both the deterministic V2 `contract_identity` rows embedded in that handoff and the returned `CONTRACT_HANDOFF_DIGEST`. Retain the exact handoff file and digest as one pair. Do not independently recreate, pretty-print, copy, merge, parse from an older receipt, or re-key the manifest/source-count/identity payload.

Pass the exact handoff and `CONTRACT_HANDOFF_DIGEST` to `$verify-spec-closure`. Require every consumable PASS or FAIL verdict to echo the exact same digest. Missing or mismatched digest makes the certification result invalid/incomplete.

Any repository mutation or other candidate mutation that invalidates the semantic candidate also invalidates the handoff/digest pair. Rebuild through `$spec-contract` and obtain fresh semantic certification.

### Finalization override

The base procedure's instruction to rerun `$spec-contract` after semantic PASS is superseded. After a valid PASS, finalization MUST consume the same exact handoff bytes and digest seen by the certifier. If either is lost or changed, rebuild and recertify before finalization.

Invoke only `finalize-parts` and supply:

```bash
python "$ARTIFACT_TOOL" finalize-parts \
  --contract-input "$CONTRACT_HANDOFF" \
  --contract-digest "$CONTRACT_HANDOFF_DIGEST" \
  --proofs-input "$PROOFS_INPUT" \
  --gates-input "$GATES_INPUT" \
  --mode <full|checkpoint> \
  --receipt-output "$RECEIPT_FILE" \
  [--prior-checkpoint <checkpoint>] \
  [--repair <repair>]... \
  [--inherited-finding <finding>]...
```

Direct `finalize` is not a valid lifecycle path.

The deterministic utility MUST, before writing a receipt:

- compare SHA-256 of the exact `--contract-input` bytes with `--contract-digest`;
- independently recompute V2 `SPEC_CONTRACT_HASH` from embedded deterministic `contract_identity` rows and require equality with the supplied contract hash;
- assemble the verification record without treating display prose as contract identity;
- render the manifest in a human-readable versioned Markdown-safe format;
- immediately parse that rendered manifest through the current `$review-spec` consumer and require exact `cell` / `source` / `requirement` round-trip equality.

If any check fails, do not write or persist a receipt.

Receipts remain deliberately human-readable. The renderer owns escaping/encoding. Callers MUST NOT pre-escape receipt fields or reconstruct display rows from a previous receipt. Existing valid legacy receipts remain readable by `$review-spec`; newly persisted receipts use the hardened versioned format.

After applying this override, execute the complete procedure in `SKILL.base.md`.
