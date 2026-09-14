from pathlib import Path
import subprocess

BASE = "793c9e1c046d4b9a6b531b1b645c131af50a7bbb"
EXPECTED_PARENT = "2e1ed79c60f331236cfa1d5e30f1cb93aba1d499"
TARGETS = {
    ".agents/skills/README.md",
    ".agents/skills/review-spec-remediation/SKILL.md",
    ".agents/skills/review-spec/SKILL.md",
    ".agents/skills/to-tickets/SKILL.md",
    ".agents/skills/verify-ticket-closure/SKILL.md",
    "docs/process/common-sense-invariant-hardening-semantic-domain-finality-addendum.md",
}

def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: anchor count {text.count(old)} for {old[:100]!r}")
    p.write_text(text.replace(old, new, 1))

parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], text=True).strip()
if parent != EXPECTED_PARENT:
    raise RuntimeError(f"unexpected transport parent {parent}")

verify = ".agents/skills/verify-ticket-closure/SKILL.md"
replace_once(
    verify,
    "`$verify-ticket-closure` has two execution modes. The normal ticket lifecycle uses the fresh verifier leaf; direct human invocation is optional recovery/manual entry, not a required authorization gate.\n",
    "For ordinary ticket-candidate certification, `$verify-ticket-closure` has two entry modes. The Certified Closure Domain Reconciliation mode above is a separate prescribed internal-composition path and terminates after its reconciliation result; it does not enter the ordinary candidate-certification procedure below. The normal ticket lifecycle uses the fresh verifier leaf; direct human invocation is optional recovery/manual entry, not a required authorization gate.\n",
)
replace_once(
    verify,
    "## Verifier Integrity\n\nOnly the fresh dispatched verifier executes the remaining sections.\n",
    "## Verifier Integrity\n\nFor ordinary ticket-candidate certification, only the fresh dispatched verifier executes the remaining sections. Certified Closure Domain Reconciliation uses its own Reconciler Integrity contract above and stops before this ordinary certification path.\n",
)

review = ".agents/skills/review-spec/SKILL.md"
anchor = "Token/model cost is an execution constraint, never permission to omit coverage, skip required proof, weaken Domain Finality Reconciliation, bypass Attention, or relax the Exit Gate.\n"
replace_once(
    review,
    anchor,
    anchor + "\nA `$verify-ticket-closure` Certified Domain Reconciliation invoked by the finality gate is delegated semantic certification, not an additional review/challenger pass. Its fresh-verifier requirement is governed by that skill and does not authorize any extra review agents or challengers.\n",
)

readme = ".agents/skills/README.md"
replace_once(
    readme,
    "$review-spec\n    ↓ zero Blocking findings\ncreate or reuse the one conventional Spec Review issue\n",
    "$review-spec\n    ↓ zero Blocking findings and zero unresolved certification reconciliations\ncreate or reuse the one conventional Spec Review issue\n",
)

# Persistent net delta from the pre-hardening main must remain exactly the authorized six files.
changed = set(subprocess.check_output(["git", "diff", "--name-only", BASE], text=True).splitlines())
changed -= {".github/scripts/clarify_domain_reconciliation.py", ".github/workflows/clarify-domain-reconciliation.yml"}
if changed != TARGETS:
    raise RuntimeError(f"unexpected persistent delta: {sorted(changed)}")
subprocess.run(["git", "diff", "--check"], check=True)
print("reconciliation routing clarification validated")
