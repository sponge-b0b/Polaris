# Workflow Hash Identity Contract

Polaris workflow hashes identify **byte representations**, not vague content. A 64-hex SHA-256 value is not self-describing and MUST NOT be compared across identity kinds merely because the shapes match.

## Canonical runtime

`scripts/workflow_hashing.py` owns SHA-256 construction for workflow runtime code. New workflow code MUST use a named representation helper from that module rather than calling `hashlib.sha256`, `hashlib.new("sha256", ...)`, or an equivalent ad-hoc implementation.

The shared representations are:

| Identity representation | Exact bytes hashed | Typical use |
| --- | --- | --- |
| exact bytes | input bytes unchanged | framed state, binary/domain-framed identities |
| exact UTF-8 text | `text.encode("utf-8")` unchanged | formal text receipts after the caller has explicitly chosen any stripping rule |
| raw file bytes | file bytes unchanged | serialized-file evidence only |
| canonical JSON | UTF-8 JSON with `ensure_ascii=False`, sorted keys, compact separators, **no trailing newline** | semantic JSON identities and Attention receipts |
| prefixed canonical JSON | exact caller-supplied prefix bytes followed by canonical JSON | domain-separated semantic identities |

Serialization is not semantic identity. In particular, a canonical JSON identity and the SHA-256 of a JSON file containing those bytes plus a newline are different hashes and MUST have different names at the call site.

## Durable identity rule

A persisted hash field MUST define all of the following:

1. the semantic identity being named;
2. the exact byte representation hashed;
3. any domain/prefix framing;
4. whether presentation prefixes such as `sha256:` are part of the stored value;
5. the schema/version that owns that representation.

Changing any of those rules changes the durable identity contract. It requires an explicit versioned migration; it is not a refactor.

## Current named identities

The current workflow contains these established identities:

- **Attention Result SHA-256** — exact UTF-8 bytes of the already-validated formal Attention block after the protocol's explicit outer `strip()`.
- **Attention Receipt Hash** — canonical JSON object bytes, no trailing newline. The on-disk receipt serialization may contain a trailing newline and therefore has a different raw-file SHA-256.
- **implement-ticket candidate state / protected donor candidate state** — an established framed byte stream over path, state/mode, and exact content SHA-256 values; the aggregate is SHA-256 of those framed bytes.
- **workflow handoff manifest SHA-256** — canonical JSON object bytes.
- **Spec/ticket/cell/topology contract hashes** — established domain-prefixed canonical JSON or exact UTF-8 body bytes as defined by `scripts/spec_contract.py`.
- **CCL proposal hash** — established canonical semantic JSON, stored with a `sha256:` presentation prefix.
- **review finding/remediation hashes** — established domain-prefixed canonical JSON.
- **workflow journal event hashes** — established canonical JSON; non-numbered subject tokens also use a truncated exact-UTF-8 URL digest.
- **ticket reslice recovery record SHA-256** — exact UTF-8 bytes of the managed recovery comment text.
- **routing/to-specs/ownership manifest hashes** — established JSON representations owned by their current schemas. Some predate the shared runtime and remain migration debt until moved without changing output bytes.

## Enforcement and migration debt

`tests/workflow/tooling/test_workflow_hashing_policy.py` inventories direct SHA-256 construction in workflow Python runtime. The only permanent direct SHA-256 implementation is `scripts/workflow_hashing.py`.

Older runtime files that have not yet been mechanically migrated are an **exact, shrinking allowlist** with expected direct-call counts. The test fails if:

- a new file constructs SHA-256 directly;
- an allowlisted file adds another direct SHA-256 call; or
- the inventory changes without an explicit test update.

The allowlist is migration debt, not permission to create new hash conventions. Move an existing identity to the shared runtime only when regression tests prove the durable digest remains bit-for-bit unchanged.
