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

It does not verify implementation, review implementation, create findings, mutate tracker state, edit repository files, commit, push, or decide remediation.

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

The helper resolves the repository default branch and immutable default-branch head from GitHub, not from a possibly stale remote-tracking ref. If that exact commit object is absent locally, it may fetch the default branch over the repository's canonical HTTPS URL into `FETCH_HEAD` only. It must not depend on the configured `origin` transport, switch branches, change the index/worktree, edit tracked files, commit, push, or mutate tracker state.

Default-branch ownership resolution is an ordered gate owned by this helper. Callers must not preflight, probe, fetch, or independently compare the GitHub-pinned default head before this helper completes Section 1 and returns `DEFAULT_REF`. If ownership must be refreshed because the default branch advanced, invoke `$spec-contract` again rather than reproducing its pin/fetch logic in the caller.

## 1. Pin the Spec Source

Read the current Spec body from GitHub and capture:

```bash
SPEC_BODY_HASH=$(
  gh issue view <spec_issue_number> --json body --jq .body \
    | sha256sum | awk '{print $1}'
)
```

Resolve the repository default branch and the exact GitHub head used for ownership. Execute this block as one ordered unit. The silenced `git cat-file -e` inside the block is the only permitted pre-fetch local object probe. If the pinned object is absent, fetch immediately through the canonical HTTPS path before running any `git diff`, `git rev-list`, unsilenced object probe, or other ownership command against that SHA.

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

DEFAULT_BRANCH=$(gh api "repos/$REPO" --jq .default_branch)
DEFAULT_HEAD=$(gh api "repos/$REPO/commits/$DEFAULT_BRANCH" --jq .sha)

if [ -z "$DEFAULT_BRANCH" ] || [ -z "$DEFAULT_HEAD" ]; then
  echo "SPEC OWNERSHIP: AMBIGUOUS"
  echo "Reason: repository default branch or head could not be resolved from GitHub"
  exit 1
fi

if ! git cat-file -e "${DEFAULT_HEAD}^{commit}" 2>/dev/null; then
  git fetch --quiet "https://github.com/${REPO}.git" "refs/heads/${DEFAULT_BRANCH}"
  FETCHED_HEAD=$(git rev-parse FETCH_HEAD)

  if [ "$FETCHED_HEAD" != "$DEFAULT_HEAD" ]; then
    echo "SPEC OWNERSHIP: AMBIGUOUS"
    echo "Reason: default branch advanced while ownership head was being pinned"
    exit 1
  fi
fi

git cat-file -e "${DEFAULT_HEAD}^{commit}"
DEFAULT_REF="$DEFAULT_HEAD"
```

Do not fall back from this procedure to SSH, a configured remote URL, a stale `origin/<branch>` ref, or another transport. If the canonical HTTPS fetch fails or the fetched head differs from the GitHub-pinned SHA, return ambiguous rather than improvising another refresh path.

Only after `DEFAULT_REF` is set may Section 3 run ownership comparison commands. Do not resolve, fetch, or probe the default branch again later in the same helper invocation.

Require the supplied branch, `BASELINE_COMMIT`, and `HEAD` to resolve.

If the Spec body is missing, malformed, or cannot be read completely, return:

```text
SPEC CONTRACT: INVALID
Reason: <missing/unreadable source>
```

## 2. Build the Spec Contract Manifest

Construct the contract only from the current originating Spec.

Completeness has two distinct gates:

```text
complete Spec source-unit universe
        ↓
complete normative obligation mapping
```

Do not treat `Unmapped source items: 0` as proof that every normative source item was discovered. A source item that never entered the candidate universe is still an omission.

### 2.1 Build the Source Unit Inventory

Before creating manifest cells, partition the complete Spec body into a deterministic ordered **Source Unit Inventory**.

Headings establish section identity but are not source units. Blank lines, Markdown separators, syntactic table-separator rows, and recognized workflow/provenance-only HTML markers are structural metadata and are not source units.

Every other content-bearing Markdown block is a source unit, including:

* each paragraph;
* each numbered or bulleted list item, including nested items;
* each table data row;
* each blockquote block;
* each fenced code block;
* each non-provenance HTML block.

Do not pre-filter source units by words such as `must`, `should`, `only`, or `cannot`. Keyword discovery may help classification but must never define the universe.

Assign stable document-order IDs:

```text
SU-0001
SU-0002
...
```

For every source unit record:

```text
Source Unit: SU-<n>
Source: <section + deterministic item/bullet/paragraph/table/code identity>
Text Hash: <sha256 of normalized source-unit text>
Classification: normative-new | normative-represented | non-normative
Manifest cells: <cell IDs | None>
Reason: <None | concise classification/mapping reason>
```

Use structured item numbers where the Spec supplies them. Otherwise identify the unit by its section and stable document-order unit position; do not invent a semantic label whose wording may vary between runs.

Normalize source-unit text only for hashing by normalizing line endings and removing trailing line-ending whitespace. Do not rewrite semantic text before hashing.

Classifications mean:

* **normative-new** — the unit establishes one or more contract obligations and must map to newly created manifest cell(s);
* **normative-represented** — the unit contains normative meaning already fully represented by identified manifest cell(s); it must name those cells and explain the equivalence/reference rather than silently disappearing;
* **non-normative** — the unit is contextual, explanatory, descriptive, illustrative, historical, or otherwise does not establish a Spec acceptance/exclusion obligation; it requires a concise reason.

A unit containing several materially independent obligations may map to several manifest cells. A unit containing both normative and explanatory text is normative; do not classify the whole unit non-normative merely because part of it is context.

A unit cannot be omitted because it appears duplicative, obvious, inherited from a template, already discussed elsewhere, or unlikely to affect implementation. Those are dispositions, not absence from the inventory.

Before manifest construction may complete require:

```text
Source units: <n>
Classified source units: <n>
Unclassified source units: 0
Normative source units without manifest mapping: 0
Non-normative source units without reason: 0
```

If any source unit cannot be classified confidently, the contract is invalid. Do not guess merely to reach zero.

### 2.2 Create Manifest Cells

Use stable source-derived IDs:

* numbered User Stories → `US-<number>`;
* Implementation Decision bullets → `ID-<number>`;
* Testing Decision bullets → `TD-<number>`;
* Out of Scope bullets → `OOS-<number>`;
* materially unique normative requirements elsewhere → `NORM-<number>`.

If one source item contains materially independent obligations that must be proven separately, use stable suffixes such as `US-22.a`, `US-22.b`. The parent source item remains mapped and counts once in source-item integrity.

Do not create a `NORM-*` cell when the same normative obligation is already represented by a User Story, Implementation Decision, Testing Decision, or Out of Scope cell. Classify the corresponding source unit as `normative-represented` and name the existing cell(s).

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
* other materially unique normative source units classified from the complete Source Unit Inventory.

Every normative source unit must map to at least one manifest cell, either as `normative-new` or `normative-represented`.

Do not collapse distinct positive and negative obligations merely because they concern the same subsystem.

### Manifest Integrity Gate

Before returning a manifest require:

```text
Unclassified source units: 0
Normative source units without manifest mapping: 0
Non-normative source units without reason: 0
Unmapped source items: 0
Duplicate source mappings: 0
Ambiguous source items: 0
```

Also require:

* the number of distinct `US-*` source mappings exactly equals the number of numbered User Stories;
* the number of distinct `ID-*` source mappings exactly equals the number of Implementation Decision bullets;
* the number of distinct `TD-*` source mappings exactly equals the number of Testing Decision bullets;
* the number of distinct `OOS-*` source mappings exactly equals the number of Out of Scope bullets;
* every `normative-new` source unit names every manifest cell created from it;
* every `normative-represented` source unit names at least one existing manifest cell and explains why that mapping is complete;
* every `non-normative` source unit has a concise reason;
* every additional `NORM-*` cell cites exact source text/section identity;
* every manifest cell is traceable to the originating Spec and no manifest cell is inferred from ADRs, current architecture docs, repository standards, Root Blocker history, or implementation accidents.

A contract with unresolved source-unit classification, counting, missing source items, missing mappings, or ambiguous mapping is invalid. Do not return a partial inventory or manifest as complete.

Canonicalize each Source Unit Inventory row as exactly:

```text
<Source Unit>|<Source>|<Text Hash>|<Classification>|<manifest cell IDs sorted in stable cell-ID order or None>
```

The human-readable `Reason` is mandatory where required above but is deliberately excluded from the hash so equivalent explanatory wording does not make an unchanged contract stale.

Canonicalize inventory rows in `SU-*` order and manifest rows in stable cell-ID order. Compute:

```text
SPEC_CONTRACT_HASH = SHA-256(
    canonical ordered Source Unit Inventory rows
    + canonical ordered Spec Contract Manifest rows
)
```

The contract hash therefore binds both **what the Spec said** and **how every semantic source unit was dispositioned into or outside the normative contract**, without binding incidental explanatory prose.

## 3. Classify Change Ownership

The fixed Spec baseline remains the integration origin, but it does not by itself establish ownership.

Capture the complete integration history:

```bash
git diff --name-status "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

Capture commits/files unique to the current Spec branch relative to the immutable default-branch head pinned in Section 1:

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
3. rebuild the deterministic Source Unit Inventory boundaries from the current Spec body;
4. classify every current source unit and require the complete source-unit integrity gate to pass;
5. require the persisted source counts and canonical manifest rows to satisfy the Manifest Integrity Gate;
6. require current source-unit mappings to resolve only to cells present in the persisted manifest;
7. canonicalize the current Source Unit Inventory plus persisted manifest rows and recompute `SPEC_CONTRACT_HASH`;
8. require that hash to equal the passing verification receipt;
9. require the receipt's baseline/branch/Verified HEAD to match the current invocation;
10. recompute Spec Change Ownership fresh against the immutable current default-branch head resolved in Section 1.

Do not silently rebuild a different manifest when validation fails. Do not make a new source-unit classification merely to force the old contract hash to match.

Return:

```text
SPEC CONTRACT: STALE
Reason: <body/source-universe/classification/hash/count/baseline/branch/HEAD mismatch>
```

and let the parent require fresh `$verify-spec`.

A default-branch advance that changes only ownership classification does not rewrite the source inventory or manifest. Return the fresh ownership classification to the caller.

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

Source unit integrity:
- Source units: <n>
- Classified source units: <n>
- Normative-new source units: <n>
- Normative-represented source units: <n>
- Non-normative source units: <n>
- Unclassified source units: 0
- Normative source units without manifest mapping: 0
- Non-normative source units without reason: 0

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

Source Unit Inventory:
<ordered complete SU-* rows>

Spec Contract Manifest:
<ordered complete manifest rows>
```

Do not return `SPEC CONTRACT: VALID` when any source-universe, manifest-integrity, or ownership-boundary requirement is unresolved.

## Authorized Decomposition Caller

`$to-tickets` is also an authorized internal caller of `$spec-contract` in `build` mode for the sole purpose of constructing the exact current Spec obligation universe before ticket decomposition.

This does not make `$spec-contract` a ticketing lifecycle owner and does not verify implementation. `$to-tickets` supplies the same required Spec/baseline/branch/HEAD inputs and consumes the returned Source Unit Inventory, manifest, hashes, and integrity counts as decomposition source state. All existing fail-closed source-universe and ownership requirements apply unchanged.
