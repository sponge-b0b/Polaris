from __future__ import annotations

import os
import subprocess
from pathlib import Path

OLD_BRANCH = "origin/chatgpt/verify-ticket-decomposition-357-dd2-repaired"
OLD_PATH = ".verification/proposal-357-dd2-repaired.txt"
CURRENT_HEAD = os.environ["CANDIDATE_HEAD"]
OLD_HEAD = "5ad1886205a33a73a058d98104f0f299b368b086"


def fragment(name: str) -> str:
    return Path(f".verification/fragments/{name}").read_text(encoding="utf-8").replace("__CANDIDATE_HEAD__", CURRENT_HEAD).rstrip()


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + replacement.rstrip() + "\n\n" + text[j:]


subprocess.run(["git", "fetch", "origin", "chatgpt/verify-ticket-decomposition-357-dd2-repaired"], check=True)
text = subprocess.check_output(["git", "show", f"{OLD_BRANCH}:{OLD_PATH}"], text=True)
text = text.replace(OLD_HEAD, CURRENT_HEAD)
text = text.replace(
    "PROPOSAL ALIAS:\nNEW-ASSESSMENT-CORRECTION = one new implementation ticket whose tracker number is assigned only during publication.",
    "PROPOSAL ALIASES:\nNEW-BINDING-CORRECTION = one new implementation ticket whose tracker number is assigned only during publication.\nNEW-ASSESSMENT-CORRECTION = one new implementation ticket whose tracker number is assigned only during publication.",
)

# Shift existing downstream action numbers, preserving the assessment action as the next slot.
for old, new in [
    ("ACTION 8 — NATIVE RELATIONSHIP / PUBLICATION REALIZATION", "ACTION 9 — NATIVE RELATIONSHIP / PUBLICATION REALIZATION"),
    ("ACTION 7 — UPDATE DECOMPOSITION DEFECT COMMENT 5930434832 IN PLACE", "ACTION 8 — UPDATE DECOMPOSITION DEFECT COMMENT 5930434832 IN PLACE"),
    ("ACTION 6 — UPDATE PARENT TICKET COVERAGE MANIFEST COMMENT 5899020558 IN PLACE", "ACTION 7 — UPDATE PARENT TICKET COVERAGE MANIFEST COMMENT 5899020558 IN PLACE"),
    ("ACTION 5 — UPDATE TICKET #381", "ACTION 6 — UPDATE TICKET #381"),
    ("ACTION 4 — UPDATE TICKET #380", "ACTION 5 — UPDATE TICKET #380"),
    ("ACTION 3 — UPDATE TICKET #379", "ACTION 4 — UPDATE TICKET #379"),
]:
    text = text.replace(old, new, 1)

text = replace_between(text, "ACTION 1 — UPDATE TICKET #378", "ACTION 2 — CREATE NEW-ASSESSMENT-CORRECTION", fragment("action1.txt"))
text = text.replace(
    "ACTION 2 — CREATE NEW-ASSESSMENT-CORRECTION",
    fragment("action2-binding.txt") + "\n\nACTION 3 — CREATE NEW-ASSESSMENT-CORRECTION",
    1,
)
text = text.replace("#378 — Preserve Evidence observation and binding correction lineage end to end", "#378 — Preserve Evidence observation correction lineage end to end")

# Assessment correction must consume binding-correction interpretation.
text = text.replace(
    "#377 — Assess Evidence sufficiency against authoritative requirement versions\n#378 — Preserve Evidence observation correction lineage end to end\n\n## Ticket branch",
    "#377 — Assess Evidence sufficiency against authoritative requirement versions\n#378 — Preserve Evidence observation correction lineage end to end\nNEW-BINDING-CORRECTION — Correct Evidence bindings with fixed-endpoint replacement semantics\n\n## Ticket branch",
    1,
)
# Historical reconstruction consumes both new correction-family destinations.
text = text.replace(
    "#378 — Preserve Evidence observation correction lineage end to end\nNEW-ASSESSMENT-CORRECTION — Correct sufficiency assessments with derived proof and trusted revalidation",
    "#378 — Preserve Evidence observation correction lineage end to end\nNEW-BINDING-CORRECTION — Correct Evidence bindings with fixed-endpoint replacement semantics\nNEW-ASSESSMENT-CORRECTION — Correct sufficiency assessments with derived proof and trusted revalidation",
    1,
)
text = text.replace(
    "Native relationship delta: add NEW-ASSESSMENT-CORRECTION as a blocker; preserve current blockers #375, #377, #378.",
    "Native relationship delta: add NEW-BINDING-CORRECTION and NEW-ASSESSMENT-CORRECTION as blockers; preserve current blockers #375, #377, #378.",
    1,
)

# Expand proposed TCM rows to the binding-correction destination.
for old, new in [
    ("US-3 → #378, NEW-ASSESSMENT-CORRECTION", "US-3 → #378, NEW-BINDING-CORRECTION, NEW-ASSESSMENT-CORRECTION"),
    ("ID-2 → #378, NEW-ASSESSMENT-CORRECTION", "ID-2 → #378, NEW-BINDING-CORRECTION, NEW-ASSESSMENT-CORRECTION"),
    ("ID-20 → #372, #373, #374, #377, #378, NEW-ASSESSMENT-CORRECTION, #381", "ID-20 → #372, #373, #374, #377, #378, NEW-BINDING-CORRECTION, NEW-ASSESSMENT-CORRECTION, #381"),
    ("TD-2 → #378, NEW-ASSESSMENT-CORRECTION", "TD-2 → #378, NEW-BINDING-CORRECTION, NEW-ASSESSMENT-CORRECTION"),
    ("TD-9 → #372, #373, #374, #377, #378, NEW-ASSESSMENT-CORRECTION, #381", "TD-9 → #372, #373, #374, #377, #378, NEW-BINDING-CORRECTION, NEW-ASSESSMENT-CORRECTION, #381"),
    ("Tickets/destination: #372, #374, #377, #378, NEW-ASSESSMENT-CORRECTION", "Tickets/destination: #372, #374, #377, #378, NEW-BINDING-CORRECTION, NEW-ASSESSMENT-CORRECTION"),
    ("Tickets/destination: #372, #373, #374, #385, #377, #378, NEW-ASSESSMENT-CORRECTION, #381", "Tickets/destination: #372, #373, #374, #385, #377, #378, NEW-BINDING-CORRECTION, NEW-ASSESSMENT-CORRECTION, #381"),
]:
    if old not in text:
        raise SystemExit(f"required TCM replacement missing: {old}")
    text = text.replace(old, new, 1)

text = text.replace(
    "DD-1 remains reconciled. DD-2 is reconciled by splitting simple observation/binding correction from assessment-specific correction, routing ADR 0014/ARCHSRC-4 to NEW-ASSESSMENT-CORRECTION, and carrying assessment-correction invalidation explicitly into #379, #380, and #381. DD-2 becomes reconciled only after the approved ticket bodies, native relationships, this manifest, and decomposition-defect record are published and read back exactly.",
    "DD-1 remains reconciled. DD-2 is reconciled by splitting observation correction, binding correction, and assessment-specific correction into separate context-fit slices; routing ADR 0012/ARCHSRC-2 and ARCHSRC-7 across #378 and NEW-BINDING-CORRECTION, ADR 0014/ARCHSRC-4 to NEW-ASSESSMENT-CORRECTION, and carrying assessment-correction invalidation explicitly into #379, #380, and #381. DD-2 becomes reconciled only after the approved ticket bodies, native relationships, this manifest, recovery records, and decomposition-defect record are published and read back exactly.",
    1,
)

text = replace_between(
    text,
    "### Publication State\n\nPublished/retained tickets after realization:",
    "During actual publication only, replace every exact `NEW-ASSESSMENT-CORRECTION` alias",
    fragment("publication-state.txt"),
)
text = text.replace(
    "During actual publication only, replace every exact `NEW-ASSESSMENT-CORRECTION` alias in the approved manifest with the actual newly created issue number. No other semantic or formatting substitution is authorized.",
    "During actual publication only, replace every exact `NEW-BINDING-CORRECTION` and `NEW-ASSESSMENT-CORRECTION` alias in the approved manifest with its actual newly created issue number. No other semantic or formatting substitution is authorized.",
    1,
)

old_dd = "Reconciliation: Reconciled through the approved DD-2 ticket split and consumer carry: #378 owns observation/binding correction only; NEW-ASSESSMENT-CORRECTION owns sufficiency-assessment correction with Evidence-derived proof and trusted-instant re-evaluation/atomic revalidation under ARCHSRC-2/4/7; #379 reconstructs historical assessment-correction/reassessment proof without hindsight; #380 treats assessment/reassessment/correction as explicit current-basis invalidators; #381 explicitly revalidates assessment-correction state at dependent commit. The parent TCM comment 5899020558 carries current Spec Contract Hash db6842515a70ef6133bb21c962dd96842a840287d28e7a0fd4096d05342ed034 and the exact realized routing. No closed ticket is reopened or rewritten."
new_dd = "Reconciliation: Reconciled through the approved DD-2 ticket split and consumer carry: #378 owns the shared correction foundation plus observation correction; NEW-BINDING-CORRECTION owns binding-specific fixed-endpoint correction under ARCHSRC-2/7; NEW-ASSESSMENT-CORRECTION owns sufficiency-assessment correction with Evidence-derived proof and trusted-instant re-evaluation/atomic revalidation under ARCHSRC-2/4/7; #379 reconstructs all three correction families and reassessment proof without hindsight; #380 treats assessment/reassessment/correction as explicit current-basis invalidators; #381 explicitly revalidates assessment-correction state at dependent commit. The parent TCM comment 5899020558 carries current Spec Contract Hash db6842515a70ef6133bb21c962dd96842a840287d28e7a0fd4096d05342ed034 and the exact realized routing. No closed ticket is reopened or rewritten."
text = text.replace(old_dd, new_dd, 1)
text = text.replace(
    "During actual publication only, replace `NEW-ASSESSMENT-CORRECTION` with the actual newly created issue number.",
    "During actual publication only, replace `NEW-BINDING-CORRECTION` and `NEW-ASSESSMENT-CORRECTION` with their actual newly created issue numbers.",
    1,
)

text = replace_between(text, "ACTION 9 — NATIVE RELATIONSHIP / PUBLICATION REALIZATION", "PARENT SEMANTIC-CONSUMER IMPACT EVIDENCE", fragment("action9.txt"))
text = text[: text.index("PARENT SEMANTIC-CONSUMER IMPACT EVIDENCE")] + fragment("tail.txt") + "\n"

required = [
    f"- Spec branch HEAD: {CURRENT_HEAD}",
    "ACTION 2 — CREATE NEW-BINDING-CORRECTION",
    "ACTION 3 — CREATE NEW-ASSESSMENT-CORRECTION",
    "ACTION 4 — UPDATE TICKET #379",
    "ACTION 7 — UPDATE PARENT TICKET COVERAGE MANIFEST COMMENT 5899020558 IN PLACE",
    "ACTION 8 — UPDATE DECOMPOSITION DEFECT COMMENT 5930434832 IN PLACE",
    "ACTION 9 — NATIVE RELATIONSHIP / PUBLICATION REALIZATION",
    "Tickets created: 2",
    "Live-WIP reslice recovery records required: 2",
    "Oversized tickets: 0",
]
for needle in required:
    if needle not in text:
        raise SystemExit(f"rendered proposal missing required text: {needle}")
if OLD_HEAD in text:
    raise SystemExit("stale candidate head remains in rendered proposal")
if "observation and binding correction lineage" in text:
    raise SystemExit("stale bundled observation/binding title remains")

out = Path("/tmp/proposal-357-dd2-resume.txt")
out.write_text(text, encoding="utf-8")
print(out)
