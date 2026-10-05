from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

REPO = "sponge-b0b/Polaris"
EXPECTED_MAIN_HEAD = "8cc166683fa4e103e31e3a39f385102eb0f6e7f0"
EXPECTED_AGENTS_BLOB = "d827c7725ba47b5aee86bdaa45c736bba59c14f7"
EXPECTED_SPEC_HEAD = "2f7f809d4c9ffdc6bd8619ac9403f9b0c057ac7e"
APPROVED_PROPOSAL_SHA = "cf4f732eb966a07d70b797ecf123446cf04262d2f31f13b2bc793fec0859ff8a"
SPEC_BODY_HASH = "275d831d1fe185eaabac34e9d4c6224cf98d28285e64ce03ce16f6c07668c61f"
SPEC_CONTRACT_HASH = "db6842515a70ef6133bb21c962dd96842a840287d28e7a0fd4096d05342ed034"
OLD_SPEC_CONTRACT_HASH = "a03ed466381753221e81b549da3b8e52cc66294512f86507e4ecb2aded1669c3"
BASELINE_378 = "a764f201514754f50ff1535b4d441bc03ad8d093"
TCM_COMMENT_ID = 5899020558
DD_COMMENT_ID = 5930434832
SOURCE_378_OLD_TITLE = "Preserve Evidence correction lineage and interpretation end to end"
BINDING_TITLE = "Correct Evidence bindings with fixed-endpoint replacement semantics"
ASSESSMENT_TITLE = "Correct sufficiency assessments with derived proof and trusted revalidation"
API_VERSION = "2026-03-10"


def log(msg: str) -> None:
    print(msg, flush=True)


def run(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    log("+ " + " ".join(args))
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)


def api(method: str, path: str, payload: object | None = None) -> object:
    cmd = [
        "gh", "api", "--method", method,
        "-H", "Accept: application/vnd.github+json",
        "-H", f"X-GitHub-Api-Version: {API_VERSION}",
        path,
    ]
    inp = None
    if payload is not None:
        cmd += ["--input", "-"]
        inp = json.dumps(payload)
    proc = subprocess.run(cmd, input=inp, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"GitHub API {method} {path} failed: {proc.stderr.strip()}")
    out = proc.stdout.strip()
    return json.loads(out) if out else None


def issue(number: int) -> dict:
    obj = api("GET", f"repos/{REPO}/issues/{number}")
    assert isinstance(obj, dict)
    return obj


def comment(comment_id: int) -> dict:
    obj = api("GET", f"repos/{REPO}/issues/comments/{comment_id}")
    assert isinstance(obj, dict)
    return obj


def blockers(number: int) -> list[int]:
    obj = api("GET", f"repos/{REPO}/issues/{number}/dependencies/blocked_by?per_page=100")
    assert isinstance(obj, list)
    return sorted(int(x["number"]) for x in obj)


def issue_id(number: int) -> int:
    return int(issue(number)["id"])


def add_dependency(number: int, blocker_number: int) -> None:
    api("POST", f"repos/{REPO}/issues/{number}/dependencies/blocked_by", {"issue_id": issue_id(blocker_number)})


def remove_dependency(number: int, blocker_number: int) -> None:
    api("DELETE", f"repos/{REPO}/issues/{number}/dependencies/blocked_by/{issue_id(blocker_number)}")


def add_child(parent_number: int, child_number: int) -> None:
    api("POST", f"repos/{REPO}/issues/{parent_number}/sub_issues", {"sub_issue_id": issue_id(child_number)})


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one old value, found {count}")
    return text.replace(old, new, 1)


def action_block(text: str, marker: str, next_marker: str) -> str:
    start = text.index(marker)
    end = text.index(next_marker, start)
    return text[start:end].rstrip()


def parse_ticket_action(block: str) -> tuple[str, str]:
    m = re.search(r"^(?:New title|Title|Title remains): (.+)$", block, flags=re.MULTILINE)
    if not m:
        raise SystemExit("ticket action missing title")
    title = m.group(1).strip()
    body_marker = "Complete proposed body:\n\n"
    start = block.index(body_marker) + len(body_marker)
    end = block.index("\n\nRequired label/status:", start)
    return title, block[start:end].rstrip() + "\n"


def recovery_comment(block: str, actual_number: int) -> str:
    marker = "<!-- ticket-reslice-recovery:v1 -->"
    start = block.index(marker)
    body = block[start:].strip() + "\n"
    body = re.sub(r"#<NEW-[A-Z-]+ actual issue number>", f"#{actual_number}", body)
    return body


def aliases(text: str, binding_number: int, assessment_number: int) -> str:
    return (
        text.replace("NEW-BINDING-CORRECTION", f"#{binding_number}")
        .replace("NEW-ASSESSMENT-CORRECTION", f"#{assessment_number}")
    )


def assert_issue_ready(number: int) -> None:
    obj = issue(number)
    labels = {x["name"] for x in obj.get("labels", [])}
    if obj.get("state") != "open" or "ready-for-agent" not in labels:
        raise SystemExit(f"#{number} is no longer open/ready-for-agent")


def exact_title_exists(title: str) -> list[dict]:
    q = quote_plus(f'repo:{REPO} is:issue in:title "{title}"')
    obj = api("GET", f"search/issues?q={q}&per_page=100")
    assert isinstance(obj, dict)
    return [x for x in obj.get("items", []) if x.get("title") == title]


def update_ticket(number: int, title: str, body: str) -> None:
    api("PATCH", f"repos/{REPO}/issues/{number}", {"title": title, "body": body})


def create_ticket(title: str, body: str) -> dict:
    obj = api("POST", f"repos/{REPO}/issues", {"title": title, "body": body, "labels": ["ready-for-agent"]})
    assert isinstance(obj, dict)
    return obj


def verify_ticket(number: int, title: str, body: str) -> None:
    obj = issue(number)
    labels = {x["name"] for x in obj.get("labels", [])}
    if obj.get("title") != title or obj.get("body") != body or obj.get("state") != "open" or "ready-for-agent" not in labels:
        raise SystemExit(f"#{number} exact ticket readback failed")


def build_tcm(current: str, binding_number: int, assessment_number: int) -> str:
    b = f"#{binding_number}"
    a = f"#{assessment_number}"
    out = replace_once(
        current,
        f"Spec Contract Hash: {OLD_SPEC_CONTRACT_HASH}",
        f"Spec Contract Hash: {SPEC_CONTRACT_HASH}",
        "TCM contract hash",
    )
    rows = {
        "US-3 → #378": f"US-3 → #378, {b}, {a}",
        "US-12 → #377": f"US-12 → #377, {a}",
        "ID-2 → #378": f"ID-2 → #378, {b}, {a}",
        "ID-12 → #377": f"ID-12 → #377, {a}",
        "ID-20 → #372, #373, #374, #377, #378, #381": f"ID-20 → #372, #373, #374, #377, #378, {b}, {a}, #381",
        "TD-2 → #378": f"TD-2 → #378, {b}, {a}",
        "TD-5 → #376, #377": f"TD-5 → #376, #377, {a}",
        "TD-9 → #372, #373, #374, #377, #378, #381": f"TD-9 → #372, #373, #374, #377, #378, {b}, {a}, #381",
    }
    for old, new in rows.items():
        out = replace_once(out, old, new, f"TCM row {old}")
    out = replace_once(
        out,
        "Tickets/destination: #372, #374, #377, #378",
        f"Tickets/destination: #372, #374, #377, #378, {b}, {a}",
        "TCM ARCHSRC-2",
    )
    out = replace_once(
        out,
        "Tickets/destination: #373, #376, #385, #377",
        f"Tickets/destination: #373, #376, #385, #377, {a}",
        "TCM ARCHSRC-4",
    )
    out = replace_once(
        out,
        "Tickets/destination: #372, #373, #374, #385, #377, #378, #381",
        f"Tickets/destination: #372, #373, #374, #385, #377, #378, {b}, {a}, #381",
        "TCM ARCHSRC-7",
    )
    old_recon = "DD-1 remains reconciled. The current remediation introduces no new confirmed decomposition defect; it updates amended Spec and ADR 0014 routing through #385 and #377."
    new_recon = (
        "DD-1 remains reconciled. DD-2 is reconciled by splitting observation correction, binding correction, and assessment-specific correction into separate context-fit slices; "
        f"routing ADR 0012/ARCHSRC-2 and ARCHSRC-7 across #378 and {b}, ADR 0014/ARCHSRC-4 to {a}, carrying all result-affecting observation/binding/assessment correction interpretation through #379, "
        "and carrying the corresponding current-basis invalidation and fresh commit-time revalidation explicitly into #380 and #381. DD-2 becomes reconciled only after the approved ticket bodies, native relationships, this manifest, recovery records, and decomposition-defect record are published and read back exactly."
    )
    out = replace_once(out, old_recon, new_recon, "TCM DD reconciliation")
    pub = Path(".verification/fragments/publication-state.txt").read_text(encoding="utf-8")
    pub = aliases(pub, binding_number, assessment_number)
    marker = "### Publication State\n"
    idx = out.index(marker)
    out = out[:idx] + pub
    return out


def build_dd(current: str, binding_number: int, assessment_number: int) -> str:
    marker = "### DD-2\n"
    idx = current.index(marker)
    head, tail = current[:idx], current[idx:]
    tail = replace_once(tail, "Status: unresolved", "Status: reconciled", "DD-2 status")
    tail = replace_once(tail, "Current manifest state: misrouted", "Current manifest state: reconciled", "DD-2 manifest state")
    b = f"#{binding_number}"
    a = f"#{assessment_number}"
    reconciliation = (
        "Reconciliation: Reconciled through the approved DD-2 ticket split and consumer carry: #378 owns the shared correction foundation plus observation correction; "
        f"{b} owns binding-specific fixed-endpoint correction under ARCHSRC-2/7; {a} owns sufficiency-assessment correction with Evidence-derived proof and trusted-instant re-evaluation/atomic revalidation under ARCHSRC-2/4/7; "
        "#379 reconstructs all three correction families and reassessment proof without hindsight; #380 treats result-affecting observation, binding, and assessment correction interpretation as explicit current-basis invalidators; "
        "#381 freshly reconstructs/revalidates all result-affecting correction interpretations at dependent commit. The parent TCM comment 5899020558 carries current Spec Contract Hash "
        f"{SPEC_CONTRACT_HASH} and the exact realized routing. No closed ticket is reopened or rewritten."
    )
    tail = replace_once(tail, "Reconciliation: None", reconciliation, "DD-2 reconciliation")
    return head + tail


def main() -> None:
    # Authority and source-state preflight.
    main_head = api("GET", f"repos/{REPO}/branches/main")["commit"]["sha"]
    spec_head = api("GET", f"repos/{REPO}/branches/spec-357")["commit"]["sha"]
    if main_head != EXPECTED_MAIN_HEAD:
        raise SystemExit(f"main moved: {main_head}")
    if spec_head != EXPECTED_SPEC_HEAD:
        raise SystemExit(f"spec-357 moved: {spec_head}")
    run(["git", "fetch", "origin", "main", "spec-357", "chatgpt/verify-ticket-decomposition-357-dd2-repaired"])
    agents_blob = subprocess.check_output(
        ["bash", "-lc", f"git show {EXPECTED_MAIN_HEAD}:AGENTS.md | git hash-object --stdin"], text=True
    ).strip()
    if agents_blob != EXPECTED_AGENTS_BLOB:
        raise SystemExit(f"AGENTS blob changed: {agents_blob}")

    # Rebuild exactly the human-approved proposal and verify its identity before mutation.
    env = os.environ.copy()
    env["CANDIDATE_HEAD"] = EXPECTED_SPEC_HEAD
    run([sys.executable, ".verification/build-proposal-357-dd2-resume.py"], env=env)
    run([sys.executable, ".verification/repair-current-consumers.py"])
    proposal_path = Path("/tmp/proposal-357-dd2-resume.txt")
    proposal = proposal_path.read_text(encoding="utf-8")
    proposal_sha = hashlib.sha256(proposal_path.read_bytes()).hexdigest()
    log(f"proposal_sha={proposal_sha}")
    if proposal_sha != APPROVED_PROPOSAL_SHA:
        raise SystemExit("approved proposal identity mismatch")

    markers = [
        "ACTION 1 — UPDATE TICKET #378",
        "ACTION 2 — CREATE NEW-BINDING-CORRECTION",
        "ACTION 3 — CREATE NEW-ASSESSMENT-CORRECTION",
        "ACTION 4 — UPDATE TICKET #379",
        "ACTION 5 — UPDATE TICKET #380",
        "ACTION 6 — UPDATE TICKET #381",
        "ACTION 7 — UPDATE PARENT TICKET COVERAGE MANIFEST COMMENT 5899020558 IN PLACE",
        "ACTION 8 — UPDATE DECOMPOSITION DEFECT COMMENT 5930434832 IN PLACE",
        "ACTION 9 — NATIVE RELATIONSHIP / PUBLICATION REALIZATION",
        "PARENT SEMANTIC-CONSUMER IMPACT EVIDENCE",
    ]
    blocks = [action_block(proposal, markers[i], markers[i + 1]) for i in range(9)]
    title378, body378 = parse_ticket_action(blocks[0])
    binding_title, binding_body_template = parse_ticket_action(blocks[1])
    assessment_title, assessment_body_template = parse_ticket_action(blocks[2])
    title379, body379_template = parse_ticket_action(blocks[3])
    title380, body380_template = parse_ticket_action(blocks[4])
    title381, body381_template = parse_ticket_action(blocks[5])
    if binding_title != BINDING_TITLE or assessment_title != ASSESSMENT_TITLE:
        raise SystemExit("new ticket title mismatch")

    # Tracker preflight before the first mutation.
    if issue(378)["title"] != SOURCE_378_OLD_TITLE:
        raise SystemExit("#378 title drifted before publication")
    for number in (378, 379, 380, 381):
        assert_issue_ready(number)
    expected_pre_blockers = {378: [374, 377], 379: [375, 377, 378], 380: [379], 381: [380]}
    for number, expected in expected_pre_blockers.items():
        actual = blockers(number)
        if actual != expected:
            raise SystemExit(f"#{number} blocker pre-state drifted: {actual} != {expected}")
    tcm_pre = comment(TCM_COMMENT_ID)["body"]
    dd_pre = comment(DD_COMMENT_ID)["body"]
    if f"Spec Contract Hash: {OLD_SPEC_CONTRACT_HASH}" not in tcm_pre:
        raise SystemExit("TCM pre-publication hash is no longer the certified stale value")
    if "### DD-2\nStatus: unresolved" not in dd_pre or "Reconciliation: None" not in dd_pre:
        raise SystemExit("DD-2 pre-publication state drifted")
    if exact_title_exists(BINDING_TITLE) or exact_title_exists(ASSESSMENT_TITLE):
        raise SystemExit("one or both certified destination ticket titles already exist; refusing duplicate publication")

    # Create destination tickets in deterministic order so alias substitution is stable.
    binding_obj = create_ticket(binding_title, binding_body_template)
    binding_number = int(binding_obj["number"])
    binding_body = aliases(binding_body_template, binding_number, -1)
    if binding_obj.get("body") != binding_body:
        update_ticket(binding_number, binding_title, binding_body)

    assessment_body_pre = assessment_body_template.replace("NEW-BINDING-CORRECTION", f"#{binding_number}")
    assessment_obj = create_ticket(assessment_title, assessment_body_pre)
    assessment_number = int(assessment_obj["number"])

    # Deterministic alias-to-actual-issue substitution across all certified ticket bodies.
    binding_body = aliases(binding_body_template, binding_number, assessment_number)
    assessment_body = aliases(assessment_body_template, binding_number, assessment_number)
    body378 = aliases(body378, binding_number, assessment_number)
    body379 = aliases(body379_template, binding_number, assessment_number)
    body380 = aliases(body380_template, binding_number, assessment_number)
    body381 = aliases(body381_template, binding_number, assessment_number)
    update_ticket(binding_number, binding_title, binding_body)
    update_ticket(assessment_number, assessment_title, assessment_body)
    update_ticket(378, title378, body378)
    update_ticket(379, title379, body379)
    update_ticket(380, title380, body380)
    update_ticket(381, title381, body381)

    # Native parentage and dependency realization.
    add_child(357, binding_number)
    add_child(357, assessment_number)
    remove_dependency(378, 374)
    remove_dependency(378, 377)
    add_dependency(378, 372)
    add_dependency(binding_number, 374)
    add_dependency(binding_number, 378)
    add_dependency(assessment_number, 377)
    add_dependency(assessment_number, 378)
    add_dependency(assessment_number, binding_number)
    add_dependency(379, binding_number)
    add_dependency(379, assessment_number)

    # Persist one managed recovery record per destination after issue-number realization.
    recovery_binding = recovery_comment(blocks[1], binding_number)
    recovery_assessment = recovery_comment(blocks[2], assessment_number)
    recovery_binding = aliases(recovery_binding, binding_number, assessment_number)
    recovery_assessment = aliases(recovery_assessment, binding_number, assessment_number)
    api("POST", f"repos/{REPO}/issues/{binding_number}/comments", {"body": recovery_binding})
    api("POST", f"repos/{REPO}/issues/{assessment_number}/comments", {"body": recovery_assessment})

    # Reconcile the TCM exactly after ticket/native realization.
    tcm_final = build_tcm(tcm_pre, binding_number, assessment_number)
    api("PATCH", f"repos/{REPO}/issues/comments/{TCM_COMMENT_ID}", {"body": tcm_final})

    # Mandatory pre-DD readback: tickets, labels/state, parentage, blockers, recovery records, and TCM.
    verify_ticket(378, title378, body378)
    verify_ticket(binding_number, binding_title, binding_body)
    verify_ticket(assessment_number, assessment_title, assessment_body)
    verify_ticket(379, title379, body379)
    verify_ticket(380, title380, body380)
    verify_ticket(381, title381, body381)
    expected_blockers = {
        378: [372],
        binding_number: [374, 378],
        assessment_number: sorted([377, 378, binding_number]),
        379: sorted([375, 377, 378, binding_number, assessment_number]),
        380: [379],
        381: [380],
    }
    for number, expected in expected_blockers.items():
        actual = blockers(number)
        if actual != expected:
            raise SystemExit(f"#{number} blocker readback failed: {actual} != {expected}")
    children = api("GET", f"repos/{REPO}/issues/357/sub_issues?per_page=100")
    child_numbers = {int(x["number"]) for x in children}
    if binding_number not in child_numbers or assessment_number not in child_numbers:
        raise SystemExit("new ticket parent readback failed")
    for number, expected_comment in ((binding_number, recovery_binding), (assessment_number, recovery_assessment)):
        comments = api("GET", f"repos/{REPO}/issues/{number}/comments?per_page=100")
        managed = [x["body"] for x in comments if "<!-- ticket-reslice-recovery:v1 -->" in x.get("body", "")]
        if managed != [expected_comment]:
            raise SystemExit(f"#{number} recovery-record readback failed")
    if comment(TCM_COMMENT_ID)["body"] != tcm_final:
        raise SystemExit("TCM exact readback failed")

    # Only after the mandatory publication readback above, reconcile DD-2.
    dd_final = build_dd(dd_pre, binding_number, assessment_number)
    api("PATCH", f"repos/{REPO}/issues/comments/{DD_COMMENT_ID}", {"body": dd_final})
    if comment(DD_COMMENT_ID)["body"] != dd_final:
        raise SystemExit("DD-2 exact readback failed")

    result = {
        "status": "published-and-read-back",
        "proposal_sha256": proposal_sha,
        "spec_head": EXPECTED_SPEC_HEAD,
        "binding_ticket": binding_number,
        "assessment_ticket": assessment_number,
        "ticket_bodies_read_back": [378, binding_number, assessment_number, 379, 380, 381],
        "native_blockers": {str(k): v for k, v in expected_blockers.items()},
        "native_parent": 357,
        "recovery_records": {str(binding_number): "exact", str(assessment_number): "exact"},
        "tcm_comment": TCM_COMMENT_ID,
        "tcm_contract_hash": SPEC_CONTRACT_HASH,
        "dd_comment": DD_COMMENT_ID,
        "dd2_status": "reconciled",
        "owner_local_378_wip_mutated": False,
    }
    Path("/tmp/publication-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log(Path("/tmp/publication-result.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
