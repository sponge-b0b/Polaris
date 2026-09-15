from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
TICKET = 314
REVIEW = 310
SPEC = 279
FINDING_LEDGER_COMMENT = 5662220111
CHECKPOINT_COMMENT = 5675170405
ROOT_EVIDENCE_COMMENT = 5675355580
BASELINE = "9081386b8fcbf65e117fdac6c7b8c776edaef8f0"
CANDIDATE_STATE = "3f086c624e0164e7a25ea1201bdf858b7ccbcac8a36208dd62410cde3230fc44"
COMMIT = "41bab9971d380b861cb7bbacd59ad2bdf5d9370f"
SHORT_COMMIT = "41bab99"
RF1_DISPOSITION = (
    "Ticket #314 independently certified TICKET CLOSURE: PASS for candidate "
    f"{CANDIDATE_STATE}; Root Closure Evidence comment {ROOT_EVIDENCE_COMMENT}; "
    f"persisted commit {COMMIT}."
)


def run(*args: str, input_text: str | None = None) -> str:
    proc = subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout


def gh_json(*args: str) -> dict | list:
    return json.loads(run("gh", *args))


def patch(path: str, payload: dict) -> dict:
    return json.loads(
        run(
            "gh",
            "api",
            "--method",
            "PATCH",
            path,
            "--input",
            "-",
            input_text=json.dumps(payload),
        )
    )


def require_once(body: str, old: str, new: str) -> str:
    count = body.count(old)
    if count != 1:
        raise SystemExit(f"expected exactly one reconciliation target, found {count}: {old[:100]!r}")
    return body.replace(old, new, 1)


def main() -> int:
    ticket = gh_json(
        "issue",
        "view",
        str(TICKET),
        "--repo",
        REPO,
        "--json",
        "number,title,body,state,url",
    )
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
        f"**Ticket baseline:** `{BASELINE}`",
        f"**Candidate state:** `{CANDIDATE_STATE}`",
        "TICKET CLOSURE: PASS",
        "Acceptance: 14; proven 14; violated 0; unproven 0; unchecked 0",
        "Remediation root: RB-2",
        "Protected roots: RB-1 preserved",
    ]
    missing = [fragment for fragment in required_checkpoint_fragments if fragment not in checkpoint]
    if missing:
        raise SystemExit(f"closure checkpoint binding incomplete: {missing}")

    root_evidence = gh_json("api", f"repos/{REPO}/issues/comments/{ROOT_EVIDENCE_COMMENT}")["body"]
    for fragment in (
        "## Root Closure Evidence",
        "**Root:** RB-2",
        f"**Ticket baseline:** `{BASELINE}`",
        f"**TICKET_CLOSURE_STATE:** `{CANDIDATE_STATE}`",
        f"- `{SHORT_COMMIT}` — `fix(application): own command-side read failures`",
    ):
        if fragment not in root_evidence:
            raise SystemExit(f"root closure evidence missing binding: {fragment}")

    review = gh_json(
        "issue",
        "view",
        str(REVIEW),
        "--repo",
        REPO,
        "--json",
        "number,title,body,state,url",
    )
    if review["state"] != "OPEN":
        raise SystemExit(f"Spec Review #{REVIEW} is not open")
    body = review["body"]

    reconciliation = f"""## Root Closure Reconciliation [2026-09-15]

Remediation ticket: #314 — Define application-owned command-side read failure semantics  
Root: RB-2 — Command-side persistence reads must expose a technology-neutral application-owned persistence-failure contract so raw infrastructure failures cannot escape the application boundary.  
Independent verification: TICKET CLOSURE: PASS  
Ticket baseline: `{BASELINE}`  
TICKET_CLOSURE_STATE: `{CANDIDATE_STATE}`  
Root Closure Evidence: https://github.com/{REPO}/issues/314#issuecomment-{ROOT_EVIDENCE_COMMENT}  
Commit: `{SHORT_COMMIT}` — `fix(application): own command-side read failures`

Reconciled cells:
- RB-2 / Command-side read-port failure contract: satisfied — independent verifier certified all six authoritative command-side read seams, with read-port domain construction `6/6/6/6` and no vendor-specific inward contract.
- RB-2 / Ordinary-work / relationship command reads: satisfied — independent verifier certified current command-consumer closure `12/12/12/12`, narrow translation to `PersistenceUnavailable`, semantic distinction from adjacent failure families, and no partial mutation/receipt on failed reads.

Root status update:
- RB-2: satisfied — fresh `$verify-ticket-closure` returned TICKET CLOSURE: PASS with acceptance `14/14`, violated `0`, unproven `0`, unchecked `0`; three certified closure domains were frozen and the exact candidate remained unchanged through persistence.

Protected roots:
- RB-1: satisfied — independently preserved; shared `ordinary_work.py` changes do not alter External Resolution admission, lifecycle correction, or resolution semantics.

Finding continuity:
- RF-1: satisfied — terminal disposition is ticket #314's independently certified and persisted remediation above.
- RF-2: unchanged open under RB-3.
- RF-3: unchanged open decomposition defect DD-1, owned by #316.
- RF-4: unchanged open decomposition defect DD-2, owned by #317.

Unchanged remediation:
- RB-3 remains open and is owned by #315.
- DD-1 / RF-3 remains unresolved and is owned by #316.
- DD-2 / RF-4 remains unresolved and is owned by #317.
"""

    if f"TICKET_CLOSURE_STATE: `{CANDIDATE_STATE}`" in body and "Remediation ticket: #314 — Define application-owned command-side read failure semantics" in body:
        expected_body = body
    else:
        body = require_once(
            body,
            "### RB-2 — Command-side persistence read failures must be application-owned\n\nStatus: open  ",
            "### RB-2 — Command-side persistence read failures must be application-owned\n\nStatus: satisfied  ",
        )
        old_evidence = """Current evidence:
- Canonical Finding Continuity Ledger `RF-1` remains open with zero invalidation-boundary intersection at `4baa54445e0bcd9f19bb75277a9abc84bea3008c`.
- Current `DecisionCommandStore` command-side read methods return domain/application values or `None`, while explicit unavailable outcomes exist for commit paths; the durable review record therefore still lacks an application-owned read-failure contract.
- Replacement fresh review did not terminally disposition `RF-1`; continuity rules preserve it as open."""
        new_evidence = f"""Current evidence:
- Canonical Finding Continuity Ledger `RF-1` is terminal `satisfied` by #314's independently certified remediation.
- Fresh `$verify-ticket-closure` certified acceptance `14/14`, command-side read-port domain `6/6/6/6`, command-consumer domain `12/12/12/12`, and failure-family domain `10/10/10/10` on exact candidate `{CANDIDATE_STATE}`.
- Root Closure Evidence: https://github.com/{REPO}/issues/314#issuecomment-{ROOT_EVIDENCE_COMMENT}; persisted commit `{SHORT_COMMIT}`."""
        body = require_once(body, old_evidence, new_evidence)
        body = require_once(
            body,
            "| RB-2 | Command-side read-port failure contract | Persistence unavailability on command-side reads is represented by a technology-neutral application-owned contract. | open | RF-1 / Finding Continuity Ledger comment 5662220111; Pending comment 5663229010. |",
            "| RB-2 | Command-side read-port failure contract | Persistence unavailability on command-side reads is represented by a technology-neutral application-owned contract. | satisfied | #314 `TICKET CLOSURE: PASS`; six authoritative read seams certified `6/6/6/6` with application-owned `DecisionCommandReadUnavailable`. |",
        )
        body = require_once(
            body,
            "| RB-2 | Ordinary-work / relationship command reads | Raw infrastructure read exceptions cannot escape through application command services and remain distinct from semantic conflicts/not-found. | open | RF-1; governing application/persistence failure authority. |",
            "| RB-2 | Ordinary-work / relationship command reads | Raw infrastructure read exceptions cannot escape through application command services and remain distinct from semantic conflicts/not-found. | satisfied | #314 `TICKET CLOSURE: PASS`; command-consumer closure `12/12/12/12`, narrow failure translation, no partial mutation/receipt. |",
        )
        expected_body = body.rstrip() + "\n\n" + reconciliation.rstrip() + "\n"
        patch(f"repos/{REPO}/issues/{REVIEW}", {"body": expected_body})

    readback_review = gh_json(
        "issue", "view", str(REVIEW), "--repo", REPO, "--json", "body"
    )["body"]
    if readback_review != expected_body:
        raise SystemExit("Spec Review Root Closure Reconciliation readback mismatch")
    if "### RB-3 — Relationship construction failures must cross application translation\n\nStatus: open" not in readback_review:
        raise SystemExit("RB-3 was not preserved open")

    ledger_record = gh_json("api", f"repos/{REPO}/issues/comments/{FINDING_LEDGER_COMMENT}")
    ledger_body = ledger_record["body"]
    prefix, marker, rest = ledger_body.partition("```json\n")
    if not marker:
        raise SystemExit("Finding Continuity Ledger JSON fence missing")
    json_text, marker2, suffix = rest.partition("\n```")
    if not marker2:
        raise SystemExit("Finding Continuity Ledger closing fence missing")
    rows = json.loads(json_text)
    rf1 = next((row for row in rows if row.get("id") == "RF-1"), None)
    if rf1 is None:
        raise SystemExit("RF-1 missing from Finding Continuity Ledger")
    if rf1.get("status") == "open":
        if rf1.get("disposition_evidence") not in ("", None):
            raise SystemExit("RF-1 has unexpected pre-existing disposition evidence")
        rf1["status"] = "satisfied"
        rf1["disposition_evidence"] = RF1_DISPOSITION
    elif rf1.get("status") == "satisfied" and rf1.get("disposition_evidence") == RF1_DISPOSITION:
        pass
    else:
        raise SystemExit(
            f"RF-1 conflicting durable state: status={rf1.get('status')!r}, disposition={rf1.get('disposition_evidence')!r}"
        )

    for row_id in ("RF-2", "RF-3", "RF-4"):
        row = next((item for item in rows if item.get("id") == row_id), None)
        if row is None or row.get("status") != "open":
            raise SystemExit(f"{row_id} expected to remain open")

    expected_ledger = prefix + marker + json.dumps(rows, indent=2, ensure_ascii=False) + marker2 + suffix
    if expected_ledger != ledger_body:
        patch(
            f"repos/{REPO}/issues/comments/{FINDING_LEDGER_COMMENT}",
            {"body": expected_ledger},
        )
    readback_ledger = gh_json(
        "api", f"repos/{REPO}/issues/comments/{FINDING_LEDGER_COMMENT}"
    )["body"]
    if readback_ledger != expected_ledger:
        raise SystemExit("Finding Continuity Ledger readback mismatch")

    # Re-read root-required tracker state immediately before closure.
    latest_review = gh_json(
        "issue", "view", str(REVIEW), "--repo", REPO, "--json", "body,state"
    )
    if latest_review["state"] != "OPEN" or latest_review["body"] != expected_body:
        raise SystemExit("Spec Review changed after Root Closure Reconciliation")

    closed = patch(
        f"repos/{REPO}/issues/{TICKET}",
        {"state": "closed", "state_reason": "completed"},
    )
    if closed.get("state") != "closed":
        raise SystemExit("ticket closure did not persist")

    readback_ticket = gh_json(
        "issue", "view", str(TICKET), "--repo", REPO, "--json", "state,body,url"
    )
    if readback_ticket["state"] != "CLOSED":
        raise SystemExit("ticket closure readback failed")

    print(f"ROOT_RECONCILIATION=PASS")
    print(f"FINDING_LEDGER_SHA256={hashlib.sha256(readback_ledger.encode()).hexdigest()}")
    print(f"SPEC_REVIEW_BODY_SHA256={hashlib.sha256(expected_body.encode()).hexdigest()}")
    print(f"TICKET_CLOSED=#{TICKET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
