from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from application.evaluations.contracts import (
    EvaluationDatasetRegistrationRequest,
    EvaluationDatasetSeedItem,
    EvaluationDatasetSeedRequest,
    EvaluationDatasetSeedResult,
)
from application.evaluations.evaluation_datasets import (
    EvaluationDatasetDefinition,
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_definitions,
)
from core.storage.persistence.evaluation import (
    EvaluationCaseRecord,
    EvaluationDatasetCaseReplacement,
    EvaluationDatasetRecord,
    EvaluationPersistenceBundle,
    EvaluationPersistenceRepository,
)
from domain.evaluation import EvaluationTargetType

JsonRow = Mapping[str, object]
_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class EvaluationDatasetService:
    """Register, load, and seed canonical evaluation dataset records."""

    repository: EvaluationPersistenceRepository

    async def register_dataset(
        self,
        request: EvaluationDatasetRegistrationRequest,
    ) -> EvaluationDatasetRecord:
        record = _dataset_record_from_registration_request(request)
        return await self.repository.upsert_dataset(record)

    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None:
        return await self.repository.get_dataset(dataset_id)

    async def seed_canonical_datasets(
        self,
        request: EvaluationDatasetSeedRequest,
    ) -> EvaluationDatasetSeedResult:
        """Seed canonical dataset and case records from deterministic fixtures."""

        definitions = _resolve_seed_definitions(request.dataset_name)
        dataset_records: list[EvaluationDatasetRecord] = []
        case_records: list[EvaluationCaseRecord] = []
        case_replacements: list[EvaluationDatasetCaseReplacement] = []
        items: list[EvaluationDatasetSeedItem] = []
        for definition in definitions:
            fixture_uri = _require_fixture_uri(definition)
            fixture_path = _resolve_fixture_path(fixture_uri)
            rows = _load_jsonl_rows(fixture_path)
            dataset_record = _dataset_record_from_registration_request(
                definition.to_registration_request()
            )
            records = tuple(
                _case_record_from_fixture_row(row, definition) for row in rows
            )
            dataset_records.append(dataset_record)
            case_records.extend(records)
            case_replacements.append(
                EvaluationDatasetCaseReplacement(
                    dataset_id=dataset_record.dataset_id,
                    case_ids=tuple(record.case_id for record in records),
                )
            )
            items.append(
                EvaluationDatasetSeedItem(
                    name=definition.reference.name,
                    dataset_id=definition.reference.dataset_id,
                    fixture_uri=fixture_uri,
                    case_count=len(records),
                    persisted=not request.dry_run,
                )
            )
        if request.dry_run:
            return EvaluationDatasetSeedResult(
                dry_run=True,
                items=tuple(items),
            )
        persistence_result = await self.repository.persist_evaluation_bundle(
            EvaluationPersistenceBundle(
                datasets=tuple(dataset_records),
                cases=tuple(case_records),
                dataset_case_replacements=tuple(case_replacements),
            )
        )
        return EvaluationDatasetSeedResult(
            dry_run=False,
            items=tuple(items),
            datasets_written=persistence_result.datasets_written,
            cases_written=persistence_result.cases_written,
        )


def _resolve_seed_definitions(
    dataset_name: str | None,
) -> tuple[EvaluationDatasetDefinition, ...]:
    if dataset_name is None:
        return canonical_evaluation_dataset_definitions()
    return (canonical_evaluation_dataset_definition_by_name(dataset_name),)


def _dataset_record_from_registration_request(
    request: EvaluationDatasetRegistrationRequest,
) -> EvaluationDatasetRecord:
    record = EvaluationDatasetRecord.from_reference(
        request.reference,
        target_type=request.target_type,
        description=request.description,
        source_lineage=request.source_lineage,
        deterministic_fixture_uri=request.deterministic_fixture_uri,
        threshold_profile=request.threshold_profile,
    )
    if record.active == request.active:
        return record
    return EvaluationDatasetRecord(
        dataset_id=record.dataset_id,
        name=record.name,
        version=record.version,
        target_type=record.target_type,
        description=record.description,
        tags=record.tags,
        source_lineage=record.source_lineage,
        deterministic_fixture_uri=record.deterministic_fixture_uri,
        threshold_profile=record.threshold_profile,
        active=request.active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _require_fixture_uri(definition: EvaluationDatasetDefinition) -> str:
    if definition.deterministic_fixture_uri is None:
        raise ValueError(
            f"Canonical dataset {definition.reference.name} has no fixture URI."
        )
    return definition.deterministic_fixture_uri


def _resolve_fixture_path(fixture_uri: str) -> Path:
    path = Path(fixture_uri)
    if path.is_absolute():
        return path
    return _REPO_ROOT / path


def _load_jsonl_rows(path: Path) -> tuple[JsonRow, ...]:
    rows: list[JsonRow] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            cleaned = line.strip()
            if not cleaned:
                continue
            parsed = json.loads(cleaned)
            if not isinstance(parsed, dict):
                raise ValueError(f"{path}:{line_number} must contain a JSON object.")
            rows.append(cast(JsonRow, parsed))
    return tuple(rows)


def _case_record_from_fixture_row(
    row: JsonRow,
    definition: EvaluationDatasetDefinition,
) -> EvaluationCaseRecord:
    target_type = EvaluationTargetType(_required_str(row, "target_type"))
    if target_type is not definition.target_type:
        raise ValueError(
            f"Case {_required_str(row, 'case_id')} has target_type "
            f"{target_type.value}, expected {definition.target_type.value}."
        )
    return EvaluationCaseRecord(
        case_id=_required_str(row, "case_id"),
        target_type=target_type,
        input_text=_required_str(row, "input_text"),
        actual_output=_required_str(row, "actual_output"),
        dataset_id=definition.reference.dataset_id,
        expected_output=_optional_str(row, "expected_output"),
        rubric=_optional_str(row, "rubric"),
        source_record_ids=_string_tuple(row, "source_record_ids"),
        workflow_execution_id=_optional_str(row, "workflow_execution_id"),
        langfuse_trace_id=_optional_str(row, "langfuse_trace_id"),
        langfuse_observation_id=_optional_str(row, "langfuse_observation_id"),
        retrieval_context=_string_tuple(row, "retrieval_context"),
        citation_context_ids=_string_tuple(row, "citation_context_ids"),
        tags=_string_tuple(row, "tags"),
    )


def _required_str(row: JsonRow, key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()


def _optional_str(row: JsonRow, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string when provided.")
    return value.strip()


def _string_tuple(row: JsonRow, key: str) -> tuple[str, ...]:
    value = row.get(key, ())
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list of strings when provided.")
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key} must contain only non-empty strings.")
        cleaned.append(item.strip())
    return tuple(cleaned)
