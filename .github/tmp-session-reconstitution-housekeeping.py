from pathlib import Path

PATH = Path("docs/process/session-reconstitution.md")
text = PATH.read_text(encoding="utf-8")


def replace_section(source: str, start: str, end: str, replacement: str) -> str:
    start_count = source.count(start)
    end_count = source.count(end)
    if start_count != 1 or end_count != 1:
        raise SystemExit(
            f"section anchors not unique: {start!r}={start_count}, {end!r}={end_count}"
        )
    a = source.index(start)
    b = source.index(end, a)
    return source[:a] + replacement.rstrip() + "\n\n" + source[b:]


atomic = r'''#### Make one atomic multi-file commit

Do **not** serially call the contents API on the target branch when the intended change is one commit. Use Git data directly, and validate the complete candidate before moving any branch ref:

```text
1. Read exact target branch HEAD and its tree SHA.
2. Construct the exact replacement bytes deterministically. When complete target bytes already exist in ChatGPT scratch/container, compute their expected Git blob SHA before upload. For large or escape-sensitive UTF-8 content, base64-encode those exact bytes and call GitHub.create_blob(..., encoding=base64); require the returned blob SHA to equal the expected Git blob SHA before using it.
3. GitHub.create_blob(...) once per replacement/new file.
4. GitHub.create_tree(base_tree_sha=BASE_TREE, tree_elements=[...]).
5. GitHub.create_commit(message=CONVENTIONAL_COMMIT,
                        tree_sha=NEW_TREE,
                        parent_sha=OLD_HEAD).
6. BEFORE moving the branch ref, GitHub.compare_commits(base=OLD_HEAD, head=NEW_COMMIT) and GitHub.fetch_commit(commit_sha=NEW_COMMIT); require the exact changed-file/status set and diff to match the authorized delta.
7. Re-read the target branch and require it still equals OLD_HEAD.
8. GitHub.update_ref(branch_name=TARGET_BRANCH,
                     sha=NEW_COMMIT,
                     force=false).
9. Re-read the target branch and require it now equals NEW_COMMIT.
10. Repeat the exact delta/readback audit and re-read correctness-critical files from the resulting commit.
```

A blob whose returned SHA does not match the expected exact bytes must never enter a tree. If it remains unreferenced it is inert; discard it and correct the transport rather than compensating downstream.

When exact file bytes are available locally, `git hash-object --no-filters <file>` is the shortest expected-blob check. Base64 is a transport encoding only; it does not change the target bytes or Git identity.

Do **not** create a temporary branch merely to stage a candidate commit. Unreferenced Git blobs/trees/commits are the preferred short-lived construction surface. Create a remote branch only when an actual remote ref is required by the workflow, such as an Actions execution target, a pull request head, or an explicit recovery handle. If an unreferenced candidate must survive a user handoff or session boundary, checkpoint its exact object IDs immediately under **Fragile-State Immediate Checkpoint**.

The candidate comparison in step 6 is also the mechanical pre-persistence form of the `AGENTS.md` Mandate Boundary and Structural Mutation Guard. Do not move the branch ref while the candidate contains an unauthorized path, structural operation, or optional design change.

This is the canonical method for cohesive multi-file Polaris changes made from ChatGPT.'''

text = replace_section(
    text,
    "#### Make one atomic multi-file commit",
    "#### Edit repository-wide authority on the default branch, then propagate",
    atomic,
)

authority = r'''#### Edit repository-wide authority on the default branch, then propagate

Repository-wide workflow, process, governance, and architecture authority is main-owned by default. Edit `AGENTS.md`, `.agents/skills/**`, `docs/process/**`, ADRs, architecture documents, and comparable cross-cutting authority on the default branch, not on an active Spec/feature branch, unless the artifact is explicitly branch-local or the owner directs otherwise.

If such an artifact is found changed only on the active branch, treat that as authority drift: compare it with the default branch, reconcile the generic change on the default branch first, then propagate the finalized authoritative version back into the active branch before resuming work. Use clean Git-data construction from the active branch HEAD and do not import temporary transport commits; resolve genuine branch-local divergence deliberately rather than overwriting it.

When propagation means the active branch should carry exactly the finalized main-owned authority bytes, reuse the **same finalized Git blob SHA(s)** from the default-branch result in the active branch tree. Do not re-render, retype, or independently reconstruct the propagated files. Before moving the active branch ref, compare its old HEAD to the candidate commit and require only the authorized propagation surface; after the move, require `GitHub.fetch_file` to report blob parity with the default branch for every propagated authority file.'''

text = replace_section(
    text,
    "#### Edit repository-wide authority on the default branch, then propagate",
    "#### Make a surgical edit to a large file on the default branch when full-content reconstruction is unsafe",
    authority,
)

surgical_start = "#### Make a surgical edit to a large file on the default branch when full-content reconstruction is unsafe"
surgical_end = "#### Create/update GitHub issues and durable comments"
a = text.index(surgical_start)
b = text.index(surgical_end, a)
surgical = text[a:b].rstrip()
fail_fast = r'''

Probe the hosted-runner substrate **once** before arming the substantive payload. If that probe remains queued without job allocation across repeated status reads and no current repository run explains the queue, treat scratch Actions transport as unavailable for the current task. Do not create additional scratch workflows, rotate runner labels, or accumulate alternate transport branches in response. Clean up the temporary transport files, then use the next authorized substrate: direct Git-data mutation when exact bytes can be represented safely, otherwise the smallest owner-local handoff permitted by the User-Handoff Threshold.

A successful probe authorizes only one deterministic payload attempt for that edit. GitHub Actions remains an execution fallback, not a preferred repository-text mutation path when direct Git-data construction is safe.'''
text = text[:a] + surgical + fail_fast + "\n\n" + text[b:]

handoff_heading = "#### Clean up temporary remote branches"
handoff_section = r'''#### Recover lost structured handoffs from canonical producers

Persisted comments and receipts are often deliberately human-readable projections. They are durable evidence, but they are **not a generic serialization source for reconstructing a producer's structured machine handoff**.

When a workflow uses an ephemeral structured handoff and that handoff is lost:

1. identify the canonical producer named by the current owning skill;
2. rebuild the handoff through that producer from the same durable authoritative inputs;
3. do not reverse-parse rendered Markdown tables, escaping, explanatory prose, or an older receipt to recreate producer input;
4. if the workflow bound certification/review to the exact prior handoff bytes, treat the rebuild as a new invocation and follow the owning skill's recertification/revalidation rules;
5. never edit a historical human-readable receipt merely to manufacture replacement machine state.

This is a recovery/transport rule only. The owning workflow still defines the handoff schema, durable identity, certification semantics, and whether a rebuilt handoff remains eligible for reuse.

'''
if text.count(handoff_heading) != 1:
    raise SystemExit("cleanup heading missing or duplicated")
text = text.replace(handoff_heading, handoff_section + handoff_heading, 1)

skill_guard_anchor = "## Workflow Skill Modification Guard\n\nBefore proposing, reviewing, or performing any modification to a repository workflow skill under `.agents/skills/`—or to helper code whose semantics can change a workflow skill's transitions—read the current `docs/process/common-sense-invariant-hardening.md` first.\n"
skill_guard_insert = skill_guard_anchor + r'''

Before the first repository mutation, also apply the current `AGENTS.md` **Mandate Boundary and Structural Mutation Guard** operationally:

1. state the authorized file/surface set and any explicitly authorized structural operations;
2. distinguish necessary correctness work from optional refactor/reorganization/generalization;
3. when direct Git-data construction is available, build the candidate commit without moving the target ref;
4. compare the old HEAD to that candidate and require the actual changed-file/status set to equal the authorized delta;
5. if the candidate exceeds the mandate, do not persist it—remove the extra change or surface the proposed expansion for owner discussion/approval first.
'''
if text.count(skill_guard_anchor) != 1:
    raise SystemExit("skill guard anchor missing or duplicated")
text = text.replace(skill_guard_anchor, skill_guard_insert, 1)

PATH.write_text(text, encoding="utf-8")
