from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow_hashing import sha256_canonical_json  # noqa: E402
from review_coverage import ReviewCoverageError, validate_coverage  # noqa: E402

SCHEMA = "polaris.review-convergence/v1"
_HEAD = re.compile(r"^[0-9a-f]{40}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_FINDING_LINK = re.compile(r"^RF-[0-9]+@[A-Z]+-[0-9]{3}$")


class ReviewConvergenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReviewConvergenceReceipt:
    reviewed_head: str
    spec_contract_hash: str
    rounds: int
    surface_count: int
    probe_count: int
    finding_link_count: int
    convergence_sha256: str


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewConvergenceError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _fingerprint(value: Any) -> str:
    return sha256_canonical_json(value)


def _snapshot(contract: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    receipt = validate_coverage(contract, coverage)
    surfaces: list[str] = []
    probes: list[str] = []
    finding_links: set[str] = set()

    for row in coverage["cells"]:
        cell = row["cell"]
        surface_fingerprints: dict[str, str] = {}
        for surface in row["surfaces"]:
            fingerprint = _fingerprint(
                {
                    "cell": cell,
                    "role": surface["role"],
                    "evidence": surface["evidence"],
                }
            )
            surface_fingerprints[surface["surface_id"]] = fingerprint
            surfaces.append(fingerprint)

        for probe in row["probes"]:
            probe_surface_fingerprints = sorted(
                surface_fingerprints[surface_id]
                for surface_id in probe["surface_ids"]
            )
            probes.append(
                _fingerprint(
                    {
                        "cell": cell,
                        "lens": probe["lens"],
                        "surfaces": probe_surface_fingerprints,
                        "falsifier": probe["falsifier"],
                        "evidence": probe["evidence"],
                        "finding_ids": sorted(probe["finding_ids"]),
                    }
                )
            )
            for finding_id in probe["finding_ids"]:
                finding_links.add(f"{finding_id}@{cell}")

    return {
        "coverage_sha256": receipt.coverage_sha256,
        "surface_fingerprints": sorted(set(surfaces)),
        "probe_fingerprints": sorted(set(probes)),
        "finding_links": sorted(finding_links),
    }


def build_convergence(
    contract: dict[str, Any], coverages: list[dict[str, Any]]
) -> dict[str, Any]:
    _need(len(coverages) >= 2, "convergence: at least two complete review rounds required")
    snapshots: list[dict[str, Any]] = []
    reviewed_head: str | None = None
    contract_hash = contract.get("spec_contract_hash")
    _need(
        isinstance(contract_hash, str) and _HASH.fullmatch(contract_hash) is not None,
        "contract: invalid Spec Contract Hash",
    )

    for index, coverage in enumerate(coverages, start=1):
        receipt = validate_coverage(contract, coverage)
        if reviewed_head is None:
            reviewed_head = receipt.reviewed_head
        _need(
            receipt.reviewed_head == reviewed_head,
            "convergence: all rounds must review the exact same candidate",
        )
        snapshot = _snapshot(contract, coverage)
        snapshots.append({"round": index, **snapshot})

    assert reviewed_head is not None
    return {
        "schema": SCHEMA,
        "spec_contract_hash": contract_hash,
        "reviewed_head": reviewed_head,
        "rounds": snapshots,
    }


def _validate_fingerprint_list(value: Any, field: str) -> tuple[str, ...]:
    _need(isinstance(value, list), f"convergence: {field} must be a list")
    _need(
        all(isinstance(item, str) and _HASH.fullmatch(item) for item in value),
        f"convergence: invalid {field} fingerprint",
    )
    _need(value == sorted(set(value)), f"convergence: {field} must be sorted and unique")
    return tuple(value)


def _validate_finding_links(value: Any) -> tuple[str, ...]:
    _need(isinstance(value, list), "convergence: finding_links must be a list")
    _need(
        all(isinstance(item, str) and _FINDING_LINK.fullmatch(item) for item in value),
        "convergence: invalid finding link",
    )
    _need(value == sorted(set(value)), "convergence: finding_links must be sorted and unique")
    return tuple(value)


def validate_convergence(value: dict[str, Any]) -> ReviewConvergenceReceipt:
    _need(value.get("schema") == SCHEMA, f"convergence: schema must be {SCHEMA}")
    _need(
        set(value) == {"schema", "spec_contract_hash", "reviewed_head", "rounds"},
        "convergence: unsupported top-level fields",
    )
    contract_hash = value.get("spec_contract_hash")
    _need(
        isinstance(contract_hash, str) and _HASH.fullmatch(contract_hash) is not None,
        "convergence: invalid Spec Contract Hash",
    )
    reviewed_head = value.get("reviewed_head")
    _need(
        isinstance(reviewed_head, str) and _HEAD.fullmatch(reviewed_head) is not None,
        "convergence: invalid reviewed HEAD",
    )
    rounds = value.get("rounds")
    _need(
        isinstance(rounds, list) and len(rounds) >= 2,
        "convergence: at least two complete review rounds required",
    )

    normalized: list[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []
    for index, row in enumerate(rounds, start=1):
        _need(isinstance(row, dict), "convergence: invalid round row")
        _need(
            set(row)
            == {
                "round",
                "coverage_sha256",
                "surface_fingerprints",
                "probe_fingerprints",
                "finding_links",
            },
            "convergence: unsupported round fields",
        )
        _need(row.get("round") == index, "convergence: rounds must be canonical and contiguous")
        coverage_hash = row.get("coverage_sha256")
        _need(
            isinstance(coverage_hash, str) and _HASH.fullmatch(coverage_hash) is not None,
            "convergence: invalid coverage hash",
        )
        surfaces = _validate_fingerprint_list(
            row.get("surface_fingerprints"), "surface_fingerprints"
        )
        probes = _validate_fingerprint_list(
            row.get("probe_fingerprints"), "probe_fingerprints"
        )
        finding_links = _validate_finding_links(row.get("finding_links"))
        normalized.append((surfaces, probes, finding_links))

    previous = normalized[-2]
    current = normalized[-1]
    added_surfaces = set(current[0]) - set(previous[0])
    removed_surfaces = set(previous[0]) - set(current[0])
    added_probes = set(current[1]) - set(previous[1])
    removed_probes = set(previous[1]) - set(current[1])
    added_links = set(current[2]) - set(previous[2])
    removed_links = set(previous[2]) - set(current[2])
    _need(
        not (
            added_surfaces
            or removed_surfaces
            or added_probes
            or removed_probes
            or added_links
            or removed_links
        ),
        "convergence: final challenger changed the material review universe; run another fresh complete challenger round",
    )

    return ReviewConvergenceReceipt(
        reviewed_head=reviewed_head,
        spec_contract_hash=contract_hash,
        rounds=len(rounds),
        surface_count=len(current[0]),
        probe_count=len(current[1]),
        finding_link_count=len(current[2]),
        convergence_sha256=sha256_canonical_json(value),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    build.add_argument("spec_contract", type=Path)
    build.add_argument("output", type=Path)
    build.add_argument("coverage", type=Path, nargs="+")

    validate = sub.add_parser("validate")
    validate.add_argument("convergence", type=Path)
    return parser


def _print_receipt(receipt: ReviewConvergenceReceipt) -> None:
    print("REVIEW CONVERGENCE: VALID")
    print(f"Reviewed HEAD: {receipt.reviewed_head}")
    print(f"Spec Contract Hash: {receipt.spec_contract_hash}")
    print(f"Complete challenger rounds: {receipt.rounds}")
    print("Final material surface delta: +0/-0")
    print("Final adversarial probe delta: +0/-0")
    print("Final finding-link delta: +0/-0")
    print(f"Converged review surfaces: {receipt.surface_count}")
    print(f"Converged adversarial probes: {receipt.probe_count}")
    print(f"Converged finding links: {receipt.finding_link_count}")
    print(f"Review Convergence SHA-256: {receipt.convergence_sha256}")


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        if args.command == "build":
            contract = _read_json(args.spec_contract)
            coverages = [_read_json(path) for path in args.coverage]
            artifact = build_convergence(contract, coverages)
            args.output.write_text(
                json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            receipt = validate_convergence(artifact)
        else:
            receipt = validate_convergence(_read_json(args.convergence))
    except (
        ReviewConvergenceError,
        ReviewCoverageError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        parser.error(str(exc))

    _print_receipt(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
