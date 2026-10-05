from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

SESSION_ID = "357dd2b3-8c7e-4f5a-a1d2-9b0c3e4f5a67"
PRIOR_RUN_ID = "37333932665"
PRIOR_ARTIFACT = "ticket-decomposition-357-dd2-resume2-session"
PRIOR_ARCHIVE_NAME = "copilot-home-resumed2.tgz"
CANDIDATE_HEAD = "2f7f809d4c9ffdc6bd8619ac9403f9b0c057ac7e"
VERIFIER_SKILL_BLOB = "5e8e389ef9509a7da628f37870ea6adab725737a"
ADR0014_BLOB = "fe79e744ef6155d81afebb549d16d7759e26e656"


def run(args: list[str], **kwargs):
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, check=True, text=True, **kwargs)


run(["git", "fetch", "origin", "spec-357", "chatgpt/verify-ticket-decomposition-357-dd2-repaired"])
head = subprocess.check_output(["git", "rev-parse", "refs/remotes/origin/spec-357"], text=True).strip()
if head != CANDIDATE_HEAD:
    raise SystemExit(f"candidate head moved: {head}")
skill_blob = subprocess.check_output(["bash", "-lc", f"git show {CANDIDATE_HEAD}:.agents/skills/verify-ticket-decomposition/SKILL.md | git hash-object --stdin"], text=True).strip()
if skill_blob != VERIFIER_SKILL_BLOB:
    raise SystemExit("verifier skill blob mismatch")
adr_blob = subprocess.check_output(["bash", "-lc", f"git show {CANDIDATE_HEAD}:docs/adr/0014-evidence-derive-r3-sufficiency-from-executable-requirements.md | git hash-object --stdin"], text=True).strip()
if adr_blob != ADR0014_BLOB:
    raise SystemExit("ADR 0014 blob mismatch")

env = os.environ.copy()
env["CANDIDATE_HEAD"] = CANDIDATE_HEAD
run([sys.executable, ".verification/build-proposal-357-dd2-resume.py"], env=env)
run([sys.executable, ".verification/repair-current-consumers.py"], env=env)
proposal = Path("/tmp/proposal-357-dd2-resume.txt")
proposal_sha = hashlib.sha256(proposal.read_bytes()).hexdigest()
print(f"proposal_sha={proposal_sha}", flush=True)

prior_dir = Path("/tmp/prior-session")
shutil.rmtree(prior_dir, ignore_errors=True)
prior_dir.mkdir(parents=True)
run(["gh", "run", "download", PRIOR_RUN_ID, "-n", PRIOR_ARTIFACT, "-D", str(prior_dir)])
archive = prior_dir / PRIOR_ARCHIVE_NAME
if not archive.exists():
    raise SystemExit(f"prior verifier session archive missing: {archive}")

copilot_home = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "copilot-home-dd2"
shutil.rmtree(copilot_home, ignore_errors=True)
copilot_home.mkdir(parents=True)
with tarfile.open(archive, "r:gz") as tf:
    tf.extractall(copilot_home)
if not (copilot_home / "session-state" / SESSION_ID).is_dir():
    raise SystemExit("exact verifier session directory missing after restore")

run(["npm", "install", "-g", "@github/copilot"])

prompt = f"""Continue the SAME Polaris $to-tickets decomposition-verifier session after your latest terminal FAIL.
Execute .agents/skills/verify-ticket-decomposition/SKILL.md exactly for the newly repaired candidate.

The exact current Spec branch candidate remains {CANDIDATE_HEAD}.
The exact repaired proposal is /tmp/proposal-357-dd2-resume.txt.
The exact repaired proposal identity is {proposal_sha}.
The verifier skill blob remains {VERIFIER_SKILL_BLOB}.

Your latest FAIL had exactly one finding: the family-A semantic-consumer matrix and proposed #380/#381 contracts omitted current-basis and dependent-commit effects from result-affecting observation and binding corrections. The parent has repaired only that finding: #380 now carries observation/binding/assessment correction interpretation and invalidation, #381 now freshly reconstructs/revalidates all those correction interpretations, and the family-A consumer matrix now includes both tickets. Treat this as a claimed repair to falsify, not as an assumed conclusion.

Independently recover current live GitHub state yourself with read-only gh commands before verdict. Re-read the relevant Spec/tickets, comments 5899020558 and 5930434832, states, parentage, and native dependency relationships rather than trusting proposal prose for persisted state. Re-read ADRs 0012, 0013, and 0014 from {CANDIDATE_HEAD}. Recheck the entire exact proposal, not only the latest repair, for source closure, ticket semantic carry, semantic-consumer propagation, dependency fidelity, live-WIP reslice safety, TCM/DD exactness, context fit, and design delegation.

Do not mutate repository or tracker state, do not redesign the proposal, and do not spawn another verifier.
Return exactly one complete terminal verdict in the skill-required format beginning with exactly either:
TICKET DECOMPOSITION: PASS
or
TICKET DECOMPOSITION: FAIL
Bind the verdict to proposal identity {proposal_sha}.
"""

copilot_env = os.environ.copy()
copilot_env["COPILOT_HOME"] = str(copilot_home)
cmd = [
    "copilot", f"--resume={SESSION_ID}", "-s", "-p", prompt, "--no-ask-user",
    "--allow-tool=read",
    "--allow-tool=shell(git:*)",
    "--allow-tool=shell(gh:*)",
    "--allow-tool=shell(cat:*)",
    "--allow-tool=shell(sed:*)",
    "--allow-tool=shell(grep:*)",
    "--allow-tool=shell(pwd:*)",
    "--allow-tool=shell(find:*)",
    "--allow-tool=shell(jq:*)",
]
verdict_path = Path("/tmp/verdict-resumed.txt")
result = None
try:
    result = subprocess.run(cmd, env=copilot_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    verdict_path.write_text(result.stdout or "", encoding="utf-8")
    print(result.stdout or "", flush=True)
finally:
    refreshed = Path("/tmp/copilot-home-resumed2.tgz")
    run(["tar", "-C", str(copilot_home), "-czf", str(refreshed), "."])
    archive_sha = hashlib.sha256(refreshed.read_bytes()).hexdigest()
    manifest = Path("/tmp/session-manifest-resumed2.txt")
    manifest.write_text(
        "\n".join([
            f"verifier_session_id={SESSION_ID}",
            f"proposal_sha256={proposal_sha}",
            f"candidate_head={CANDIDATE_HEAD}",
            f"verifier_skill_blob={VERIFIER_SKILL_BLOB}",
            f"prior_actions_run_id={PRIOR_RUN_ID}",
            f"actions_run_id={os.environ.get('GITHUB_RUN_ID', '')}",
            f"copilot_home_archive_sha256={archive_sha}",
            "",
        ]),
        encoding="utf-8",
    )
    print(manifest.read_text(encoding="utf-8"), flush=True)

if result is None or result.returncode != 0:
    raise SystemExit(result.returncode if result is not None else 1)
verdict = verdict_path.read_text(encoding="utf-8")
terminal = [line for line in verdict.splitlines() if line in {"TICKET DECOMPOSITION: PASS", "TICKET DECOMPOSITION: FAIL"}]
if len(terminal) != 1:
    raise SystemExit(f"expected one terminal verdict, got {len(terminal)}")
if proposal_sha not in verdict:
    raise SystemExit("verdict missing proposal identity")
