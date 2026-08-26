# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Lifecycle authority

GitHub commands and connector operations are tracker mechanics, not permission to create or mutate workflow artifacts.

Agents must create, publish, close, reopen, or otherwise perform lifecycle-significant mutation of a workflow issue only through the skill that owns that artifact's lifecycle. A tool capability, this document, repository write access, or a request to "record" or "track" work does not by itself authorize direct issue creation or lifecycle mutation.

Before creating any issue, identify the lifecycle-owning skill and follow its publication/approval contract. If no existing skill owns the proposed artifact type, do not create the issue directly; keep the information in the appropriate repository artifact or surface the missing workflow owner.

Direct issue reads and mechanical operations are allowed only when an owning skill or explicit repository procedure authorizes them for the active lifecycle.

## Conventions

The commands below describe mechanics to use when the applicable lifecycle owner authorizes the operation.

- **Create an issue**: use `gh issue create --title "..." --body "..."` only for simple single-line bodies. For Markdown or any multi-line body, use a literal heredoc through `--body-file -` so shell syntax is never expanded:

  ```bash
  gh issue create \
    --title "..." \
    --body-file - <<'EOF'
  Markdown containing `symbols`, $variables, $(commands), and other shell-sensitive text stays literal.
  EOF
  ```

  Do not use an unquoted heredoc delimiter or interpolate a multi-line body through the shell.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## Issue Handling Protocols

### Mandatory Pre-Flight Execution
Before an agent processes any issue entry, it must query the remote metadata state:
```bash
gh issue view <ISSUE_NUMBER> --json labels
```

### Label Enforcement Matrices
- **Label:** `wayfinder:research`
  - **Action:** Proceed via the /research skill.
- **Label:** `wayfinder:prototype`
  - **Action:** Proceed via the /prototype skill.
- **Label:** `wayfinder:grilling`
  - **Action:** Proceed via the /grilling and /domain-modeling skills, one question at a time. The default case.
- **Label:** All other variations
  - **Action:** Route to **AFK** mode and execute the task autonomously using local tools as needed.
  
## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

When set to `yes`, PRs run through the same labels and states as issues, using the `gh pr` equivalents:

- **Read a PR**: `gh pr view <number> --comments` and `gh pr diff <number>`.
- **List external PRs for triage**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` then keep only `authorAssociation` of `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR`, or `NONE` (drop `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comment / label / close**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

GitHub shares one number space across issues and PRs, so a bare `#42` may be either — resolve with `gh pr view 42` and fall back to `gh issue view 42`.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (`gh api` on the sub-issues endpoint). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: GitHub's **native issue dependencies** are the canonical, UI-visible representation. Use `$github-issue-dependencies` for relationship mechanics. Legacy textual `Blocked by` metadata may be retained as historical/explanatory context but is not a second dependency authority when native relationships are available. A ticket is unblocked when every native blocker is closed.
- **Frontier query**: list the map's open children, drop any with an open native blocker or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` — the session's first write after required project-delivery authorization.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.

## Project Delivery Management

`$project-delivery-management` owns project-level delivery coordination across independent Wayfinder lineages. Dependency answers **what may proceed**; focus answers **what Polaris intends to work now**.

Canonical rules:

- discover Wayfinder maps from open issues labelled `wayfinder:map`; do not maintain a second map registry;
- discover the single Project Delivery Management control issue by `project-delivery:management`; it is not a Wayfinder, Project item, or parent of maps;
- derive the Wayfinder frontier from open canonical maps with no open direct native blockers;
- persist only focused Wayfinders and exact parallel-focus authorization on the control issue; frontier/blocked/queued state remains derived;
- require explicit human focus/switch/parallel authorization; never infer focus from Project fields, Priority, assignees, issue order/age, activity, branches, or conversation state;
- keep cross-Wayfinder semantic dependencies at the narrowest authoritative artifact whose lifecycle completion satisfies the prerequisite; `$project-delivery-management` owns cross-lineage semantics and delegates native relationship mutation to `$github-issue-dependencies`;
- reserve Wayfinder-to-Wayfinder blockers for true whole-map prerequisites; never create dependency edges merely to enforce project WIP;
- derive the Spec dependency frontier from open Specs with no open native blockers; a Wayfinder-managed Spec is actionable only when at least one current governing Wayfinder is focused;
- permit multiple independent actionable Specs inside a focused Wayfinder; do not persist a separate active-Spec queue or WIP field;
- treat a closed Wayfinder as the durable delivery-complete marker. If authoritative re-entry or open governed Derived/Remediation Spec work exists, reopen the Wayfinder before substantive advancement;
- keep the public GitHub Project downstream and non-authoritative. Project drift is repaired from canonical issue/provenance/dependency/focus state, never the reverse.

Project Delivery Management bootstrap initializes `Focused Wayfinders: None` and `Parallel authorization: None`. After bootstrap, zero or multiple canonical control issues is invalid state and project-gated advancement fails closed.
