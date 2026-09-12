# Session Reconstitution

## Purpose

This guide defines how a ChatGPT-hosted Polaris working session should:

1. reconstruct enough durable project context to continue prior work safely and efficiently; and
2. maintain the small amount of session-only continuation state that would otherwise be lost if the ChatGPT conversation ends unexpectedly.

It is a **ChatGPT bootstrap, recovery, and active-session continuity procedure**, not a source of architectural truth, workflow state, or domain semantics.

The goal is to avoid rebuilding project context from large conversation transcripts when the repository and tracker already preserve durable state, while durably checkpointing only the ephemeral continuation state that the repository and tracker cannot recover cheaply or reliably.

## Runtime Scope

This process exists specifically for **ChatGPT-hosted Polaris working sessions** where conversational context can be lost between sessions.

It is **not** a Codex workflow skill, is not part of the Polaris delivery state machine, and must not be invoked or composed by repository workflow skills.

Codex agents do not need to consider or maintain the ChatGPT Session Ledger unless a human explicitly asks them to modify this process itself.

During a ChatGPT working session, the ChatGPT agent that reconstitutes the session owns subsequent ledger synchronization for the remainder of that active session.

## ChatGPT Runtime Capability Contract

This section records the **known mechanical capability baseline** for ChatGPT-hosted Polaris sessions. It is intentionally ChatGPT-specific and exists so a new session does not waste time rediscovering how to perform recurring repository and workflow operations.

This is a capability contract, **not workflow authority**. Mechanical ability to mutate GitHub state never bypasses `AGENTS.md`, the active `SKILL.md`, human-approval gates, branch guards, or lifecycle sequencing.

Treat the capabilities and methods below as already known after reconstitution. **Do not perform capability discovery for an operation listed here.** Do not spend turns enumerating tools, trying alternate transports, offering patches, or asking the repository owner to perform work that this contract says ChatGPT can perform. Re-evaluate a listed capability only when the canonical operation itself returns an unavailable/unsupported error or the runtime explicitly reports that the capability is absent.

### Known ChatGPT-Side Capabilities

The connected GitHub runtime can, without the repository owner's local checkout:

- read repository files, blobs, commits, branches, diffs, commit status, issues, issue comments, pull requests, reviews, and GitHub Actions results;
- search repository code and tracker artifacts;
- compare exact commits/refs;
- create and update repository files;
- create Git blobs, trees, and commits and fast-forward an existing branch ref;
- create temporary branches from an exact commit;
- create/update issues and issue comments, labels, assignees, and ordinary tracker metadata exposed by the connector;
- create/update pull requests, request/review PRs, and merge a PR with an expected-head guard;
- create temporary push-triggered GitHub Actions workflows on scratch branches when an authorized workflow requires repository-command execution;
- execute reproducible repository-local commands in GitHub-hosted Actions against an exact remote candidate/ref, including `git`, locked `uv`, pytest, Ruff, Mypy, repository scripts, and safely provisionable services when the active workflow permits them;
- inspect GitHub Actions runs, jobs, logs, and artifacts;
- update the ChatGPT Session Ledger state comment and read it back exactly.

The ChatGPT analysis/container runtime can also perform deterministic text/data transformation, hashing, JSON construction, and other scratch computation. It is **not** the repository owner's checkout and must not be treated as evidence of the owner's local Git/worktree/service state.


### Execution-Substrate Rule

A repository workflow requiring shell commands does **not** by itself require the repository owner's machine. In Polaris skill language, repository-local/workspace-local verification describes the scope and candidate being verified, not the physical computer that must execute it.

When the exact candidate/ref, locked repository environment, required services, and other prerequisites can be reproduced safely on a GitHub-hosted runner, ChatGPT owns that execution through GitHub Actions. This includes ordinary `$implement-ticket` code verification such as `$verify-code`, Ruff, Mypy, targeted pytest, `$verify-architecture`, repository scripts, and other prescribed command gates.

GitHub Actions is only an **execution substrate**. It does not weaken or replace the active skill. ChatGPT must still execute the complete owning workflow semantics: exact baseline/candidate binding, target discovery, service preflight, contract/consumer manifests, delegated child gates, fail-closed handling, required readback, and the skill's terminal result. Running a convenient subset of the same commands is not equivalent to completing the skill.

For an end-to-end workflow such as `$implement-ticket`, perform every mechanically available stage on the ChatGPT side when the connector plus an exact-candidate Actions runner can satisfy it. Do not create a human handoff merely because a step is expressed as Bash, `git`, `uv`, pytest, Ruff, Mypy, or another repository command.

Prefer this execution order unless the governing workflow prescribes something stricter:

1. direct GitHub connector actions for repository/tracker reads and mutations;
2. GitHub-hosted Actions for reproducible repository-command execution against an exact candidate/ref;
3. owner-machine handoff only when a required fact or command genuinely depends on owner-local state, unavailable credentials/services/hardware, or another connector/runtime gap.

### Known Local-Only or Connector-Missing Capabilities

ChatGPT cannot directly observe or execute inside the repository owner's local Polaris checkout. Therefore ChatGPT cannot itself establish:

- the owner's current `git status`, local branch, uncommitted files, unpushed commits, stash state, or locally generated files unless those facts become durable remotely or the owner returns command output;
- results that specifically depend on the owner's checkout or owner-machine environment and cannot be reproduced safely from durable remote state, such as commands whose required inputs are uncommitted local files, owner-only credentials, machine-specific hardware, sockets, or services unavailable to the Actions/runtime environment;
- local environment variables, credentials, sockets, services, or machine-specific filesystem state.

These boundaries do **not** make ordinary repository-local commands owner-only. When a required command can run reproducibly from the exact remote candidate in GitHub Actions, ChatGPT should run it there. If a required service can be provisioned safely and reproducibly in the runner under the active workflow's rules, that service is likewise ChatGPT-owned for that verification.

The current connected GitHub runtime also does **not** expose remote Git-ref deletion and does not provide the GitHub Projects v2 mutation surface used by Polaris Project projection. Those operations remain local `git`/`gh` handoffs unless the runtime explicitly gains those capabilities in the future.

Do not infer from these local-only boundaries that repository mutation generally belongs to the owner. It does not: remote repository/tracker work remains ChatGPT-owned whenever the operation is listed as available above.

### Non-Discovery Rule

For the recurring operations below, use the prescribed method immediately. Do not search for a different connector action, create a download, ask the owner to copy a patch, or experiment with multiple approaches first.

A targeted capability check is permitted only when:

1. the prescribed operation actually fails because the capability is unavailable or unsupported; or
2. the task requires an operation not covered by this contract.

When a new genuinely stable capability or limitation is discovered, update this section so later sessions inherit it instead of rediscovering it.

After a recurring mechanical task succeeds with a stable method, capture the shortest proven method and its selection condition here before moving on when they are not already recorded. Replace disproven mechanics instead of preserving them as alternatives; later sessions must not repeat capability/transport discovery for known work.

### Canonical Mechanical Playbook

The sequences below are the preferred ChatGPT-side mechanics. The active workflow still decides **whether and when** the operation is authorized.

#### Read a repository file or exact revision

Use:

```text
GitHub.fetch_file(repository_full_name=REPO, path=PATH, ref=REF)
```

For a large file, fetch bounded line ranges rather than repeatedly requesting the whole file. For repository search, use `GitHub.search` and then `GitHub.fetch_file` for the authoritative full context. Do not use public web search for Polaris repository content when the GitHub connector can read it directly.

#### Read branch/commit state and exact deltas

Use the GitHub branch/commit read followed by:

```text
GitHub.compare_commits(repo_full_name=REPO, base=BASE, head=HEAD)
GitHub.fetch_commit(repo_full_name=REPO, commit_sha=HEAD)
```

Prefer the workflow's durable baseline/anchor → exact candidate `HEAD` comparison over a broad recent-history scan.

#### Make a small single-file repository edit

When the complete replacement content can be represented safely:

```text
GitHub.fetch_file(... path=PATH, ref=BRANCH)         # obtain current blob SHA/content
GitHub.update_file(... path=PATH, content=CONTENT,
                   sha=CURRENT_BLOB_SHA,
                   branch=BRANCH,
                   message=CONVENTIONAL_COMMIT)
GitHub.fetch_file(... path=PATH, ref=RESULT_COMMIT)  # readback
GitHub.fetch_commit(... commit_sha=RESULT_COMMIT)    # diff audit
```

Markdown, skill, and workflow-policy files are ordinary UTF-8 repository files for this rule. Use this path immediately when complete replacement content is safe; if a large/truncated file makes whole-file replacement unsafe, do not reconstruct it from excerpts or probe alternate transports—use the surgical fallback below.

Do not give the owner a patch/file to apply and do not ask the owner to commit/push this change.

#### Make one atomic multi-file commit

Do **not** serially call the contents API on the target branch when the intended change is one commit. Use Git data directly:

```text
1. Read exact target branch HEAD and its tree SHA.
2. GitHub.create_blob(...) once per replacement/new file.
3. GitHub.create_tree(base_tree_sha=BASE_TREE, tree_elements=[...]).
4. GitHub.create_commit(message=CONVENTIONAL_COMMIT,
                        tree_sha=NEW_TREE,
                        parent_sha=OLD_HEAD).
5. Re-read the target branch and require it still equals OLD_HEAD.
6. GitHub.update_ref(branch_name=TARGET_BRANCH,
                     sha=NEW_COMMIT,
                     force=false).
7. GitHub.compare_commits(base=OLD_HEAD, head=NEW_COMMIT).
8. GitHub.fetch_commit(commit_sha=NEW_COMMIT) and audit the exact changed-file/diff surface.
```

This is the canonical method for cohesive multi-file Polaris changes made from ChatGPT.

#### Propagate repository-wide authority changes to the active working branch

When ChatGPT changes repository-wide workflow/process authority on the default branch while a Spec/feature branch is active—including `AGENTS.md`, `.agents/skills/**`, process documentation, or comparable cross-cutting policy—propagate the finalized authoritative file versions into the active branch before resuming work there. Do not leave the active branch running stale workflow authority.

Use clean Git-data construction from the active branch HEAD, replacing only the finalized authoritative blobs from the default branch; do not merge temporary transport commits. If the active branch has divergent edits to the same authority files, compare first and resolve deliberately rather than overwriting them.

#### Make a surgical edit to a large file on the default branch when full-content reconstruction is unsafe

Preserve untouched bytes instead of manually reconstructing a large file from excerpts.

For the current ChatGPT GitHub runtime, use this registered one-shot default-branch transport:

```text
1. Read and pin the exact default-branch HEAD; require the temporary workflow/script paths to be absent.
2. GitHub.create_file(... branch=DEFAULT_BRANCH) a minimal push-triggered probe workflow, then require a successful probe run.
3. GitHub.create_file(... branch=DEFAULT_BRANCH) a temporary deterministic edit script containing exact anchors/assertions.
4. GitHub.update_file(...) the registered workflow to a minimal armed job that checks out DEFAULT_BRANCH,
   runs the temporary script, runs `git diff --check`, audits the target diff, removes both temporary files,
   commits the intended target edit plus both deletions, and pushes DEFAULT_BRANCH.
5. Read the armed workflow run and require success.
6. Re-read DEFAULT_BRANCH and fetch the resulting commit/diff; require only the intended target edit and
   removal of the temporary workflow/script.
7. Re-read the edited target file from the resulting commit.
```

Keep substantive edit logic out of workflow YAML; the temporary script is the deterministic payload. Do not introduce the workflow only on a non-default scratch branch; that path did not schedule reliably in this runtime. This fallback intentionally uses temporary transport commits and leaves no workflow/script in the final tree. Use it only when direct `update_file` or direct Git-data construction would risk whole-file corruption.

For non-default target branches, use direct `update_file` or clean Git-data construction when safe. If neither can safely represent the edit, that case is not covered by this playbook and permits one targeted capability check under the Non-Discovery Rule.

#### Create/update GitHub issues and durable comments

Use the connector directly:

```text
GitHub.fetch_issue(...)
GitHub.fetch_issue_comments(...)
GitHub.update_issue(...)
GitHub.add_comment_to_issue(...)
GitHub.update_issue_comment(...)
```

After any correctness-critical comment mutation, fetch the issue comments again and verify the exact marker/body/state expected by the governing workflow. The ChatGPT Session Ledger is always updated this way; never ask the owner to edit it manually.

#### Create, inspect, and merge pull requests

Use:

```text
GitHub.create_pull_request(...)
GitHub.fetch_pr(...)
GitHub.get_pr_diff(...) or GitHub.fetch_pr_patch(...)
GitHub.merge_pull_request(... expected_head_sha=EXPECTED_HEAD)
```

Use the workflow's required merge method and guards. Do not hand ordinary PR creation/merge back to the owner merely because `gh` could also perform it.

#### Run repository-local validation or other repository commands

Use GitHub Actions as the canonical ChatGPT-side execution substrate when the command can be reproduced from durable remote state.

```text
1. Bind the exact workflow baseline/candidate/ref before execution.
2. Create or reuse a temporary scratch branch from that exact candidate when an ephemeral workflow file is required.
3. Add a push-triggered scratch workflow that checks out the exact candidate, verifies the expected SHA/baseline/clean state, and provisions the repository's locked tool/runtime contract.
4. Execute the complete active skill semantics, not merely a convenient command subset. Preserve required preflights, manifests, delegated child gates, environment guards, and terminal reporting.
5. Inspect the Actions run/jobs/logs and require every mandatory step to reach the owning workflow's valid terminal result.
6. Keep ephemeral workflow files and execution plumbing on the scratch branch only; never merge them into the canonical branch merely to obtain command execution.
7. If execution produces intended repository content, promote only the intended generated blobs/content through the normal clean-commit path. Otherwise treat the Actions result as verification evidence only.
8. Remote scratch-branch cleanup remains optional owner housekeeping when ref deletion is connector-missing; it never blocks the authoritative workflow.
```

For `$verify-code`, for example, an Actions run must still perform its baseline-derived target resolution, Contract Transition / Consumer Closure work when applicable, diff hygiene, test-service preflight, targeted Ruff/Mypy/pytest, applicable `$verify-architecture`, coding-standards verification, and exact candidate readback. A workflow that only runs Ruff/Mypy/pytest does **not** establish `$verify-code` completion.

#### Run genuinely owner-machine-only commands

Use a human shell handoff only when the active workflow requires a fact or command that cannot be reproduced safely through the connector or GitHub Actions. Give only the missing operation in one fail-closed subshell, normally shaped as:

```bash
(
  set -euo pipefail
  ROOT="$(git rev-parse --show-toplevel)"
  cd "$ROOT"

  test "$(git branch --show-current)" = "<expected-branch>"
  test "$(git rev-parse HEAD)" = "<expected-full-sha>"
  test -z "$(git status --porcelain)"

  <only the exact owner-local command(s) required by the active workflow>
)
```

Legitimate reasons include required knowledge of uncommitted owner-local state, credentials/secrets not available to an authorized runner, machine-specific hardware, or a required local service that cannot be safely/reproducibly provisioned remotely. Add only the guards needed by the owning skill. Do not hand the entire workflow to the owner. The owner returns the complete output; ChatGPT consumes it as evidence and resumes from the first incomplete stage.

#### Persist canonical receipts that depend on a repo-local finalizer

Do not create a downloadable ZIP, patch, or handoff file for the owner.

When the governing skill requires a canonical repository-local script that ChatGPT cannot execute in GitHub Actions or another available runtime because a genuine owner-local prerequisite remains:

1. ChatGPT prepares every remotely possible prerequisite and durable input itself;
2. provide one scoped local subshell that reconstructs any transient inputs from durable state or inline deterministic data, runs the canonical script, performs its fixed-point guards, and when appropriate POSTs the resulting receipt through the owner's authenticated `gh` CLI;
3. the owner returns command output only;
4. ChatGPT independently reads the persisted receipt through the GitHub connector and completes the remaining durable lifecycle work.

Do not ask the owner to download intermediate files merely to bridge ChatGPT to the local finalizer.

#### Delete a temporary remote branch

Remote ref deletion is local-only in this runtime. Use exactly this shape:

```bash
(
  set -euo pipefail
  ROOT="$(git rev-parse --show-toplevel)"
  cd "$ROOT"
  git push origin --delete <temporary-branch>
  git fetch --prune origin
)
```

Only ask for this after ChatGPT has verified that the temporary branch is not authoritative and is not required for recovery.

#### Reconcile GitHub Project projection

Routine lifecycle skills do not perform eager Project synchronization. Under current Polaris policy, normal automatic Project reconstruction is deferred to `$spec-merge-cleanup`; an explicit human-requested board refresh is the other ordinary entry.

The current ChatGPT connector does not expose the required Projects v2 mutation surface. At an authorized `$project-tracking` boundary, read the current `$project-tracking` contract and provide its exact `gh`/GraphQL Project commands in one scoped local subshell. Do not rediscover Project mechanics during every intermediate skill, and do not project intermediate lifecycle state merely because the board can lag.

#### Update the ChatGPT Session Ledger

Use this exact mechanical sequence whenever Phase 2 requires synchronization:

```text
1. GitHub.fetch_issue_comments(Session Ledger issue).
2. Require exactly one state-marker comment and read its Generation.
3. Build the complete replacement body; increment Generation exactly once.
4. GitHub.update_issue_comment(comment_id=STATE_COMMENT_ID, comment=NEW_BODY).
5. GitHub.fetch_issue_comments(Session Ledger issue) again.
6. Require the same comment ID, state marker, new Generation, and intended body/state.
```

Never create a new ledger comment for ordinary synchronization and never delegate this mutation to the owner.

### User-Handoff Threshold

The owner should receive shell commands only for work that is genuinely local-only or connector/runtime-missing, principally:

- owner checkout/worktree state that the workflow specifically requires and that cannot be reconstructed from durable remote state;
- repository commands whose required inputs depend on owner-only credentials, uncommitted local files, machine-specific hardware, sockets, or services that cannot be safely/reproducibly provisioned in GitHub Actions;
- remote branch deletion;
- authorized GitHub Projects v2 mutation;
- another operation that the canonical ChatGPT-side connector/Actions method actually attempted and proved unavailable.

Ordinary repo-local tests, linters, type checks, repository scripts, and service-free verification are **not** human handoffs merely because ChatGPT cannot execute inside the owner's checkout. Run them through an exact-candidate GitHub Actions workflow when the active skill permits that execution substrate.

Do **not** give the owner repository patches, replacement source files, ZIPs, generated downloads, copy/paste implementation, `git commit`, or `git push` instructions for work ChatGPT can mutate or execute remotely. The standing collaboration model is: **ChatGPT does everything mechanically available on its side; the owner runs only the smallest scoped local subshell that genuinely cannot be executed or established remotely.**

## Core Principle

Reconstitute from durable project state first, then restore the minimum necessary ephemeral state from the dedicated **ChatGPT Session Ledger** GitHub singleton.

Durable repository/tracker state remains authoritative. The ledger exists only for context that would otherwise be stranded in a conversation, such as:

- the exact task or thread that was in progress;
- the exact workflow checkpoint at which work stopped;
- the last local-only command/result needed to resume safely;
- an uncommitted or unpushed local state that is not visible remotely;
- unreferenced Git blobs, trees, or other temporary recovery handles needed to recover a candidate exactly;
- a temporary decision, sequencing choice, or working assumption that has not yet been persisted to its authoritative artifact;
- a tool/capability handoff that requires the user to perform the next mechanical step outside the agent's available tooling.

The ledger must contain **one active continuation record**, not an accumulating session history. Once older context is durably represented elsewhere or no longer describes the active thread, remove it from the ledger rather than preserving it as background narrative.

If remembered conversation or the ChatGPT Session Ledger conflicts with current durable state, surface the conflict and prefer the applicable authority defined by `AGENTS.md` unless the user explicitly resolves it otherwise.

## Polaris-Wide Meta-Level Attention

A reconstituted ChatGPT Polaris session carries a standing **Polaris-wide meta-level Attention** obligation for the entire active session.

The current task is the immediate work surface, **not the boundary of attention**. While doing the work in front of it, ChatGPT must also continuously evaluate what the current observation implies for Polaris as a whole. This includes product intent, domain semantics, architecture, authority, code, persistence, APIs, tests, documentation, Living Entity Wiki knowledge, workflow skills, tracker state, lifecycle/governance mechanics, and downstream/upstream contracts.

The operating model is:

```text
do the current work correctly

AND, continuously:

current observation
    ↓
compare against the Polaris system model
    ↓
detect material inconsistency / drift / latent risk / missing ownership / opportunity
    ↓
raise Attention when warranted
    ↓
disposition it to the right lifecycle or no action
```

In particular, do not wait for the repository owner to notice a broader consequence first. Surface materially relevant findings such as:

- an inconsistency elsewhere in Polaris exposed by the current work;
- architecture, domain language, persistence, APIs, docs, wiki, skills, tests, or tracker state no longer telling the same story;
- duplicate or competing sources of truth;
- stale authority or assumptions invalidated by a later decision;
- ownership, boundary, dependency, lifecycle, or abstraction drift;
- a workflow/process defect revealed by an otherwise local failure;
- a downstream artifact silently depending on semantics that no durable authority owns;
- repeated symptom fixes indicating an earlier governing defect;
- technically valid work that is wrong for Polaris as a product;
- unnecessary machinery, scope creep, or a violation of established lean/bottom-up principles;
- latent temporal, concurrency, correction, replay, auditability, lineage, authority, or fail-closed consequences;
- a materially useful opportunity that should become Attention even though it is outside the immediate task.

Use a materiality threshold rather than generating speculative noise:

> **Would a competent architect who understood Polaris as a whole want this brought to their attention now?**

If yes, surface it. If no, continue without distraction.

Polaris-wide Attention does **not** authorize uncontrolled scope expansion or unrelated mutation. A finding must be dispositioned appropriately: address it in current work when it is truly part of the current obligation; treat it as a blocker when it invalidates current work; route it through the appropriate architecture/planning/workflow lifecycle when separate action is required; capture valuable deliberate deferral through the existing future-work mechanism; or take no action when it is not material.

This is a standing collaboration/reasoning obligation, not conversational state and not a substitute for the product's durable Attention/domain artifacts. It survives session loss by virtue of this document and must be restored during every session reconstitution.

## Authority

Start with `AGENTS.md` and follow its authority model.

In particular:

- code, configuration, executable checks, and relevant tests describe implementation reality;
- accepted ADRs define active architectural decisions;
- `docs/current/` describes current architecture;
- `wiki/entities/` contains derived architectural knowledge;
- workflow artifacts and native tracker relationships define delivery state;
- the GitHub Project is an operational projection and does not override authoritative repository or tracker state;
- the ChatGPT Session Ledger is an ephemeral recovery aid and never overrides any of the above.

Do **not** read `CONTEXT.md` merely because a session is being reconstructed. Follow the `AGENTS.md` rules for when canonical domain vocabulary actually requires it.

## ChatGPT Session Ledger Singleton

The mutable ledger lives outside Git history in exactly one dedicated open GitHub issue.

Canonical singleton identity:

```text
Title: ChatGPT Session Ledger
Issue body marker: <!-- polaris-chatgpt-session-ledger-control:v1 -->
State comment marker: <!-- polaris-chatgpt-session-ledger-state:v1 -->
```

The singleton is ChatGPT recovery infrastructure only. It must not be treated as a Wayfinder, Spec, Ticket, verification/review artifact, dependency authority, Project Delivery artifact, or GitHub Project item.

Resolve the singleton from current GitHub state. Require exactly one open issue with the exact title and control marker. Multiple matching issues fail closed.

The issue must contain exactly one machine-managed state comment with the state marker. Zero state comments are valid only during first-time bootstrap when the current continuation state can be reconstructed safely; otherwise missing state is invalid. Multiple state comments fail closed.

### Ledger State Contract

The state comment contains exactly one current continuation record using this shape:

```text
<!-- polaris-chatgpt-session-ledger-state:v1 -->
# Current Session Ledger

**Version:** 1
**Generation:** <positive integer>
**Maintained at:** <RFC 3339 timestamp with timezone offset>

## Active Continuation Record

**Active branch:** <branch | None>
**Active artifact:** <canonical issue/PR/artifact reference | direct task>
**Workflow owner:** <$skill | direct>
**Workflow checkpoint:** <precise completed stage / next suspended stage>
**Last durable commit:** <full SHA | None>
**Baseline / anchor:** <full SHA or durable artifact anchor | None>
**Candidate state:** <durable candidate/recovery description | None>
**Expected next transition:** <one concise transition>

## Session-Only Evidence

- <only current evidence that cannot be recovered cheaply from durable authority>

## Recovery Handles

- <exact local/unreferenced recovery handle needed to resume | None>
```

`Generation` is monotonic. Every successful synchronization increments the prior generation exactly once. `Maintained at` records when that generation was durably written; elapsed time alone never triggers an update.

The routing coordinates are not workflow authority. Verify every applicable coordinate against current durable state before using ledger prose.

Treat the record as stale when any coordinate that should still be true is contradicted by durable state, for example:

- the active artifact has closed or changed lifecycle owner;
- the declared branch no longer exists or no longer points at the recorded durable candidate;
- the baseline/anchor no longer matches the durable workflow artifact;
- the recorded checkpoint has already been completed durably;
- the expected next transition is no longer reachable from the current native frontier.

A stale coordinate does not authorize guessing a replacement from the rest of the ledger. Reconstruct the replacement from durable repository/tracker state, report the conflict when material, and continue from the smallest correct next action.

## Phase 1 — Session Reconstitution

### 1. Establish repository state

Inspect the current default branch and recent relevant commits.

When the active workflow has a durable branch and baseline/anchor, compare that exact baseline/anchor to the branch `HEAD` and confirm the changed-file surface before assuming what work is present. Do not substitute a broad recent-commit scan when a durable comparison anchor exists.

Determine whether the user's local working tree may contain uncommitted or unpushed state that cannot be observed remotely. Never assume remote repository state includes those changes.

### 2. Load repository operating policy

Read `AGENTS.md` before interpreting project state or making changes.

#### Mandatory workflow hardening context

During every ChatGPT-hosted Polaris session reconstitution, read every current repository file matching:

```text
docs/process/common-sense-invariant-hardening*.md
```

The glob is intentional. Do not hard-code the current file count or rely on prior-session memory; later hardening addenda must become part of bootstrap automatically. Read the canonical `docs/process/common-sense-invariant-hardening.md` index and all matching base/addendum records it governs before using, evaluating, or modifying Polaris workflow skills.

These documents are mandatory process-hardening context for the session. They do not replace the active workflow contract: each current `SKILL.md` remains authoritative for its own procedure.

#### Skill Authorization Override

For every ChatGPT-hosted Polaris working session reconstituted through this document, the repository owner grants the following temporary owner-level workflow override. Reading this section is sufficient owner authorization for that session; no separate per-session restatement is required unless the owner explicitly revokes or changes it.

For this ChatGPT-hosted Polaris working session, I authorize a temporary owner-level workflow override for repository skills that require delegation to, certification by, or review from a fresh or independent sub-agent when this ChatGPT runtime cannot spawn such an agent.

Under this override:

* ChatGPT may perform the required delegated, certification, adversarial-review, or verification work itself in a separate deliberate pass.
* ChatGPT must re-read and independently evaluate the authoritative inputs for that pass rather than relying on its earlier drafting conclusions.
* The substitute pass must remain non-mutating whenever the original sub-agent role is required to be non-mutating.
* ChatGPT must not claim that a genuinely independent or fresh sub-agent performed the work. It must identify the result as an owner-authorized in-session substitute.
* A skill requirement whose sole purpose is agent independence or freshness may therefore be satisfied for this session by this owner-authorized substitute review.
* All substantive correctness requirements, coverage requirements, fail-closed checks, repository/tracker guards, architecture requirements, verification criteria, and output contracts of the skill remain in force. This override removes only the requirement for a separate agent identity/context where that capability is unavailable.
* This authorization applies to `$to-tickets`, `$implement-ticket`, `$verify-spec`, `$review-spec` and any other Polaris workflow skills encountered during this ChatGPT session that have the same unavailable-sub-agent dependency.
* This authorization does not permit ChatGPT to bypass a genuine product, architecture, safety, repository-state, or human-approval decision that the governing workflow assigns to me.

I accept the reduced independence inherent in having the same ChatGPT instance perform the substitute verification pass and authorize the work to continue on that basis.

#### Codex CLI Authorization Boundary

ChatGPT must **never invoke, embed, or instruct execution of `codex`, `codex exec`, or any equivalent command that launches the repository owner's Codex CLI unless the repository owner has explicitly authorized that Codex CLI invocation in the current conversation**.

The repository owner's Codex CLI quota, credits, and tokens are owner-controlled resources. ChatGPT has no standing authority to spend them merely because a workflow could be delegated to Codex or because a local shell command is otherwise available.

In particular:

* a repository skill reference such as `$spec-contract`, `$verify-spec`, or another `$skill` is **not** authorization to launch Codex CLI;
* the owner-authorized in-session substitute-agent override above is **not** authorization to launch Codex CLI;
* inability to spawn a fresh or independent agent is **not** authorization to launch Codex CLI;
* a connector or local-tool limitation is **not** authorization to launch Codex CLI;
* do not hide a Codex CLI invocation inside a larger Bash block, helper script, subshell, or generated command sequence.

When a workflow step can be completed in the active ChatGPT runtime, through connected tooling, or through ordinary non-Codex local commands, use those mechanisms instead.

If a required step genuinely cannot be completed without invoking Codex CLI, stop before constructing an executable Codex command and ask the repository owner for explicit authorization. State what Codex would be used for and why the available ChatGPT, connector, and local non-Codex mechanisms are insufficient.

Authorization is specific to the requested invocation and does not create standing permission for later Codex CLI use unless the repository owner explicitly says otherwise.

An accidental or unauthorized Codex CLI invocation is a process defect. Do not repeat it, retry it, or consume additional Codex quota while attempting recovery. Preserve any successful work completed before the invocation, determine whether the Codex attempt mutated state, and continue through non-Codex mechanisms where possible.

Load narrower skills only when their responsibility is relevant to the active work. Prefer current skill contracts over remembered behavior from earlier sessions.

Common workflow skills include:

- `$wayfinder`
- `$to-specs`
- `$to-tickets`
- `$implement-ticket`
- `$verify-spec`
- `$review-spec`
- `$spec-merge-cleanup`
- `$architecture-remediation`
- `$project-tracking`

For source-code changes, follow `$coding-standards`.

For commits, follow `$conventional-commits` in `.agents/skills/conventional-commits/SKILL.md`. Do not reconstruct commit-message rules from memory or restate a divergent local convention.

For Living Entity Wiki work, use the current contracts for `$wiki-sync`, `$wiki-lint`, and `$wiki-synthesize` as applicable.

### 3. Identify the active durable artifacts

Determine which repository and tracker artifacts represent the work currently in progress.

Depending on the task, inspect only the smallest relevant set, such as:

- active Wayfinder maps;
- Specs and their dependency relationships;
- Tickets and Ticket baselines;
- verification or review receipts;
- current architecture documents and ADRs;
- `wiki/index.md` and relevant `wiki/entities/` pages;
- research or audit documents under `docs/research/`;
- process guidance under `docs/process/`;
- relevant GitHub Issues, pull requests, and Project projection state.

Do not perform a broad repository tour when narrower evidence is sufficient.

### 4. Reconstruct workflow state from durable evidence

Treat the delivery workflow as a state machine rather than assuming a one-way pipeline.

The normal path is approximately:

```text
$wayfinder
    ↓
$to-specs
    ↓
$to-tickets
    ↓
$implement-ticket
    ↓
$verify-spec
    ↓
$review-spec
    ↓
$spec-merge-cleanup
```

Verification failure, review findings, remediation, or genuine architectural ambiguity may cause re-entry into an earlier state.

Keep these concepts distinct:

- **technical dependency** — what is allowed to advance;
- **project focus** — what the team has chosen to advance now;
- **workflow state** — where an artifact is in its lifecycle;
- **Project state** — the board's projection of durable state.

Do not invent dependency edges to express project focus or work-in-progress preference.

### 5. Reconstruct architectural context only as needed

Use Wayfinders for genuine architectural uncertainty, not as a mandatory wrapper around ordinary cleanup or implementation.

Typical routing:

- obvious mechanical cleanup → direct change or focused Spec;
- dead or stale code with clear ownership → direct cleanup;
- structural refactor with known semantics → Refactor Spec;
- implementation of already accepted architecture → implementation work;
- unclear canonical ownership → Wayfinder;
- competing abstractions or unresolved boundaries → Wayfinder;
- implementation that would need to invent or change durable semantics → architecture re-entry.
Do not infer architectural uncertainty merely from file size, complexity, duplication, or poor metrics.

### 6. Restore the ChatGPT Session Ledger

After durable state is reconstructed, resolve the ChatGPT Session Ledger singleton and read its state comment.

Use it only to restore the exact stopping point and session-only context that cannot be recovered cheaply or reliably from the repository/tracker.

#### Workflow-Specific Re-entry Coordinates

Use the applicable workflow's current `SKILL.md` as authority for exact guards and semantics. The bundles below are only the minimum recovery coordinates that should normally be checked before reading broader context.

| Workflow owner | Minimum durable re-entry bundle |
| --- | --- |
| `$wayfinder` | active Wayfinder issue/map; current decision/handoff state; native blockers/dependents relevant to the active decision; current governing branch/commit when repository work is involved |
| `$to-specs` | governing Wayfinder/handoff; current derived/remediation Spec children; native dependency state; current branch/anchor required by the handoff |
| `$to-tickets` | parent Spec; Spec branch/workspace baseline; current native ticket children; ticket dependency relationships; current Spec lifecycle state |
| `$implement-ticket` | current default-branch `HEAD`; Ticket branch `HEAD`; Ticket baseline; native direct parent; ticket open/closed state; parent native child frontier; direct ticket dependents; remediation checkpoint/root state when applicable |
| `$verify-spec` | Spec branch candidate `HEAD`; Spec/workspace baseline; Spec state; open implementation/remediation children; current verification receipt/checkpoint or proof state; native blockers relevant to verification actionability |
| `$review-spec` | exact verified candidate `HEAD`; latest valid verification receipt; Spec state; current review/remediation artifact state; open remediation children when any exist |
| `$spec-merge-cleanup` | exact reviewed candidate `HEAD`; current default-branch `HEAD`; durable review/merge authorization state; current PR/merge state when applicable; remaining child/remediation state |
| `$architecture-remediation` | blocked artifact; exact unresolved architecture question/conflict; governing authority set; current remediation/decision artifact and native relationship state; active `independent-architecture-remediation-checkpoint:v1` when Independent-Spec owner-guided remediation is in progress |

For an active branch with a durable SHA baseline, compare baseline → `HEAD` and confirm the exact changed-file set. For a suspended workflow, recover the owning skill's current contract and resume at the first incomplete authoritative stage rather than replaying already completed stages.

#### Session-Only Evidence

After the coordinates validate, restore only evidence that is not durably recoverable, such as:

- local clean/dirty working-tree state;
- results of local-only tests, profiling, or service probes;
- an unpushed commit or local branch position;
- exact unreferenced Git blob/tree IDs or equivalent recovery handles;
- the exact output of a human-run `gh`/shell step required by a connector boundary;
- a temporary assumption that has not yet acquired an authoritative home.

For every ledger fact that matters to the resumed task:

1. verify repository/tracker facts against current durable state;
2. treat local-only state as provisional unless the ledger contains the exact result from the prior session or the user confirms current state;
3. discard or revise facts that have become stale, contradicted, completed, or durably persisted elsewhere;
4. continue from the smallest correct next action rather than replaying completed work.

The user should not need to provide a separate `LAST ACTIVE THREAD` when the ledger is current.

### 7. Check for conflicts before continuing

Before resuming work, identify any material conflict among:

- the ChatGPT Session Ledger;
- current repository state;
- current tracker state;
- applicable skill contracts;
- architectural authorities.

Surface genuine conflicts explicitly rather than silently selecting whichever state is easiest to continue from.

### 8. Repair and activate continuity

After reconstruction, compare the ledger coordinates with the recovered authoritative state.

If the ledger is stale but the correct replacement can be established safely from durable state plus trustworthy current-session evidence, synchronize it immediately before substantive work continues. If missing ephemeral evidence prevents safe repair, report the gap rather than inventing replacement state.

After a valid or repaired ledger is established, retain its exact normalized continuation state as the in-session `LAST_SYNCED_CONTINUATION_STATE` and activate **Phase 2 — Active Session Continuity** for the remainder of the ChatGPT working session.

### 9. Report the recovered state concisely

The initial response after reconstitution should state only:

- the current repository/workflow state;
- the active objective;
- the exact stopping point;
- the next logical action;
- any genuine uncertainty or blocker.

Do not respond with a generic Polaris overview or repeat every artifact inspected.

## Phase 2 — Active Session Continuity

### Continuity Invariant

After successful reconstitution, the ChatGPT agent owns synchronization of the singleton for the rest of the active ChatGPT working session.

Do **not** wait until the conversation appears likely to end. A ChatGPT session may terminate unexpectedly. Continuation state must be checkpointed when it materially changes.

Freshness is **state-based, not time-based**:

```text
CURRENT_CONTINUATION_STATE != LAST_SYNCED_CONTINUATION_STATE
```

Elapsed time alone is never a synchronization trigger. A long interval with no continuation-state change may require no write; several meaningful workflow transitions in a short interval may require several writes.

### Mandatory Synchronization Points

At each event below, recompute the current continuation state. If it differs from `LAST_SYNCED_CONTINUATION_STATE`, synchronize the singleton before proceeding past the boundary.

| Event | Required action |
| --- | --- |
| Active artifact changes | Synchronize |
| Workflow owner changes | Synchronize |
| Active branch changes | Synchronize |
| Baseline/anchor becomes known or changes | Synchronize |
| Durable candidate commit/`HEAD` changes | Synchronize |
| Workflow checkpoint materially advances | Synchronize |
| Expected next transition changes | Synchronize |
| A workflow completes and another becomes next | Synchronize |
| User supplies local-only evidence required for continuation | Synchronize |
| Local-only validation, profiling, service-probe, or test evidence becomes important to re-entry | Synchronize |
| Uncommitted or unpushed state becomes important to continuation | Synchronize |
| Unreferenced Git blobs/trees or another fragile temporary recovery handle are created | **Synchronize immediately** |
| Previously ephemeral state becomes durable elsewhere | Synchronize and remove redundant ledger evidence |
| A human handoff is reached | Synchronize **before returning control** |
| A hard blocker is reached | Synchronize **before returning control** |
| A completed response establishes a new exact stopping point | Synchronize **before returning control** |
| No meaningful ephemeral continuation state remains | Synchronize to the minimal current durable coordinates |

A state transition that matches a Mandatory Synchronization Point is the trigger. Do not replace this table with a subjective test such as “worth preserving,” “important enough,” or “session seems nearly finished.”

### Fragile-State Immediate Checkpoint

Fragile state is session-only state that may become unrecoverable if the current conversation or tool context disappears, including:

- unreferenced Git blob/tree/commit objects;
- temporary candidate-tree identifiers;
- local-only command output required to avoid repeating or mis-sequencing work;
- unpushed commits or branch positions not observable from the remote;
- other opaque recovery handles whose identifiers exist only in the active conversation/tool context.

When such state is created or becomes necessary for exact continuation, synchronize it **immediately**. Do not wait for a later workflow handoff.

If the state cannot be durably represented safely, record the limitation and the smallest reproducible reconstruction path instead of implying that the exact candidate is recoverable.

### Synchronization Protocol

For every required synchronization:

1. resolve and revalidate the canonical singleton issue;
2. read the one state-marker comment and its current `Generation`;
3. derive `CURRENT_CONTINUATION_STATE` from current authoritative state plus only necessary session-only evidence;
4. remove stale or now-durable evidence rather than appending history;
5. increment `Generation` by exactly one;
6. set `Maintained at` to the current RFC 3339 timestamp with timezone offset;
7. replace the existing state comment in one write;
8. read back that exact comment;
9. require the persisted body to equal the intended body exactly;
10. only after exact readback succeeds, set `LAST_SYNCED_CONTINUATION_STATE` to the newly persisted normalized state.

Do not create a new comment for every synchronization. The singleton keeps exactly one mutable state comment so it represents current continuation state rather than a session history.

If the write succeeds but exact readback fails, do not assume continuity state is healthy. Report the mismatch and recover the canonical state before relying on the ledger again.

### ChatGPT Return Guard

Once Phase 2 is active, the ChatGPT agent must not intentionally return control at a meaningful continuation boundary with stale ledger state.

Before a response that:

- asks the user to run a command whose result is required to continue;
- hands off to another workflow or lifecycle owner;
- reports a hard blocker;
- reports completion;
- or otherwise establishes a new exact stopping point,

compare `CURRENT_CONTINUATION_STATE` with `LAST_SYNCED_CONTINUATION_STATE`.

If they differ, synchronize first.

The practical guard question is:

```text
Would a fresh ChatGPT session need a different continuation record after this response?
```

If yes, synchronization is required before the response is treated as the stopping point.

### Ledger Hygiene

At every synchronization:

- keep exactly one Active Continuation Record;
- replace superseded continuation notes rather than appending history;
- remove facts that have acquired another durable authoritative home unless still needed as re-entry coordinates;
- preserve only current session-only evidence needed to avoid repeating completed local work;
- use full commit SHAs for durable commit/baseline coordinates;
- store exact opaque recovery handles when they are necessary and safe to persist;
- never turn the ledger into a substitute verification receipt, review record, architecture decision, root checkpoint, workflow state store, or Project state store.

If there is no meaningful ephemeral continuation state, record that explicitly and keep the ledger minimal.

### Deferred Future Work Capture

Whenever Polaris work consciously defers something valuable for later, do not leave that future work only in conversation or in the ChatGPT Session Ledger.

Before moving past a thread that reaches a conclusion such as **“good idea, deliberately not now”**, ask:

> **Is this already durably represented somewhere?**

Check current durable lifecycle and Project state first. An existing Wayfinder, Spec, Ticket, issue, pull request, or Idea & Intake item counts only when it actually represents the deferred work. Do not create a duplicate intake item for work that is already represented.

If no durable representation exists and the deferred work is genuinely worth remembering, create an **Idea & Intake** item before moving on.

The intake item should preserve enough context to recover what should eventually be revisited, why it is valuable, why it is deliberately deferred now, and any known prerequisite or trigger for reconsidering it.

Idea & Intake is the durable future-work inbox, not authorization to implement the item and not a reason to manufacture a Spec prematurely. Do not capture speculative noise merely because it was mentioned.

During session reconstitution, if restored session-only evidence reveals valuable work that was consciously deferred but never durably represented, apply this same rule before discarding that evidence from the ledger.

## Collaboration Boundary

Perform work directly through available repository, GitHub, and other connected tooling whenever possible. Apply the **ChatGPT Runtime Capability Contract** above before considering any user handoff. For operations listed there, capability discovery is already complete; only an actual unavailable/unsupported result justifies re-evaluating the mechanical path.

Repository mutation ownership is explicit: when the available ChatGPT tooling can safely create, edit, delete, commit, push, or otherwise mutate repository/tracker state, the agent must perform that work directly, subject to the active workflow's own sequencing and guards. Do not substitute a patch, downloadable repository file, generated diff, copy/paste implementation, or instructions asking the user to apply/commit/push those changes merely because local execution would also be possible. Only provide such artifacts or mutation commands when the user explicitly asks for them or when the required mutation genuinely cannot be performed through the available tooling.

The normal collaboration model is:

1. the agent performs every safe workflow/repository/tracker step that its available tools support;
2. when a required step depends on local state or an unavailable connector capability, the agent gives the user the exact command(s) needed to perform only that missing step;
3. the user runs the command(s) and returns the output;
4. the agent treats that output as evidence and resumes the workflow from the correct durable checkpoint rather than restarting completed work.

A connector limitation is not, by itself, a reason to abandon an otherwise executable workflow. For example, when the connected GitHub tool cannot perform an operation that the authenticated GitHub CLI can perform, provide the exact `gh` commands for the user to run outside ChatGPT and continue from the returned result.

When the user explicitly asks for the literal `gh`/Bash commands that a workflow or skill would execute, answer at that command layer. Do not substitute another skill invocation or redirect the user back through the workflow when the requested underlying commands can be provided safely.

Ask the user to run local commands only when the required state or operation is unavailable remotely, such as:

- uncommitted local changes;
- local test execution;
- profiling;
- local repository-analysis tools;
- environment-specific scripts or services;
- GitHub operations that are supported by the user's authenticated `gh` CLI but not by the available connector.

When local execution is required:

- provide exact Linux/bash commands;
- **every Bash command block must be a subshell using `(...)`**;
- make the block fail closed where practical (`set -euo pipefail`, explicit expected-state checks, or equivalent safeguards);
- minimize the commands to the missing operation rather than handing the whole workflow back to the user;
- use the returned output as evidence before mutating subsequent durable state.

## Workflow Skill Modification Guard

Before proposing, reviewing, or performing any modification to a repository workflow skill under `.agents/skills/`—or to helper code whose semantics can change a workflow skill's transitions—read the current `docs/process/common-sense-invariant-hardening.md` first.

Treat that document as mandatory design guidance for the modification. In particular:

- identify the consequential transition, PASS, skip, routing choice, mutation, or closure being hardened;
- close the authoritative candidate universe and any nested universe before counting dispositions;
- require explicit evidence-backed dispositions for escape states such as inherited, not-applicable, already-covered, or no-work;
- test whether the proposed state can self-certify semantic correctness and require an independently checkable witness when judgment remains;
- preserve observed failures until they receive an explicit causal disposition rather than allowing later scope narrowing to erase them;
- preserve delegated-gate ownership when a parent workflow relies on another skill's procedure or terminal result;
- harden the earliest authoritative transition that allowed the defect to escape instead of encoding the latest historical symptom.

The hardening record is design guidance, not an executable substitute for the skill being changed. The current `SKILL.md` remains authoritative for the workflow's procedure, and any new invariant must be enforced locally by the transition-owning skill rather than added only to the hardening record.