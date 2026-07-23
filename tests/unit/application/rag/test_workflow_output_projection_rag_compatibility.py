from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from application.projections.workflow_outputs import (
    CompletedRunProjectionSummary,
    WorkflowOutputProjectionOperationsService,
    WorkflowOutputProjectionRequest,
    WorkflowOutputProjectionRetryRequest,
    WorkflowOutputProjectionService,
)
from application.rag.contracts.rag_operation_models import RagIngestOperationRequest
from application.rag.ingestion.curated_rag_document_builder import (
    CuratedRagDocumentBuilder,
)
from application.rag.ingestion.curated_rag_models import (
    CuratedRagBuildOptions,
    CuratedRagSource,
)
from application.rag.ingestion.curated_rag_structured_sources import (
    source_candidate_for_structured_source,
)
from application.rag.ingestion.rag_source_loaders import (
    CuratedRagSourceLoaderRegistry,
    PortfolioRagSourceLoader,
)
from application.rag.operations.rag_ingestion_operations import (
    RagIngestionOperationsService,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.portfolio import (
    PortfolioAllocationSnapshotRecord,
    PortfolioExpansionPersistenceRepository,
    PortfolioRiskSnapshotRecord,
)
from core.storage.persistence.projections import (
    WorkflowOutputProjectionJobRecord,
    WorkflowOutputProjectionJobRepository,
    WorkflowOutputProjectionJobStatus,
)
from core.storage.persistence.rag import (
    RagEligibilitySourceCandidate,
    RagPersistenceRepository,
    RagPersistenceResult,
    RagSourceEligibilityRecord,
    evaluate_default_rag_source_eligibility,
)


class FakePortfolioExpansionRepository:
    def __init__(
        self,
        *,
        risk_records: Sequence[PortfolioRiskSnapshotRecord] = (),
        allocation_records: Sequence[PortfolioAllocationSnapshotRecord] = (),
    ) -> None:
        self._risk_records = tuple(risk_records)
        self._allocation_records = tuple(allocation_records)
        self.risk_calls: list[str] = []
        self.allocation_calls: list[str] = []

    async def list_risk_snapshots(
        self,
        *,
        account_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioRiskSnapshotRecord]:
        self.risk_calls.append(account_id)
        return tuple(
            record
            for record in self._risk_records
            if record.account_id == account_id
            and (start is None or record.timestamp >= start)
            and (end is None or record.timestamp <= end)
        )

    async def list_allocation_snapshots(
        self,
        *,
        account_id: str,
        allocation_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioAllocationSnapshotRecord]:
        self.allocation_calls.append(account_id)
        return tuple(
            record
            for record in self._allocation_records
            if record.account_id == account_id
            and (allocation_type is None or record.allocation_type == allocation_type)
            and (start is None or record.timestamp >= start)
            and (end is None or record.timestamp <= end)
        )


class FakeRagEligibilityRepository:
    def __init__(self, records: Sequence[RagSourceEligibilityRecord]) -> None:
        self._records = tuple(records)
        self.list_calls: list[dict[str, object]] = []

    async def list_source_eligibility(
        self,
        *,
        source_table: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        eligible: bool | None = None,
    ) -> Sequence[RagSourceEligibilityRecord]:
        self.list_calls.append(
            {
                "source_table": source_table,
                "source_id": source_id,
                "source_type": source_type,
                "eligible": eligible,
            }
        )
        return tuple(
            record
            for record in self._records
            if (source_table is None or record.source_table == source_table)
            and (source_id is None or record.source_id == source_id)
            and (source_type is None or record.source_type == source_type)
            and (eligible is None or record.eligible is eligible)
        )


class RecordingCuratedRagIngestion:
    def __init__(self) -> None:
        self.persisted: list[tuple[CuratedRagSource, CuratedRagBuildOptions]] = []

    async def persist_source(
        self,
        source: CuratedRagSource,
        *,
        options: CuratedRagBuildOptions | None = None,
    ) -> RagPersistenceResult:
        self.persisted.append((source, options or CuratedRagBuildOptions()))
        return RagPersistenceResult.succeeded(
            document_id=f"document-{len(self.persisted)}",
            records_persisted=1,
        )


class FakeProjectionService:
    def __init__(self) -> None:
        self.requests: list[WorkflowOutputProjectionRequest] = []

    async def project_completed_run(
        self,
        request: WorkflowOutputProjectionRequest,
    ) -> CompletedRunProjectionSummary:
        self.requests.append(request)
        return CompletedRunProjectionSummary(
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            run_id=request.run_id,
        )


class FakeProjectionJobRepository:
    def __init__(self, jobs: Sequence[WorkflowOutputProjectionJobRecord]) -> None:
        self._jobs = tuple(jobs)
        self.list_calls: list[dict[str, object]] = []
        self.recover_calls: list[tuple[datetime, str]] = []

    async def list_jobs(
        self,
        *,
        run_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        projector_name: str | None = None,
        statuses: Sequence[WorkflowOutputProjectionJobStatus | str] | None = None,
        limit: int | None = None,
    ) -> Sequence[WorkflowOutputProjectionJobRecord]:
        self.list_calls.append(
            {
                "run_id": run_id,
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "projector_name": projector_name,
                "statuses": tuple(statuses or ()),
                "limit": limit,
            }
        )
        return self._jobs[:limit]

    async def recover_stale_running_jobs(
        self,
        *,
        started_before: datetime,
        error: str,
    ) -> int:
        self.recover_calls.append((started_before, error))
        return 0


@pytest.mark.parametrize(
    ("record_kind", "source_table", "source_type"),
    [
        ("risk", "portfolio_risk_snapshots", "portfolio_risk_summary"),
        (
            "allocation",
            "portfolio_allocation_snapshots",
            "portfolio_allocation_summary",
        ),
    ],
)
def test_projected_portfolio_records_satisfy_existing_rag_eligibility_rules(
    record_kind: str,
    source_table: str,
    source_type: str,
) -> None:
    record = _risk_record() if record_kind == "risk" else _allocation_record()
    candidate = source_candidate_for_structured_source(record)
    eligibility = evaluate_default_rag_source_eligibility(candidate)

    assert eligibility.eligible is True
    assert eligibility.source_table == source_table
    assert eligibility.source_type == source_type
    assert eligibility.metadata["rule_name"] == "curated_summary_eligible"
    assert eligibility.metadata["account_id"] == "account-1"
    assert eligibility.metadata["workflow_name"] == "morning_report"
    assert eligibility.metadata["execution_id"] == "execution-1"

    bundle = CuratedRagDocumentBuilder().build_from_source(
        record,
        options=CuratedRagBuildOptions(queue_embedding_jobs=True),
        source_eligibility=eligibility,
    )

    assert bundle.document.source_table == source_table
    assert bundle.document.source_id == eligibility.source_id
    assert bundle.document.source_type == source_type
    assert bundle.document.metadata["curated_source"] is True
    source_kind = bundle.document.metadata["source_kind"]
    assert isinstance(source_kind, str)
    assert source_kind.startswith("portfolio_")
    assert len(bundle.chunks) > 0
    assert len(bundle.embedding_jobs) == len(bundle.chunks)


def test_raw_completed_run_outputs_remain_ineligible_for_rag() -> None:
    raw_runtime_candidate = RagEligibilitySourceCandidate(
        source_table="workflow_node_runs",
        source_id="node-output-1",
        source_type="runtime_node_run",
    )

    eligibility = evaluate_default_rag_source_eligibility(raw_runtime_candidate)

    assert eligibility.eligible is False
    assert eligibility.metadata["rule_name"] == "raw_runtime_ineligible"

    raw_payload = cast(CuratedRagSource, {"node_outputs": {"portfolio": {}}})
    with pytest.raises(TypeError, match="curated PostgreSQL source records"):
        CuratedRagDocumentBuilder().build_from_source(raw_payload)


@pytest.mark.asyncio
async def test_rag_ingestion_loads_projected_portfolio_records_from_curated_postgres_sources() -> (  # noqa: E501
    None
):
    risk = _risk_record()
    allocation = _allocation_record()
    eligibilities = tuple(
        evaluate_default_rag_source_eligibility(
            source_candidate_for_structured_source(record)
        )
        for record in (risk, allocation)
    )
    portfolio_repository = FakePortfolioExpansionRepository(
        risk_records=(risk,),
        allocation_records=(allocation,),
    )
    rag_repository = FakeRagEligibilityRepository(eligibilities)
    ingestion = RecordingCuratedRagIngestion()
    loader_registry = CuratedRagSourceLoaderRegistry(
        (
            PortfolioRagSourceLoader(
                cast(PortfolioExpansionPersistenceRepository, portfolio_repository)
            ),
        )
    )
    service = RagIngestionOperationsService(
        rag_repository=cast(RagPersistenceRepository, rag_repository),
        source_loader_registry=loader_registry,
        ingestion_service=ingestion,
    )

    result = await service.ingest(
        RagIngestOperationRequest(
            source="portfolio",
            queue_embedding_jobs=False,
            queue_graph_jobs=False,
        )
    )

    assert result.success is True
    assert result.records_processed == 2
    assert [type(source) for source, _options in ingestion.persisted] == [
        PortfolioRiskSnapshotRecord,
        PortfolioAllocationSnapshotRecord,
    ]
    assert all(
        options.require_source_eligibility for _source, options in ingestion.persisted
    )
    assert all(
        not options.queue_embedding_jobs for _source, options in ingestion.persisted
    )
    assert rag_repository.list_calls == [
        {
            "source_table": "portfolio_risk_snapshots",
            "source_id": None,
            "source_type": None,
            "eligible": True,
        },
        {
            "source_table": "portfolio_allocation_snapshots",
            "source_id": None,
            "source_type": None,
            "eligible": True,
        },
    ]
    assert portfolio_repository.risk_calls == ["account-1"]
    assert portfolio_repository.allocation_calls == ["account-1"]


@pytest.mark.asyncio
async def test_projection_retry_replays_projection_without_triggering_rag_ingestion() -> (  # noqa: E501
    None
):
    job = WorkflowOutputProjectionJobRecord(
        projection_job_id="projection-job-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="execution-1",
        node_name="portfolio_state_builder",
        projector_name="portfolio_workflow_output_projector",
        output_contract="polaris.portfolio.state",
        output_schema_version=1,
        source_fingerprint="fingerprint-1",
        status=WorkflowOutputProjectionJobStatus.FAILED,
    )
    projection_service = FakeProjectionService()
    repository = FakeProjectionJobRepository((job,))
    service = WorkflowOutputProjectionOperationsService(
        projection_service=cast(WorkflowOutputProjectionService, projection_service),
        projection_job_repository=cast(
            WorkflowOutputProjectionJobRepository, repository
        ),
    )

    result = await service.retry_projection(
        WorkflowOutputProjectionRetryRequest(
            workflow_name="morning_report",
            statuses=(WorkflowOutputProjectionJobStatus.FAILED,),
            limit=10,
        )
    )

    assert result.matched_jobs == 1
    assert result.retried_jobs == 1
    assert projection_service.requests == [
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="execution-1",
            run_id="run-1",
            requested_at=result.requested.requested_at,
            force_reproject=False,
        )
    ]
    assert repository.recover_calls == []


def test_projection_layer_has_no_rag_or_external_projection_dependencies() -> None:
    forbidden_tokens = (
        "application.rag",
        "qdrant",
        "neo4j",
        "rerank",
        "embedding",
        "Rag",
    )
    paths = tuple(Path("application/projections/workflow_outputs").glob("**/*.py")) + (
        Path(
            "core/storage/persistence/repositories/"
            "postgres_workflow_output_projection_job_repository.py"
        ),
    )

    violations: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path}:{token}")

    assert violations == []


def _timestamp() -> datetime:
    return datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="execution-1",
        runtime_id="runtime-1",
        node_name="portfolio_state_builder",
    )


def _risk_record() -> PortfolioRiskSnapshotRecord:
    return PortfolioRiskSnapshotRecord(
        risk_snapshot_id="risk-1",
        account_id="account-1",
        timestamp=_timestamp(),
        lineage=_lineage(),
        account_health="healthy",
        risk_level="moderate",
        risk_score=0.31,
        risk_signals={"summary": "risk within limits"},
    )


def _allocation_record() -> PortfolioAllocationSnapshotRecord:
    return PortfolioAllocationSnapshotRecord(
        allocation_snapshot_id="allocation-1",
        account_id="account-1",
        timestamp=_timestamp(),
        allocation_type="sector",
        allocation_name="technology",
        current_weight=0.24,
        lineage=_lineage(),
        target_weight=0.22,
        drift=0.02,
    )
