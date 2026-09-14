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
TICKET_305_CANDIDATE = "ffcb64795f07d1cafeeaceacb1e0fe548d66d0d3"
TICKET_305_CLOSURE_COMMENT = 5643823816


def run(*args: str, cwd: Path | None = None, input_text: str | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def section(text: str, start: str, end: str | None = None) -> str:
    begin = text.index(start)
    if end is None:
        return text[begin:]
    finish = text.index(end, begin)
    return text[begin:finish]


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    transport = workspace / "transport"
    candidate = workspace / "candidate"
    root = Path(os.environ["RUNNER_TEMP"]) / (
        f"review-spec-279-challenge-{os.environ['GITHUB_RUN_ID']}-"
        f"{os.environ['GITHUB_RUN_ATTEMPT']}"
    )
    root.mkdir(parents=True, exist_ok=False)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as handle:
        handle.write(f"REVIEW_ROOT={root}\n")

    # Re-pin the immutable review checkpoint before the independently authorized challenge.
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
    assert checkpoint["spec_body_hash"] == BODY_HASH
    assert checkpoint["spec_contract_hash"] == CONTRACT_HASH
    assert checkpoint["verification_hash"] == VERIFICATION_HASH
    assert int(checkpoint["receipt_id"]) == RECEIPT_ID
    assert len(checkpoint["manifest"]) == 122
    assert not checkpoint["coverage"]["unresolved"]

    ticket_body = run(
        "gh",
        "issue",
        "view",
        "305",
        "--repo",
        REPO,
        "--json",
        "body",
        "--jq",
        ".body",
        cwd=candidate,
    )
    closure_raw = run(
        "gh",
        "api",
        f"repos/{REPO}/issues/comments/{TICKET_305_CLOSURE_COMMENT}",
        "--jq",
        ".body",
        cwd=candidate,
    )

    app_path = candidate / "src/polaris/application/decisions/relationships.py"
    domain_path = candidate / "src/polaris/domain/decisions/relationships.py"
    tests_path = candidate / "tests/application/decisions/test_relationships.py"
    app_text = app_path.read_text(encoding="utf-8")
    domain_text = domain_path.read_text(encoding="utf-8")
    tests_text = tests_path.read_text(encoding="utf-8")

    domain_focus = section(
        domain_text,
        "def _changed_groups(",
        "def derive_relationship_applicability(",
    )
    test_store = section(
        tests_text,
        "class FakeRelationshipStore:",
        "def _actor()",
    )
    test_focus = section(
        tests_text,
        "def test_relationship_correction_preserves_original_and_can_contest_support",
        "def test_persistence_unavailable_is_distinct_and_atomic",
    )
    semantic_diff = run(
        "git",
        "diff",
        "--unified=80",
        TICKET_305_CANDIDATE,
        HEAD,
        "--",
        "src/polaris/application/decisions/relationships.py",
        "src/polaris/domain/decisions/relationships.py",
        "tests/application/decisions/test_relationships.py",
        cwd=candidate,
    )

    current_review_skill = (transport / ".agents/skills/review-spec/SKILL.md").read_text(
        encoding="utf-8"
    )
    finality_focus = section(
        current_review_skill,
        "## 9. Conditional Challenge",
        "## 13. Pending Review Remediation",
    )

    instructions = r'''You are one genuinely independent, owner-authorized bounded challenger for Polaris `$review-spec` on Spec #279. You did not participate in implementation, verification, the primary fresh review, prior remediation, or parent orchestration.

Your scope is EXACTLY ONE QUESTION: relationship-correction expected-version enforcement and Certified Semantic Domain Finality. Do not review any other Spec cell, Standards candidate, architecture surface, naming concern, test quality, or implementation area.

Do NOT seek or use the current Spec Review issue, primary reviewer output, Root Blocker history, prior review conclusions, conversation memory, or any material not embedded below. You are intentionally NOT being told the primary reviewer's conclusion. The supplied #305 certification is prior ticket-closure evidence needed only for Domain Finality reconciliation.

Exact candidate: spec-279@4baa54445e0bcd9f19bb75277a9abc84bea3008c
Verified baseline: 4daed9034891600597a47c01b6c39d5ebd9914ca
Prior #305 certified candidate: ffcb64795f07d1cafeeaceacb1e0fe548d66d0d3

BOUNDED CHALLENGE:
1. From current Spec #279 authority (especially US-33, ID-22, TD-21) and ticket #305 authority, determine the exact required expected-version behavior for privileged relationship correction.
2. Trace ONLY the current relationship-correction path from `CorrectDecisionRelationshipCommand` through `DecisionRelationshipCorrectionService.correct`, domain `apply_relationship_command`, `_changed_groups` / `_touched_decisions` / `_validate_touched_versions`, application error translation, and `_commit_relationship`.
3. Test the falsifier conceptually: the caller supplies an envelope that omits one or both expected versions for the existing source/target Decisions touched by the corrected relationship. Determine whether the operation can reach persistence commit as semantic success, or whether the canonical domain/application path rejects it first; identify the caller-visible semantic outcome.
4. Reconcile that result with #305's frozen Certified Closure Domain ND-4 (Transactional revalidation protection), the #305 certification of missing/stale correction versions, and the exact diff from #305 candidate to current HEAD. Determine whether this question is inside the frozen certified domain, whether governing authority changed, and whether relevant semantic implementation changed after certification.
5. Apply the supplied `$review-spec` Domain Finality rules. Do not broaden the frozen domain. If current evidence demonstrates a genuine regression or an in-domain falsifier, say so. If the supposed falsifier is excluded by the canonical path and unchanged certified authority/domain, say so. If proof is insufficient, fail closed as unresolved.

Do not rerun tests or verification gates. Do not mutate anything. Do not use shell, network, memory, URLs, or external tools. Use only the embedded authority/evidence.

Emit EXACTLY one JSON object and nothing else:
{
  "reviewer_execution":"fresh-github-actions-copilot-independent-bounded-challenge",
  "challenge_scope":"relationship-correction-expected-version-and-domain-finality",
  "authority":{
    "endpoint_expected_versions_required":"yes|no|ambiguous",
    "evidence":"concise authority basis"
  },
  "current_implementation":{
    "missing_endpoint_version_behavior":"rejects-before-commit|can-commit|ambiguous",
    "caller_visible_outcome":"ConcurrencyConflict|RelationshipConflict|InvalidDecisionCommand|other|ambiguous",
    "commit_reached":"yes|no|ambiguous",
    "evidence":"concise call-path evidence"
  },
  "certified_domain":{
    "membership":"in-domain|out-of-domain|ambiguous",
    "governing_authority_changed":"yes|no|ambiguous",
    "relevant_semantic_implementation_changed_since_305":"yes|no|ambiguous",
    "finality_disposition":"prior-domain-controls|prior-domain-stale|closure-authority-defect|ambiguous",
    "evidence":"concise finality evidence"
  },
  "challenge_disposition":"falsifier-excluded|finding-confirmed|unresolved",
  "actionable_blocker":"yes|no|unresolved",
  "architecture_decision_required":"Yes|No|Ambiguous",
  "explanation":"compact final explanation",
  "challenge_triggers":[]
}

A complete result must resolve every enum above and leave `challenge_triggers` empty. If the evidence cannot support that, return `unresolved`/`ambiguous` values and one precise trigger instead of guessing.
'''

    prompt_parts = [
        instructions,
        "\n=== CURRENT ROOT AGENTS POLICY ===\n",
        (transport / "AGENTS.md").read_text(encoding="utf-8"),
        "\n=== CURRENT REVIEW-SPEC CONDITIONAL CHALLENGE + FINALITY RULES ===\n",
        finality_focus,
        "\n=== SPEC #279 BODY ===\n",
        spec_body.read_text(encoding="utf-8"),
        "\n=== TICKET #305 BODY ===\n",
        ticket_body,
        "\n=== TICKET #305 CERTIFIED CLOSURE COMMENT 5643823816 ===\n",
        closure_raw,
        "\n=== CURRENT APPLICATION RELATIONSHIP COORDINATION ===\n",
        app_text,
        "\n=== CURRENT DOMAIN RELATIONSHIP COMMAND / VERSION GUARD FOCUS ===\n",
        domain_focus,
        "\n=== CURRENT TEST STORE COMMIT REVALIDATION FOCUS ===\n",
        test_store,
        "\n=== CURRENT RELATIONSHIP CORRECTION TEST FOCUS ===\n",
        test_focus,
        "\n=== EXACT RELEVANT DIFF: #305 CERTIFIED CANDIDATE -> CURRENT HEAD ===\n",
        semantic_diff or "<no relevant diff>",
    ]
    prompt = "".join(prompt_parts)

    copilot_home = root / "copilot-home"
    copilot_home.mkdir()
    env = os.environ.copy()
    env["COPILOT_HOME"] = str(copilot_home)
    result = subprocess.run(
        [
            "copilot",
            "-s",
            "--no-custom-instructions",
            "--disable-builtin-mcps",
            "--deny-tool=shell,write,url,memory",
            "--no-ask-user",
            "--no-remote",
            "--no-remote-export",
        ],
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode

    review_path = root / "review-result.json"
    review_path.write_text(result.stdout, encoding="utf-8")
    review = json.loads(result.stdout)
    assert review["reviewer_execution"] == (
        "fresh-github-actions-copilot-independent-bounded-challenge"
    )
    assert review["challenge_scope"] == (
        "relationship-correction-expected-version-and-domain-finality"
    )
    assert review["authority"]["endpoint_expected_versions_required"] in {
        "yes", "no", "ambiguous"
    }
    assert review["current_implementation"]["missing_endpoint_version_behavior"] in {
        "rejects-before-commit", "can-commit", "ambiguous"
    }
    assert review["current_implementation"]["commit_reached"] in {
        "yes", "no", "ambiguous"
    }
    assert review["certified_domain"]["membership"] in {
        "in-domain", "out-of-domain", "ambiguous"
    }
    assert review["certified_domain"]["governing_authority_changed"] in {
        "yes", "no", "ambiguous"
    }
    assert review["certified_domain"][
        "relevant_semantic_implementation_changed_since_305"
    ] in {"yes", "no", "ambiguous"}
    assert review["certified_domain"]["finality_disposition"] in {
        "prior-domain-controls",
        "prior-domain-stale",
        "closure-authority-defect",
        "ambiguous",
    }
    assert review["challenge_disposition"] in {
        "falsifier-excluded", "finding-confirmed", "unresolved"
    }
    assert review["actionable_blocker"] in {"yes", "no", "unresolved"}
    assert review["architecture_decision_required"] in {"Yes", "No", "Ambiguous"}
    if review["challenge_disposition"] != "unresolved":
        assert not review.get("challenge_triggers")

    result_summary = {
        "challenge_scope": review["challenge_scope"],
        "challenge_disposition": review["challenge_disposition"],
        "actionable_blocker": review["actionable_blocker"],
        "domain_membership": review["certified_domain"]["membership"],
        "finality_disposition": review["certified_domain"]["finality_disposition"],
    }
    (root / "review-summary.json").write_text(
        json.dumps(result_summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    # Retain the prior artifact filenames so the already-temporary workflow needs no
    # structural modification for this explicitly authorized bounded challenge.
    (root / "provenance.json").write_text(
        json.dumps({"bounded_challenge": True}, indent=2), encoding="utf-8"
    )
    (root / "standards-universe.json").write_text("[]\n", encoding="utf-8")
    (root / "architecture-universe.json").write_text(
        json.dumps({"bounded_challenge": ["ARCH-1", "ARCH-3"]}, indent=2),
        encoding="utf-8",
    )

    print("Independent bounded challenge validation: PASS")
    print(json.dumps(result_summary, sort_keys=True))
    print("=== REVIEW-RESULT-BEGIN ===")
    print(review_path.read_text(encoding="utf-8"))
    print("=== REVIEW-RESULT-END ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
