---
name: verify-spec-closure
description: Independently certify or reject the semantic Spec contract at the exact stable HEAD prepared by `$verify-spec`. This is a fresh non-mutating leaf verifier; `$verify-spec` retains orchestration, gates, repairs, and receipt persistence.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Spec Closure

Read `SKILL.base.md` in full before execution. The preserved procedure there remains normative except where this front-door hardening section explicitly supersedes it.

## Exact Contract-Handoff Binding

This section is authoritative for verifier invocation and verdict binding.

Receive the immutable exact `$spec-contract` handoff plus its `CONTRACT_HANDOFF_DIGEST` from `$verify-spec`. The handoff includes deterministic V2 structural identity rows used to reproduce `SPEC_CONTRACT_HASH` and human-readable manifest projection used for semantic certification.

`SPEC_CONTRACT_HASH` remains durable cross-run structural identity. `CONTRACT_HANDOFF_DIGEST` is invocation-local transport binding only: it proves which exact handoff bytes this verifier saw, is not semantic identity, is not tracker authority, and MUST NOT be compared across independent `$spec-contract` builds.

Require a syntactically valid SHA-256 digest at dispatch. Echo it unchanged in every consumable PASS or FAIL verdict immediately after `Spec contract hash`:

```text
Contract handoff digest: <sha256>
```

A missing, changed, or contradictory digest makes the certification result invalid/incomplete; do not emit a consumable PASS or FAIL.

Certification binding/reuse therefore applies to the exact handoff bytes as well as the baseline, Spec body/contract hashes, branch, HEAD, and authoritative mutable inputs. A fresh independent handoff may reproduce the same `SPEC_CONTRACT_HASH` while having a different digest; that is not contract drift, but it requires a fresh certification transaction for those new bytes.

After applying this override, execute the complete procedure in `SKILL.base.md`.
