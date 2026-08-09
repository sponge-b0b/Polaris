---
name: github-issue-dependencies
description: Invoked only by `$to-tickets` when publishing tickets with blocking edges to a GitHub tracker — not a standalone command. Documents the native `gh` CLI flags for sub-issue and blocked-by/blocking relationships, so this doesn't need to be re-researched on every invocation.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# GitHub Issue Dependencies

This skill is invoked by `$to-tickets` at Step 5 ("Publish the tickets to the configured tracker"), specifically when the configured tracker is GitHub and the tickets being published have blocking edges. Use the commands below rather than researching this from scratch or falling back to raw `gh api graphql` mutations — the CLI now does this natively.

## Native `gh` flags

As of `gh` CLI **v2.94.0** (June 2026), `gh issue create` supports:

- `--parent <number>` — creates the new issue as a native sub-issue of `<number>` (a real parent/child hierarchy, not just a text mention)
- `--blocked-by <numbers>` — marks the new issue as blocked by the given issue number(s)/URL(s), comma-separated for multiple
- `--blocking <numbers>` — marks the new issue as blocking the given issue number(s)/URL(s)
- `--type <name>` — sets the issue type, if your tracker uses GitHub's issue types

All four flags can be combined in one call. Example — a ticket blocked by two earlier tickets, filed as a sub-issue of the spec:

```bash
gh issue create \
  --title "..." \
  --body "..." \
  --parent <spec_issue_number> \
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

For adding or changing these relationships on an issue that's already been created — relevant during `to-remediation-tickets`'s regression/dedup handling, for example — check `gh issue edit --help` for the corresponding flags. They were added alongside the create-time ones in the same release, but the exact flag names weren't independently verified for this skill; confirm against `--help` output before relying on a specific flag name.
