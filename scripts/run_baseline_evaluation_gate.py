from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

PASSED_STATUS = "passed"


class EvaluationGateService(Protocol):
    async def status(self) -> Any: ...

    async def seed_datasets(
        self,
        dataset_name: str | None = None,
        *,
        dry_run: bool = False,
    ) -> Any: ...

    async def list_datasets(self) -> Any: ...

    async def run_dataset(self, dataset_name: str) -> Any: ...


class AiObservabilityGateService(Protocol):
    async def ai_status(self) -> Any: ...


@dataclass(frozen=True, slots=True)
class ReleaseGateOptions:
    datasets: tuple[str, ...]
    skip_seed: bool = False
    skip_live_evaluation: bool = False
    check_ai_observability: bool = False


@dataclass(frozen=True, slots=True)
class DatasetSeedExpectation:
    name: str
    dataset_id: str
    expected_case_count: int


async def run_release_gate(
    options: ReleaseGateOptions,
    *,
    evaluation_service: EvaluationGateService | None = None,
    ai_observability_service: AiObservabilityGateService | None = None,
) -> int:
    """Run the golden-dataset release gate.

    The gate intentionally uses the same CLI-facing services as humans use from
    ``polaris eval`` so it validates the canonical application path without
    duplicating evaluation or persistence behavior.
    """

    evaluator = evaluation_service or _default_evaluation_service()
    datasets = options.datasets or _canonical_dataset_names()
    print("Polaris Golden Dataset Release Gate")
    print(f"Datasets: {', '.join(datasets)}")

    status = await evaluator.status()
    if not _truthy_attr(status, "enabled") or not _truthy_attr(status, "configured"):
        print(
            "Evaluation configuration check failed: "
            f"{getattr(status, 'message', 'DeepEval is not configured.')}"
        )
        return 1

    expectations = await _resolve_seed_expectations(evaluator, datasets)
    if expectations is None:
        return 1

    if not options.skip_seed:
        if not await _seed_selected_datasets(evaluator, datasets):
            return 1
    else:
        print("Skipping PostgreSQL seed writes.")

    if not await _verify_persisted_counts(evaluator, expectations):
        return 1

    if options.check_ai_observability:
        observer = ai_observability_service or _default_ai_observability_service()
        if not await _verify_ai_observability(observer):
            return 1

    if not options.skip_live_evaluation:
        if not await _run_live_benchmark(evaluator, datasets):
            return 1
    else:
        print("Skipping live DeepEval execution.")

    print("Release gate passed.")
    return 0


async def _resolve_seed_expectations(
    evaluator: EvaluationGateService,
    datasets: Sequence[str],
) -> tuple[DatasetSeedExpectation, ...] | None:
    expectations: list[DatasetSeedExpectation] = []
    for dataset_name in datasets:
        result = await evaluator.seed_datasets(dataset_name, dry_run=True)
        if (
            not getattr(result, "success", False)
            or getattr(result, "seed_result", None) is None
        ):
            print(
                f"Dry-run seed failed for {dataset_name}: "
                f"{getattr(result, 'error', 'unknown error')}"
            )
            return None
        seed_result = result.seed_result
        items = tuple(getattr(seed_result, "items", ()))
        if len(items) != 1:
            print(
                f"Dry-run seed for {dataset_name} returned {len(items)} datasets; "
                "expected exactly 1."
            )
            return None
        item = items[0]
        expectations.append(
            DatasetSeedExpectation(
                name=str(item.name),
                dataset_id=str(item.dataset_id),
                expected_case_count=int(item.case_count),
            )
        )
    expected_total = sum(item.expected_case_count for item in expectations)
    print(f"Fixture expectation: {len(expectations)} datasets, {expected_total} cases")
    return tuple(expectations)


async def _seed_selected_datasets(
    evaluator: EvaluationGateService,
    datasets: Sequence[str],
) -> bool:
    for dataset_name in datasets:
        result = await evaluator.seed_datasets(dataset_name, dry_run=False)
        if (
            not getattr(result, "success", False)
            or getattr(result, "seed_result", None) is None
        ):
            print(
                f"PostgreSQL seed failed for {dataset_name}: "
                f"{getattr(result, 'error', 'unknown error')}"
            )
            return False
        seed_result = result.seed_result
        print(
            f"Seeded {dataset_name}: "
            f"{getattr(seed_result, 'case_count', 0)} fixture cases"
        )
    return True


async def _verify_persisted_counts(
    evaluator: EvaluationGateService,
    expectations: Sequence[DatasetSeedExpectation],
) -> bool:
    result = await evaluator.list_datasets()
    if not getattr(result, "success", False):
        print(f"Dataset listing failed: {getattr(result, 'error', 'unknown error')}")
        return False

    persisted_by_name = {str(item.name): item for item in result.items}
    passed = True
    for expectation in expectations:
        persisted = persisted_by_name.get(expectation.name)
        if persisted is None:
            print(f"Persisted dataset missing: {expectation.name}")
            passed = False
            continue
        persisted_count = getattr(persisted, "persisted_case_count", None)
        if persisted_count != expectation.expected_case_count:
            print(
                "Persisted count mismatch for "
                f"{expectation.name}: expected {expectation.expected_case_count}, "
                f"found {persisted_count}"
            )
            passed = False
            continue
        if not getattr(persisted, "persisted", False):
            print(f"Dataset was not persisted: {expectation.name}")
            passed = False
            continue
        print(f"Verified {expectation.name}: {persisted_count} persisted cases")
    return passed


async def _verify_ai_observability(observer: AiObservabilityGateService) -> bool:
    status = await observer.ai_status()
    if not _truthy_attr(status, "healthy"):
        reasons = ", ".join(str(reason) for reason in getattr(status, "reasons", ()))
        print(f"AI observability is not healthy: {reasons or 'no reason reported'}")
        return False
    print("AI observability status is healthy.")
    return True


async def _run_live_benchmark(
    evaluator: EvaluationGateService,
    datasets: Sequence[str],
) -> bool:
    passed = True
    for dataset_name in datasets:
        result = await evaluator.run_dataset(dataset_name)
        if not getattr(result, "success", False):
            print(
                f"DeepEval run command failed for {dataset_name}: "
                f"{getattr(result, 'error', 'unknown error')}"
            )
            passed = False
            continue
        run_id = getattr(result, "run_id", None)
        run_status = getattr(result, "run_status", None)
        print(f"DeepEval run {dataset_name}: run_id={run_id} status={run_status}")
        if run_status != PASSED_STATUS:
            passed = False
    return passed


def _truthy_attr(value: Any, attr: str) -> bool:
    return bool(getattr(value, attr, False))


def _canonical_dataset_names() -> tuple[str, ...]:
    from application.evaluations import canonical_evaluation_dataset_definitions

    return tuple(
        definition.reference.name
        for definition in canonical_evaluation_dataset_definitions()
    )


def _default_evaluation_service() -> EvaluationGateService:
    from interfaces.cli.services.evaluation_command_service import (
        EvaluationCommandService,
    )

    return EvaluationCommandService()


def _default_ai_observability_service() -> AiObservabilityGateService:
    from interfaces.cli.services.observability_command_service import (
        ObservabilityCommandService,
    )

    return ObservabilityCommandService()


def _parse_args(argv: Sequence[str] | None = None) -> ReleaseGateOptions:
    parser = argparse.ArgumentParser(
        description="Run the Polaris golden-dataset release gate."
    )
    parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        default=[],
        help="Canonical dataset name to gate. May be supplied more than once. Defaults to all canonical datasets.",  # noqa: E501
    )
    parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Do not write fixture records to PostgreSQL before verification.",
    )
    parser.add_argument(
        "--skip-live-evaluation",
        action="store_true",
        help="Verify seeding and persisted counts without running DeepEval.",
    )
    parser.add_argument(
        "--check-ai-observability",
        action="store_true",
        help="Fail the gate if the Langfuse AI-observability queue is unhealthy.",
    )
    args = parser.parse_args(argv)
    return ReleaseGateOptions(
        datasets=tuple(args.datasets),
        skip_seed=bool(args.skip_seed),
        skip_live_evaluation=bool(args.skip_live_evaluation),
        check_ai_observability=bool(args.check_ai_observability),
    )


async def _main(argv: Sequence[str] | None = None) -> int:
    return await run_release_gate(_parse_args(argv))


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return asyncio.run(_main(argv))
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"Release gate failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
