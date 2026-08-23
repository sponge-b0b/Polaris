---
name: github-issue-dependencies
description: Internal GitHub relationship helper used by `$to-tickets` and `$project-delivery-management` for authorized native parent/child and dependency mutations. Documents current `gh` CLI relationship flags so lifecycle owners do not duplicate tracker mechanics.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# GitHub Issue Dependencies

This is a **mechanical relationship helper**, not a semantic lifecycle owner and not a standalone Human Handoff.

Authorized callers:

* `$to-tickets` — native direct-decomposition hierarchy plus dependency edges it already owns;
* `$project-delivery-management` — native `blocked by` / `blocking` mutations only after it has established cross-Wayfinder semantic ownership, lowest-accurate placement, and cycle safety.

Do not let this helper decide whether a dependency is semantically required, where it belongs, or which lifecycle owns it.

## Native `gh` flags

As of `gh` CLI **v2.94.0** (June 2026), `gh issue create` supports:

- `--parent <number>` — creates the new issue as a native sub-issue of `<number>`;
- `--blocked-by <numbers>` — marks the new issue as blocked by the given issue number(s)/URL(s), comma-separated for multiple;
- `--blocking <numbers>` — marks the new issue as blocking the given issue number(s)/URL(s);
- `--type <name>` — sets the issue type, if your tracker uses GitHub's issue types.

All four flags can be combined in one call.

### `$to-tickets` hierarchy invariant

Only `$to-tickets` may use this helper to establish direct-decomposition parentage during ticket publication/reconciliation.

Resolve `<native_parent_issue_number>` from the artifact directly decomposed by `$to-tickets`:

- ordinary Spec ticketing → the Spec issue number;
- Spec Review remediation → the Spec Review issue number.

Do not substitute an upstream provenance issue for the direct decomposition parent. In particular, a remediation ticket's originating Parent Spec remains lifecycle/branch provenance and is not its native GitHub parent.

Example:

```bash
gh issue create \
  --title "..." \
  --body "..." \
  --parent <native_parent_issue_number> \
  --blocked-by <blocker_1_number>,<blocker_2_number> \
  --label ready-for-agent
```

`$project-delivery-management` must **not** use `--parent`, `--remove-parent`, `--add-sub-issue`, or `--remove-sub-issue` when reconciling cross-Wayfinder dependencies.

## Before relying on this

Confirm the installed `gh` version supports the required relationship flags:

```bash
gh --version   # needs >= 2.94.0
```

If an authorized caller needs a native operation the installed CLI cannot perform, return the tool/version blocker to that caller. Do not silently replace native relationships with text or raw GraphQL from this helper unless the owning lifecycle explicitly defines that fallback.

## Editing relationships on an already-published issue

Use `gh issue edit` directly for existing issue relationships.

### Parent/sub-issue operations — `$to-tickets` only

Set or change an issue's native parent:

```bash
gh issue edit <issue_number> --parent <native_parent_issue_number>
```

Remove its native parent:

```bash
gh issue edit <issue_number> --remove-parent
```

When operating from the parent side:

```bash
gh issue edit <parent_issue_number> --add-sub-issue <child_issue_number>
gh issue edit <parent_issue_number> --remove-sub-issue <child_issue_number>
```

### Dependency operations — authorized semantic owner required

Add or remove dependency relationships:

```bash
gh issue edit <issue_number> --add-blocked-by <blocker_numbers_or_urls>
gh issue edit <issue_number> --remove-blocked-by <blocker_numbers_or_urls>
gh issue edit <issue_number> --add-blocking <blocked_issue_numbers_or_urls>
gh issue edit <issue_number> --remove-blocking <blocked_issue_numbers_or_urls>
```

The relationship flags accept comma-separated issue numbers or URLs where multiple relationships are supported.

For `$project-delivery-management`, mutate only the exact cross-Wayfinder edge it authorized. Do not add/remove neighboring dependencies, hierarchy, labels, Project fields, or lifecycle state in the same helper call.

## Verification

A zero exit status is not sufficient proof.

After every native relationship mutation, the caller must re-read the affected issue relationship and require the requested result:

* add → exact relationship exists;
* remove → exact relationship is absent;
* parent change → exact direct parent matches.

If verification fails, return the mutation/verification failure to the semantic owner. Do not compensate by writing text-based duplicate relationship state.
