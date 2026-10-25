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

SCHEMA = "polaris.review-finding-adjudication/v1"
_LEDGER_SCHEMA = "polaris.review-findings/v2"
_COVERAGE_SCHEMA = "polaris.review-coverage/v1"
_HEAD = re.compile(r"^[0-9a-f]{40}$")
_FINDING = re.compile(r"^RF-[0-9]+$")
_EVIDENCE_LOCATOR = re.compile(
    r"(?:src|tests)/[A-Za-z0-9_./-]+\.py:"
    r"\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*"
)


class ReviewFindingError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReviewFindingReceipt:
    reviewed_head: str
    spec_contract_hash: str
    finding_count: int
    link_count: int
    adjudication_sha256: str


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewFindingError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _contract_index(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _need(
        contract.get("schema") == "polaris.spec-contract/v1",
        "contract: wrong schema",
    )
    cells = contract.get("cells")
    _need(isinstance(cells, list), "contract: cells must be a list")
    result: dict[str, dict[str, Any]] = {}
    for cell in cells:
        _need(isinstance(cell, dict), "contract: invalid cell row")
        cell_id = cell.get("cell")
        _need(isinstance(cell_id, str) and cell_id, "contract: cell missing id")
        _need(cell_id not in result, f"contract: duplicate cell {cell_id}")
        result[cell_id] = cell
    return result


def _ledger_findings(
    ledger: dict[str, Any],
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    _need(ledger.get("schema") == _LEDGER_SCHEMA, "ledger: wrong schema")
    _need(
        ledger.get("spec_contract_hash") == contract.get("spec_contract_hash"),
        "ledger: stale Spec Contract Hash",
    )
    findings = ledger.get("findings")
    _need(isinstance(findings, list), "ledger: findings must be a list")
    seen: set[str] = set()
    for finding in findings:
        _need(isinstance(finding, dict), "ledger: invalid finding row")
        finding_id = finding.get("finding_id")
        _need(
            isinstance(finding_id, str)
            and _FINDING.fullmatch(finding_id) is not None,
            "ledger: invalid finding ID",
        )
        _need(finding_id not in seen, f"ledger: duplicate finding {finding_id}")
        seen.add(finding_id)
    return findings


def _coverage_links(
    coverage: dict[str, Any],
    findings: list[dict[str, Any]],
) -> dict[str, set[str]]:
    _need(
        coverage.get("schema") == _COVERAGE_SCHEMA,
        "coverage: wrong schema",
    )
    finding_ids = {finding["finding_id"] for finding in findings}
    links = {finding_id: set() for finding_id in finding_ids}
    cells = coverage.get("cells")
    _need(isinstance(cells, list), "coverage: cells must be a list")
    for cell in cells:
        _need(isinstance(cell, dict), "coverage: invalid cell row")
        cell_id = cell.get("cell")
        _need(isinstance(cell_id, str) and cell_id, "coverage: missing cell id")
        probes = cell.get("probes")
        _need(isinstance(probes, list), f"{cell_id}: probes must be a list")
        for probe in probes:
            _need(isinstance(probe, dict), f"{cell_id}: invalid probe")
            probe_findings = probe.get("finding_ids")
            _need(
                isinstance(probe_findings, list),
                f"{cell_id}: finding_ids must be a list",
            )
            for finding_id in probe_findings:
                _need(
                    finding_id in finding_ids,
                    f"{cell_id}: coverage references unknown finding {finding_id}",
                )
                links[finding_id].add(cell_id)
    return links


def _validate_finding_cells(
    finding: dict[str, Any],
    contract_index: dict[str, dict[str, Any]],
    coverage_links: dict[str, set[str]],
) -> int:
    finding_id = finding["finding_id"]
    cells = finding.get("cells")
    _need(isinstance(cells, list), f"{finding_id}: cells must be a list")
    expected_ids: list[str] = []
    seen: set[str] = set()
    for item in cells:
        _need(isinstance(item, dict), f"{finding_id}: invalid cell reference")
        _need(
            set(item) == {"cell", "cell_hash"},
            f"{finding_id}: unsupported cell reference fields",
        )
        cell_id = item.get("cell")
        _need(
            isinstance(cell_id, str) and cell_id in contract_index,
            f"{finding_id}: unknown affected cell {cell_id}",
        )
        _need(cell_id not in seen, f"{finding_id}: duplicate affected cell {cell_id}")
        seen.add(cell_id)
        _need(
            item.get("cell_hash") == contract_index[cell_id].get("cell_hash"),
            f"{finding_id}: stale affected cell hash {cell_id}",
        )
        expected_ids.append(cell_id)
    _need(
        coverage_links.get(finding_id, set()) == set(expected_ids),
        f"{finding_id}: coverage/finding cell mismatch",
    )
    return len(expected_ids)


def _validate_evidence_checks(
    finding_id: str,
    finding: dict[str, Any],
    checks: Any,
) -> None:
    evidence = finding.get("evidence")
    _need(
        isinstance(evidence, str) and bool(evidence.strip()),
        f"{finding_id}: finding evidence required",
    )
    _need(
        isinstance(checks, list) and bool(checks),
        f"{finding_id}: evidence adjudication required",
    )
    checked: set[str] = set()
    for check in checks:
        _need(isinstance(check, dict), f"{finding_id}: invalid evidence check")
        _need(
            set(check) == {"locator", "claim", "observed", "result"},
            f"{finding_id}: unsupported evidence check fields",
        )
        locator = check.get("locator")
        _need(
            isinstance(locator, str) and bool(locator.strip()),
            f"{finding_id}: evidence locator required",
        )
        _need(locator in evidence, f"{finding_id}: locator not present in evidence")
        _need(locator not in checked, f"{finding_id}: duplicate evidence locator")
        checked.add(locator)
        for field in ("claim", "observed"):
            value = check.get(field)
            _need(
                isinstance(value, str) and bool(value.strip()),
                f"{finding_id}: evidence {field} required",
            )
        _need(
            check.get("result") == "supports",
            f"{finding_id}: final evidence check must support final finding",
        )
    cited = set(_EVIDENCE_LOCATOR.findall(evidence))
    if cited:
        _need(
            checked == cited,
            f"{finding_id}: every cited code evidence locator must be adjudicated",
        )


def _validate_cell_scope_checks(
    finding_id: str,
    finding: dict[str, Any],
    checks: Any,
) -> None:
    finding_cells = finding.get("cells")
    _need(isinstance(finding_cells, list), f"{finding_id}: cells must be a list")
    _need(
        isinstance(checks, list) and len(checks) == len(finding_cells),
        f"{finding_id}: cell-scope adjudication must cover every affected cell",
    )
    for expected, check in zip(finding_cells, checks, strict=True):
        _need(isinstance(check, dict), f"{finding_id}: invalid cell-scope check")
        _need(
            set(check) == {"cell", "cell_hash", "rationale"},
            f"{finding_id}: unsupported cell-scope check fields",
        )
        _need(
            check.get("cell") == expected.get("cell")
            and check.get("cell_hash") == expected.get("cell_hash"),
            f"{finding_id}: cell-scope check does not match final finding",
        )
        rationale = check.get("rationale")
        _need(
            isinstance(rationale, str) and bool(rationale.strip()),
            f"{finding_id}: affected-cell rationale required",
        )


def _validate_adjudication_row(
    finding: dict[str, Any],
    row: Any,
) -> None:
    finding_id = finding["finding_id"]
    _need(isinstance(row, dict), f"{finding_id}: invalid adjudication row")
    _need(
        set(row)
        == {
            "finding_id",
            "finding_sha256",
            "verdict",
            "evidence_checks",
            "cell_scope_checks",
            "falsifier_check",
        },
        f"{finding_id}: unsupported adjudication fields",
    )
    _need(
        row.get("finding_id") == finding_id,
        f"{finding_id}: adjudication order/identity mismatch",
    )
    _need(
        row.get("finding_sha256") == sha256_canonical_json(finding),
        f"{finding_id}: stale final finding hash",
    )
    _need(
        row.get("verdict") == "confirmed",
        f"{finding_id}: final finding must be independently confirmed",
    )
    _validate_evidence_checks(finding_id, finding, row.get("evidence_checks"))
    _validate_cell_scope_checks(finding_id, finding, row.get("cell_scope_checks"))
    falsifier_check = row.get("falsifier_check")
    _need(
        isinstance(falsifier_check, str) and bool(falsifier_check.strip()),
        f"{finding_id}: falsifier adjudication required",
    )


def validate_review_findings(
    contract: dict[str, Any],
    coverage: dict[str, Any],
    ledger: dict[str, Any],
    adjudication: dict[str, Any],
) -> ReviewFindingReceipt:
    contract_index = _contract_index(contract)
    contract_hash = contract.get("spec_contract_hash")
    _need(
        isinstance(contract_hash, str) and bool(contract_hash),
        "contract: missing Spec Contract Hash",
    )
    findings = _ledger_findings(ledger, contract)
    _need(
        coverage.get("spec_contract_hash") == contract_hash,
        "coverage: stale Spec Contract Hash",
    )
    reviewed_head = coverage.get("reviewed_head")
    _need(
        isinstance(reviewed_head, str)
        and _HEAD.fullmatch(reviewed_head) is not None,
        "coverage: reviewed_head must be one full lowercase commit SHA",
    )
    links = _coverage_links(coverage, findings)
    link_count = 0
    for finding in findings:
        link_count += _validate_finding_cells(
            finding,
            contract_index,
            links,
        )

    _need(
        adjudication.get("schema") == SCHEMA,
        f"adjudication: schema must be {SCHEMA}",
    )
    _need(
        set(adjudication)
        == {"schema", "spec_contract_hash", "reviewed_head", "findings"},
        "adjudication: unsupported top-level fields",
    )
    _need(
        adjudication.get("spec_contract_hash") == contract_hash,
        "adjudication: stale Spec Contract Hash",
    )
    _need(
        adjudication.get("reviewed_head") == reviewed_head,
        "adjudication: stale reviewed HEAD",
    )
    rows = adjudication.get("findings")
    _need(
        isinstance(rows, list) and len(rows) == len(findings),
        "adjudication: finding count does not match final ledger",
    )
    for finding, row in zip(findings, rows, strict=True):
        _validate_adjudication_row(finding, row)

    return ReviewFindingReceipt(
        reviewed_head=reviewed_head,
        spec_contract_hash=contract_hash,
        finding_count=len(findings),
        link_count=link_count,
        adjudication_sha256=sha256_canonical_json(adjudication),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("spec_contract", type=Path)
    validate.add_argument("coverage", type=Path)
    validate.add_argument("findings", type=Path)
    validate.add_argument("adjudication", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        contract = _read_json(args.spec_contract)
        coverage = _read_json(args.coverage)
        findings = _read_json(args.findings)
        adjudication = _read_json(args.adjudication)
        receipt = validate_review_findings(
            contract,
            coverage,
            findings,
            adjudication,
        )
    except (ReviewFindingError, json.JSONDecodeError, OSError) as exc:
        print(f"REVIEW FINDINGS: INVALID\nReason: {exc}")
        return 1

    print("REVIEW FINDINGS: VALID")
    print(f"Reviewed HEAD: {receipt.reviewed_head}")
    print(f"Spec Contract Hash: {receipt.spec_contract_hash}")
    print(
        f"Final findings adjudicated: "
        f"{receipt.finding_count}/{receipt.finding_count}"
    )
    print("Coverage/finding cell links: VALID")
    print("Unchecked cited code evidence locators: 0")
    print(f"Finding-cell links: {receipt.link_count}")
    print(
        f"Finding Adjudication SHA-256: "
        f"{receipt.adjudication_sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
