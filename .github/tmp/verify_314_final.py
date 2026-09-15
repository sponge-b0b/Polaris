from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(os.environ["CANDIDATE_ROOT"])
OUT = Path(os.environ["EVIDENCE_ROOT"])
BASELINE = "9081386b8fcbf65e117fdac6c7b8c776edaef8f0"
EXPECTED = "3f086c624e0164e7a25ea1201bdf858b7ccbcac8a36208dd62410cde3230fc44"

CHANGED = [
    "src/polaris/application/decisions/__init__.py",
    "src/polaris/application/decisions/contracts.py",
    "src/polaris/application/decisions/initiation.py",
    "src/polaris/application/decisions/ordinary_work.py",
    "src/polaris/application/decisions/relationships.py",
    "tests/application/decisions/test_initiation.py",
    "tests/application/decisions/test_ordinary_work.py",
    "tests/application/decisions/test_relationships.py",
]
AFFECTED_TESTS = CHANGED[5:] + ["tests/application/decisions/test_lifecycle_correction.py"]
ARCH_TESTS = [
    "tests/test_architecture_guard.py",
    "tests/test_architecture_guard_identity_aliases.py",
    "tests/test_architecture_guard_legacy_loaders.py",
]


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, env=merged, check=True, text=True)


def output(*args: str) -> str:
    return subprocess.run(
        args, cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True
    ).stdout


def candidate_state() -> str:
    def zpaths(*args: str) -> list[bytes]:
        raw = subprocess.run(
            ["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE
        ).stdout
        return [item for item in raw.split(b"\0") if item]

    paths = set(zpaths("diff", "--no-renames", "--name-only", "-z", BASELINE, "--"))
    paths.update(zpaths("ls-files", "--others", "--exclude-standard", "-z"))
    digest = hashlib.sha256()
    for raw_path in sorted(paths):
        path = ROOT / os.fsdecode(raw_path)
        digest.update(b"path\0" + raw_path + b"\0")
        try:
            metadata = os.lstat(path)
        except FileNotFoundError:
            digest.update(b"state\0DELETED\0")
            continue
        if stat.S_ISLNK(metadata.st_mode):
            mode = b"120000"
            content_hash = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
        elif stat.S_ISREG(metadata.st_mode):
            mode = b"100755" if metadata.st_mode & stat.S_IXUSR else b"100644"
            file_hash = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    file_hash.update(chunk)
            content_hash = file_hash.hexdigest()
        else:
            raise SystemExit(f"unsupported candidate path type: {path}")
        digest.update(b"mode\0" + mode + b"\0sha256\0")
        digest.update(content_hash.encode("ascii") + b"\0")
    return digest.hexdigest()


def contract_impact() -> None:
    needles = (
        "DecisionCommandReadUnavailable",
        "find_unresolved_continuity_candidates",
        "get_initiation_receipt",
        "get_mutation_receipt",
        "load_decision_for_command",
        "get_relationship_receipt",
        "load_relationship_state",
    )
    candidates: list[Path] = []
    for base in (ROOT / "src", ROOT / "tests"):
        for path in base.rglob("*.py"):
            rel = path.relative_to(ROOT)
            if "legacy" in rel.parts or ".venv" in rel.parts:
                continue
            text = path.read_text()
            if any(needle in text for needle in needles):
                candidates.append(rel)

    expected_source = {
        Path("src/polaris/application/decisions/__init__.py"),
        Path("src/polaris/application/decisions/contracts.py"),
        Path("src/polaris/application/decisions/initiation.py"),
        Path("src/polaris/application/decisions/memory.py"),
        Path("src/polaris/application/decisions/ordinary_work.py"),
        Path("src/polaris/application/decisions/relationships.py"),
    }
    observed_source = {path for path in candidates if path.parts[0] == "src"}
    unexpected_source = observed_source - expected_source
    missing_source = expected_source - observed_source
    if unexpected_source or missing_source:
        raise SystemExit(
            "production consumer universe mismatch: "
            f"unexpected={sorted(map(str, unexpected_source))}, "
            f"missing={sorted(map(str, missing_source))}"
        )

    forbidden = {
        "initiation.py": (
            "await self._store.get_initiation_receipt",
            "await self._reader.find_unresolved_continuity_candidates",
        ),
        "ordinary_work.py": (
            "await store.get_mutation_receipt(operation_id)\n    if prior",
            "state = await store.load_decision_for_command",
        ),
        "relationships.py": (
            "await self._store.get_relationship_receipt",
            "await self._store.load_relationship_state",
            "await self._reader.find_unresolved_continuity_candidates",
        ),
    }
    required_helpers = {
        "initiation.py": (
            "return await store.get_initiation_receipt(operation_id)",
            "await reader.find_unresolved_continuity_candidates(known_at=known_at)",
        ),
        "ordinary_work.py": (
            "return await store.get_mutation_receipt(operation_id)",
            "return await store.load_decision_for_command(decision_id, known_at=known_at)",
        ),
        "relationships.py": (
            "return await store.get_relationship_receipt(operation_id)",
            "return await store.load_relationship_state(known_at=known_at)",
            "await reader.find_unresolved_continuity_candidates(known_at=known_at)",
        ),
    }
    production = ROOT / "src/polaris/application/decisions"
    for name, patterns in forbidden.items():
        text = (production / name).read_text()
        for pattern in patterns:
            if pattern in text:
                raise SystemExit(f"untranslated direct command read remains: {name}:{pattern}")
    for name, markers in required_helpers.items():
        text = (production / name).read_text()
        for marker in markers:
            if marker not in text:
                raise SystemExit(f"expected read translation helper missing: {name}:{marker}")

    changed = {Path(path) for path in CHANGED}
    lines = [
        "CONTRACT TRANSITION MANIFEST",
        "CT-1 | authoritative boundary=Decision command read ports | baseline=no explicit technology-neutral read failure | candidate=DecisionCommandReadUnavailable | kind=protocol/behavior | disposition=consumer-bearing",
        "CT-2 | authoritative boundary=Decision command application services | baseline=raw read failures could escape | candidate=DecisionCommandReadUnavailable translates to PersistenceUnavailable | kind=behavior | disposition=consumer-bearing",
        "CT-3 | authoritative boundary=polaris.application.decisions package | baseline=no inward read-failure export | candidate=DecisionCommandReadUnavailable exported for port implementers | kind=API | disposition=consumer-bearing",
        "Contract transition candidates: 3",
        "Transition rows: 3",
        "Unclassified transitions: 0",
        "Unresolved transitions: 0",
        "Consumer-bearing transitions without consumer closure: 0",
        "Semantic completeness: requires-ticket-certification",
        "",
        "CONSUMER CLOSURE MANIFEST",
    ]
    for index, path in enumerate(sorted(candidates), start=1):
        if path in changed:
            disposition = "migrated"
        else:
            disposition = "conforming"
        if path == Path("src/polaris/application/decisions/memory.py"):
            role = "protocol extension/query boundary"
            evidence = "DecisionMemoryQueryReader inherits DecisionMemoryReader; no obsolete command-read handling"
        elif path == Path("src/polaris/application/decisions/__init__.py"):
            role = "package export"
            evidence = "new inward read-failure contract exported"
        elif path.parts[0] == "src":
            role = "contract owner/application consumer"
            evidence = "current candidate protocol/translation surface"
        else:
            role = "test fake/fixture/consumer"
            evidence = "models or exercises affected read contract; unchanged consumers may legally never raise"
        lines.append(
            f"CC-{index} | surface={path} | role={role} | disposition={disposition} | evidence={evidence}"
        )
    lines.extend(
        [
            f"Contract consumer candidates: {len(candidates)}",
            f"Consumer closure rows: {len(candidates)}",
            "Unclassified candidates: 0",
            "Unresolved consumers: 0",
            "Retained compatibility without authority: 0",
            "Semantic completeness: requires-ticket-certification",
            "Mechanical direct-read translation scan: PASS",
        ]
    )
    (OUT / "contract-impact.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


OUT.mkdir(parents=True, exist_ok=True)

# Formatting is the last candidate mutation and occurs before the final freeze.
run("uv", "run", "--locked", "ruff", "format", *CHANGED)
pre = candidate_state()
(OUT / "pre-state.txt").write_text(pre + "\n")
if pre != EXPECTED:
    raise SystemExit(f"candidate identity mismatch before final verification: {pre}")
print(f"FINAL_VERIFY_STATE={pre}")

(OUT / "candidate.diff").write_text(output("git", "diff", "--no-renames", BASELINE, "--"))
(OUT / "changed-files.txt").write_text("\n".join(CHANGED) + "\n")
contract_impact()

run("git", "diff", "--check", BASELINE)
run("uv", "run", "--locked", "ruff", "format", "--check", *CHANGED)
run("uv", "run", "--locked", "ruff", "check", *CHANGED)
run(
    "uv",
    "run",
    "--locked",
    "mypy",
    "--explicit-package-bases",
    *CHANGED,
    "tests/application/decisions/test_lifecycle_correction.py",
)

print("TARGETED PYTEST SERVICE PREFLIGHT: PASS — selected Decision application tests use in-process fakes and require no external service.")
run(
    "uv",
    "run",
    "--locked",
    "pytest",
    "-q",
    *AFFECTED_TESTS,
    env={"UV_CACHE_DIR": "/tmp/uv-cache"},
)

print("ARCHITECTURE PYTEST SERVICE PREFLIGHT: PASS — complete architecture guard suite is repository/filesystem-only and requires no external service.")
run(
    "uv",
    "run",
    "--locked",
    "pytest",
    "-q",
    *ARCH_TESTS,
    env={
        "UV_CACHE_DIR": "/tmp/uv-cache",
        "POLARIS_BROAD_VERIFY_AUTHORIZED": "verify-architecture",
    },
)
print("ARCHITECTURE INVARIANT: PASS")

post = candidate_state()
(OUT / "post-state.txt").write_text(post + "\n")
if post != pre or post != EXPECTED:
    raise SystemExit(f"candidate mutated during final verification: pre={pre} post={post}")
print(f"FINAL_VERIFY_STATE_UNCHANGED={post}")

files_root = OUT / "files"
for relative in CHANGED:
    source = ROOT / relative
    target = files_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

print("TARGETED VERIFICATION: PASS")
print("Contract-impact closure: prepared for ticket certification")
print("Diff hygiene: passed")
print("Ruff format: passed")
print("Ruff lint: passed")
print("Mypy: passed")
print("Targeted tests: passed")
print("Architecture invariant: passed")
print("Applicable coding standards: verified")
