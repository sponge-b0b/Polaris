from __future__ import annotations

import hashlib
import json
import subprocess
import sys

REPO = "sponge-b0b/Polaris"
TICKET = 315
REVIEW = 310
FINDING_LEDGER_COMMENT = 5662220111
CHECKPOINT_COMMENT = 5675531025
ROOT_EVIDENCE_COMMENT = 5675660811
BASELINE = "41bab9971d380b861cb7bbacd59ad2bdf5d9370f"
CANDIDATE_STATE = "64ac0a239d7f472205063a45ae1d59b3815321f753afe67e8deb31658657b341"
COMMIT = "e243c2c50b0d2a2ed4ee539f040fed53597a402f"
SHORT_COMMIT = "e243c2c"
RF2_DISPOSITION = (
    "Ticket #315 independently certified TICKET CLOSURE: PASS for candidate "
    f"{CANDIDATE_STATE}; Root Closure Evidence comment {ROOT_EVIDENCE_COMMENT}; "
    f"persisted commit {COMMIT}."
)


def run(*args: str, input_text: str | None = None) -> str:
    proc = subprocess.run(args, input=input_text, text=True, capture_output=True, check=False)
    if proc.returncode:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout


def gh_json(*args: str) -> dict | list:
    return json.loads(run("gh", *args))


def patch(path: str, payload: dict) -> dict:
    return json.loads(run("gh", "api", "--method", "PATCH", path, "--input", "-", input_text=json.dumps(payload)))


def require_once(body: str, old: str, new: str) -> str:
    count = body.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one reconciliation target, found {count}: {old[:120]!r}")
    return body.replace(old, new, 1)


def main() -> int:
    ticket = gh_json("issue", "view", str(TICKET), "--repo", REPO, "--json", "number,title,body,state,url")
    if ticket["state"] != "OPEN":
        raise SystemExit(f"ticket #{TICKET} unexpectedly not open before closure: {ticket['state']}")
    parent = gh_json("api", f"repos/{REPO}/issues/{TICKET}/parent")
    if parent.get("number") != REVIEW:
        raise SystemExit(f"native parent mismatch: {parent.get('number')}")
    branch = gh_json("api", f"repos/{REPO}/branches/spec-279")
    if branch["commit"]["sha"] != COMMIT:
        raise SystemExit(f"spec-279 head mismatch: {branch['commit']['sha']}")

    checkpoint = gh_json("api", f"repos/{REPO}/issues/comments/{CHECKPOINT_COMMENT}")["body"]
    required_checkpoint_fragments = [
        "<!-- implement-ticket-closure-checkpoint:v2 -->",
        "**Stage:** verifier-passed",
        f"**Ticket:** #{TICKET}",
        f"**Ticket baseline:** {BASELINE}",
        f"**Candidate state:** {CANDIDATE_STATE}",
        "TICKET CLOSURE: PASS",
        "Acceptance: 18; proven 18; violated 0; unproven 0; unchecked 0",
        "Remediation root: RB-3",
        "Protected roots: RB-2 preserved",
    ]
    missing = [fragment for fragment in required_checkpoint_fragments if fragment not in checkpoint]
    if missing:
        raise SystemExit(f"closure checkpoint binding incomplete: {missing}")

    root_evidence = gh_json("api", f"repos/{REPO}/issues/comments/{ROOT_EVIDENCE_COMMENT}")["body"]
    for fragment in (
        "## Root Closure Evidence",
        "**Root:** RB-3",
        f"**Ticket baseline:** `{BASELINE}`",
        f"**TICKET_CLOSURE_STATE:** `{CANDIDATE_STATE}`",
        f"- `{SHORT_COMMIT}` — `fix(application): translate relationship construction failures`",
    ):
        if fragment not in root_evidence:
            raise SystemExit(f"root closure evidence missing binding: {fragment}")

    review = gh_json("issue", "view", str(REVIEW), "--repo", REPO, "--json", "number,title,body,state,url")
    if review["state"] != "OPEN":
        raise SystemExit(f"Spec Review #{REVIEW} is not open")
    body = review["body"]

    reconciliation = f"""## Root Closure Reconciliation [2026-09-15]

Remediation ticket: #315 — Translate relationship construction failures at the application boundary  
Root: RB-3 — Relationship-construction domain failures must cross the application-owned relationship error-translation boundary rather than leaking raw domain exceptions.  
Independent verification: TICKET CLOSURE: PASS  
Ticket baseline: `{BASELINE}`  
TICKET_CLOSURE_STATE: `{CANDIDATE_STATE}`  
Root Closure Evidence: https://github.com/{REPO}/issues/315#issuecomment-{ROOT_EVIDENCE_COMMENT}  
Commit: `{SHORT_COMMIT}` — `fix(application): translate relationship construction failures`

Reconciled cells:
- RB-3 / Renewal / Supersession relationship construction: satisfied — independent verifier certified constructor-bearing application relationship paths `3/3/3/3`, with renewal and Supersession fact construction inside the established narrow translation boundary.
- RB-3 / Relationship correction construction: satisfied — independent verifier certified privileged `relationship_correction()` construction inside the same boundary with established history/conflict typing preserved.

Root status update:
- RB-3: satisfied — fresh `$verify-ticket-closure` returned TICKET CLOSURE: PASS with acceptance `18/18`, violated `0`, unproven `0`, unchecked `0`; three certified closure domains were frozen and the exact candidate remained unchanged through persistence.

Protected roots:
- RB-2: satisfied — independently preserved; shared relationship command read/unavailability translation remains unchanged.
- RB-1: satisfied and unaffected by this ticket.

Finding continuity:
- RF-1: remains terminal `satisfied` by #314.
- RF-2: satisfied — terminal disposition is ticket #315's independently certified and persisted remediation above.
- RF-3: unchanged open decomposition defect DD-1, implementation obligation owned by #316.
- RF-4: unchanged open decomposition defect DD-2, implementation obligation owned by #317.

Unchanged remediation:
- DD-1 / RF-3 remains implementation-open on #316.
- DD-2 / RF-4 remains implementation-open on #317.
"""

    if f"TICKET_CLOSURE_STATE: `{CANDIDATE_STATE}`" in body and "Remediation ticket: #315 — Translate relationship construction failures at the application boundary" in body:
        expected_body = body
    else:
        body = require_once(
            body,
            "### RB-3 — Relationship construction failures must cross application translation\n\nStatus: open  ",
            "### RB-3 — Relationship construction failures must cross application translation\n\nStatus: satisfied  ",
        )
        old_evidence = """Current evidence:
- Canonical Finding Continuity Ledger `RF-2` remains open with zero invalidation-boundary intersection at `4baa54445e0bcd9f19bb75277a9abc84bea3008c`.
- Durable review evidence shows `relationship_fact()` and `relationship_correction()` construction occurs before the `_RELATIONSHIP_ERRORS` translation guard on affected paths.
- Replacement fresh review did not terminally disposition `RF-2`; continuity rules preserve it as open."""
        new_evidence = f"""Current evidence:
- Canonical Finding Continuity Ledger `RF-2` is terminal `satisfied` by #315's independently certified remediation.
- Fresh `$verify-ticket-closure` certified acceptance `18/18`, constructor-bearing application relationship paths `3/3/3/3`, established relationship-domain failure translation family `6/6/6/6`, and both RB-3 active cells `2/2/2/2` on exact candidate `{CANDIDATE_STATE}`.
- Root Closure Evidence: https://github.com/{REPO}/issues/315#issuecomment-{ROOT_EVIDENCE_COMMENT}; persisted commit `{SHORT_COMMIT}`."""
        body = require_once(body, old_evidence, new_evidence)
        body = require_once(
            body,
            "| RB-3 | Renewal / Supersession relationship construction | Relationship-fact construction failures cross the established application translation boundary. | open | RF-2 / Finding Continuity Ledger comment 5662220111. |",
            "| RB-3 | Renewal / Supersession relationship construction | Relationship-fact construction failures cross the established application translation boundary. | satisfied | #315 `TICKET CLOSURE: PASS`; renewal/Supersession constructor-bearing application paths certified inside `_RELATIONSHIP_ERRORS`. |",
        )
        body = require_once(
            body,
            "| RB-3 | Relationship correction construction | `relationship_correction()` failures cross the established application translation boundary and preserve semantic conflict typing. | open | RF-2; Pending comment 5663229010. |",
            "| RB-3 | Relationship correction construction | `relationship_correction()` failures cross the established application translation boundary and preserve semantic conflict typing. | satisfied | #315 `TICKET CLOSURE: PASS`; correction constructor translation certified with history/conflict typing preserved. |",
        )
        expected_body = body.rstrip() + "\n\n" + reconciliation.rstrip() + "\n"
        patch(f"repos/{REPO}/issues/{REVIEW}", {"body": expected_body})

    readback_review = gh_json("issue", "view", str(REVIEW), "--repo", REPO, "--json", "body")["body"]
    if readback_review != expected_body:
        raise SystemExit("Spec Review Root Closure Reconciliation readback mismatch")
    if "### RB-2 — Command-side persistence read failures must be application-owned\n\nStatus: satisfied" not in readback_review:
        raise SystemExit("RB-2 was not preserved satisfied")

    ledger_record = gh_json("api", f"repos/{REPO}/issues/comments/{FINDING_LEDGER_COMMENT}")
    ledger_body = ledger_record["body"]
    prefix, marker, rest = ledger_body.partition("```json\n")
    if not marker:
        raise SystemExit("Finding Continuity Ledger JSON fence missing")
    json_text, marker2, suffix = rest.partition("\n```")
    if not marker2:
        raise SystemExit("Finding Continuity Ledger closing fence missing")
    rows = json.loads(json_text)
    rf2 = next((row for row in rows if row.get("id") == "RF-2"), None)
    if rf2 is None:
        raise SystemExit("RF-2 missing from Finding Continuity Ledger")
    if rf2.get("status") == "open":
        if rf2.get("disposition_evidence") not in ("", None):
            raise SystemExit("RF-2 has unexpected pre-existing disposition evidence")
        rf2["status"] = "satisfied"
        rf2["disposition_evidence"] = RF2_DISPOSITION
    elif rf2.get("status") == "satisfied" and rf2.get("disposition_evidence") == RF2_DISPOSITION:
        pass
    else:
        raise SystemExit(f"RF-2 conflicting durable state: status={rf2.get('status')!r}, disposition={rf2.get('disposition_evidence')!r}")

    rf1 = next((row for row in rows if row.get("id") == "RF-1"), None)
    if rf1 is None or rf1.get("status") != "satisfied":
        raise SystemExit("RF-1 expected to remain satisfied")
    for row_id in ("RF-3", "RF-4"):
        row = next((item for item in rows if item.get("id") == row_id), None)
        if row is None or row.get("status") != "open":
            raise SystemExit(f"{row_id} expected to remain open")

    expected_ledger = prefix + marker + json.dumps(rows, indent=2, ensure_ascii=False) + marker2 + suffix
    if expected_ledger != ledger_body:
        patch(f"repos/{REPO}/issues/comments/{FINDING_LEDGER_COMMENT}", {"body": expected_ledger})
    readback_ledger = gh_json("api", f"repos/{REPO}/issues/comments/{FINDING_LEDGER_COMMENT}")["body"]
    if readback_ledger != expected_ledger:
        raise SystemExit("Finding Continuity Ledger readback mismatch")

    latest_review = gh_json("issue", "view", str(REVIEW), "--repo", REPO, "--json", "body,state")
    if latest_review["state"] != "OPEN" or latest_review["body"] != expected_body:
        raise SystemExit("Spec Review changed after Root Closure Reconciliation")

    closed = patch(f"repos/{REPO}/issues/{TICKET}", {"state": "closed", "state_reason": "completed"})
    if closed.get("state") != "closed":
        raise SystemExit("ticket closure did not persist")
    readback_ticket = gh_json("issue", "view", str(TICKET), "--repo", REPO, "--json", "state,body,url")
    if readback_ticket["state"] != "CLOSED":
        raise SystemExit("ticket closure readback failed")

    print("ROOT_RECONCILIATION=PASS")
    print(f"FINDING_LEDGER_SHA256={hashlib.sha256(readback_ledger.encode()).hexdigest()}")
    print(f"SPEC_REVIEW_BODY_SHA256={hashlib.sha256(expected_body.encode()).hexdigest()}")
    print(f"TICKET_CLOSED=#{TICKET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
