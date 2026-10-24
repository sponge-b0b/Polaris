from __future__ import annotations

import ast
from pathlib import Path

from scripts.workflow_hashing import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_canonical_json,
    sha256_file_bytes,
    sha256_prefixed_canonical_json,
    sha256_utf8_text,
)

ROOT = Path(__file__).resolve().parents[3]
HASH_RUNTIME = ROOT / "scripts/workflow_hashing.py"

# Migration debt only. These are the exact direct SHA-256 call sites that predate
# workflow_hashing.py. This set and each call count may shrink, but must not grow.
LEGACY_DIRECT_SHA256_CALLS = {
    "scripts/ccl.py": 1,
    "scripts/review_remediation.py": 1,
    "scripts/spec_contract.py": 1,
    "scripts/workflow_journal.py": 2,
    "scripts/workflow_reslice_recovery.py": 1,
    "scripts/workflow_routing_defects.py": 1,
    "scripts/workflow_spec_ownership.py": 1,
    "scripts/workflow_to_specs.py": 1,
}


def _runtime_python_files() -> tuple[Path, ...]:
    files = set((ROOT / "scripts").glob("*.py"))
    files.update((ROOT / ".agents/skills").glob("**/scripts/*.py"))
    files.discard(HASH_RUNTIME)
    return tuple(sorted(files))


def _direct_sha256_calls(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hashlib_aliases: set[str] = set()
    sha256_aliases: set[str] = set()
    new_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == "hashlib":
                    hashlib_aliases.add(item.asname or item.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "hashlib":
            for item in node.names:
                if item.name == "sha256":
                    sha256_aliases.add(item.asname or item.name)
                elif item.name == "new":
                    new_aliases.add(item.asname or item.name)

    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in hashlib_aliases
            and func.attr == "sha256"
        ):
            count += 1
            continue
        if isinstance(func, ast.Name) and func.id in sha256_aliases:
            count += 1
            continue

        is_hashlib_new = (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in hashlib_aliases
            and func.attr == "new"
        )
        is_imported_new = isinstance(func, ast.Name) and func.id in new_aliases
        if (is_hashlib_new or is_imported_new) and node.args:
            algorithm = node.args[0]
            if isinstance(algorithm, ast.Constant) and algorithm.value == "sha256":
                count += 1
    return count


def test_workflow_runtime_cannot_add_ad_hoc_sha256() -> None:
    observed: dict[str, int] = {}
    for path in _runtime_python_files():
        count = _direct_sha256_calls(path)
        if count:
            observed[path.relative_to(ROOT).as_posix()] = count

    assert observed == LEGACY_DIRECT_SHA256_CALLS


def test_exact_bytes_identity_is_stable() -> None:
    assert sha256_bytes(b"abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_exact_utf8_text_does_not_normalize_newlines() -> None:
    assert sha256_utf8_text("a\n") == (
        "87428fc522803d31065e7bce3cf03fe475096631e5e07bbd7a0fde60c4cf25c7"
    )
    assert sha256_utf8_text("a") != sha256_utf8_text("a\n")


def test_canonical_json_representation_is_explicit_and_stable() -> None:
    left = {"b": 2, "a": "é"}
    right = {"a": "é", "b": 2}

    assert canonical_json_bytes(left) == b'{"a":"\xc3\xa9","b":2}'
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert sha256_canonical_json(left) == (
        "06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de"
    )


def test_canonical_json_hash_is_not_serialized_file_hash(tmp_path: Path) -> None:
    value = {"b": 2, "a": "é"}
    path = tmp_path / "receipt.json"
    path.write_bytes(canonical_json_bytes(value) + b"\n")

    assert sha256_canonical_json(value) != sha256_file_bytes(path)
    assert sha256_file_bytes(path) == (
        "ceadaa5632d2aee2ae6dd68fa424ca9d1c318cd64d2d00c784e18f52f38fffab"
    )


def test_prefixed_canonical_json_preserves_exact_domain_bytes() -> None:
    value = {"b": 2, "a": "é"}
    assert sha256_prefixed_canonical_json(b"POLARIS-TEST-V1\0", value) == (
        "927d361bf862867f99e53f405ba579f23178ac58e58bc665ee7cc762e7f6d832"
    )
