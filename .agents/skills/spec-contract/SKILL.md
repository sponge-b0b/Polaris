---
name: spec-contract
description: Build or validate the deterministic Spec obligation manifest and distinguish Spec-owned changes from inherited integration history for Spec verification and review.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Spec Contract

`$spec-contract` is an internal, non-lifecycle helper for `$verify-spec` and `$review-spec`.

It owns two shared facts that must not be independently reinvented by those callers:

1. the complete **Spec Contract Manifest** of normative obligations;
2. the **Spec Change Ownership** classification separating fixed-baseline integration history from work owned by the current Spec.

It does not verify implementation, review implementation, create findings, mutate tracker state, edit repository files, or decide remediation.

## Session Independence

Assume no prior conversational or agent-session state.

Recover all inputs from the explicit invocation, repository, and durable tracker state. Do not use remembered requirement counts, prior reviewer conclusions, or Root Blocker history to construct the contract.

## Invocation

The parent supplies:

* originating Spec issue/URL;
* fixed `BASELINE_COMMIT`;
* current Spec branch;
* current `HEAD`;
* mode: `build` or `validate`;
* in `validate` mode, the persisted manifest/counts/hash from the current passing **Spec Verification Receipt**.

The helper may refresh the remote-tracking ref for the repository default branch. It must not switch branches, change the index/worktree, edit tracked files, commit, push, or mutate tracker state.

## 1. Pin the Spec Source

Read the current Spec body from GitHub and capture:

```bash
SPEC_BODY_HASH=$(
  gh issue view <spec_issue_number> --json body --jq .body \
    | sha256sum | awk '{print $1}'
)
```

Resolve the repository default branch:

```bash
DEFAULT_BRANCH=$(
  gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
)

git fetch --quiet origin "$DEFAULT_BRANCH"
DEFAULT_REF="origin/$DEFAULT_BRANCH"
```

Require the supplied branch, `BASELINE_COMMIT`, and `HEAD` to resolve.

If the Spec body is missing, malformed, or cannot be read completely, return:

```text
SPEC CONTRACT: INVALID
Reason: <missing/unreadable source>
```

## 2. Build the Spec Contract Manifest

Construct the manifest only from the current originating Spec.

Use stable source-derived IDs:

* numbered User Stories → `US-<number>`;
* Implementation Decision bullets → `ID-<number>`;
* Testing Decision bullets → `TD-<number>`;
* Out of Scope bullets → `OOS-<number>`;
* materially unique normative requirements elsewhere → `NORM-<number>`.

If one source item contains materially independent obligations that must be proven separately, use stable suffixes such as `US-22.a`, `US-22.b`. The parent source item remains mapped and counts once in source-item integrity.

Do not create a `NORM-*` cell when the same normative obligation is already represented by a User Story, Implementation Decision, Testing Decision, or Out of Scope cell.

A manifest row contains:

```text
Cell: <stable ID>
Source: <exact section + item number/bullet identity>
Requirement: <concise normative obligation preserving MUST / MUST NOT / ONLY / CANNOT / fail-closed semantics>
Named surfaces: <explicitly named boundary/path/entity when present, otherwise None>
```

### Required Source Coverage

Enumerate and count independently:

* numbered User Stories;
* Implementation Decision bullets;
* Testing Decision bullets;
* Out of Scope bullets;
* other materially unique normative clauses containing `must`, `must not`, `only`, `cannot`, `fail closed`, `without fallback`, `unavailable`, `reconstruct`, `idempotent`, `no bypass`, or equivalent mandatory language not already represented.

Every enumerated source item must map to at least one manifest cell.

Do not collapse distinct positive and negative obligations merely because they concern the same subsystem.

### Manifest Integrity Gate

Before returning a manifest require:

```text
Unmapped source items: 0
Duplicate source mappings: 0
Ambiguous source items: 0
```

Also require:

* the number of distinct `US-*` source mappings exactly equals the number of numbered User Stories;
* the number of distinct `ID-*` source mappings exactly equals the number of Implementation Decision bullets;
* the number of distinct `TD-*` source mappings exactly equals the number of Testing Decision bullets;
* the number of distinct `OOS-*` source mappings exactly equals the number of Out of Scope bullets;
* every additional `NORM-*` cell cites exact source text/section identity;
* every manifest cell is traceable to the originating Spec and no manifest cell is inferred from ADRs, current architecture docs, repository standards, Root Blocker history, or implementation accidents.

A manifest with unresolved counting, missing source items, or ambiguous mapping is invalid. Do not return a partial manifest as complete.

Canonicalize rows in stable ID order and compute:

```text
SPEC_CONTRACT_HASH = SHA-256(canonical ordered manifest rows)
```

## 3. Classify Change Ownership

The fixed Spec baseline remains the integration origin, but it does not by itself establish ownership.

Capture the complete integration history:

```bash
git diff --name-status "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

Capture commits/files unique to the current Spec branch relative to the current default branch:

```bash
git rev-list --reverse HEAD --not "$DEFAULT_REF"
git diff --name-status "$DEFAULT_REF"...HEAD
```

If `BASELINE_COMMIT` is not in a usable ancestry relationship for bounded integration history, or the default-branch relationship cannot be resolved without ambiguity, return `SPEC OWNERSHIP: AMBIGUOUS` rather than guessing.

Classify repository surfaces as:

* **Spec-owned** — changed by current branch work not reachable from the current default branch;
* **Mixed** — changed by both inherited default-branch work and Spec-owned work;
* **Inherited-only** — present in fixed-baseline→`HEAD` integration history but absent from the Spec-owned branch delta;
* **Unchanged/named** — not changed by the Spec but explicitly named by a Spec obligation or governing architecture and therefore potentially relevant to behavioral proof.

For review/verification attribution:

* Spec-owned and Mixed surfaces are owned change surfaces.
* Inherited-only surfaces are integration context, not automatically current-Spec Standards scope.
* An inherited-only surface may still be inspected when an exact Spec obligation or applicable architecture authority requires current behavior through that surface.
* A deterministic repository-standard defect that is inherited-only and has no direct Spec/architecture obligation is not a Blocking finding owned by this Spec.
* Pre-existing code is not exempt from a Spec or Architecture obligation merely because it is inherited. Ownership limits unrelated repository-policy attribution; it does not weaken required product/architecture behavior.

### Tracker Ownership

Classify as Spec-owned tracker state only formal artifacts/transitions belonging to this Spec lifecycle, such as:

* the Spec itself;
* its implementation tickets;
* its Spec Review and remediation tickets;
* native hierarchy/dependency state owned by those artifacts;
* verification/review receipts and lifecycle state durably written for this Spec.

Global project-delivery state, unrelated Wayfinders/Specs, repository-wide policy issues, and unrelated Project items are not Spec-owned merely because they changed while this Spec was active. They may still be mutable authorization inputs revalidated by their owning lifecycle guards.

## 4. Validate Mode

In `validate` mode:

1. recompute `SPEC_BODY_HASH`;
2. require it to equal the passing verification receipt;
3. require the persisted source counts and canonical manifest rows to satisfy the Manifest Integrity Gate;
4. recompute `SPEC_CONTRACT_HASH` from those rows and require an exact match;
5. require the receipt's baseline/branch/Verified HEAD to match the current invocation;
6. recompute Spec Change Ownership fresh against the current default branch.

Do not silently rebuild a different manifest when validation fails.

Return:

```text
SPEC CONTRACT: STALE
Reason: <body/hash/count/baseline/branch/HEAD mismatch>
```

and let the parent require fresh `$verify-spec`.

A default-branch advance that changes only ownership classification does not rewrite the manifest. Return the fresh ownership classification to the caller.

## Return Contract

Return exactly one complete result containing:

```text
SPEC CONTRACT: VALID

Spec: #<n>
Spec Body Hash: <sha256>
Spec Contract Hash: <sha256>
Baseline: <sha>
Branch: <branch>
HEAD: <sha>
Default branch: <name>
Default branch ref: <sha>

Source counts:
- User Stories: <n>
- Implementation Decisions: <n>
- Testing Decisions: <n>
- Out of Scope: <n>
- Other normative source items: <n>

Manifest cells: <n>
Unmapped source items: 0
Duplicate source mappings: 0
Ambiguous source items: 0

Spec-owned commits: <n>
Spec-owned repository surfaces: <summary/list>
Mixed repository surfaces: <summary/list>
Inherited-only integration surfaces: <summary/list>
Spec-owned tracker surfaces: <summary/list>

Spec Contract Manifest:
<ordered complete manifest rows>
```

Do not return `SPEC CONTRACT: VALID` when any manifest-integrity or ownership-boundary requirement is unresolved.
