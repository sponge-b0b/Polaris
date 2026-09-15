from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
SPEC = 279
REVIEW = 310
SOURCE_HEAD = "9081386b8fcbf65e117fdac6c7b8c776edaef8f0"
SPEC_BASELINE = "4daed9034891600597a47c01b6c39d5ebd9914ca"
SPEC_BODY_HASH = "5f59ee666c65e9e93fe3b69403dbf4bc5328332d14d6339fc55b067755e4eb17"
SPEC_CONTRACT_HASH = "3044b039742306f1c0ed10085479c7c823ed463443e8d11d761f45de564fb334"
PROPOSAL_ID = "4c1e32a2dc6c39fbd5e5bb0d5da0a53bd44b4cf10720af0a612c11b07cbc2b0c"
WORKSPACE_METADATA_COMMENT = 5629965742
COVERAGE_COMMENT = 5630203405
DD_COMMENT = 5663250943

TICKETS = [
    ("T1", "Define application-owned command-side read failure semantics", ".github/tmp/to_tickets_310_t1.md"),
    ("T2", "Translate relationship construction failures at the application boundary", ".github/tmp/to_tickets_310_t2.md"),
    ("T3", "Add atomic multi-relationship correction coordination", ".github/tmp/to_tickets_310_t3.md"),
    ("T4", "Attach omitted renewal lineage to existing Decisions", ".github/tmp/to_tickets_310_t4.md"),
]


def run(*args: str, input_text: str | None = None, check: bool = True) -> str:
    result = subprocess.run(args, input=input_text, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def gh(*args: str) -> str:
    return run("gh", *args)


def gh_json(*args: str):
    return json.loads(gh(*args))


def normalize_body(text: str) -> str:
    return text.rstrip("\n")


def issue_snapshot(number: int) -> dict:
    return gh_json(
        "issue", "view", str(number), "--repo", REPO,
        "--json", "number,title,body,state,labels,parent,url",
    )


def verify_ticket(number: int, title: str, body_path: Path) -> dict:
    snap = issue_snapshot(number)
    expected_body = normalize_body(body_path.read_text(encoding="utf-8"))
    actual_body = normalize_body(snap["body"])
    assert snap["title"] == title, (number, snap["title"], title)
    assert actual_body == expected_body, f"body mismatch for #{number}"
    assert snap["state"] == "OPEN", (number, snap["state"])
    labels = {row["name"] for row in snap.get("labels", [])}
    assert "ready-for-agent" in labels, (number, labels)
    parent = snap.get("parent")
    assert parent and int(parent["number"]) == REVIEW, (number, parent)
    return snap


def exact_title_matches(title: str) -> list[dict]:
    rows = gh_json(
        "issue", "list", "--repo", REPO, "--state", "all",
        "--search", f'"{title}" in:title',
        "--limit", "100", "--json", "number,title,state,url",
    )
    return [row for row in rows if row["title"] == title]


def create_or_resume_ticket(root: Path, key: str, title: str, rel_body: str) -> dict:
    body_path = root / rel_body
    matches = exact_title_matches(title)
    if len(matches) > 1:
        raise SystemExit(f"duplicate exact-title issues for {title!r}: {matches}")
    if len(matches) == 1:
        number = int(matches[0]["number"])
        return verify_ticket(number, title, body_path)

    url = gh(
        "issue", "create", "--repo", REPO,
        "--title", title,
        "--body-file", str(body_path),
        "--parent", str(REVIEW),
        "--label", "ready-for-agent",
    ).strip()
    number = int(url.rstrip("/").split("/")[-1])
    return verify_ticket(number, title, body_path)


def patch_comment(comment_id: int, body: str, out_path: Path) -> None:
    out_path.write_text(body.rstrip("\n") + "\n", encoding="utf-8")
    gh(
        "api", "--method", "PATCH",
        f"repos/{REPO}/issues/comments/{comment_id}",
        "-F", f"body=@{out_path}",
    )
    readback = gh("api", f"repos/{REPO}/issues/comments/{comment_id}", "--jq", ".body")
    assert normalize_body(readback) == normalize_body(out_path.read_text(encoding="utf-8"))


def reconcile_coverage(root: Path, nums: dict[str, int], urls: dict[str, str]) -> str:
    body = gh("api", f"repos/{REPO}/issues/comments/{COVERAGE_COMMENT}", "--jq", ".body")
    assert body.startswith("## Ticket Coverage Manifest")
    assert f"Spec Body Hash: `{SPEC_BODY_HASH}`" in body
    assert f"Spec baseline: `{SPEC_BASELINE}`" in body

    marker = "\n## Remediation Reconciliation — Spec Review #310\n"
    if marker in body:
        body = body.split(marker, 1)[0].rstrip() + "\n"

    body = re.sub(
        r"^Spec Contract Hash: `[^`]+`$",
        f"Spec Contract Hash: `{SPEC_CONTRACT_HASH}`",
        body,
        count=1,
        flags=re.M,
    )
    assert f"Spec Contract Hash: `{SPEC_CONTRACT_HASH}`" in body

    m = re.search(r"^Approved proposal identity: `([^`]+)`$", body, flags=re.M)
    assert m
    prior_proposal = m.group(1)
    replacement = (
        f"Approved proposal identity: `{PROPOSAL_ID}`\n"
        f"Prior approved proposal identity: `{prior_proposal}`"
        if prior_proposal != PROPOSAL_ID
        else f"Approved proposal identity: `{PROPOSAL_ID}`"
    )
    body = body[:m.start()] + replacement + body[m.end():]

    def append_ticket(cell: str, *numbers: int) -> None:
        nonlocal body
        pat = re.compile(rf"^{re.escape(cell)} → (.+)$", re.M)
        mm = pat.search(body)
        assert mm, cell
        line = mm.group(0)
        current = mm.group(1)
        additions = [f"#{n}" for n in numbers if f"#{n}" not in current]
        if additions:
            new_line = line + ", " + ", ".join(additions)
            body = body[:mm.start()] + new_line + body[mm.end():]

    append_ticket("ID-24", nums["T1"])
    append_ticket("ID-26", nums["T1"], nums["T2"])
    append_ticket("TD-21", nums["T1"], nums["T2"])

    if "\nNORM-1 → " not in body:
        norm_rows = (
            "NORM-1 → #301, #302, #303, #304, #305, #306 — existing implementation lineage; "
            "active remediation is represented by ID-24/ID-26/TD-21 rows.\n"
            "NORM-2 → #301\n"
            "NORM-3 → #301, #302, #303, #304, #305, #306\n"
            f"NORM-4 → no-implementation-work — #278 is closed and Spec #279 has fixed baseline `{SPEC_BASELINE}`.\n"
        )
        anchor = "OOS-1 → "
        idx = body.index(anchor)
        body = body[:idx] + norm_rows + body[idx:]

    body = re.sub(r"^Spec contract cells: \d+$", "Spec contract cells: 122", body, count=1, flags=re.M)
    body = re.sub(r"^Mapped: \d+$", "Mapped: 122", body, count=1, flags=re.M)
    assert "Spec contract cells: 122" in body
    assert "Mapped: 122" in body

    rem = f"""
## Remediation Reconciliation — Spec Review #310

Current source artifact: Spec Review #310 — Spec Review: Implement Investment Decision application lifecycle and Decision Memory queries  
Source product state: `spec-279@{SOURCE_HEAD}`  
Spec Body Hash: `{SPEC_BODY_HASH}`  
Spec Contract Hash: `{SPEC_CONTRACT_HASH}`  
Approved remediation proposal identity: `{PROPOSAL_ID}`

### Review Remediation Ticket Coverage

- RB-2 / command-side read-port failure contract → #{nums["T1"]}.
- RB-2 / ordinary-work and relationship command reads → #{nums["T1"]}.
- RB-3 / renewal and Supersession relationship construction → #{nums["T2"]}.
- RB-3 / relationship-correction construction → #{nums["T2"]}.
- DD-1 / RF-3 → `ARCHSRC-1` → #{nums["T3"]}.
- DD-2 / RF-4 → `ARCHSRC-2` → #{nums["T4"]}.

Publication:
- #{nums["T1"]} {TICKETS[0][1]}
- #{nums["T2"]} {TICKETS[1][1]}
- #{nums["T3"]} {TICKETS[2][1]}
- #{nums["T4"]} {TICKETS[3][1]}
- Native parent: Spec Review #310 for all four remediation tickets.
- Parent Spec provenance / branch owner: #279.
- Native dependencies among these four tickets: None.
- Ticket branch: `spec-279` for all four.
- Ticket baseline at publication: `Pending` for all four.
- Initial label/status: `ready-for-agent` for all four.
- Project-field mutation: none.

### Architecture / Design Obligation Coverage

`ARCHSRC-1`
- Source: `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §§12–13 and §17; `docs/proposed/investment-decisions-decision-relationship-model.md` §5.4; `docs/proposed/durable-persistence-investment-decision-history.md` §§5 and 8.
- Requirement: accept and validate one complete explicitly supplied atomic relationship-correction set capable of repairing several relationships together; validate complete final history and commit every requested correction atomically without an intermediate public graph state.
- Spec-cell reference: None — architecture/design-only decomposition gap.
- Disposition: implementation-ticket → #{nums["T3"]}.

`ARCHSRC-2`
- Source: `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §11 and §17; `docs/proposed/investment-decisions-decision-relationship-model.md` §§2.1 and 6.8; `docs/proposed/durable-persistence-investment-decision-history.md` §8.
- Requirement: support later attributable attachment of genuinely omitted renewal lineage to an already-established source Decision/Need only when the same historical admission predicates and explicit renewal relationship basis are proven, without recreating/reopening identity or rewriting immutable history.
- Spec-cell reference: None — architecture/design-only decomposition gap.
- Disposition: implementation-ticket → #{nums["T4"]}.

Architecture/design source units bounded: 6  
Material non-duplicated architecture obligations: 2  
Architecture disposition rows: 2  
Unmapped architecture obligations: 0  
Ambiguous architecture obligations: 0  
Implementation architecture obligations without ticket coverage: 0  
Deferred obligations without durable existing owner: 0

### Current Coverage Accounting

Spec contract cells: 122  
Disposition rows: 122  
Mapped/dispositioned: 122  
Unmapped cells: 0  
Ambiguous cells: 0  
Unclassified cells: 0  
Implementation cells without ticket coverage: 0  
Non-ticket dispositions without reason/authority: 0  
Material design choices delegated to implementation: 0

This manifest remains decomposition provenance and coverage authority. It is not proof that any implementation ticket has passed closure verification.
"""
    body = body.rstrip() + "\n" + rem.lstrip()
    out = root / "coverage-manifest.md"
    patch_comment(COVERAGE_COMMENT, body, out)
    return hashlib.sha256(out.read_bytes()).hexdigest()


def reconcile_decomposition_defects(root: Path, nums: dict[str, int], urls: dict[str, str]) -> str:
    body = gh("api", f"repos/{REPO}/issues/comments/{DD_COMMENT}", "--jq", ".body")
    assert body.startswith("<!-- decomposition-defects:v1 -->")
    assert "### DD-1 — Atomic multi-relationship correction omitted from decomposition" in body
    assert "### DD-2 — Late omitted-renewal-lineage attachment omitted from decomposition" in body

    titles = {k: t for k, t, _ in TICKETS}

    def edit_top_block(text: str, heading: str, next_heading: str | None, ticket_key: str, arch: str) -> str:
        start = text.index(heading)
        end = text.index(next_heading, start) if next_heading else len(text)
        block = text[start:end]
        block = block.replace("Status: unresolved", "Status: reconciled", 1)
        finding_line = "Finding: RF-3" if ticket_key == "T3" else "Finding: RF-4"
        if f"Architecture obligation: {arch}" not in block:
            block = block.replace(finding_line, f"{finding_line}\nArchitecture obligation: {arch}", 1)
        block = block.replace(
            "Routing: `$to-tickets #310`",
            f"Routing: #{nums[ticket_key]} — {titles[ticket_key]}",
            1,
        )
        return text[:start] + block + text[end:]

    body = edit_top_block(
        body,
        "### DD-1 — Atomic multi-relationship correction omitted from decomposition",
        "### DD-2 — Late omitted-renewal-lineage attachment omitted from decomposition",
        "T3",
        "ARCHSRC-1",
    )
    body = edit_top_block(
        body,
        "### DD-2 — Late omitted-renewal-lineage attachment omitted from decomposition",
        "## Verification Revalidation — $verify-spec #279",
        "T4",
        "ARCHSRC-2",
    )

    prefix, sep, suffix = body.partition("## Verification Revalidation — $verify-spec #279")
    assert sep
    prefix = prefix.replace("Unresolved decomposition defects: 2", "Unresolved decomposition defects: 0", 1)
    prefix = prefix.replace(
        "Open decomposition-defect RF rows: RF-3, RF-4",
        f"Open decomposition-defect RF rows: None — RF-3 → #{nums['T3']} and RF-4 → #{nums['T4']} are reconciled forward to active implementation tickets.",
        1,
    )
    body = prefix + sep + suffix

    marker = "\n## Ticket Reconciliation — $to-tickets #310\n"
    if marker in body:
        body = body.split(marker, 1)[0].rstrip() + "\n"

    body = body.rstrip() + f"""

## Ticket Reconciliation — $to-tickets #310

Approved proposal identity: `{PROPOSAL_ID}`  
Source product state: `spec-279@{SOURCE_HEAD}`  
Parent Ticket Coverage Manifest: comment {COVERAGE_COMMENT}, reconciled and read back before this status update.

- DD-1 / RF-3: `reconciled` → `ARCHSRC-1` → #{nums["T3"]} ({urls["T3"]}).
- DD-2 / RF-4: `reconciled` → `ARCHSRC-2` → #{nums["T4"]} ({urls["T4"]}).

Confirmed decomposition defects supplied: 2  
Decomposition defects dispositioned: 2  
Unmapped decomposition defects: 0  
Ambiguous decomposition destinations: 0  
Architecture obligations without active ticket/authorized non-ticket destination: 0

The decomposition defects are reconciled as decomposition state. Their implementation obligations remain open on the routed remediation tickets until normal implementation and `$verify-ticket-closure` complete.
"""
    out = root / "decomposition-defects.md"
    patch_comment(DD_COMMENT, body, out)
    return hashlib.sha256(out.read_bytes()).hexdigest()


def main() -> int:
    root = Path(os.environ["GITHUB_WORKSPACE"])
    out_dir = Path(os.environ["RUNNER_TEMP"]) / f"to-tickets-310-publish-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    out_dir.mkdir(parents=True, exist_ok=False)

    branch_head = gh("api", f"repos/{REPO}/branches/spec-279", "--jq", ".commit.sha").strip()
    assert branch_head == SOURCE_HEAD, branch_head

    review = gh_json("issue", "view", str(REVIEW), "--repo", REPO, "--json", "number,title,state,url")
    assert review["title"] == "Spec Review: Implement Investment Decision application lifecycle and Decision Memory queries"
    assert review["state"] == "OPEN"

    meta = gh("api", f"repos/{REPO}/issues/comments/{WORKSPACE_METADATA_COMMENT}", "--jq", ".body")
    assert f"**Baseline Commit Hash:** {SPEC_BASELINE}" in meta
    assert "**Branch:** spec-279" in meta

    coverage_before = gh("api", f"repos/{REPO}/issues/comments/{COVERAGE_COMMENT}", "--jq", ".body")
    assert coverage_before.startswith("## Ticket Coverage Manifest")
    assert f"Spec Body Hash: `{SPEC_BODY_HASH}`" in coverage_before

    dd_before = gh("api", f"repos/{REPO}/issues/comments/{DD_COMMENT}", "--jq", ".body")
    assert dd_before.startswith("<!-- decomposition-defects:v1 -->")
    assert "DD-1" in dd_before and "DD-2" in dd_before

    published: dict[str, dict] = {}
    for key, title, rel_body in TICKETS:
        published[key] = create_or_resume_ticket(root, key, title, rel_body)

    nums = {k: int(v["number"]) for k, v in published.items()}
    urls = {k: v["url"] for k, v in published.items()}
    assert len(set(nums.values())) == 4

    for key, title, rel_body in TICKETS:
        verify_ticket(nums[key], title, root / rel_body)

    coverage_sha = reconcile_coverage(out_dir, nums, urls)
    dd_sha = reconcile_decomposition_defects(out_dir, nums, urls)

    result = {
        "proposal_identity": PROPOSAL_ID,
        "source_head": SOURCE_HEAD,
        "spec_baseline": SPEC_BASELINE,
        "tickets": {
            key: {
                "number": nums[key],
                "title": {k: t for k, t, _ in TICKETS}[key],
                "url": urls[key],
                "parent": REVIEW,
                "label": "ready-for-agent",
                "branch": "spec-279",
                "baseline": "Pending",
            }
            for key in nums
        },
        "native_dependency_edges_added": 0,
        "coverage_comment_id": COVERAGE_COMMENT,
        "coverage_body_sha256": coverage_sha,
        "decomposition_comment_id": DD_COMMENT,
        "decomposition_body_sha256": dd_sha,
        "readback": "PASS",
    }
    result_path = out_dir / "publication.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    env_file = Path(os.environ["GITHUB_ENV"])
    with env_file.open("a", encoding="utf-8") as f:
        f.write(f"PUBLISH_ROOT={out_dir}\n")
    print("TO-TICKETS PUBLICATION: PASS")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
