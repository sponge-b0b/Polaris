from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

REPO = "sponge-b0b/Polaris"
PROPOSAL_ID = "2610b4536a686b5ca44676a00fbe3a45c2c293e551945b82d329f512906f7f43"

EXPECTED_OLD = {
    357: "6ebec27e7fcb883accf1b414496e3786ba159efeaa44f041853cce09555b4fae",
    358: "3843558849fee416f08cdef3e80cd6e3589ace78397283957cdbcaa2d8f0e8e9",
    359: "84dce8a425b62e0d01df084ba91b641485a592fe6e68cce952aa685b50e110b7",
    360: "a360741008c865f8e9d61cdd58003c6377bf763c633267584e34737932944bfb",
    361: "0b2f2b9542c5dfbbee27d75464c50b3ea085c4e0f380f10e18da5ba923d9a682",
    362: "2e918d50c8d5c40c5e0f86dad6d64a8fa5a78f59300e05773f120eef3ea8af76",
    363: "17d54ee8e3230f0c27a57b828d0b344d04412f1b2a2fed695ca816150e26e065",
}
EXPECTED_NEW = {
    357: "275d831d1fe185eaabac34e9d4c6224cf98d28285e64ce03ce16f6c07668c61f",
    358: "b1fe322c16183000f881c14fff39f57751a5c175c2f88d2ee67460381dc02aaf",
    359: "5fe3e54fdcc1bd0a0b85c63c10457a34b6b186338224902993ee842e5ca8c8bc",
    360: "161ec42c53f5469dc058df97d4a652e88ad10348c7c1acfbde062b71149b6a0d",
    361: "4155a9388b8af350636a067ed8d4ac9346caf3e388375a552788ccb30bf39373",
    362: "48507550ca71154cf089590bb429e483033677a977b86d6c1206f3c008d9218a",
    363: "9a23ba04fe44072f9418d7f2c9bdcdb9e7cfb80e53b92b11f9ab5da83d12774f",
}
STATE = {
    349: "886d75d881bbc9cd9e50199c0a1d1a5589e0005a588075e082f6f3754aad6f43",
    350: "cc9bf6fe0ab92567151c5902ef13d86d2d14d14e16345f70e436f13369ca08e2",
    351: "afc8ec792ce6a58c8e50a084fc6c0ee055e0b219251672ae97def045e88a58ee",
    352: "bfd28538a4d01614b4600fd7dfc6740a38e1557543e6c92eb0ca58c1a6435b47",
    353: "a73efe6262d22a19937bb5d569cc08ae67bc8e46f2b98c4c9dd140d871c80ab6",
    354: "bae9bc09959b4367db09271671a4e11ed2a27e6ae34963eaaf337f5cc133ae8c",
    355: "a1689260a0871a67589b143806e452692ad611459d212dd3812c51667d9d44c9",
    356: "910cd0f17ce6ccbafe9ba1a2db6f60cc7377c1fad8667171881a9adde46a71c0",
    364: "ea08c94ae4512a0ec780a8b3ba7101fef5fc351ff64c62d61bf17c70f37a530c",
}
SPEC_DECISIONS = {
    357: [349, 350, 355, 356, 364],
    358: [349, 350, 351, 355, 356, 364],
    359: [349, 352, 355, 356, 364],
    360: [349, 353, 355, 356, 364],
    361: [349, 354, 355, 356, 364],
    362: [349, 350, 351, 352, 353, 354, 355, 356, 364],
    363: [349, 350, 351, 352, 353, 354, 355, 356, 364],
}

def run(args: list[str], input_text: str | None = None) -> str:
    cp = subprocess.run(args, input=input_text, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode:
        print(cp.stdout, file=sys.stderr, end="")
        print(cp.stderr, file=sys.stderr, end="")
        raise SystemExit(f"command failed: {' '.join(args)}")
    return cp.stdout

def digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def replace_one(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected anchor once, found {count}")
    return s.replace(old, new, 1)

def add_marker(body: str, n: int) -> str:
    first = body.split("\n", 1)[0]
    if "wayfinder-decision-states:v1" in body:
        raise SystemExit(f"#{n}: state marker already present in old body")
    states = ",".join(f"#{d}:{STATE[d]}" for d in SPEC_DECISIONS[n])
    return first + "\n" + f"<!-- wayfinder-decision-states:v1 map=#348; states={states} -->" + body[len(first):]

def common(body: str, n: int) -> str:
    body = add_marker(body, n)
    body = body.replace("ADRs 0001–0013", "ADRs 0001–0014")
    body = body.replace("ADRs 0006–0013", "ADRs 0006–0014")
    body = body.replace("ADRs 0012–0013", "ADRs 0012–0014")
    body = body.replace("ADR 0012–0013", "ADR 0012–0014")
    mapping = {
        357: ("ADRs 0006, 0011, 0012, and 0013", "ADRs 0006, 0011, 0012, 0013, and 0014"),
        358: ("ADRs 0007, 0011, 0012, and 0013", "ADRs 0007, 0011, 0012, 0013, and 0014"),
        359: ("ADRs 0008, 0011, 0012, and 0013", "ADRs 0008, 0011, 0012, 0013, and 0014"),
        360: ("ADRs 0009, 0011, 0012, and 0013", "ADRs 0009, 0011, 0012, 0013, and 0014"),
        361: ("ADRs 0010, 0011, 0012, and 0013", "ADRs 0010, 0011, 0012, 0013, and 0014"),
    }
    if n in mapping:
        body = body.replace(*mapping[n])
    return body

def transform(n: int, body: str) -> str:
    body = common(body, n)
    if n == 357:
        pairs = [
            (
                "12. As a reviewer, I want each sufficiency assessment to preserve every applicable material requirement disposition, so that missing support is never fabricated as Evidence.",
                "12. As a reviewer, I want each sufficiency assessment to preserve one Evidence-derived disposition for every present sufficiency requirement, while freshness remains a binding-fitness evaluation and authoritative negative applicability/zero-definition witnesses remain distinct, so that missing support is never fabricated as Evidence.",
                "u12",
            ),
            (
                "Implement ADRs 0006, 0012, and 0013 as direct domain-owned business truth plus one application-facing Evidence reconstruction boundary. Persist the four accepted Evidence fact families and their correction lineages, bind them only to the closed typed judgment union and authoritative target-owned claim catalogs, resolve immutable Configuration-owned requirement versions, and expose historical and current-support queries with exact temporal, version, and negative-predicate semantics. Extend the greenfield PostgreSQL lineage behind inward-owned contracts while preserving external factual authority and atomic cross-owner revalidation.",
                "Implement ADRs 0006 and 0012–0014 as direct domain-owned business truth plus one application-facing Evidence reconstruction boundary. Persist the four accepted Evidence fact families and their correction lineages, bind them only to the closed typed judgment union and authoritative target-owned claim catalogs, resolve immutable Configuration-owned requirement versions, and derive sufficiency from the closed Evidence-owned `MinimumEligibleEvidence` predicate over the complete interpreted binding universe. Preserve exact contributor/deficiency proof and authoritative negative-applicability witnesses while exposing historical and current-support queries with exact temporal, version, and negative-predicate semantics. Extend the greenfield PostgreSQL lineage behind inward-owned contracts while preserving external factual authority and atomic cross-owner revalidation.",
                "solution",
            ),
            (
                "- **Affected architecture obligations:** durable Evidence identity and correction; typed target/scope/role/use; target-owned claim catalogs; immutable requirement authority/history; historical reconstruction; exact current-support basis and atomic revalidation.",
                "- **Affected architecture obligations:** durable Evidence identity and correction; typed target/scope/role/use; target-owned claim catalogs; immutable requirement authority/history; executable Evidence-owned sufficiency predicates; derived disposition/proof semantics and exact negative witnesses; historical reconstruction; exact current-support basis and atomic revalidation.",
                "obligations",
            ),
            (
                "9. Implement Configuration-owned `EvidenceRequirementSetId`, immutable `EvidenceRequirementSetVersionId`, and dependent `EvidenceRequirementId` with typed applicability and attributable source/effective/recorded boundaries.",
                "9. Implement Configuration-owned `EvidenceRequirementSetId`, immutable `EvidenceRequirementSetVersionId`, and dependent `EvidenceRequirementId` with typed applicability and attributable source/effective/recorded boundaries. Each sufficiency definition carries the closed Evidence-owned `MinimumEligibleEvidence(minimum_distinct_observations, qualifying_roles)` predicate plus explicit `REQUIRED | NOT_APPLICABLE` state; requirement identity continuity compares the typed predicate, not narrative prose.",
                "impl9",
            ),
            (
                "12. Persist sufficiency assessments with exact set version, contributing bindings, and one accepted disposition for every applicable material requirement. A changed requirement version creates a new assessment root.",
                "12. Derive sufficiency assessments rather than accepting caller-authored dispositions or authoritative support subsets. At exact `(T,K)`, load the complete interpreted binding universe for target/scope/use/applicability; count distinct eligible `EvidenceObservationId` values; preserve positive contributors separately from unavailable/unknown/stale/indeterminate/contested deficiency witnesses; and entail `SATISFIED | MISSING | UNAVAILABLE | STALE | UNKNOWN | DISPUTED | CONTESTED | NOT_APPLICABLE` under ADR 0014 precedence. `NOT_APPLICABLE` requires the exact Configuration witness, while a complete zero-sufficiency-definition version requires the distinct version-level no-requirement witness. Persist the exact predicate/version, counted observations, contributor/fact support, deficiency reasons, freshness/no-freshness basis, negative witnesses, support version, and relied-upon absence guards. A changed requirement version creates a new assessment root, and trusted commit-time revalidation covers the complete requirement/binding/correction/support/negative-predicate basis before append.",
                "impl12",
            ),
            (
                "4. Requirement tests for typed applicability, complete immutable versions, correction/supersession ancestry, exactly-one resolution, unchanged versus changed requirement identity, and explicit negative applicability.",
                "4. Requirement tests for typed applicability, complete immutable versions, correction/supersession ancestry, exactly-one resolution, typed `MinimumEligibleEvidence` identity continuity, `REQUIRED | NOT_APPLICABLE`, per-requirement negative witnesses, and the distinct complete-zero-sufficiency-definition witness.",
                "test4",
            ),
            (
                "5. Freshness/sufficiency tests for every accepted result/disposition and for missing, unavailable, contested, or invalid requirement authority.",
                "5. Freshness/sufficiency tests for every accepted result/disposition; zero-support and wrong-role cases; unavailable, unknown, stale, indeterminate-freshness, disputed, and contested deficiency bounds; duplicate bindings over one observation; rejection of caller-selected subsets or fabricated `SATISFIED`; exact `NOT_APPLICABLE`/zero-definition witnesses; and missing, unavailable, contested, incomplete, or invalid requirement authority.",
                "test5",
            ),
            (
                "- Decision #364 and ADRs 0012–0014 resolve the architecture blocker previously recorded on this Spec; that historical comment remains audit evidence rather than current blocking state.",
                "- Decision #364 and ADRs 0012–0014 resolve the Evidence architecture required by this Spec. ADR 0014 supersedes the pre-remediation free-text/caller-authored sufficiency seam while preserving the accepted identity, binding, correction, claim, requirement-history, reconstruction, and current-basis contracts from ADRs 0012–0013; historical blocker/verifier comments remain audit evidence rather than current authority.",
                "note",
            ),
        ]
        for old, new, label in pairs:
            body = replace_one(body, old, new, f"#357 {label}")
    elif n in (358, 359, 360, 361):
        prefix = {
            358: "Implement ADR 0007 as durable Investment Intelligence semantics and participate in ADRs 0012–0014 as a typed Evidence target owner.",
            359: "Implement ADR 0008 as decision-grade actual Portfolio State, alternative-relative Projected Portfolio Consequences/optional Projected Portfolio State, and attributable multidimensional Portfolio Risk Assessments. Participate in ADRs 0012–0014 by owning complete versioned claim catalogs for Consequence and Risk targets and by revalidating any current Evidence basis used to form dependent assessments.",
            360: "Implement the authority-bearing/domain/application portion of ADR 0009 and participate in ADRs 0012–0014 as a typed Evidence target owner.",
            361: "Implement ADR 0010 as separate durable Outcome, Decision Evaluation, and Lesson facts and participate in ADRs 0012–0014 for Evaluation/Lesson Evidence targeting.",
        }[n]
        body = replace_one(
            body, prefix,
            prefix + " When this capability consumes a sufficiency result, it consumes the Evidence-derived result and exact proof/witnesses through the inward contract; it never authors requirement dispositions or selects an authoritative support subset.",
            f"#{n} solution",
        )
        body = replace_one(
            body,
            "against the frozen inward Evidence contract",
            "against the frozen inward Evidence contract, including ADR 0014-derived sufficiency and negative-witness semantics",
            f"#{n} contract",
        )
    elif n == 362:
        pairs = [
            (
                "Implement ADR 0011 and the presentation realization of ADR 0009 while composing the complete ADR 0012–0014 Evidence contract. Extend the existing greenfield PostgreSQL lineage for R3 facts behind inward-owned contracts, provide application-owned Durable Decision Memory composition for current and historical views, expose exact claim/requirement/support provenance and typed outcomes, enforce semantic atomicity and command-basis revalidation at integration seams, and build the first interactive CLI as a thin adapter over those shared commands/queries.",
                "Implement ADR 0011 and the presentation realization of ADR 0009 while composing the complete ADR 0012–0014 Evidence contract. Extend the existing greenfield PostgreSQL lineage for R3 facts behind inward-owned contracts, provide application-owned Durable Decision Memory composition for current and historical views, expose exact claim/requirement/support provenance—including typed executable sufficiency predicates, derived dispositions/proof, and authoritative negative witnesses—enforce semantic atomicity and command-basis revalidation at integration seams, and build the first interactive CLI as a thin adapter over those shared commands/queries.",
                "solution",
            ),
            (
                "9. As a reviewer, I want the exact Configuration-owned requirement set/version and requirement dispositions visible for freshness and sufficiency conclusions, so that results are attributable to historical rules.",
                "9. As a reviewer, I want the exact Configuration-owned requirement set/version, typed sufficiency predicate/applicability, Evidence-derived disposition, contributor/deficiency proof, and negative witness visible for freshness and sufficiency conclusions, so that results are attributable to historical rules rather than caller assertions.",
                "u9",
            ),
            (
                "7. Surface exact requirement-set version, applicability assignment, freshness basis, sufficiency dispositions, and missing/contested/unavailable/invalid authority outcomes from the Evidence/Application contract.",
                "7. Surface the exact requirement-set/version, `MinimumEligibleEvidence` predicate, applicability assignment, freshness/no-freshness basis, Evidence-derived sufficiency disposition, counted observations, contributor and deficiency-witness provenance, exact `NOT_APPLICABLE`/zero-definition witness when present, and missing/contested/unavailable/invalid authority outcomes from the Evidence/Application contract. Composition and CLI layers never synthesize dispositions or choose authoritative support subsets.",
                "impl7",
            ),
            (
                "2. Historical reconstruction tests across target claim catalogs, requirement versions, judgment-time Evidence, Recommendation, Portfolio/Risk, Human Decision, and Learning facts.",
                "2. Historical reconstruction tests across target claim catalogs, requirement versions and typed predicates/applicability, Evidence-derived sufficiency proof/witnesses, judgment-time Evidence, Recommendation, Portfolio/Risk, Human Decision, and Learning facts.",
                "test2",
            ),
            (
                "8. CLI tests at the command/query adapter boundary proving concise and detailed display of claim/requirement/Evidence states and correct command submission without testing presentation internals excessively.",
                "8. CLI tests at the command/query adapter boundary proving concise and detailed display of claim/requirement/Evidence states—including derived sufficiency proof and negative witnesses—and correct command submission without testing presentation internals excessively.",
                "test8",
            ),
        ]
        for old, new, label in pairs:
            body = replace_one(body, old, new, f"#362 {label}")
    elif n == 363:
        pairs = [
            (
                "Add a narrow integrated acceptance layer over the certified R3 capabilities. Exercise only four cross-domain scenario families through the same application and CLI-facing seams used by the product. Include representative claim-specific binding, requirement-version, fail-closed reconstruction, and stale current-basis behavior inside those families without building a separate exhaustive matrix. Reuse the real PostgreSQL adapter where restart/history/transaction behavior is material, preserve greenfield/legacy isolation, and leave detailed domain-edge acceptance to the owning Specs.",
                "Add a narrow integrated acceptance layer over the certified R3 capabilities. Exercise only four cross-domain scenario families through the same application and CLI-facing seams used by the product. Include representative claim-specific binding, executable sufficiency predicate/disposition entailment with exact proof/witness provenance, requirement-version, fail-closed reconstruction, and stale current-basis behavior inside those families without building a separate exhaustive matrix. Reuse the real PostgreSQL adapter where restart/history/transaction behavior is material, preserve greenfield/legacy isolation, and leave detailed domain-edge acceptance to the owning Specs.",
                "solution",
            ),
            (
                "1. Scenario family 1: fresh/sufficient attributable claim-specific Evidence under one resolved requirement version, with material conflict; meaningful challenge; Portfolio/Risk participates; Polaris recommends; human modifies/rejects/differs; both judgments and resolution semantics remain reconstructable.",
                "1. Scenario family 1: fresh/sufficient attributable claim-specific Evidence under one resolved `MinimumEligibleEvidence` requirement version, with sufficiency derived from the complete binding universe and distinct-observation counting; include material conflict, meaningful challenge, Portfolio/Risk participation, a Polaris Recommendation, and human modification/rejection/divergence while preserving both judgments and the exact sufficiency proof.",
                "scenario1",
            ),
            (
                "2. Scenario family 2: required support stale/insufficient/conflicted, requirement authority unresolved, or consequence/Risk unresolved; Polaris explicitly withholds; authorized human decides without Recommendation; reconstruction preserves why and the exact historical authority.",
                "2. Scenario family 2: required support stale/insufficient/conflicted, requirement authority unresolved, or consequence/Risk unresolved; Polaris explicitly withholds and an authorized human may decide without Recommendation; reconstruction preserves why and the exact historical authority/proof. Within this same bounded family, separately prove that an authoritative per-requirement `NOT_APPLICABLE` witness or complete-zero-sufficiency-definition witness is preserved as negative authority and is not treated as missing support or as a withholding cause by itself.",
                "scenario2",
            ),
            (
                "8. Explicit proof that claim-specific Evidence resolves through target-owned historical membership and exact requirement authority.",
                "8. Explicit proof that claim-specific Evidence resolves through target-owned historical membership and exact requirement authority, that sufficiency is derived from the complete binding universe rather than a caller-selected subset, and that `NOT_APPLICABLE`/zero-definition outcomes require their exact Configuration witnesses.",
                "test8",
            ),
        ]
        for old, new, label in pairs:
            body = replace_one(body, old, new, f"#363 {label}")
    return body

token = os.environ.get("GITHUB_TOKEN")
if not token:
    raise SystemExit("GITHUB_TOKEN missing")
os.environ["GH_TOKEN"] = token

current: dict[int, str] = {}
candidate: dict[int, str] = {}
status: dict[int, str] = {}

for n in sorted(EXPECTED_OLD):
    issue = json.loads(run(["gh", "api", f"repos/{REPO}/issues/{n}"]))
    body = issue.get("body") or ""
    d = digest(body)
    current[n] = body
    if d == EXPECTED_NEW[n]:
        candidate[n] = body
        status[n] = "already-certified"
        continue
    if d != EXPECTED_OLD[n]:
        raise SystemExit(f"#{n}: unexpected source hash {d}")
    body2 = transform(n, body)
    d2 = digest(body2)
    if d2 != EXPECTED_NEW[n]:
        raise SystemExit(f"#{n}: candidate hash mismatch {d2}")
    candidate[n] = body2
    status[n] = "ready"

print(f"PROPOSAL_ID={PROPOSAL_ID}")
for n in sorted(status):
    print(f"PRECHECK #{n}: {status[n]} old={digest(current[n])} new={digest(candidate[n])}")

for n in sorted(candidate):
    if status[n] == "already-certified":
        continue
    payload = json.dumps({"body": candidate[n]}, ensure_ascii=False)
    run(["gh", "api", "-X", "PATCH", f"repos/{REPO}/issues/{n}", "--input", "-"], payload)
    rb = json.loads(run(["gh", "api", f"repos/{REPO}/issues/{n}"]))
    d = digest(rb.get("body") or "")
    if d != EXPECTED_NEW[n]:
        raise SystemExit(f"#{n}: post-write readback mismatch {d}")
    print(f"PUBLISHED #{n}: {d}")

for n in sorted(EXPECTED_NEW):
    rb = json.loads(run(["gh", "api", f"repos/{REPO}/issues/{n}"]))
    d = digest(rb.get("body") or "")
    if d != EXPECTED_NEW[n]:
        raise SystemExit(f"FINAL #{n}: mismatch {d}")
    print(f"FINAL #{n}: {d}")

print("TO_SPECS_SPEC_PUBLICATION=PASS")
