# graphify reference: commit hook and native CLAUDE.md integration

Load this when the user asked to install the post-commit hook or wire graphify into a project's CLAUDE.md.

## For git commit hook

Install a post-commit hook that auto-rebuilds the graph after every commit. No background process needed - triggers once per commit, works with any editor.

```bash
graphify hook install    # install
graphify hook uninstall  # remove
graphify hook status     # check
```

After every `git commit`, the hook detects which code files changed (via `git diff HEAD~1`), re-runs AST extraction on those files, and rebuilds `graph.json` and `GRAPH_REPORT.md`. Doc/image changes are ignored by the hook - run `/graphify --update` manually for those.

If a post-commit hook already exists, graphify appends to it rather than replacing it.

---

## For native CLAUDE.md integration

Run only when the user explicitly requests native Graphify integration:

```bash
graphify claude install
```

This writes a generated `## graphify` section to the local `CLAUDE.md`. In Polaris, generated instructions must preserve `AGENTS.md` repository-analysis routing: Graphify may keep its graph refreshed, but it must not claim every codebase question merely because the graph exists. Review and reconcile any generated catchall routing before accepting the integration.

```bash
graphify claude uninstall  # remove the section
```
