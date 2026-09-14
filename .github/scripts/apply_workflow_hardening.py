from __future__ import annotations

import subprocess
from pathlib import Path

EXPECTED_PARENT = "793c9e1c046d4b9a6b531b1b645c131af50a7bbb"
TARGETS = {
    "docs/process/common-sense-invariant-hardening-semantic-domain-finality-addendum.md",
    ".agents/skills/verify-ticket-closure/SKILL.md",
    ".agents/skills/review-spec/SKILL.md",
    ".agents/skills/review-spec-remediation/SKILL.md",
    ".agents/skills/to-tickets/SKILL.md",
    ".agents/skills/README.md",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected anchor exactly once, found {count}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1))


def insert_before(path: str, anchor: str, insertion: str) -> None:
    replace_once(path, anchor, insertion + anchor)


parent = run("git", "rev-parse", "HEAD^")
if parent != EXPECTED_PARENT:
    raise RuntimeError(f"unexpected staging parent: {parent} != {EXPECTED_PARENT}")

# 1. Complete Certified Semantic Domain Finality with a real reconciliation transition.
finality = "docs/process/common-sense-invariant-hardening-semantic-domain-finality-addendum.md"
replace_once(
    finality,
    """This is a semantic-certification integrity failure. It does not silently become current implementation remediation. Halt the affected lifecycle boundary and require explicit authority/domain reconciliation. Preserve the implementation observation, but do not authorize `$to-tickets` from it until the authoritative domain conflict is resolved.\n\nA broader plausible reading, lexical sibling, thematic similarity, implementation adjacency, or reviewer preference is **not** an explicit authority contradiction.\n""",
    """This is a semantic-certification integrity failure. It does not silently become current implementation remediation. Halt only the affected certified domain/cell and route it to the semantic completion owner that created that domain for **Certified Closure Domain Reconciliation**. For ticket/root domains created by `$verify-ticket-closure`, that skill owns the reconciliation. Preserve the implementation observation while reconciliation runs, but do not authorize `$to-tickets` from that observation until reconciliation makes it actionable. Unrelated finality-surviving remediation remains actionable and must not be globally held.\n\nA broader plausible reading, lexical sibling, thematic similarity, implementation adjacency, or reviewer preference is **not** an explicit authority contradiction.\n""",
)
insert_before(
    finality,
    "## Root and Review Convergence\n",
    """## Certified Closure Domain Reconciliation\n\nA `closure-authority-defect` is a transitional certification-integrity state, not a terminal lifecycle dead end and not a new public workflow stage.\n\nThe domain's semantic completion owner independently reconciles the exact prior certification against the exact unchanged authority it claimed to represent. The reconciliation has exactly three terminal results:\n\n```text\ndefect-confirmed\ndefect-rejected\nreconciliation-unresolved\n```\n\n### `defect-confirmed`\n\nThe prior membership predicate/source set is explicitly contradicted by its own unchanged authority. Reconstruct the **complete affected domain** authority-first from that same authority; do not merely append the candidate that exposed the defect. Persist a superseding membership record that preserves the historical PASS as historical truth while marking the defective prior membership boundary as no longer finality authority. A later/current review then reruns Domain Finality Reconciliation against the superseding domain. If the implementation observation is in-domain under the corrected boundary, it may become ordinary Blocking remediation.\n\n### `defect-rejected`\n\nThe claimed contradiction is not explicit authority evidence sufficient to invalidate the frozen boundary. The prior Certified Closure Domain remains finality authority and the observation is handled as `domain-expansion` unless another ordinary finality disposition applies.\n\n### `reconciliation-unresolved`\n\nThe authority/certification relationship cannot be resolved without guesswork. Hold only the affected certified domain/cell. Unrelated current Blocking remediation may continue, but review PASS remains illegal while any required reconciliation is unresolved.\n\nReconciliation must be independently certified under the same no-self-certification principle as the original semantic completion transition. It may supersede membership authority; it does not rewrite historical evidence, retroactively recertify the historical implementation candidate, or create implementation work by itself.\n\n""",
)

# 2. Let the ticket semantic-closure owner repair a defective domain and prevent recurrence.
verify_ticket = ".agents/skills/verify-ticket-closure/SKILL.md"
insert_before(
    verify_ticket,
    "## Invocation Semantics\n",
    """## Certified Closure Domain Reconciliation Mode\n\n`$verify-ticket-closure` also owns bounded reconciliation of a Certified Closure Domain that this skill previously created when `$review-spec` has established a provisional `closure-authority-defect`. This is **membership-authority reconciliation**, not re-verification of the historical ticket candidate.\n\n### Invocation and inputs\n\nThis mode is prescribed internal composition from `$review-spec`. The review parent supplies only durable retrieval coordinates:\n\n* originating ticket and parent Spec;\n* exact historical closure checkpoint/verdict;\n* affected Certified Closure Domain ID(s);\n* recorded prior authority identity;\n* current identity of the same authority;\n* exact explicit contradiction source(s);\n* the review observation that exposed the contradiction.\n\nThe fresh reconciler independently rereads the prior domain record and exact authority. The observation is a falsifier candidate, not authority and not the definition of the corrected domain.\n\n### Reconciler integrity\n\nUse one genuinely fresh, non-mutating, non-delegating semantic verifier. It must not have implemented the historical candidate or participated in the current review finding. It may not repair code, rewrite the ticket, mutate tracker state, or recertify historical member correctness.\n\nWhen the active host cannot create a separate verifier and repository owner authorization explicitly supplies an equivalent in-session substitute under the repository session-reconstitution contract, preserve every other integrity requirement and identify the result as that substitute.\n\n### Reconciliation procedure\n\n1. Validate the exact historical domain record, authority identity, and current unchanged/changed authority identity.\n2. Decide whether the cited contradiction is explicit and mechanically identifiable in the same authority the prior domain claimed to cover. A broader plausible interpretation or adjacent sibling is insufficient.\n3. If the contradiction is confirmed, reconstruct the **entire affected membership universe authority-first** using the same Domain Construction Manifest rules in this skill. Do not seed or bound reconstruction from the reviewer's discovered candidate.\n4. Close every nested finite/discoverable domain required to establish the corrected membership boundary.\n5. Return one terminal result below.\n\n### Terminal results\n\nConfirmed:\n\n```text\nDOMAIN RECONCILIATION: DEFECT CONFIRMED\nOriginating ticket: <#n>\nPrior certification: <durable reference>\nPrior domain: <ND/root ID>\nAuthority identity: <exact identity>\nExplicit contradiction: <exact source>\nCorrected membership predicate: <predicate>\nCorrected dimensions/source sets: <sets>\nExpected/generated/inspected/dispositioned: <counts or open-world criterion>\nPrior membership finality superseded: yes\nHistorical PASS preserved: yes\n```\n\nRejected:\n\n```text\nDOMAIN RECONCILIATION: DEFECT REJECTED\nOriginating ticket: <#n>\nPrior certification: <durable reference>\nPrior domain: <ND/root ID>\nAuthority identity: <exact identity>\nReason: <why the claimed contradiction does not invalidate the frozen predicate/source set>\nPrior membership finality superseded: no\n```\n\nUnresolved:\n\n```text\nDOMAIN RECONCILIATION: UNRESOLVED\nOriginating ticket: <#n>\nPrior certification: <durable reference>\nPrior domain: <ND/root ID>\nUnresolved state: <missing/ambiguous/contradictory authority or certification evidence>\n```\n\nThe reconciler returns the terminal record to `$review-spec`. The review parent persists a confirmed/rejected result durably on the originating ticket as one `<!-- certified-domain-reconciliation:v1 -->` record, verifies exact readback, and then reruns only the affected Domain Finality Reconciliation. `UNRESOLVED` is preserved on the Spec Review state and holds only the affected domain/cell.\n\n""",
)
insert_before(
    verify_ticket,
    "## 2. Build the Authoritative Acceptance Universe\n",
    """### Authority Source Coverage Manifest\n\nBefore acceptance-cell construction, close the bounded **authority-source universe** that materially defines this ticket's promised slice. This prevents a verifier from proving every obligation it noticed while silently omitting an explicit requirement from an architecture/design source the ticket claims to consume.\n\nStart from:\n\n* the ticket's normative body and acceptance/verification/preservation obligations;\n* the carried parent-Spec clauses identified by `Spec obligations`;\n* the exact architecture/design sections required to interpret the ticket's promised slice, including sources named by the ticket/Spec as governing that slice.\n\nDo not ingest unrelated sections merely because a large design document is referenced. Broaden only when a bounded section depends on another source or cannot be interpreted completely in isolation.\n\nClassify every materially normative source unit in that bounded authority-source set:\n\n```text\nAuthority unit: AUTH-<n>\nSource: <durable source + section/anchor>\nRequirement: <compact normative obligation>\nDisposition: current-ticket | preservation | verification-only | deferred-existing-owner | not-applicable\nDestination: <AC/ND ID | durable other ticket/Spec/owner | None>\nReason/authority: <required for every non-current-ticket disposition>\n```\n\nRules:\n\n* `current-ticket` obligations must enter the acceptance universe;\n* `preservation` obligations must enter the preservation proof universe;\n* `verification-only` obligations must have an explicit proof destination in this verifier;\n* `deferred-existing-owner` requires durable authority naming the other owner; do not invent a future destination to make the manifest close;\n* `not-applicable` requires exact authority/reason;\n* a broad statement that the ticket "consumes" a design source does not permit cherry-picking only the clauses already reflected in implementation/tests;\n* implementation shape, existing tests, Proposed Closure Evidence, and known findings may help locate evidence but may not define which authority units exist.\n\nBefore continuing require:\n\n```text\nBounded authority sources: <n>\nMaterial normative authority units: <n>\nAuthority disposition rows: <n>\nUnmapped authority units: 0\nAmbiguous authority units: 0\nCurrent-ticket authority units absent from acceptance cells: 0\nDeferred units without durable existing owner: 0\n```\n\nAny non-zero value leaves the affected ticket acceptance universe unproven and prohibits PASS.\n\n""",
)

# 3. Resolve domain defects in review, localize holds, and reduce review cost/noise.
review = ".agents/skills/review-spec/SKILL.md"
insert_before(
    review,
    "## Reviewer Execution Budget\n",
    """### Certification Integrity Projection\n\nWhen Domain Finality Reconciliation detects or resolves certification-integrity state, add a compact supplemental section **after** the three review axes:\n\n```markdown\n## Certification Integrity\n- <domain/reconciliation result or unresolved affected cell>\n```\n\nThis section is supplemental process state, not a fourth review axis. A provisional `closure-authority-defect` is not presented as an active axis `Blocking` finding until reconciliation makes the underlying implementation observation actionable. If reconciliation is confirmed and the observation becomes an `in-domain-falsifier`, return the actionable finding to its original Standards/Spec/Architecture axis and preserve the reconciliation summary here.\n\n""",
)
insert_before(
    review,
    "## Preserve the Adversarial Boundary\n",
    """## Review Execution Efficiency\n\nCorrectness coverage is mandatory; repeated retrieval and transcript volume are not. Use the following execution discipline for every review:\n\n1. **Build one Review Context Index before reviewer dispatch.** Record the exact verified receipt/HEAD, Spec Contract identity, change-provenance artifact, Architecture Impact/source identities, current Spec Review issue, known machine-managed comment IDs/markers, Ticket Coverage Manifest, and prior Review Proof Reuse Ledger when present. Reuse this index while those identities remain unchanged.\n2. **Retrieve by durable coordinate first.** Prefer exact issue/comment IDs, markers, source sections, hashes, and domain IDs. Do not fetch/search complete historical issue sets or comment histories when the required provenance is already directly addressable. Broaden only to resolve a material ambiguity or completeness question.\n3. **Reduce mechanically before semantic inspection.** Use deterministic filtering/counting/hashing/grouping for large JSON, manifests, comments, and proof ledgers. Give the reviewer the compact authoritative rows plus exact drill-down coordinates; expand raw payloads only when the compact form cannot settle the claim.\n4. **Do not dump scratch construction artifacts into the human transcript.** Raw proof-group JSON, long source inventories, and machine manifests remain working state unless the user requests them or a durable workflow record requires them. Present compact counts/findings and persist only the canonical required artifact.\n5. **Freeze findings once per axis.** After an axis freezes, upstream-certification provenance and Domain Finality work are bounded to those frozen findings. Do not re-search unrelated historical tickets/issues merely to look for more provenance.\n6. **Reuse factual evidence across axes, never semantic conclusions.** The one reviewer may reuse an exact file excerpt, hash, test result, or authority source already loaded; it must still make each axis's disposition independently.\n7. **No automatic retry/challenger churn.** A failed deterministic query is corrected against the actual schema; it does not justify spraying alternate broad searches. The existing reviewer performs the one bounded finality self-challenge when required. Additional semantic reviewers/challengers still require explicit human authorization.\n8. **Use certified review-proof reuse on re-review.** Re-evaluate only stale/invalidated proof groups plus active remediation/finality cells. Do not rerun clean groups whose certifier-approved invalidation boundaries remain untouched.\n9. **Avoid status-noise polling.** Waiting for the single reviewer or deterministic operation must not create repeated "no result yet" transcript entries or duplicate semantic work.\n\nEfficiency never permits incomplete universe construction, omitted falsifiers, weakened finality reconciliation, or skipped Attention.\n\n""",
)
replace_once(
    review,
    "* rerun `$verify-ticket-closure` or `$verify-spec-closure` merely to confirm a review finding;\n",
    "* rerun ordinary `$verify-ticket-closure` or `$verify-spec-closure` merely to confirm a review finding; Certified Closure Domain Reconciliation mode is the sole exception and reconciles membership authority rather than recertifying the historical candidate;\n",
)
replace_once(
    review,
    """#### `closure-authority-defect`\n\nUnchanged durable authority contains an **exact explicit contradiction** to the certified membership predicate/source set, such as an authoritative enumerated member omitted from a certification that claimed that exact enumeration.\n\nThis is process-integrity evidence about semantic certification. Do not convert it silently into current implementation remediation. Halt the affected root/cell behind explicit authority/domain reconciliation; preserve the implementation observation separately.\n\nA broader plausible reading, thematic similarity, sibling implementation mechanism, lexical adjacency, or reviewer preference is not an explicit authority contradiction.\n""",
    """#### `closure-authority-defect`\n\nUnchanged durable authority contains an **exact explicit contradiction** to the certified membership predicate/source set, such as an authoritative enumerated member omitted from a certification that claimed that exact enumeration.\n\nThis is process-integrity evidence about semantic certification. Do not convert it silently into implementation remediation and do not globally hold unrelated current findings. Hold only the affected domain/cell while performing **Certified Closure Domain Reconciliation** through the semantic completion owner that created the domain. For ticket/root domains created by `$verify-ticket-closure`, invoke that skill internally in its Certified Closure Domain Reconciliation mode.\n\nConsume the result immediately in the same review lifecycle:\n\n* `DOMAIN RECONCILIATION: DEFECT CONFIRMED` — persist/read back the superseding membership record on the originating ticket, then rerun Domain Finality Reconciliation only for the affected observation against that corrected domain. If it is now in-domain, it becomes an ordinary `in-domain-falsifier` and may return to its originating review axis as Blocking.\n* `DOMAIN RECONCILIATION: DEFECT REJECTED` — keep the prior domain as finality authority and disposition the observation as `domain-expansion` unless another ordinary finality disposition applies.\n* `DOMAIN RECONCILIATION: UNRESOLVED` — preserve an unresolved certification-integrity hold for only the affected domain/cell. It does not suppress unrelated actionable findings, but it prevents Review PASS.\n\nA broader plausible reading, thematic similarity, sibling implementation mechanism, lexical adjacency, or reviewer preference is not an explicit authority contradiction. Reconciliation must rebuild the complete affected domain authority-first when a defect is confirmed; it may not merely append the candidate that exposed the defect.\n""",
)
replace_once(
    review,
    """### Pending/aggregate state\n\nOnly findings that survive Domain Finality Reconciliation count as current Blocking findings, Root Blocker reopenings, convergence triggers, or `$to-tickets` inputs.\n\nPersist non-actionable domain-expansion/process-integrity observations in the Pending packet's provenance/scope/finality section so history is not erased.\n""",
    """### Pending/aggregate state\n\nTrack these independently:\n\n```text\nACTIVE_BLOCKING_FINDINGS: <n>\nUNRESOLVED_CERTIFICATION_RECONCILIATIONS: <n>\n```\n\nOnly findings that survive Domain Finality Reconciliation count as current Blocking findings, Root Blocker reopenings, convergence triggers, or `$to-tickets` inputs. An unresolved certification reconciliation holds only its affected domain/cell and does not prevent unrelated `ACTIVE_BLOCKING_FINDINGS` from entering normal remediation.\n\nReview PASS/Exit Receipt requires both counts to be zero. Persist non-actionable domain-expansion/process-integrity observations and any unresolved reconciliation in the Pending packet's provenance/scope/finality section so history is not erased.\n""",
)

# 4. Make remediation consume local holds without suppressing independent actionable blockers.
remediation = ".agents/skills/review-spec-remediation/SKILL.md"
replace_once(
    remediation,
    "* `closure-authority-defect` — **not** implementation remediation. Preserve the observation and halt the affected root/cell behind explicit authority/domain reconciliation; do not pass it to `$to-tickets`;\n",
    "* `closure-authority-defect` — **not** implementation remediation while unresolved. Preserve the observation and hold only the affected root/cell. `$review-spec` owns invoking the certified-domain reconciliation transition and must supply any confirmed/rejected result before this skill can treat that observation differently; do not pass an unresolved defect to `$to-tickets`;\n",
)
insert_before(
    remediation,
    "### Domain-excluded acceptance state\n",
    """### Reconciliation locality\n\nA certification-integrity hold is local to the affected certified domain/cell. It must never suppress unrelated finality-surviving Blocking findings.\n\n`$review-spec` may supply durable reconciliation provenance showing that a prior `closure-authority-defect` was confirmed and the affected domain superseded. By the time such an observation enters this skill as actionable remediation, `$review-spec` must already have rerun Domain Finality Reconciliation and classified it through an ordinary actionable disposition such as `in-domain-falsifier`. This skill does not reinterpret or rebuild certified domains itself.\n\nTrack unresolved reconciliation state separately from active remediation:\n\n```text\nUnresolved certification reconciliations: <n>\nActive architecture-conforming Blocking findings: <n>\n```\n\n""",
)
replace_once(
    remediation,
    "* closure-authority-defect/domain-expansion observations awaiting or excluded from current implementation remediation.\n",
    "* unresolved `closure-authority-defect` observations and `domain-expansion` observations excluded from current implementation remediation.\n",
)
insert_before(
    remediation,
    "If active architecture-conforming remediation remains, halt using:\n",
    """Unresolved certification reconciliations do not change this count and do not block a `$to-tickets` handoff for unrelated active remediation. Include their count as supplemental state so they cannot disappear.\n\nIf no active architecture-conforming remediation remains but one or more certification reconciliations are unresolved, return control to `$review-spec` with those affected domain/cell identities. Do not emit `$to-tickets`, do not mark the review clean, and do not manufacture an implementation root from the unresolved process-integrity state.\n\n""",
)

# 5. Prevent decomposition from silently dropping architecture/design obligations outside Spec cells.
to_tickets = ".agents/skills/to-tickets/SKILL.md"
replace_once(
    to_tickets,
    "Source obligations/root cells complete: yes\nProposal coverage complete: yes\n",
    "Source obligations/root cells complete: yes\nArchitecture/design obligation coverage complete: yes\nArchitecture/design obligations missing or ambiguous: 0\nProposal coverage complete: yes\n",
)
replace_once(
    to_tickets,
    "* the Spec Obligation Disposition Manifest;\n* the proposed ticket `Spec obligations` mappings;\n",
    "* the Spec Obligation Disposition Manifest;\n* the Architecture/Design Obligation Disposition Manifest when the Spec/tickets consume governing architecture/design sources;\n* the proposed ticket `Spec obligations` mappings;\n",
)
insert_before(
    to_tickets,
    "## Ticket Provenance\n",
    """## Architecture / Design Obligation Coverage\n\nSpec cells remain the primary decomposition universe, but they are not permission to drop an explicit architecture/design obligation that materially constrains the implementation slice and is not represented by its own Spec cell. For a fresh Spec proposal, close this second bounded source universe before proposal certification.\n\n### Build the bounded source set\n\nStart from architecture/design authority explicitly named by the Spec's Architecture Impact/readiness state and by the proposed tickets' Architecture context. Reduce to the exact sections/anchors materially required to implement those ticket slices; do not sweep unrelated architecture documents merely because they are linked somewhere in the repository.\n\nClassify every materially normative obligation in that bounded source set that is not already completely represented by a Spec Contract cell:\n\n```text\nArchitecture obligation: ARCHSRC-<n>\nSource: <durable path/ADR/doc + section/anchor>\nRequirement: <compact normative obligation>\nDisposition: implementation-ticket | verification-only | deferred-existing-owner | not-applicable\nTickets/destination: <ticket(s) | durable existing owner | None>\nReason/authority: <required for non-ticket dispositions>\n```\n\nRules:\n\n* `implementation-ticket` obligations must be explicit in the mapped ticket's build/acceptance/preservation contract; a broad `Architecture context` citation is not sufficient coverage;\n* `verification-only` requires an explicit later proof owner;\n* `deferred-existing-owner` requires a durable existing ticket/Spec/lifecycle owner already established by authority; `$to-tickets` may not invent one to close the table;\n* `not-applicable` requires exact source/scope authority;\n* when one obligation is already fully represented by a Spec cell, record the Spec-cell reference instead of duplicating implementation responsibility;\n* implementation shape, existing tests, and proposed ticket wording do not define the architecture-obligation universe.\n\nBefore proposal-readiness certification require:\n\n```text\nBounded architecture/design sources: <n>\nMaterial non-duplicated architecture obligations: <n>\nArchitecture disposition rows: <n>\nUnmapped architecture obligations: 0\nAmbiguous architecture obligations: 0\nImplementation architecture obligations without ticket coverage: 0\nDeferred obligations without durable existing owner: 0\n```\n\nCall this the **Architecture/Design Obligation Disposition Manifest**. The fresh proposal certifier independently validates its source-unit completeness from the bounded authority sources; the drafting parent may not self-certify that every relevant architecture clause was noticed.\n\nExtend the parent `## Ticket Coverage Manifest` with a compact `Architecture / Design Obligation Coverage` subsection containing each `ARCHSRC-*` source anchor, disposition, and ticket/destination. These rows are decomposition provenance, not new Spec Contract cells and not architecture decisions.\n\n""",
)
replace_once(
    to_tickets,
    "* Spec Obligation Disposition Manifest is complete when applicable;\n* every ticket's `Spec obligations` set equals its approved mapping when applicable;\n",
    "* Spec Obligation Disposition Manifest is complete when applicable;\n* Architecture/Design Obligation Disposition Manifest is complete when applicable, with missing/ambiguous obligations 0;\n* every ticket's `Spec obligations` set equals its approved mapping when applicable;\n",
)

# 6. Document the internal reconciliation edge in cross-skill lifecycle authority.
readme = ".agents/skills/README.md"
replace_once(
    readme,
    """$review-spec\n    ├─ zero Blocking findings\n    │      ├─ create or reuse the one conventional Spec Review issue\n    │      ├─ persist Spec Review Exit Receipt on that review issue\n    │      └─ HUMAN → $spec-merge-cleanup\n    │\n    ├─ Blocking findings; no new architecture decision required\n""",
    """$review-spec\n    ├─ zero Blocking findings and zero unresolved certification reconciliations\n    │      ├─ create or reuse the one conventional Spec Review issue\n    │      ├─ persist Spec Review Exit Receipt on that review issue\n    │      └─ HUMAN → $spec-merge-cleanup\n    │\n    ├─ closure-authority defect against a ticket/root Certified Closure Domain\n    │      ├─ internal → $verify-ticket-closure [Certified Domain Reconciliation mode]\n    │      ├─ confirmed → supersede membership boundary; re-run affected finality disposition\n    │      ├─ rejected → domain-expansion/non-actionable unless another disposition applies\n    │      └─ unresolved → hold affected domain/cell only; unrelated remediation may proceed\n    │\n    ├─ Blocking findings; no new architecture decision required\n""",
)
insert_before(
    readme,
    "When architecture-conforming Blocking findings remain:\n",
    """When review discovers an explicit contradiction between an unchanged authority and a ticket/root Certified Closure Domain, `$review-spec` invokes `$verify-ticket-closure` internally in **Certified Domain Reconciliation mode**. This is not a new public lifecycle stage and does not recertify the historical candidate. A confirmed reconciliation rebuilds and durably supersedes only the defective membership boundary, after which the affected review observation is re-dispositioned normally. A rejected contradiction remains governed by the prior boundary. An unresolved reconciliation holds only its affected domain/cell and prevents Review PASS, but it does not globally suppress unrelated active remediation.\n\n""",
)

# Validate intended semantic markers and exact persistent delta.
checks = {
    finality: ["## Certified Closure Domain Reconciliation", "defect-confirmed", "reconciliation-unresolved"],
    verify_ticket: ["## Certified Closure Domain Reconciliation Mode", "### Authority Source Coverage Manifest", "DOMAIN RECONCILIATION: DEFECT CONFIRMED"],
    review: ["## Review Execution Efficiency", "### Certification Integrity Projection", "UNRESOLVED_CERTIFICATION_RECONCILIATIONS"],
    remediation: ["### Reconciliation locality", "Unresolved certification reconciliations"],
    to_tickets: ["## Architecture / Design Obligation Coverage", "Architecture/Design Obligation Disposition Manifest"],
    readme: ["Certified Domain Reconciliation mode", "hold affected domain/cell only"],
}
for path, markers in checks.items():
    text = Path(path).read_text()
    for marker in markers:
        if marker not in text:
            raise RuntimeError(f"{path}: missing validation marker {marker!r}")

# The old dead-end wording must be gone from executable remediation/review authority.
for path in (review, remediation):
    text = Path(path).read_text()
    if "halt the affected root/cell behind explicit authority/domain reconciliation" in text:
        raise RuntimeError(f"{path}: stale dead-end wording remains")

# Net delta from the pre-transport main commit must be exactly the authorized six files.
changed = set(run("git", "diff", "--name-only", EXPECTED_PARENT).splitlines())
if changed != TARGETS:
    raise RuntimeError(f"unexpected net changed paths: {sorted(changed)}")

subprocess.run(["git", "diff", "--check", EXPECTED_PARENT], check=True)
print("workflow hardening patch validated")
