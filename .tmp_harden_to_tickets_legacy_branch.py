from pathlib import Path
import subprocess

path = Path('.agents/skills/to-tickets/SKILL.md')
text = path.read_text()


def replace_once(old: str, new: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'expected exactly one anchor, found {count}: {old[:80]!r}')
    text = text.replace(old, new, 1)


replace_once(
    "Do not create, update, close, label, parent, or change dependencies for any ticket until branch identity, local/remote branch state, upstream tracking, GitHub Development linkage, and Spec baseline metadata have all been verified or persisted as required by that rule.",
    "Do not create, update, close, label, parent, or change dependencies for any ticket until branch identity, local/remote branch state, upstream tracking, GitHub Development linkage **or the qualified legacy pre-existing branch reconciliation below**, and Spec baseline metadata have all been verified or persisted as required by that rule.",
)

replace_once(
    "The Spec branch is a durable GitHub development branch, not a local-only workspace convenience. On first use, `$to-tickets` owns creating it on `origin`, linking it to the originating Spec's GitHub Development section, and establishing the local upstream. Later ticketing/remediation reuses that same linked branch.",
    "The Spec branch is a durable GitHub development branch, not a local-only workspace convenience. On first use, `$to-tickets` owns creating it on `origin`, linking it to the originating Spec's GitHub Development section, and establishing the local upstream. Later ticketing/remediation reuses that same linked branch. A historical Spec branch that already existed on `origin` before this linkage rule may use the narrow legacy reconciliation below when GitHub exposes no supported operation for attaching that already-existing branch; this does not weaken the first-use rule for new branches.",
)

replace_once(
    "### 3. Create or Reuse the Linked Spec Branch",
    "### 3. Create or Reuse the Spec Branch",
)

replace_once(
    "Do not create another branch for remediation or amended-Spec ticket deltas. Do not silently fall back to a local-only branch if `gh issue develop`, the remote push, or Development linkage is unavailable.\n\nVerify branch identity, upstream, and GitHub Development linkage before continuing:",
    """Do not create another branch for remediation or amended-Spec ticket deltas. Do not silently fall back to a local-only branch if `gh issue develop`, the remote push, or Development linkage is unavailable.\n\n#### Legacy pre-existing branch reconciliation\n\nA **legacy pre-existing Spec branch** may lack GitHub Development linkage only when the exact `spec-<spec_issue_number>` branch already existed on `origin` before this invocation and current GitHub tooling exposes no supported operation for attaching that already-existing branch. This is a narrow reconciliation path for historical repository state; it is not an alternate branch-creation path.\n\nWhen Development linkage is absent for an already-existing remote branch, require all of the following before publication:\n\n* the branch name is exactly `spec-<spec_issue_number>`;\n* local branch identity and upstream tracking resolve exactly to `origin/$SPEC_BRANCH`;\n* the originating Spec contains exactly one `## Workspace Metadata` comment;\n* that single comment records exactly `**Branch:** $SPEC_BRANCH` and one full 40-character `**Baseline Commit Hash:** <sha>`;\n* the recorded baseline commit exists and is an ancestor of the current Spec branch;\n* `gh issue develop --list \"$spec_issue_number\"` returns no conflicting linked branch;\n* the remote branch existed before the current invocation.\n\nIf any condition fails, halt. Never delete/recreate, rename, or replace a durable existing Spec branch merely to manufacture Development linkage. Every newly created Spec branch continues to require `gh issue develop` so creation and linkage occur together.\n\nVerify branch identity, upstream, and Development linkage or qualified legacy reconciliation before continuing:""",
)

replace_once(
    """if ! gh issue develop --list \"$spec_issue_number\" | grep -Fq \"$SPEC_BRANCH\"; then\n  echo \"❌ Spec branch is not linked to the parent Spec's GitHub Development section.\"\n  exit 1\nfi""",
    """LINKED_BRANCHES=$(gh issue develop --list \"$spec_issue_number\")\nLEGACY_PREEXISTING_BRANCH=false\n\nif grep -Fq \"$SPEC_BRANCH\" <<<\"$LINKED_BRANCHES\"; then\n  :\nelif [ \"$REMOTE_BRANCH_EXISTS\" = true ]; then\n  if [ -n \"$(printf '%s' \"$LINKED_BRANCHES\" | tr -d '[:space:]')\" ]; then\n    echo \"❌ Parent Spec has conflicting GitHub Development linkage; expected $SPEC_BRANCH.\"\n    exit 1\n  fi\n\n  WORKSPACE_METADATA=$(gh issue view \"$spec_issue_number\" --json comments -q \\\n    '[.comments[].body | select(contains(\"## Workspace Metadata\"))] | if length == 1 then .[0] else \"\" end')\n\n  if [ -z \"$WORKSPACE_METADATA\" ]; then\n    echo \"❌ Unlinked pre-existing Spec branch requires exactly one Workspace Metadata comment.\"\n    exit 1\n  fi\n\n  if [ \"$(printf '%s\\n' \"$WORKSPACE_METADATA\" | grep -c '^\\*\\*Branch:\\*\\* ')\" -ne 1 ] \\\n    || [ \"$(printf '%s\\n' \"$WORKSPACE_METADATA\" | grep -c '^\\*\\*Baseline Commit Hash:\\*\\* ')\" -ne 1 ]; then\n    echo \"❌ Workspace Metadata must contain exactly one Branch and one Baseline Commit Hash line.\"\n    exit 1\n  fi\n\n  RECORDED_BRANCH=$(printf '%s\\n' \"$WORKSPACE_METADATA\" | sed -n 's/^\\*\\*Branch:\\*\\* //p')\n  RECORDED_BASELINE=$(printf '%s\\n' \"$WORKSPACE_METADATA\" | sed -n 's/^\\*\\*Baseline Commit Hash:\\*\\* //p')\n\n  if [ \"$RECORDED_BRANCH\" != \"$SPEC_BRANCH\" ]; then\n    echo \"❌ Workspace Metadata branch does not match $SPEC_BRANCH.\"\n    exit 1\n  fi\n\n  if ! [[ \"$RECORDED_BASELINE\" =~ ^[0-9a-f]{40}$ ]]; then\n    echo \"❌ Workspace Metadata baseline must be one full 40-character commit SHA.\"\n    exit 1\n  fi\n\n  if ! git cat-file -e \"$RECORDED_BASELINE^{commit}\" 2>/dev/null \\\n    || ! git merge-base --is-ancestor \"$RECORDED_BASELINE\" HEAD; then\n    echo \"❌ Workspace Metadata baseline is not valid ancestry for the current Spec branch.\"\n    exit 1\n  fi\n\n  LEGACY_PREEXISTING_BRANCH=true\nelse\n  echo \"❌ Spec branch is not linked to the parent Spec's GitHub Development section.\"\n  exit 1\nfi""",
)

path.write_text(text)
subprocess.run(['git', 'diff', '--check'], check=True)

updated = path.read_text()
required = [
    '#### Legacy pre-existing branch reconciliation',
    'LEGACY_PREEXISTING_BRANCH=false',
    'Every newly created Spec branch continues to require `gh issue develop`',
    'Never delete/recreate, rename, or replace a durable existing Spec branch merely to manufacture Development linkage.',
]
for marker in required:
    if marker not in updated:
        raise SystemExit(f'missing expected marker after edit: {marker}')

print('to-tickets legacy branch reconciliation hardening applied')
