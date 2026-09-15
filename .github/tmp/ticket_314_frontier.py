from __future__ import annotations

import json
import subprocess
import sys

REPO = "sponge-b0b/Polaris"
FRONTIER_PARENT = 310
TICKET = 314
FINDING_LEDGER_COMMENT = 5662220111


def run(*args: str) -> str:
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    if proc.returncode:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout


def gh_slurp(endpoint: str) -> list[dict]:
    raw = run(
        "gh",
        "api",
        "--paginate",
        "--slurp",
        "-H",
        "X-GitHub-Api-Version: 2026-03-10",
        endpoint,
    )
    pages = json.loads(raw)
    return [item for page in pages for item in page]


def main() -> int:
    # Prescribed post-closure frontier read: exactly once.
    children = gh_slurp(
        f"repos/{REPO}/issues/{FRONTIER_PARENT}/sub_issues?per_page=100"
    )
    open_children = [
        {"number": row["number"], "title": row["title"], "url": row["html_url"]}
        for row in children
        if row.get("state") == "open"
    ]

    frontier: list[dict] = []
    for child in sorted(open_children, key=lambda row: row["number"]):
        # Prescribed per-child blocker read: exactly once per open direct child.
        blockers = gh_slurp(
            f"repos/{REPO}/issues/{child['number']}/dependencies/blocked_by?per_page=100"
        )
        open_blockers = [
            {"number": row["number"], "title": row["title"], "url": row["html_url"]}
            for row in blockers
            if row.get("state") == "open"
        ]
        frontier.append({**child, "open_blockers": open_blockers, "executable": not open_blockers})

    # Prescribed direct-dependent read for the just-closed ticket: exactly once.
    dependents = gh_slurp(
        f"repos/{REPO}/issues/{TICKET}/dependencies/blocking?per_page=100"
    )
    open_dependents = [row for row in dependents if row.get("state") == "open"]
    dependent_state: list[dict] = []
    for dependent in sorted(open_dependents, key=lambda row: row["number"]):
        # Prescribed blocker read: exactly once per open dependent.
        blockers = gh_slurp(
            f"repos/{REPO}/issues/{dependent['number']}/dependencies/blocked_by?per_page=100"
        )
        open_blockers = [
            {"number": row["number"], "title": row["title"], "url": row["html_url"]}
            for row in blockers
            if row.get("state") == "open"
        ]
        dependent_state.append(
            {
                "number": dependent["number"],
                "title": dependent["title"],
                "url": dependent["html_url"],
                "parent_issue_url": dependent.get("parent_issue_url"),
                "open_blockers": open_blockers,
                "executable": not open_blockers,
            }
        )

    review = json.loads(
        run(
            "gh",
            "issue",
            "view",
            str(FRONTIER_PARENT),
            "--repo",
            REPO,
            "--json",
            "number,title,body,state,url",
        )
    )
    ledger = json.loads(
        run("gh", "api", f"repos/{REPO}/issues/comments/{FINDING_LEDGER_COMMENT}")
    )["body"]

    if review["state"] != "OPEN":
        raise SystemExit("Spec Review #310 unexpectedly not open")
    if "### RB-2 — Command-side persistence read failures must be application-owned\n\nStatus: satisfied" not in review["body"]:
        raise SystemExit("RB-2 reconciliation missing")
    if "### RB-3 — Relationship construction failures must cross application translation\n\nStatus: open" not in review["body"]:
        raise SystemExit("RB-3 open state missing")
    if '"id": "RF-1"' not in ledger or '"status": "satisfied"' not in ledger:
        raise SystemExit("RF-1 terminal satisfied state not recoverable")

    result = {
        "frontier_parent": {
            "number": FRONTIER_PARENT,
            "title": review["title"],
            "url": review["url"],
        },
        "open_children": frontier,
        "open_direct_dependents_of_314": dependent_state,
        "review_lifecycle": "Review Remediation",
        "parent_spec_next_skill": None,
        "reason": "open remediation children remain and RB-3 remains open",
    }
    print("FRONTIER_RESULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
