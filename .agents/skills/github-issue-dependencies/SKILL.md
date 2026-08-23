---
name: github-issue-dependencies
description: Invoked only by `$to-tickets` when publishing or updating native GitHub issue relationships — parent/child hierarchy and blocking edges — not a standalone command. Documents the native `gh` CLI flags for sub-issue and blocked-by/blocking relationships, so this doesn't need to be re-researched on every invocation.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# GitHub Issue Dependencies

This skill is invoked by `$to-tickets` at Step 5 ("Publish the tickets to the configured tracker") when the configured tracker is GitHub and native parent/child or blocked-by/blocking relationships must be published or updated. Use the commands below rather than researching this from scratch or falling back to raw `gh api graphql` mutations — the CLI now does this natively.

## Native `gh` flags

As of `gh` CLI **v2.94.0** (June 2026), `gh issue create` supports:

- `--parent <number>` — creates the new issue as a native sub-issue of `<number>` (a real parent/child hierarchy, not just a text mention)
- `--blocked-by <numbers>` — marks the new issue as blocked by the given issue number(s)/URL(s), comma-separated for multiple
- `--blocking <numbers>` — marks the new issue as blocking the given issue number(s)/URL(s)
- `--type <name>` — sets the issue type, if your tracker uses GitHub's issue types

All four flags can be combined in one call. `$to-tickets` must resolve `<native_parent_issue_number>` from its direct-decomposition invariant before invoking this helper:

- ordinary Spec ticketing → the Spec issue number;
- Spec Review remediation → the Spec Review issue number.

Do not substitute an upstream provenance issue for the direct decomposition parent. In particular, a remediation ticket's originating Parent Spec remains lifecycle/branch provenance and is not its native GitHub parent.

Example — a ticket blocked by two earlier tickets and filed under the artifact directly decomposed by `$to-tickets`:

```bash
gh issue create \
  --title "..." \
  --body "..." \
  --parent <native_parent_issue_number> \
  --blocked-by <blocker_1_number>,<blocker_2_number> \
  --label ready-for-agent
```

## Before relying on this

Confirm the installed `gh` version actually supports these flags:

```bash
gh --version   # needs >= 2.94.0
```

If it's older than 2.94.0, fall back to the text-based "Blocked by" convention already described in `$to-tickets` Step 5, rather than reaching for raw `gh api graphql` mutations — those still work, but add real complexity for something the CLI now does natively on a current version.

## Editing relationships on an already-published issue

Use `gh issue edit` directly for existing issue relationships.

Set or change an issue's native parent using the same direct-decomposition invariant as create-time publication:

```bash
gh issue edit <issue_number> --parent <native_parent_issue_number>
```

Remove its native parent:

```bash
gh issue edit <issue_number> --remove-parent
```

When operating from the parent side, add or remove existing sub-issues:

```bash
gh issue edit <parent_issue_number> --add-sub-issue <child_issue_number>
gh issue edit <parent_issue_number> --remove-sub-issue <child_issue_number>
```

Add or remove dependency relationships:

```bash
gh issue edit <issue_number> --add-blocked-by <blocker_numbers_or_urls>
gh issue edit <issue_number> --remove-blocked-by <blocker_numbers_or_urls>
gh issue edit <issue_number> --add-blocking <blocked_issue_numbers_or_urls>
gh issue edit <issue_number> --remove-blocking <blocked_issue_numbers_or_urls>
```

The relationship flags accept comma-separated issue numbers or URLs where multiple relationships are supported. Prefer `--parent` / `--remove-parent` when reconciling one ticket's immediate decomposition ownership; use `--add-sub-issue` / `--remove-sub-issue` when the parent issue is the natural reconciliation anchor.
