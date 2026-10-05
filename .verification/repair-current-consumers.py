from pathlib import Path


def fragment(name: str) -> str:
    return Path(f".verification/fragments/{name}").read_text(encoding="utf-8").rstrip()


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[:i] + replacement.rstrip() + "\n\n" + text[j:]


path = Path("/tmp/proposal-357-dd2-resume.txt")
text = path.read_text(encoding="utf-8")
text = replace_between(text, "ACTION 5 — UPDATE TICKET #380", "ACTION 6 — UPDATE TICKET #381", fragment("action5-current-basis.txt"))
text = replace_between(text, "ACTION 6 — UPDATE TICKET #381", "ACTION 7 — UPDATE PARENT TICKET COVERAGE MANIFEST COMMENT 5899020558 IN PLACE", fragment("action6-dependent-commit.txt"))

text = text.replace(
    "DD-1 remains reconciled. DD-2 is reconciled by splitting observation correction, binding correction, and assessment-specific correction into separate context-fit slices; routing ADR 0012/ARCHSRC-2 and ARCHSRC-7 across #378 and NEW-BINDING-CORRECTION, ADR 0014/ARCHSRC-4 to NEW-ASSESSMENT-CORRECTION, and carrying assessment-correction invalidation explicitly into #379, #380, and #381. DD-2 becomes reconciled only after the approved ticket bodies, native relationships, this manifest, recovery records, and decomposition-defect record are published and read back exactly.",
    "DD-1 remains reconciled. DD-2 is reconciled by splitting observation correction, binding correction, and assessment-specific correction into separate context-fit slices; routing ADR 0012/ARCHSRC-2 and ARCHSRC-7 across #378 and NEW-BINDING-CORRECTION, ADR 0014/ARCHSRC-4 to NEW-ASSESSMENT-CORRECTION, carrying all result-affecting observation/binding/assessment correction interpretation through #379, and carrying the corresponding current-basis invalidation and fresh commit-time revalidation explicitly into #380 and #381. DD-2 becomes reconciled only after the approved ticket bodies, native relationships, this manifest, recovery records, and decomposition-defect record are published and read back exactly.",
    1,
)
text = text.replace(
    "#379 reconstructs all three correction families and reassessment proof without hindsight; #380 treats assessment/reassessment/correction as explicit current-basis invalidators; #381 explicitly revalidates assessment-correction state at dependent commit.",
    "#379 reconstructs all three correction families and reassessment proof without hindsight; #380 treats result-affecting observation, binding, and assessment correction interpretation as explicit current-basis invalidators; #381 freshly reconstructs/revalidates all result-affecting correction interpretations at dependent commit.",
    1,
)

required = [
    "Consumer #380: applies — current-support basis captures the exact current interpreted observation/binding correction state",
    "Consumer #381: applies — fresh dependent-commit reconstruction/revalidation observes the complete current observation/binding correction state",
    "concurrent observation-correction invalidation",
    "concurrent binding-correction invalidation",
]
for needle in required:
    if needle not in text:
        raise SystemExit(f"current-consumer repair missing required semantic carry: {needle}")

path.write_text(text, encoding="utf-8")
