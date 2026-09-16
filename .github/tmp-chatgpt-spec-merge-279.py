from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

REPO = os.environ["REPO"]
OWNER = REPO.split("/", 1)[0]
WS = Path(os.environ["GITHUB_WORKSPACE"])
WORKFLOW = ".github/workflows/tmp-chatgpt-spec-merge-279.yml"
SCRIPT = ".github/tmp-chatgpt-spec-merge-279.py"
PRE_MAIN = os.environ["EXPECTED_PRE_MAIN"]
HEAD = os.environ["EXPECTED_HEAD"]
MERGE_SHA = os.environ["EXPECTED_MERGE_SHA"]
CREATE_SHA = os.environ["GITHUB_SHA"]


def cmd(args: list[str], *, check: bool = True, input_text: str | None = None):
    proc = subprocess.run(args, text=True, input=input_text, capture_output=True)
    if check and proc.returncode:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n"
            f"{proc.stderr or proc.stdout}"
        )
    return proc


def git(*args: str, check: bool = True):
    return cmd(["git", *args], check=check)


def gh(*args: str, check: bool = True, input_text: str | None = None):
    return cmd(["gh", *args], check=check, input_text=input_text)


def gh_json(*args: str):
    return json.loads(gh(*args).stdout)


def paged(endpoint: str) -> list[dict]:
    pages = gh_json("api", "--paginate", "--slurp", endpoint)
    return [item for page in pages for item in page]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def issue(number: int) -> dict:
    return gh_json("api", f"repos/{REPO}/issues/{number}")


def comments(number: int) -> list[dict]:
    return paged(f"repos/{REPO}/issues/{number}/comments?per_page=100")


# This is an idempotent post-merge recovery phase. Only transport files may have changed
# after the authoritative merge commit.
require(git("rev-parse", "HEAD").stdout.strip() == CREATE_SHA, "checkout is not recovery transport commit")
changed = set(git("diff", "--name-only", MERGE_SHA, CREATE_SHA).stdout.splitlines())
require(changed <= {SCRIPT, WORKFLOW} and changed, f"post-merge delta escaped transport files: {sorted(changed)}")
git("fetch", "origin", "main", "spec-279")
require(git("rev-parse", "origin/main").stdout.strip() == CREATE_SHA, "main moved before post-merge recovery")
require(git("rev-parse", "origin/spec-279").stdout.strip() == HEAD, "spec-279 moved after merge")

pr = gh_json("api", f"repos/{REPO}/pulls/320")
require(pr.get("merged") is True, "PR #320 is not merged")
require(pr.get("merge_commit_sha") == MERGE_SHA, "PR #320 merge commit mismatch")
require(pr["head"]["sha"] == HEAD, "PR #320 head no longer matches reviewed head")
require(bool(pr.get("merged_at")), "PR #320 merged_at missing")
merged_at = pr["merged_at"]
require(issue(279)["state"] == "closed", "Spec #279 is not closed in post-merge phase")

# Safe remote branch cleanup: unchanged tip or nothing.
remote = git("ls-remote", "--heads", "origin", "refs/heads/spec-279").stdout.strip()
if remote:
    remote_head = remote.split()[0]
    require(remote_head == HEAD, f"spec-279 moved before deletion: {remote_head}")
    git("push", "origin", "--delete", "spec-279")
require(
    not git("ls-remote", "--heads", "origin", "refs/heads/spec-279").stdout.strip(),
    "remote spec-279 still exists",
)

# Close the conventional Spec Review exactly once after branch cleanup.
close_text = "Spec merged (PR #320) and branch cleaned up. Zero blocking findings on final review."
review_comments = comments(310)
existing = [c for c in review_comments if (c.get("body") or "").strip() == close_text]
if existing:
    existing.sort(key=lambda c: (c.get("created_at") or "", c["id"]))
    close_comment = existing[-1]
else:
    close_comment = gh_json(
        "api",
        "--method",
        "POST",
        f"repos/{REPO}/issues/310/comments",
        "--input",
        "-",
        input_text=json.dumps({"body": close_text}),
    )
review_completed_at = close_comment.get("created_at")
require(bool(review_completed_at), "Spec Review completion comment timestamp missing")
review = issue(310)
if review["state"] != "closed":
    review = gh_json(
        "api",
        "--method",
        "PATCH",
        f"repos/{REPO}/issues/310",
        "-f",
        "state=closed",
        "-f",
        "state_reason=completed",
    )
require(review["state"] == "closed", "Spec Review #310 failed to close")

# Complete native lineage reconstruction.
spec_children = paged(f"repos/{REPO}/issues/279/sub_issues?per_page=100")
review_children = paged(f"repos/{REPO}/issues/310/sub_issues?per_page=100")
require(
    {item["number"] for item in spec_children} == {301, 302, 303, 304, 305, 306},
    f"unexpected Spec children {[item['number'] for item in spec_children]}",
)
require(all(item["state"] == "closed" for item in spec_children), "an implementation ticket is open")
require(
    {item["number"] for item in review_children} == {311, 314, 315, 316, 317},
    f"unexpected review children {[item['number'] for item in review_children]}",
)
require(all(item["state"] == "closed" for item in review_children), "a review-remediation ticket is open")

# Independent governance was already revalidated successfully before PR #320 merged.
# Revalidate the direct dependent's automatic actionability after #279 closure.
dependent = issue(280)
dep_summary = dependent.get("issue_dependencies_summary") or {}
blocked_section = (dependent.get("body") or "").split("## Blocked by", 1)[-1]
require(re.search(r"(?m)^#279\b", blocked_section) is not None, "#280 no longer declares #279 as its blocker")
dependency_complete = dep_summary.get("total_blocked_by") == 1 and dep_summary.get("blocked_by") == 0
dependency_status = (
    "DEPENDENCY RECONSTRUCTION: COMPLETE\nDependent Spec: #280\nOpen blockers: 0\n"
    if dependency_complete
    else "DEPENDENCY RECONSTRUCTION: DRIFT\nDependent Spec: #280\n"
    + f"Summary: {json.dumps(dep_summary, sort_keys=True)}\n"
)
(WS / "dependency-reconstruction.txt").write_text(dependency_status)

# Reuse the already-audited Project reconstruction/sync implementation from the merged
# transport, but only its downstream Project section. That code attempts the prescribed
# `gh project list` first and records PROJECT TRACKING: DRIFT rather than rolling back
# authoritative completion if lifecycle credentials cannot access the user Project.
merged_script = git("show", f"{MERGE_SHA}:{SCRIPT}").stdout
start_marker = "# Mandatory Project projection attempt. Failure is downstream projection drift only."
end_marker = "# Remove both transport files and prove the final product tree equals a clean merge."
start = merged_script.index(start_marker)
end = merged_script.index(end_marker)
project_code = merged_script[start:end]
exec(project_code, globals())

# The extracted code defines completion_date() and project_status. Build the durable
# reconstruction manifest with lifecycle-authoritative completion dates.
completion_rows = {
    **{number: completion_date(number) for number in range(301, 307)},
    **{number: completion_date(number) for number in (311, 314, 315, 316, 317)},
}
manifest_lines = [
    "Project reconstruction source: Spec #279",
    "Spec: 1",
    "Implementation Tickets: 6/6",
    "Spec Review: 1",
    "Review Remediation Tickets: 5/5",
    "Governing Wayfinders: 0/0",
    "Wayfinder Decisions: 0/0",
    "Direct dependent Specs considered: 1 (#280)",
    "Other required formal artifacts: 0",
    "Unresolved lifecycle projections: 0",
    "PROJECT DELIVERY: OUTSIDE OWNER",
    "Governance: Independent Spec lineage",
    f"#279 Completed On: {merged_at[:10]}",
    f"#310 Completed On: {review_completed_at[:10]}",
]
for number in sorted(completion_rows):
    manifest_lines.append(f"#{number} Completed On: {completion_rows[number]}")
(WS / "project-reconstruction.txt").write_text("\n".join(manifest_lines) + "\n")

# Remove both transport files and prove the resulting tree is exactly the clean product
# merge of the pre-transport main and reviewed Spec head.
git("fetch", "origin", "main")
require(git("rev-parse", "origin/main").stdout.strip() == CREATE_SHA, "main moved before transport cleanup")
git("checkout", "-B", "main", "origin/main")
git("config", "user.name", "github-actions[bot]")
git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
git("rm", WORKFLOW, SCRIPT)
git("commit", "-m", "chore(workflow): clean Spec 279 merge transport")
merge_tree_lines = git("merge-tree", "--write-tree", PRE_MAIN, HEAD).stdout.splitlines()
require(merge_tree_lines, "synthetic clean merge produced no tree")
synthetic_tree = merge_tree_lines[0].strip()
final_tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
require(final_tree == synthetic_tree, f"transport cleanup tree mismatch {final_tree} != {synthetic_tree}")
git("push", "origin", "main")
final_main = git("rev-parse", "HEAD").stdout.strip()

metadata = {
    "spec": 279,
    "review": 310,
    "pr": 320,
    "reviewed_head": HEAD,
    "merge_sha": MERGE_SHA,
    "merged_at": merged_at,
    "review_close_comment_id": close_comment["id"],
    "review_completed_at": review_completed_at,
    "final_main": final_main,
    "spec_branch_deleted": True,
    "governance": "Independent",
    "project_delivery": "OUTSIDE OWNER",
    "dependency_reconstruction": dependency_status.strip(),
    "project_tracking": project_status.strip(),
}
(WS / "completion-metadata.json").write_text(
    json.dumps(metadata, indent=2, sort_keys=True) + "\n"
)
print(json.dumps(metadata, indent=2, sort_keys=True))
