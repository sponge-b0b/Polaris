from pathlib import Path

path = Path('docs/process/session-reconstitution.md')
text = path.read_text()
anchor = 'This is the canonical method for cohesive multi-file Polaris changes made from ChatGPT.\n'
addition = '''\n#### Propagate repository-wide authority changes to the active working branch\n\nWhen ChatGPT changes repository-wide workflow/process authority on the default branch while a Spec/feature branch is active—including `AGENTS.md`, `.agents/skills/**`, process documentation, or comparable cross-cutting policy—propagate the finalized authoritative file versions into the active branch before resuming work there. Do not leave the active branch running stale workflow authority.\n\nUse clean Git-data construction from the active branch HEAD, replacing only the finalized authoritative blobs from the default branch; do not merge temporary transport commits. If the active branch has divergent edits to the same authority files, compare first and resolve deliberately rather than overwriting them.\n'''
assert text.count(anchor) == 1
path.write_text(text.replace(anchor, anchor + addition))
