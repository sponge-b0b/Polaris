from pathlib import Path
import subprocess

path = Path("docs/process/session-reconstitution.md")
text = path.read_text()

anchor1 = """## Phase 1 — Session Reconstitution\n\n### 1. Establish repository state\n"""
replacement1 = """## Phase 1 — Session Reconstitution\n\n### 0. Bootstrap Policy Admission Gate\n\nThis gate is the **first operational step** of every ChatGPT-hosted Polaris session, including continuation sessions where prior conversation, summaries, or Session Ledger state are available. Complete it before interpreting workflow authority, treating recovered state as actionable, or performing any repository/tracker mutation.\n\n1. Resolve the current default branch and its exact `HEAD`.\n2. Read the complete root `AGENTS.md` from that exact default-branch `HEAD`.\n3. Retain its Git blob SHA as `LAST_LOADED_AGENTS_BLOB` and the default-branch `HEAD` as `LAST_POLICY_HEAD`.\n4. Only after that read may the session continue to repository-state reconstruction, narrower process/skill loading, or Session Ledger recovery.\n\nPrior conversation, model memory, a context/session summary, Session Ledger prose, a previous-session `AGENTS.md` read, or quoted excerpts do **not** satisfy this gate. Missing or unreadable `AGENTS.md` fails closed for workflow continuation and mutation.\n\n#### Policy Freshness Before Mutation\n\nBefore **every** repository or tracker mutation during the active ChatGPT session:\n\n1. re-resolve the current default-branch `HEAD` and current root `AGENTS.md` blob SHA;\n2. require the current blob SHA to equal `LAST_LOADED_AGENTS_BLOB`; if it differs, re-read the complete current `AGENTS.md`, update `LAST_LOADED_AGENTS_BLOB` / `LAST_POLICY_HEAD`, and restart mandate/scope evaluation for the proposed mutation;\n3. if only the default-branch `HEAD` changed while the `AGENTS.md` blob is unchanged, update `LAST_POLICY_HEAD` without treating unchanged policy bytes as stale;\n4. apply the current `AGENTS.md` **Mandate Boundary and Structural Mutation Guard** to the exact proposed delta;\n5. do not mutate until the authorized delta is explicit and no optional structural/design change remains without owner approval.\n\nA mutation already performed cannot be justified retroactively by reading `AGENTS.md` afterward. Conversation summaries and prior-session policy knowledge are recovery aids only; they never substitute for current policy admission.\n\nBefore each mutation, the session must be able to establish:\n\n```text\nAGENTS.md loaded this session: yes\nLoaded AGENTS.md blob: <sha>\nCurrent AGENTS.md blob: <same sha>\nPolicy freshness at mutation admission: PASS\nMandate delta reconciled before mutation: PASS\n```\n\nThese are in-session admission facts, not a new receipt or Session Ledger schema. Do not persist them merely for bookkeeping.\n\n### 1. Establish repository state\n"""

anchor2 = """### 2. Load repository operating policy\n\nRead `AGENTS.md` before interpreting project state or making changes.\n\n#### Mandatory workflow hardening context\n"""
replacement2 = """### 2. Load narrower repository operating context\n\n`AGENTS.md` is already loaded by the Step 0 admission gate. Do not defer that read to this stage. Load only the additional process and skill context required by the active work.\n\n#### Mandatory workflow hardening context\n"""

for anchor, replacement in ((anchor1, replacement1), (anchor2, replacement2)):
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"expected exactly one anchor, found {count}: {anchor.splitlines()[0]}")
    text = text.replace(anchor, replacement, 1)

path.write_text(text)
subprocess.run(["git", "diff", "--check", "--", str(path)], check=True)
subprocess.run(["git", "add", str(path)], check=True)
subprocess.run(["git", "diff", "--cached", "--check"], check=True)
subprocess.run(["git", "config", "user.name", "Bob Taylor"], check=True)
subprocess.run(["git", "config", "user.email", "bobltaylorjr@gmail.com"], check=True)
subprocess.run(["git", "commit", "-m", "fix(process): harden ChatGPT bootstrap admission"], check=True)
subprocess.run(["git", "push", "origin", "HEAD:main"], check=True)
