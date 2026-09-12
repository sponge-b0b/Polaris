from pathlib import Path
import subprocess

path = Path('docs/process/session-reconstitution.md')
text = path.read_text()
changed = False

old = '''#### Propagate repository-wide authority changes to the active working branch

When ChatGPT changes repository-wide workflow/process authority on the default branch while a Spec/feature branch is active—including `AGENTS.md`, `.agents/skills/**`, process documentation, or comparable cross-cutting policy—propagate the finalized authoritative file versions into the active branch before resuming work there. Do not leave the active branch running stale workflow authority.

Use clean Git-data construction from the active branch HEAD, replacing only the finalized authoritative blobs from the default branch; do not merge temporary transport commits. If the active branch has divergent edits to the same authority files, compare first and resolve deliberately rather than overwriting them.
'''
new = '''#### Edit repository-wide authority on the default branch, then propagate

Repository-wide workflow, process, governance, and architecture authority is main-owned by default. Edit `AGENTS.md`, `.agents/skills/**`, `docs/process/**`, ADRs, architecture documents, and comparable cross-cutting authority on the default branch, not on an active Spec/feature branch, unless the artifact is explicitly branch-local or the owner directs otherwise.

If such an artifact is found changed only on the active branch, treat that as authority drift: compare it with the default branch, reconcile the generic change on the default branch first, then propagate the finalized authoritative version back into the active branch before resuming work. Use clean Git-data construction from the active branch HEAD and do not import temporary transport commits; resolve genuine branch-local divergence deliberately rather than overwriting it.
'''
if old in text:
    assert text.count(old) == 1
    text = text.replace(old, new)
    changed = True
else:
    assert new in text

old = '''#### Delete a temporary remote branch

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
'''
new = '''#### Clean up temporary remote branches

Remote ref deletion is local-only in this runtime, but cleanup is part of the lifecycle rather than optional housekeeping.

At each ticket closure, after the accepted/certified result is durably promoted and no recovery handle depends on its temporary refs, ChatGPT must enumerate that ticket's temporary remote branches, verify they are not the default/active branch, an open-PR head, authoritative state, or required recovery state, then give the owner one deletion command. At Spec completion, perform a final Spec-wide sweep for any leftover temporary branches. Do not classify `spec-*`, `wayfinder-*`, `workflow-*`, or other deliberately named durable branches as disposable solely because they are old.

Use one scoped deletion command for all verified disposable branches:

```bash
(
  set -euo pipefail
  ROOT="$(git rev-parse --show-toplevel)"
  cd "$ROOT"
  git push origin --delete <temporary-branch-1> <temporary-branch-2> ...
  git fetch --prune origin
)
```

If a temporary branch must be retained, record the exact recovery reason in the ChatGPT Session Ledger and revisit it at the next cleanup boundary.
'''
if old in text:
    assert text.count(old) == 1
    text = text.replace(old, new)
    changed = True
else:
    assert new in text

if not changed:
    print('HOUSEKEEPING_HARDENING_ALREADY_APPLIED=1')
    raise SystemExit(0)

path.write_text(text)
subprocess.run(['git', 'diff', '--check'], check=True)
subprocess.run(['git', 'diff', '--', str(path)], check=True)
subprocess.run(['git', 'config', 'user.name', 'Bob Taylor'], check=True)
subprocess.run(['git', 'config', 'user.email', 'bobltaylorjr@gmail.com'], check=True)
subprocess.run(['git', 'add', str(path)], check=True)
subprocess.run(['git', 'commit', '-m', 'docs(process): harden authority and branch housekeeping'], check=True)
subprocess.run(['git', 'push'], check=True)
