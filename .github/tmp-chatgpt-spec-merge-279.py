from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

REPO = os.environ["REPO"]
OWNER = REPO.split("/", 1)[0]
WS = Path(os.environ["GITHUB_WORKSPACE"])
WORKFLOW = ".github/workflows/tmp-chatgpt-spec-merge-279.yml"
SCRIPT = ".github/tmp-chatgpt-spec-merge-279.py"
PRE_MAIN = os.environ["EXPECTED_PRE_MAIN"]
HEAD = os.environ["EXPECTED_HEAD"]
BASELINE = os.environ["EXPECTED_BASELINE"]
BODY_HASH = os.environ["EXPECTED_BODY_HASH"]
CONTRACT_HASH = os.environ["EXPECTED_CONTRACT_HASH"]
LEDGER_HASH = os.environ["EXPECTED_LEDGER_HASH"]
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


def receipt_field(body: str, label: str) -> str:
    match = re.search(rf"^\*\*{re.escape(label)}:\*\* (.+)$", body, re.M)
    require(match is not None, f"missing receipt field {label}")
    return match.group(1).strip()


# Exact pre-completion authority.
require(git("rev-parse", "HEAD").stdout.strip() == CREATE_SHA, "checkout is not transport commit")
changed = [x for x in git("diff", "--name-only", PRE_MAIN, CREATE_SHA).stdout.splitlines() if x]
require(changed == [SCRIPT, WORKFLOW], f"transport delta is not exactly the two transport files: {changed}")
git("fetch", "origin", "main", "spec-279")
require(git("rev-parse", "origin/main").stdout.strip() == CREATE_SHA, "main moved before completion")
require(git("rev-parse", "origin/spec-279").stdout.strip() == HEAD, "spec-279 moved after review")

spec = issue(279)
review = issue(310)
require(spec["state"] == "open", "#279 is not open at pre-completion gate")
require(review["state"] == "open", "#310 is not open at pre-completion gate")
spec_body = spec.get("body") or ""
require(hashlib.sha256(spec_body.encode()).hexdigest() == BODY_HASH, "Spec body hash changed")

spec_comments = comments(279)
review_comments = comments(310)
workspace = [c for c in spec_comments if "## Workspace Metadata" in (c.get("body") or "")]
require(len(workspace) == 1, f"Workspace Metadata count {len(workspace)}")
workspace_body = workspace[0]["body"]
require(f"**Baseline Commit Hash:** {BASELINE}" in workspace_body, "Workspace baseline mismatch")
require("**Branch:** spec-279" in workspace_body, "Workspace branch mismatch")

verification = [
    c
    for c in spec_comments
    if "## Spec Verification Receipt" in (c.get("body") or "")
    and "**Status:** passed" in c["body"]
    and f"**Verified HEAD:** {HEAD}" in c["body"]
]
require(verification, "matching passing Spec Verification Receipt missing")
verification.sort(key=lambda c: (c.get("created_at") or "", c["id"]))
verification_receipt = verification[-1]
require(
    str(verification_receipt["id"]) == os.environ["VERIFY_COMMENT"],
    f"latest matching verification receipt is {verification_receipt['id']}",
)
verification_body = verification_receipt["body"]
require(receipt_field(verification_body, "Verified Baseline") == BASELINE, "verification baseline mismatch")
require(receipt_field(verification_body, "Branch") == "spec-279", "verification branch mismatch")
require(receipt_field(verification_body, "Spec Body Hash") == BODY_HASH, "verification body hash mismatch")
require(receipt_field(verification_body, "Spec Contract Hash") == CONTRACT_HASH, "verification contract hash mismatch")

ledgers = [
    c
    for c in review_comments
    if "<!-- review-spec-finding-ledger:v1 -->" in (c.get("body") or "")
]
require(len(ledgers) == 1, f"finding ledger count {len(ledgers)}")
ledger = ledgers[0]
require(str(ledger["id"]) == os.environ["LEDGER_COMMENT"], "finding ledger identity mismatch")
ledger_body = ledger["body"]
live_ledger_hash = hashlib.sha256(ledger_body.encode()).hexdigest()
require(live_ledger_hash == LEDGER_HASH, f"finding ledger hash mismatch {live_ledger_hash}")
require(receipt_field(ledger_body, "Reviewed HEAD") == HEAD, "finding ledger HEAD mismatch")
require(receipt_field(ledger_body, "Spec Body Hash") == BODY_HASH, "finding ledger body hash mismatch")
require(receipt_field(ledger_body, "Spec Contract Hash") == CONTRACT_HASH, "finding ledger contract hash mismatch")

exit_receipts = [
    c for c in review_comments if "## Spec Review Exit Receipt" in (c.get("body") or "")
]
require(exit_receipts, "Spec Review Exit Receipt missing")
exit_receipts.sort(key=lambda c: (c.get("created_at") or "", c["id"]))
exit_receipt = exit_receipts[-1]
require(str(exit_receipt["id"]) == os.environ["EXIT_COMMENT"], f"latest Exit Receipt is {exit_receipt['id']}")
exit_body = exit_receipt["body"]
expected_exit = {
    "Status": "passed",
    "Spec Review": "#310",
    "Reviewed HEAD": HEAD,
    "Reviewed Baseline": BASELINE,
    "Branch": "spec-279",
    "Spec Body Hash": BODY_HASH,
    "Spec Contract Hash": CONTRACT_HASH,
    "Finding Ledger Hash": live_ledger_hash,
    "Blocking findings": "0",
    "Open blocking findings": "0",
    "Unaccounted prior findings": "0",
    "Unresolved continuity cells": "0",
    "Unresolved decomposition defects": "0",
    "Root blockers": "satisfied/owner-overridden/scope-retired",
    "Candidate new roots": "0",
    "Review coverage": "complete",
    "Unchecked coverage cells": "0",
}
for label, value in expected_exit.items():
    require(receipt_field(exit_body, label) == value, f"Exit Receipt mismatch {label}")

# Exhaustive Independent governance recovery for #279 and dependent #280.
for spec_number in (279, 280):
    current = issue(spec_number)
    provenance = (current.get("body") or "") + "\n" + "\n".join(
        c.get("body") or "" for c in comments(spec_number)
    )
    require("wayfinder-source" not in provenance, f"#{spec_number} has wayfinder-source provenance")
    require("wayfinder-remediation" not in provenance, f"#{spec_number} has wayfinder-remediation provenance")

wayfinders = paged(
    f"repos/{REPO}/issues?state=all&labels=wayfinder%3Amap&per_page=100"
)
for wayfinder in wayfinders:
    wayfinder_text = (wayfinder.get("body") or "") + "\n" + "\n".join(
        c.get("body") or "" for c in comments(wayfinder["number"])
    )
    for spec_number in (279, 280):
        patterns = (
            rf"(?im)^.*Spec Handoff.*#\s*{spec_number}\b",
            rf"(?im)^.*Derived Spec.*#\s*{spec_number}\b",
            rf"(?im)^.*Remediation Spec.*#\s*{spec_number}\b",
        )
        require(
            not any(re.search(pattern, wayfinder_text) for pattern in patterns),
            f"Wayfinder #{wayfinder['number']} governs Spec #{spec_number}",
        )

# Exact PR gate.
pr = None
for _ in range(6):
    pr = gh_json("api", f"repos/{REPO}/pulls/320")
    if pr.get("mergeable") is not None:
        break
    time.sleep(2)
require(pr is not None and pr["state"] == "open", "PR #320 is not open")
require(pr["base"]["ref"] == "main", "PR #320 base mismatch")
require(pr["head"]["ref"] == "spec-279", "PR #320 head branch mismatch")
require(pr["head"]["sha"] == HEAD, "PR #320 head SHA mismatch")
require(
    pr.get("mergeable") is True and pr.get("mergeable_state") == "clean",
    f"PR #320 not cleanly mergeable: {pr.get('mergeable')}/{pr.get('mergeable_state')}",
)

# Merge exact reviewed state.
merged = gh_json(
    "api",
    "--method",
    "PUT",
    f"repos/{REPO}/pulls/320/merge",
    "-f",
    "merge_method=merge",
    "-f",
    f"sha={HEAD}",
)
require(merged.get("merged") is True, f"PR merge failed: {merged}")
merge_sha = merged["sha"]
pr = gh_json("api", f"repos/{REPO}/pulls/320")
require(pr.get("merged") is True, "PR #320 did not persist merged state")
require(pr["head"]["sha"] == HEAD, "merged PR head differs from reviewed head")
require(pr["merge_commit_sha"] == merge_sha, "merge SHA mismatch")
merged_at = pr.get("merged_at")
require(bool(merged_at), "merged_at missing")
git("fetch", "origin", "main", "spec-279")
require(git("rev-parse", "origin/main").stdout.strip() == merge_sha, "main is not merge commit")
require(
    git("merge-base", "--is-ancestor", HEAD, "origin/main", check=False).returncode == 0,
    "reviewed HEAD is not merged into main",
)
require(git("rev-parse", f"{merge_sha}^1").stdout.strip() == CREATE_SHA, "unexpected merge first parent")
require(git("rev-parse", f"{merge_sha}^2").stdout.strip() == HEAD, "unexpected merge second parent")
require(issue(279)["state"] == "closed", "Closes #279 did not close Spec")

# Safe branch cleanup.
remote = git("ls-remote", "--heads", "origin", "refs/heads/spec-279").stdout.strip()
if remote:
    remote_head = remote.split()[0]
    require(remote_head == HEAD, f"spec-279 moved before deletion: {remote_head}")
    git("push", "origin", "--delete", "spec-279")
require(
    not git("ls-remote", "--heads", "origin", "refs/heads/spec-279").stdout.strip(),
    "remote spec-279 still exists",
)

# Close conventional Spec Review with authoritative completion comment.
close_text = "Spec merged (PR #320) and branch cleaned up. Zero blocking findings on final review."
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
closed_review = gh_json(
    "api", "--method", "PATCH", f"repos/{REPO}/issues/310", "-f", "state=closed", "-f", "state_reason=completed"
)
require(closed_review["state"] == "closed", "Spec Review #310 failed to close")

# Reconstruct complete completed-Spec lineage.
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

dependent = issue(280)
dep_summary = dependent.get("issue_dependencies_summary") or {}
dependent_body = dependent.get("body") or ""
blocked_section = dependent_body.split("## Blocked by", 1)[-1]
require(re.search(r"(?m)^#279\b", blocked_section) is not None, "#280 no longer declares #279 as its blocker")
dependency_complete = dep_summary.get("total_blocked_by") == 1 and dep_summary.get("blocked_by") == 0
dependency_status = (
    "DEPENDENCY RECONSTRUCTION: COMPLETE\nDependent Spec: #280\nOpen blockers: 0\n"
    if dependency_complete
    else "DEPENDENCY RECONSTRUCTION: DRIFT\nDependent Spec: #280\n"
    + f"Summary: {json.dumps(dep_summary, sort_keys=True)}\n"
)
(WS / "dependency-reconstruction.txt").write_text(dependency_status)

(WS / "project-reconstruction.txt").write_text(
    "Project reconstruction source: Spec #279\n"
    "Spec: 1\n"
    "Implementation Tickets: 6/6\n"
    "Spec Review: 1\n"
    "Review Remediation Tickets: 5/5\n"
    "Governing Wayfinders: 0/0\n"
    "Wayfinder Decisions: 0/0\n"
    "Direct dependent Specs considered: 1\n"
    "Other required formal artifacts: 0\n"
    "Unresolved lifecycle projections: 0\n"
    "PROJECT DELIVERY: OUTSIDE OWNER\n"
    "Governance: Independent Spec lineage\n"
)

# Mandatory Project projection attempt. Failure is downstream projection drift only.
def project_drift(reason: str) -> str:
    text = "PROJECT TRACKING: DRIFT\n" + reason.strip() + "\n"
    (WS / "project-tracking-status.txt").write_text(text)
    print(text, end="")
    return text


def completion_date(number: int) -> str:
    issue_comments = comments(number)
    needles = (
        "implement-ticket-closure-checkpoint:v2",
        "TICKET CLOSURE: PASS",
        "Root Closure Evidence",
        "closure evidence",
    )
    candidates = [
        comment
        for comment in issue_comments
        if any(needle.lower() in (comment.get("body") or "").lower() for needle in needles)
    ]
    require(candidates, f"#{number} lacks durable ticket closure evidence")
    candidates.sort(
        key=lambda comment: (
            comment.get("updated_at") or comment.get("created_at") or "",
            comment["id"],
        )
    )
    timestamp = candidates[-1].get("updated_at") or candidates[-1].get("created_at")
    require(bool(timestamp), f"#{number} closure evidence lacks timestamp")
    return timestamp[:10]


def attempt_project_sync() -> str:
    if not dependency_complete:
        return project_drift(
            "Artifact: #280\nCause: dependent blocker reconstruction is unresolved; authoritative #279 completion remains valid"
        )

    projections = [
        dict(number=279, artifact="Spec", workflow="Complete", next="None", work="Done", root="None", completed=merged_at[:10]),
        *[
            dict(number=number, artifact="Implementation Ticket", workflow="Complete", next="None", work="Done", root="None", completed=completion_date(number))
            for number in range(301, 307)
        ],
        dict(number=310, artifact="Spec Review", workflow="Complete", next="None", work="Done", root="None", completed=review_completed_at[:10]),
    ]
    roots = {311: "RB-1", 314: "RB-2", 315: "RB-3", 316: "None", 317: "None"}
    projections += [
        dict(number=number, artifact="Review Remediation Ticket", workflow="Complete", next="None", work="Done", root=root, completed=completion_date(number))
        for number, root in roots.items()
    ]
    projections.append(
        dict(number=280, artifact="Spec", workflow="Ready to Ticket", next="$to-tickets", work="Ready", root="None", completed=None)
    )

    result = gh("project", "list", "--owner", OWNER, "--format", "json", check=False)
    if result.returncode:
        return project_drift(
            "Cause: prescribed `gh project list` is unavailable with lifecycle credentials: "
            + (result.stderr or result.stdout).strip()
        )
    data = json.loads(result.stdout)
    projects = data.get("projects", data if isinstance(data, list) else [])
    matches = [
        project
        for project in projects
        if project.get("title") == "Polaris" and not project.get("closed", False)
    ]
    if len(matches) != 1:
        return project_drift(
            f"Cause: expected exactly one open Polaris Project, found {len(matches)}"
        )
    project = matches[0]
    project_number = str(project["number"])
    project_id = project["id"]

    result = gh(
        "project",
        "field-list",
        project_number,
        "--owner",
        OWNER,
        "--limit",
        "100",
        "--format",
        "json",
        check=False,
    )
    if result.returncode:
        return project_drift(
            "Cause: Project field schema unreadable: "
            + (result.stderr or result.stdout).strip()
        )
    field_data = json.loads(result.stdout)
    fields = field_data.get("fields", field_data if isinstance(field_data, list) else [])
    by_name = {field["name"]: field for field in fields}
    required_fields = [
        "Artifact Type",
        "Workflow State",
        "Next Skill",
        "Work Status",
        "Intake State",
        "Priority",
        "Area",
        "Root Blocker",
        "Completed On",
        "Delivery State",
    ]
    missing = [name for name in required_fields if name not in by_name]
    if missing:
        return project_drift("Cause: missing Project schema fields: " + ", ".join(missing))

    select_fields = (
        "Artifact Type",
        "Workflow State",
        "Next Skill",
        "Work Status",
        "Intake State",
        "Priority",
        "Area",
        "Delivery State",
    )
    options = {
        name: {option["name"]: option["id"] for option in by_name[name].get("options", [])}
        for name in select_fields
    }
    requested_fields = [
        "Artifact Type",
        "Workflow State",
        "Delivery State",
        "Next Skill",
        "Work Status",
        "Intake State",
        "Priority",
        "Area",
        "Root Blocker",
        "Completed On",
    ]

    def read_rows() -> dict[int, dict]:
        args = ["project", "item-list", project_number, "--owner", OWNER, "--limit", "1000"]
        for field_name in requested_fields:
            args += ["--field", field_name]
        read = gh(*args, check=False)
        if read.returncode:
            raise RuntimeError(
                "Project affected-row read failed: "
                + (read.stderr or read.stdout).strip()
            )
        rows: dict[int, dict] = {}
        for line in read.stdout.splitlines():
            parts = line.split("\t")
            item_index = next(
                (index for index, value in enumerate(parts) if value.startswith("PVTI_")),
                None,
            )
            repo_index = next(
                (index for index, value in enumerate(parts) if value == REPO), None
            )
            number_index = next(
                (
                    index
                    for index, value in enumerate(parts)
                    if re.fullmatch(r"#?\d+", value or "")
                ),
                None,
            )
            if item_index is None or repo_index is None or number_index is None:
                continue
            number = int(parts[number_index].lstrip("#"))
            tail = parts[item_index + 1 :]
            if len(tail) != len(requested_fields):
                raise RuntimeError(
                    f"unreadable Project row shape for #{number}: expected {len(requested_fields)} custom fields after item id, got {len(tail)}"
                )
            rows[number] = {
                "id": parts[item_index],
                "values": dict(zip(requested_fields, tail)),
            }
        return rows

    try:
        rows = read_rows()
    except Exception as exc:
        return project_drift("Cause: " + str(exc))

    missing_members = [projection for projection in projections if projection["number"] not in rows]
    for projection in missing_members:
        url = f"https://github.com/{REPO}/issues/{projection['number']}"
        added = gh(
            "project",
            "item-add",
            project_number,
            "--owner",
            OWNER,
            "--url",
            url,
            "--format",
            "json",
            check=False,
        )
        if added.returncode:
            return project_drift(
                f"Artifact: #{projection['number']}\nCause: Project membership add failed: "
                + (added.stderr or added.stdout).strip()
            )
    if missing_members:
        try:
            rows = read_rows()
        except Exception as exc:
            return project_drift("Cause: " + str(exc))
    if any(projection["number"] not in rows for projection in projections):
        return project_drift(
            "Cause: reconstructed artifacts remain absent after membership reconciliation"
        )

    for projection in projections:
        desired = {
            "Artifact Type": projection["artifact"],
            "Workflow State": projection["workflow"],
            "Next Skill": projection["next"],
            "Work Status": projection["work"],
            "Delivery State": "Released"
            if projection["workflow"] == "Complete"
            else "Independent",
        }
        for field_name, value in desired.items():
            if value not in options[field_name]:
                return project_drift(
                    f"Artifact: #{projection['number']}\nCause: missing option {field_name}={value}"
                )

    deltas: list[tuple[str, int, str, str | None]] = []

    def select(projection: dict, field_name: str, value: str) -> None:
        if rows[projection["number"]]["values"].get(field_name, "") != value:
            deltas.append(
                ("select", projection["number"], field_name, options[field_name][value])
            )

    def text(projection: dict, field_name: str, value: str) -> None:
        current = rows[projection["number"]]["values"].get(field_name, "")
        if value == "None":
            if current:
                deltas.append(("clear", projection["number"], field_name, None))
        elif current != value:
            deltas.append(("text", projection["number"], field_name, value))

    def date(projection: dict, field_name: str, value: str | None) -> None:
        current = rows[projection["number"]]["values"].get(field_name, "")
        if value is None:
            if current:
                deltas.append(("clear", projection["number"], field_name, None))
        elif current != value:
            deltas.append(("date", projection["number"], field_name, value))

    for projection in projections:
        select(projection, "Artifact Type", projection["artifact"])
        select(projection, "Workflow State", projection["workflow"])
        select(projection, "Next Skill", projection["next"])
        select(projection, "Work Status", projection["work"])
        select(
            projection,
            "Delivery State",
            "Released" if projection["workflow"] == "Complete" else "Independent",
        )
        text(projection, "Root Blocker", projection["root"])
        date(projection, "Completed On", projection["completed"])
        if rows[projection["number"]]["values"].get("Intake State", ""):
            deltas.append(("clear", projection["number"], "Intake State", None))

    if deltas:
        field_ids = {name: by_name[name]["id"] for name in required_fields}
        aliases: list[str] = []
        for index, (kind, number, field_name, value) in enumerate(deltas, 1):
            alias = f"u{index}"
            item_id = rows[number]["id"]
            field_id = field_ids[field_name]
            if kind == "clear":
                aliases.append(
                    f"{alias}: clearProjectV2ItemFieldValue(input:{{projectId:{json.dumps(project_id)},itemId:{json.dumps(item_id)},fieldId:{json.dumps(field_id)}}}){{projectV2Item{{id}}}}"
                )
            else:
                value_key = {
                    "select": "singleSelectOptionId",
                    "text": "text",
                    "date": "date",
                }[kind]
                aliases.append(
                    f"{alias}: updateProjectV2ItemFieldValue(input:{{projectId:{json.dumps(project_id)},itemId:{json.dumps(item_id)},fieldId:{json.dumps(field_id)},value:{{{value_key}:{json.dumps(value)}}}}}){{projectV2Item{{id}}}}"
                )
        mutation = "mutation {\n" + "\n".join(aliases) + "\n}"
        mutation_result = gh(
            "api", "graphql", "-f", "query=" + mutation, check=False
        )
        if mutation_result.returncode:
            return project_drift(
                "Cause: batched Project mutation failed: "
                + (mutation_result.stderr or mutation_result.stdout).strip()
            )
        response = json.loads(mutation_result.stdout)
        if response.get("errors"):
            return project_drift(
                "Cause: GraphQL errors: " + json.dumps(response["errors"])
            )
        for index in range(1, len(deltas) + 1):
            returned_id = (
                (((response.get("data") or {}).get(f"u{index}") or {}).get("projectV2Item") or {}).get("id")
            )
            if not returned_id:
                return project_drift(
                    f"Cause: Project mutation alias u{index} returned no item id"
                )

    try:
        final_rows = read_rows()
    except Exception as exc:
        return project_drift(
            "Cause: final Project verification read failed: " + str(exc)
        )

    problems: list[str] = []
    for projection in projections:
        values = final_rows.get(projection["number"], {}).get("values", {})
        expected = {
            "Artifact Type": projection["artifact"],
            "Workflow State": projection["workflow"],
            "Next Skill": projection["next"],
            "Work Status": projection["work"],
            "Delivery State": "Released"
            if projection["workflow"] == "Complete"
            else "Independent",
            "Root Blocker": "" if projection["root"] == "None" else projection["root"],
            "Completed On": projection["completed"] or "",
            "Intake State": "",
        }
        for field_name, expected_value in expected.items():
            if values.get(field_name, "") != expected_value:
                problems.append(
                    f"#{projection['number']} {field_name}: {values.get(field_name, '')!r} != {expected_value!r}"
                )
    if problems:
        return project_drift("Unreconciled:\n" + "\n".join(problems))

    text_result = (
        "PROJECT TRACKING: SYNCED\n"
        "Artifacts: #279, #301-#306, #310, #311, #314-#317, #280\n"
    )
    (WS / "project-tracking-status.txt").write_text(text_result)
    print(text_result, end="")
    return text_result


project_status = attempt_project_sync()

# Remove both transport files and prove the final product tree equals a clean merge.
git("fetch", "origin", "main")
require(git("rev-parse", "origin/main").stdout.strip() == merge_sha, "main moved before transport cleanup")
git("checkout", "-B", "main", "origin/main")
git("config", "user.name", "github-actions[bot]")
git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
git("rm", WORKFLOW, SCRIPT)
git("commit", "-m", "chore(workflow): clean Spec 279 merge transport")
merge_tree_lines = git("merge-tree", "--write-tree", PRE_MAIN, HEAD).stdout.splitlines()
require(merge_tree_lines, "synthetic clean merge produced no tree")
synthetic_tree = merge_tree_lines[0].strip()
final_tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
require(
    final_tree == synthetic_tree,
    f"transport cleanup tree mismatch {final_tree} != {synthetic_tree}",
)
git("push", "origin", "main")
final_main = git("rev-parse", "HEAD").stdout.strip()

metadata = {
    "spec": 279,
    "review": 310,
    "pr": 320,
    "reviewed_head": HEAD,
    "baseline": BASELINE,
    "merge_sha": merge_sha,
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
