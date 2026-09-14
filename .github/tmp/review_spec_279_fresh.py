from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
SPEC = 279
HEAD = "4baa54445e0bcd9f19bb75277a9abc84bea3008c"
BASELINE = "4daed9034891600597a47c01b6c39d5ebd9914ca"
BODY_HASH = "5f59ee666c65e9e93fe3b69403dbf4bc5328332d14d6339fc55b067755e4eb17"
CONTRACT_HASH = "3044b039742306f1c0ed10085479c7c823ed463443e8d11d761f45de564fb334"
VERIFICATION_HASH = "4b7f7a1641603337b2880adb851ca8ee4d4c13baee97b1da0f80a63d69eac9e4"
RECEIPT_ID = 5659536204


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    candidate = workspace / "candidate"
    root = Path(os.environ["RUNNER_TEMP"]) / (
        f"review-spec-279-exit-{os.environ['GITHUB_RUN_ID']}-"
        f"{os.environ['GITHUB_RUN_ATTEMPT']}"
    )
    root.mkdir(parents=True, exist_ok=False)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as handle:
        handle.write(f"REVIEW_ROOT={root}\n")

    comments = root / "spec-comments.json"
    comments.write_text(
        run(
            "gh",
            "api",
            "--paginate",
            "--slurp",
            "-H",
            "X-GitHub-Api-Version: 2026-03-10",
            f"repos/{REPO}/issues/{SPEC}/comments?per_page=100",
            cwd=candidate,
        ),
        encoding="utf-8",
    )
    summary = root / "spec-comments-summary.json"
    summary.write_text(
        run(
            "python",
            ".agents/skills/verify-spec/scripts/verify_spec_artifacts.py",
            "comments",
            "--input",
            str(comments),
            cwd=candidate,
        ),
        encoding="utf-8",
    )
    spec_body = root / "spec-body.md"
    spec_body.write_text(
        run(
            "gh",
            "issue",
            "view",
            str(SPEC),
            "--repo",
            REPO,
            "--json",
            "body",
            "--jq",
            ".body",
            cwd=candidate,
        ),
        encoding="utf-8",
    )
    checkpoint_path = root / "checkpoint.json"
    checkpoint_path.write_text(
        run(
            "python",
            ".agents/skills/review-spec/scripts/review_spec_artifacts.py",
            "checkpoint",
            "--comments-summary",
            str(summary),
            "--spec-body",
            str(spec_body),
            "--spec",
            str(SPEC),
            "--head",
            HEAD,
            "--branch",
            "spec-279",
            cwd=candidate,
        ),
        encoding="utf-8",
    )
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["head"] == HEAD
    assert checkpoint["baseline"] == BASELINE
    assert checkpoint["branch"] == "spec-279"
    assert checkpoint["spec_body_hash"] == BODY_HASH
    assert checkpoint["spec_contract_hash"] == CONTRACT_HASH
    assert checkpoint["verification_hash"] == VERIFICATION_HASH
    assert int(checkpoint["receipt_id"]) == RECEIPT_ID
    assert len(checkpoint["manifest"]) == 122
    assert not checkpoint["coverage"]["unresolved"]
    assert run("git", "rev-parse", "HEAD", cwd=candidate).strip() == HEAD
    assert not run("git", "status", "--porcelain", cwd=candidate).strip()

    exit_input = {
        "head": HEAD,
        "baseline": BASELINE,
        "branch": "spec-279",
        "spec_body_hash": BODY_HASH,
        "spec_contract_hash": CONTRACT_HASH,
        "primary_reviewers": "1 fresh reviewer (fresh-github-actions-copilot-single-reviewer-three-axis-passes)",
        "targeted_challengers": 1,
        "saturation_challengers": 0,
        "reviewer_execution": "fresh primary three-axis reviewer plus one fresh independent bounded finality challenger",
        "reviewer_execution_override": "Owner explicitly authorized one second independent reviewer solely for the relationship-correction expected-version challenge/finality reconciliation; no finding acceptance or suppression was waived.",
    }
    exit_input_path = root / "exit-input.json"
    exit_input_path.write_text(json.dumps(exit_input, indent=2), encoding="utf-8")
    exit_file = root / "exit-receipt.md"
    run(
        "python",
        ".agents/skills/review-spec/scripts/review_spec_artifacts.py",
        "render-exit",
        "--input",
        str(exit_input_path),
        "--output",
        str(exit_file),
        cwd=candidate,
    )
    receipt = exit_file.read_text(encoding="utf-8")
    assert receipt.startswith("## Spec Review Exit Receipt\n")
    assert "**Status:** passed" in receipt
    assert f"**Reviewed HEAD:** {HEAD}" in receipt
    assert "**Blocking findings:** 0" in receipt
    assert "**Candidate new roots:** 0" in receipt
    assert "**Unchecked coverage cells:** 0" in receipt

    (root / "review-result.json").write_text(
        json.dumps({"exit_receipt": receipt}, indent=2), encoding="utf-8"
    )
    (root / "review-summary.json").write_text(
        json.dumps(
            {
                "blocking_findings": 0,
                "candidate_new_roots": 0,
                "unchecked_cells": 0,
                "targeted_challengers": 1,
                "saturation_challengers": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "provenance.json").write_text(
        json.dumps(
            {
                "provisional_relationship_correction_finding": "domain-finality-rejected",
                "bounded_challenge_run": 34814978740,
                "challenge_disposition": "falsifier-excluded",
                "actionable_blocker": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "standards-universe.json").write_text("[]\n", encoding="utf-8")
    (root / "architecture-universe.json").write_text(
        json.dumps({"finality_surviving_blockers": []}, indent=2), encoding="utf-8"
    )

    print("Canonical review Exit Receipt render: PASS")
    print("=== EXIT-RECEIPT-BEGIN ===")
    print(receipt, end="")
    print("=== EXIT-RECEIPT-END ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
