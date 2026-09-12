from pathlib import Path
import subprocess

path = Path('docs/process/session-reconstitution.md')
text = path.read_text()
changed = False


def replace_once(old: str, new: str) -> None:
    global text, changed
    if old in text:
        assert text.count(old) == 1
        text = text.replace(old, new)
        changed = True
    else:
        assert new in text


replace_once(
    "- create/update pull requests, request/review PRs, and merge a PR with an expected-head guard;\n- inspect GitHub Actions runs, jobs, logs, and artifacts;\n",
    "- create/update pull requests, request/review PRs, and merge a PR with an expected-head guard;\n- execute reproducible repository commands in GitHub Actions against an exact durable candidate/ref;\n- inspect GitHub Actions runs, jobs, logs, and artifacts;\n",
)

replace_once(
    "The ChatGPT analysis/container runtime can also perform deterministic text/data transformation, hashing, JSON construction, and other scratch computation. It is **not** the repository owner's checkout and must not be treated as evidence of the owner's local Git/worktree/service state.\n\n### Known Local-Only or Connector-Missing Capabilities\n",
    "The ChatGPT analysis/container runtime can also perform deterministic text/data transformation, hashing, JSON construction, and other scratch computation. It is **not** the repository owner's checkout and must not be treated as evidence of the owner's local Git/worktree/service state.\n\n### Execution-Substrate Rule\n\nRepository-local or workspace-local command requirements do not imply owner-machine execution. When the exact candidate/ref and required prerequisites can be reproduced safely in GitHub Actions, ChatGPT owns that execution.\n\nGitHub Actions is only an execution substrate: the complete owning skill still governs baseline/candidate binding, preflights, delegated gates, fail-closed behavior, evidence readback, and terminal result. Prefer direct connector actions first, exact-candidate Actions second, and owner-machine handoff only for genuinely owner-local prerequisites.\n\n### Known Local-Only or Connector-Missing Capabilities\n",
)

replace_once(
    "ChatGPT cannot directly observe or execute inside the repository owner's local Polaris checkout. Therefore ChatGPT cannot itself establish:\n\n- the owner's current `git status`, local branch, uncommitted files, unpushed commits, stash state, or locally generated files unless those facts become durable remotely or the owner returns command output;\n- repo-local `uv`, pytest, Ruff, Mypy, Arid, JSCPD, profiling, Docker/service probes, database/service state, or other environment-dependent commands against the owner's checkout;\n- local environment variables, credentials, sockets, services, or machine-specific filesystem state.\n\nThe current connected GitHub runtime also does **not** expose remote Git-ref deletion and does not provide the GitHub Projects v2 mutation surface used by Polaris Project projection. Those operations remain local `git`/`gh` handoffs unless the runtime explicitly gains those capabilities in the future.\n",
    "ChatGPT cannot directly observe or execute inside the repository owner's local Polaris checkout. Therefore ChatGPT cannot itself establish:\n\n- the owner's current `git status`, local branch, uncommitted files, unpushed commits, stash state, or locally generated files unless those facts become durable remotely or the owner returns command output;\n- commands or facts that depend on uncommitted owner-local state, owner-only credentials, machine-specific hardware, sockets, or services that cannot be safely reproduced remotely;\n- local environment variables, credentials, sockets, services, or machine-specific filesystem state.\n\nOrdinary tests, linters, type checks, repository scripts, and safely provisionable services are not owner-only merely because ChatGPT cannot execute inside the owner's checkout; run them against the exact durable candidate in GitHub Actions when the active workflow permits it.\n\nThe current connected GitHub runtime also does **not** expose remote Git-ref deletion and does not provide the GitHub Projects v2 mutation surface used by Polaris Project projection. Those operations remain local `git`/`gh` handoffs unless the runtime explicitly gains those capabilities in the future.\n",
)

replace_once(
    """For the current ChatGPT GitHub runtime, use this registered one-shot default-branch transport:\n\n```text\n1. Read and pin the exact default-branch HEAD; require the temporary workflow/script paths to be absent.\n2. GitHub.create_file(... branch=DEFAULT_BRANCH) a minimal push-triggered probe workflow, then require a successful probe run.\n3. GitHub.create_file(... branch=DEFAULT_BRANCH) a temporary deterministic edit script containing exact anchors/assertions.\n4. GitHub.update_file(...) the registered workflow to a minimal armed job that checks out DEFAULT_BRANCH,\n   runs the temporary script, runs `git diff --check`, audits the target diff, removes both temporary files,\n   commits the intended target edit plus both deletions, and pushes DEFAULT_BRANCH.\n5. Read the armed workflow run and require success.\n6. Re-read DEFAULT_BRANCH and fetch the resulting commit/diff; require only the intended target edit and\n   removal of the temporary workflow/script.\n7. Re-read the edited target file from the resulting commit.\n```\n\nKeep substantive edit logic out of workflow YAML; the temporary script is the deterministic payload. Do not introduce the workflow only on a non-default scratch branch; that path did not schedule reliably in this runtime. This fallback intentionally uses temporary transport commits and leaves no workflow/script in the final tree. Use it only when direct `update_file` or direct Git-data construction would risk whole-file corruption.\n""",
    """For the current ChatGPT GitHub runtime, use this registered one-shot default-branch transport:\n\n```text\n1. Read and pin the exact default-branch HEAD; require the temporary workflow/script paths to be absent.\n2. GitHub.create_file(... branch=DEFAULT_BRANCH) a minimal push-triggered probe workflow, then require a successful probe run.\n3. GitHub.create_file(... branch=DEFAULT_BRANCH) a temporary deterministic, idempotent edit script containing exact anchors/assertions plus `git diff --check`, commit, and push.\n4. GitHub.update_file(...) the registered workflow to a minimal job that checks out DEFAULT_BRANCH and runs only the temporary script.\n5. Read the armed workflow run and require success; re-read DEFAULT_BRANCH and audit the resulting target commit/diff.\n6. Delete the temporary workflow through the connector first, then delete the temporary script; verify both paths are absent.\n7. Re-read the edited target file from the resulting commit.\n```\n\nKeep substantive edit logic out of workflow YAML; the temporary script is the deterministic payload. Do not assume a newly introduced non-default scratch-only workflow will schedule. This fallback intentionally uses temporary transport commits but leaves no workflow/script in the final tree. Use it only when direct `update_file` or direct Git-data construction would risk whole-file corruption.\n""",
)

replace_once(
    """#### Run repository-local validation or other owner-machine commands\n\nThis is a legitimate local handoff. Give only the missing operation in one fail-closed subshell, normally shaped as:\n\n```bash\n(\n  set -euo pipefail\n  ROOT=\"$(git rev-parse --show-toplevel)\"\n  cd \"$ROOT\"\n\n  test \"$(git branch --show-current)\" = \"<expected-branch>\"\n  test \"$(git rev-parse HEAD)\" = \"<expected-full-sha>\"\n  test -z \"$(git status --porcelain)\"\n\n  <only the exact local command(s) required by the active workflow>\n)\n```\n\nAdd only the guards needed by the owning skill. Do not hand the entire workflow to the owner. The owner returns the complete output; ChatGPT consumes it as evidence and resumes from the first incomplete stage.\n""",
    """#### Run reproducible repository commands\n\nUse GitHub Actions when the required command can be reproduced from the exact durable candidate/ref. Bind the candidate first, execute the complete owning-skill semantics rather than a convenient subset, inspect the run/jobs/logs, and treat the result as verification evidence unless the workflow explicitly promotes generated repository content. Use an already-registered/proven Actions path or the current capability playbook; do not assume a newly introduced scratch-only workflow will schedule.\n\n#### Run genuinely owner-machine-only commands\n\nUse a human shell handoff only when a required fact or command cannot be reproduced safely through the connector or GitHub Actions. Give only the missing operation in one fail-closed subshell, normally shaped as:\n\n```bash\n(\n  set -euo pipefail\n  ROOT=\"$(git rev-parse --show-toplevel)\"\n  cd \"$ROOT\"\n\n  test \"$(git branch --show-current)\" = \"<expected-branch>\"\n  test \"$(git rev-parse HEAD)\" = \"<expected-full-sha>\"\n  test -z \"$(git status --porcelain)\"\n\n  <only the exact owner-local command(s) required by the active workflow>\n)\n```\n\nLegitimate reasons include required knowledge of uncommitted owner-local state, owner-only credentials, machine-specific hardware, or a required service that cannot be safely/reproducibly provisioned remotely. Add only the guards needed by the owning skill. Do not hand the entire workflow to the owner.\n""",
)

replace_once(
    "When the governing skill requires a canonical repository-local script that ChatGPT cannot execute against the owner's checkout:\n",
    "When the governing skill requires a canonical repository-local script that ChatGPT cannot execute in an available remote runtime because a genuine owner-local prerequisite remains:\n",
)

replace_once(
    """The owner should receive shell commands only for work that is genuinely local-only or connector-missing, principally:\n\n- local checkout/worktree state;\n- repo-local tests, linters, profilers, scripts, Docker/services, or environment probes;\n- remote branch deletion;\n- authorized GitHub Projects v2 mutation;\n- another operation that the canonical ChatGPT-side method actually attempted and proved unavailable.\n\nDo **not** give the owner repository patches, replacement source files, ZIPs, generated downloads, copy/paste implementation, `git commit`, or `git push` instructions for work ChatGPT can mutate remotely. The standing collaboration model is: **ChatGPT does everything mechanically available on its side; the owner runs only the smallest scoped local subshell that ChatGPT cannot execute.**\n""",
    """The owner should receive shell commands only for work that is genuinely owner-local or connector/runtime-missing, principally:\n\n- owner checkout/worktree state that the workflow specifically requires and cannot reconstruct from durable remote state;\n- commands whose required inputs depend on owner-only credentials, uncommitted local files, machine-specific hardware, sockets, or services that cannot be safely/reproducibly provisioned remotely;\n- remote branch deletion;\n- authorized GitHub Projects v2 mutation;\n- another operation that the canonical connector/Actions method actually attempted and proved unavailable.\n\nOrdinary repo-local tests, linters, type checks, repository scripts, and service-free verification are not human handoffs merely because ChatGPT cannot execute inside the owner's checkout.\n\nDo **not** give the owner repository patches, replacement source files, ZIPs, generated downloads, copy/paste implementation, `git commit`, or `git push` instructions for work ChatGPT can mutate or execute remotely. The standing collaboration model is: **ChatGPT does everything mechanically available on its side; the owner runs only the smallest scoped local subshell that genuinely cannot be executed or established remotely.**\n""",
)

if not changed:
    print('EXECUTION_POLICY_ALREADY_RECONCILED=1')
    raise SystemExit(0)

path.write_text(text)
subprocess.run(['git', 'diff', '--check'], check=True)
subprocess.run(['git', 'diff', '--', str(path)], check=True)
subprocess.run(['git', 'config', 'user.name', 'Bob Taylor'], check=True)
subprocess.run(['git', 'config', 'user.email', 'bobltaylorjr@gmail.com'], check=True)
subprocess.run(['git', 'add', str(path)], check=True)
subprocess.run(['git', 'commit', '-m', 'docs(process): reconcile execution substrate authority'], check=True)
subprocess.run(['git', 'push'], check=True)
