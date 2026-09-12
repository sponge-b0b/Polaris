from pathlib import Path

path = Path('docs/process/session-reconstitution.md')
text = path.read_text()

old = 'When a new genuinely stable capability or limitation is discovered, update this section so later sessions inherit it instead of rediscovering it.\n'
new = old + '\nAfter a recurring mechanical task succeeds with a stable method, capture the shortest proven method and its selection condition here before moving on when they are not already recorded. Replace disproven mechanics instead of preserving them as alternatives; later sessions must not repeat capability/transport discovery for known work.\n'
assert text.count(old) == 1
text = text.replace(old, new)

old = 'Do not give the owner a patch/file to apply and do not ask the owner to commit/push this change.\n\n#### Make one atomic multi-file commit\n'
new = 'Markdown, skill, and workflow-policy files are ordinary UTF-8 repository files for this rule. Use this path immediately when complete replacement content is safe; if a large/truncated file makes whole-file replacement unsafe, do not reconstruct it from excerpts or probe alternate transports—use the surgical fallback below.\n\nDo not give the owner a patch/file to apply and do not ask the owner to commit/push this change.\n\n#### Make one atomic multi-file commit\n'
assert text.count(old) == 1
text = text.replace(old, new)

old = '''#### Make a surgical edit to a large file when full-content reconstruction is unsafe

Preserve untouched bytes instead of manually reconstructing a large file from excerpts.

Preferred fallback:

```text
1. GitHub.create_branch(SCRATCH_BRANCH, exact canonical BASE_HEAD).
2. On SCRATCH_BRANCH only, GitHub.create_file(...) an ephemeral push-triggered workflow.
3. The workflow checks out SCRATCH_BRANCH, applies a deterministic script with exact anchors/assertions,
   runs `git diff --check`, prints/audits the diff, commits only the generated target file(s), and pushes SCRATCH_BRANCH.
4. ChatGPT reads the Actions run/jobs/logs and the generated commit/diff.
5. Reuse the generated target blob SHA(s) in a NEW CLEAN TREE based on the original canonical BASE_HEAD.
6. Create the real conventional commit with parent=BASE_HEAD and fast-forward the real target branch with `GitHub.update_ref(force=false)`.
7. Never merge the scratch branch and never include its workflow file in the real commit.
8. Because remote ref deletion is connector-missing, give the owner only the scoped scratch-branch deletion command after the durable real commit succeeds.
```

Use this only when direct `update_file` or direct Git-data construction would risk accidental whole-file corruption. A scratch branch is transport/execution plumbing, never lifecycle state.
'''
new = '''#### Make a surgical edit to a large file on the default branch when full-content reconstruction is unsafe

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
'''
assert text.count(old) == 1
text = text.replace(old, new)

path.write_text(text)
