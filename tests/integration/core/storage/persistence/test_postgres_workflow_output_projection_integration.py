from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from application.persistence.portfolio import PortfolioPersistenceService
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionOperationsService,
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectionRequest,
    WorkflowOutputProjectionRetryRequest,
    WorkflowOutputProjectionService,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRegistration,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projectors import (
    build_portfolio_state_projector_registration,
)
from core.database.models.completed_runs import CompletedWorkflowRunModel
from core.database.models.portfolio import (
    PortfolioAllocationSnapshotModel,
    PortfolioEquityHistoryPointModel,
    PortfolioExposureSnapshotModel,
    PortfolioPositionHistoryModel,
    PortfolioPositionLatestModel,
    PortfolioRiskSnapshotModel,
)
from core.database.models.portfolio_state import (
    PortfolioStateHistoryModel,
    PortfolioStateLatestModel,
)
from core.database.models.projections import WorkflowOutputProjectionJobModel
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunBundle,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    JsonObject,
)
from core.storage.persistence.postgres_completed_run_archive import (
    PostgresCompletedRunArchive,
)
from core.storage.persistence.projections import WorkflowOutputProjectionJobStatus
from core.storage.persistence.repositories.postgres_portfolio_expansion_persistence_repository import (  # noqa: E501
    PostgresPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_portfolio_state_repository import (
    PostgresPortfolioStateRepository,
)
from core.storage.persistence.repositories.postgres_workflow_output_projection_job_repository import (  # noqa: E501
    PostgresWorkflowOutputProjectionJobRepository,
)
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    SourceOfTruthCategory,
    classify_risk_authority,
)
from domain.workflow_outputs import (
    PORTFOLIO_STATE_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "POLARIS_TEST_DATABASE_URL is required for PostgreSQL workflow-output "
        "projection integration tests."
    ),
)

_TEST_OUTPUT_CONTRACT = "polaris.test.workflow_output_projection"
_FAILING_OUTPUT_CONTRACT = "polaris.test.workflow_output_projection.failure"
_TEST_PROJECTOR_NAME = "postgres_integration_test_projector"
_FAILING_PROJECTOR_NAME = "postgres_integration_failing_projector"


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    yield session_factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_projection_persists_portfolio_records_once_and_skips_backtest(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workflow_name = _unique_name("projection_portfolio")
    account_id = _unique_name("account")
    backtest_account_id = _unique_name("backtest-account")
    execution_id = _unique_name("exec")
    backtest_execution_id = _unique_name("backtest-exec")
    run_id = _unique_name("run")
    backtest_run_id = _unique_name("backtest-run")

    try:
        await _archive_bundle(
            postgres_session_factory,
            _bundle(
                run_id=run_id,
                workflow_name=workflow_name,
                execution_id=execution_id,
                account_id=account_id,
                execution_mode=CompletedRunExecutionMode.NORMAL,
            ),
        )

        async with postgres_session_factory() as session:
            service = _portfolio_projection_service(session, postgres_session_factory)
            first = await service.project_completed_run(
                WorkflowOutputProjectionRequest(
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                )
            )

        assert first.success is True
        assert first.succeeded_jobs == 1
        assert first.failed_jobs == 0
        assert first.records_written == 25

        async with postgres_session_factory() as session:
            await _assert_portfolio_counts(
                session,
                account_id=account_id,
                state_history=1,
                state_latest=1,
                equity_history=2,
                position_history=2,
                position_latest=2,
                exposures=12,
                risk=1,
                allocations=5,
            )
            assert (
                await _projection_job_count(
                    session,
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                    status=WorkflowOutputProjectionJobStatus.SUCCEEDED,
                )
                == 1
            )

        async with postgres_session_factory() as session:
            service = _portfolio_projection_service(session, postgres_session_factory)
            duplicate = await service.project_completed_run(
                WorkflowOutputProjectionRequest(
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                )
            )

        assert duplicate.success is True
        assert duplicate.succeeded_jobs == 0
        assert duplicate.skipped_jobs == 1

        async with postgres_session_factory() as session:
            await _assert_portfolio_counts(
                session,
                account_id=account_id,
                state_history=1,
                state_latest=1,
                equity_history=2,
                position_history=2,
                position_latest=2,
                exposures=12,
                risk=1,
                allocations=5,
            )

        await _archive_bundle(
            postgres_session_factory,
            _bundle(
                run_id=backtest_run_id,
                workflow_name=workflow_name,
                execution_id=backtest_execution_id,
                account_id=backtest_account_id,
                execution_mode=CompletedRunExecutionMode.BACKTEST,
            ),
        )

        async with postgres_session_factory() as session:
            service = _portfolio_projection_service(session, postgres_session_factory)
            backtest = await service.project_completed_run(
                WorkflowOutputProjectionRequest(
                    workflow_name=workflow_name,
                    execution_id=backtest_execution_id,
                )
            )

        assert backtest.success is True
        assert backtest.total_jobs == 1
        assert backtest.skipped_jobs == 1

        async with postgres_session_factory() as session:
            assert (
                await _projection_job_count(
                    session,
                    workflow_name=workflow_name,
                    execution_id=backtest_execution_id,
                )
                == 0
            )
            await _assert_portfolio_counts(
                session,
                account_id=backtest_account_id,
                state_history=0,
                state_latest=0,
                equity_history=0,
                position_history=0,
                position_latest=0,
                exposures=0,
                risk=0,
                allocations=0,
            )
    finally:
        await _cleanup_projection_test_data(
            postgres_session_factory,
            workflow_name=workflow_name,
            execution_ids=(execution_id, backtest_execution_id),
            account_ids=(account_id, backtest_account_id),
        )


@pytest.mark.asyncio
async def test_postgres_projection_isolates_projector_failure_and_keeps_valid_outputs(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workflow_name = _unique_name("projection_failure")
    execution_id = _unique_name("exec")
    run_id = _unique_name("run")
    account_id = _unique_name("account")

    try:
        await _archive_bundle(
            postgres_session_factory,
            _bundle(
                run_id=run_id,
                workflow_name=workflow_name,
                execution_id=execution_id,
                account_id=account_id,
                extra_nodes=(
                    _test_node(
                        run_id=run_id,
                        workflow_name=workflow_name,
                        execution_id=execution_id,
                        node_name="failing_projection_node",
                        output_contract=_FAILING_OUTPUT_CONTRACT,
                    ),
                ),
            ),
        )

        async with postgres_session_factory() as session:
            service = _projection_service(
                session,
                postgres_session_factory,
                registrations=(
                    _portfolio_registration(session),
                    _test_registration(
                        projector=ToggleProjector(
                            projector_name=_FAILING_PROJECTOR_NAME,
                            output_contract=_FAILING_OUTPUT_CONTRACT,
                            should_fail=True,
                        ),
                        output_contract=_FAILING_OUTPUT_CONTRACT,
                        projector_name=_FAILING_PROJECTOR_NAME,
                        node_name="failing_projection_node",
                    ),
                ),
            )
            summary = await service.project_completed_run(
                WorkflowOutputProjectionRequest(
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                )
            )

        assert summary.success is False
        assert summary.succeeded_jobs == 1
        assert summary.failed_jobs == 1
        assert summary.records_written == 25

        async with postgres_session_factory() as session:
            await _assert_portfolio_counts(
                session,
                account_id=account_id,
                state_history=1,
                state_latest=1,
                equity_history=2,
                position_history=2,
                position_latest=2,
                exposures=12,
                risk=1,
                allocations=5,
            )
            assert (
                await _projection_job_count(
                    session,
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                    status=WorkflowOutputProjectionJobStatus.SUCCEEDED,
                )
                == 1
            )
            assert (
                await _projection_job_count(
                    session,
                    workflow_name=workflow_name,
                    execution_id=execution_id,
                    status=WorkflowOutputProjectionJobStatus.FAILED,
                )
                == 1
            )
    finally:
        await _cleanup_projection_test_data(
            postgres_session_factory,
            workflow_name=workflow_name,
            execution_ids=(execution_id,),
            account_ids=(account_id,),
        )


@pytest.mark.asyncio
async def test_postgres_projection_retries_failed_jobs_and_recovers_stale_running_jobs(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    workflow_name = _unique_name("projection_retry")
    failed_execution_id = _unique_name("failed-exec")
    stale_execution_id = _unique_name("stale-exec")
    failed_run_id = _unique_name("failed-run")
    stale_run_id = _unique_name("stale-run")

    try:
        await _archive_bundle(
            postgres_session_factory,
            _custom_bundle(
                run_id=failed_run_id,
                workflow_name=workflow_name,
                execution_id=failed_execution_id,
                node_name="retry_projection_node",
                output_contract=_TEST_OUTPUT_CONTRACT,
            ),
        )

        async with postgres_session_factory() as session:
            failing_service = _projection_service(
                session,
                postgres_session_factory,
                registrations=(
                    _test_registration(
                        projector=ToggleProjector(should_fail=True),
                        output_contract=_TEST_OUTPUT_CONTRACT,
                        projector_name=_TEST_PROJECTOR_NAME,
                        node_name="retry_projection_node",
                    ),
                ),
            )
            failed_summary = await failing_service.project_completed_run(
                WorkflowOutputProjectionRequest(
                    workflow_name=workflow_name,
                    execution_id=failed_execution_id,
                )
            )

        assert failed_summary.success is False
        assert failed_summary.failed_jobs == 1

        async with postgres_session_factory() as session:
            repository = PostgresWorkflowOutputProjectionJobRepository(session)
            operations = WorkflowOutputProjectionOperationsService(
                projection_service=_projection_service(
                    session,
                    postgres_session_factory,
                    registrations=(
                        _test_registration(
                            projector=ToggleProjector(records_written=1),
                            output_contract=_TEST_OUTPUT_CONTRACT,
                            projector_name=_TEST_PROJECTOR_NAME,
                            node_name="retry_projection_node",
                        ),
                    ),
                ),
                projection_job_repository=repository,
            )
            retry = await operations.retry_projection(
                WorkflowOutputProjectionRetryRequest(
                    workflow_name=workflow_name,
                    execution_id=failed_execution_id,
                    statuses=(WorkflowOutputProjectionStatus.FAILED,),
                )
            )

        assert retry.matched_jobs == 1
        assert retry.retried_jobs == 1
        assert retry.summaries[0].succeeded_jobs == 1
        assert retry.summaries[0].records_written == 1

        async with postgres_session_factory() as session:
            jobs = await PostgresWorkflowOutputProjectionJobRepository(
                session
            ).list_jobs(
                workflow_name=workflow_name,
                execution_id=failed_execution_id,
            )
            assert len(jobs) == 1
            assert jobs[0].status is WorkflowOutputProjectionJobStatus.SUCCEEDED
            assert jobs[0].attempt_count == 2

        await _archive_bundle(
            postgres_session_factory,
            _custom_bundle(
                run_id=stale_run_id,
                workflow_name=workflow_name,
                execution_id=stale_execution_id,
                node_name="stale_projection_node",
                output_contract=_TEST_OUTPUT_CONTRACT,
            ),
        )

        async with postgres_session_factory() as session:
            service = _projection_service(
                session,
                postgres_session_factory,
                registrations=(
                    _test_registration(
                        projector=ToggleProjector(records_written=1),
                        output_contract=_TEST_OUTPUT_CONTRACT,
                        projector_name=_TEST_PROJECTOR_NAME,
                        node_name="stale_projection_node",
                    ),
                ),
            )
            first = await service.project_completed_run(
                WorkflowOutputProjectionRequest(
                    workflow_name=workflow_name,
                    execution_id=stale_execution_id,
                )
            )
            assert first.succeeded_jobs == 1
            await session.execute(
                update(WorkflowOutputProjectionJobModel)
                .where(
                    WorkflowOutputProjectionJobModel.workflow_name == workflow_name,
                    WorkflowOutputProjectionJobModel.execution_id == stale_execution_id,
                )
                .values(
                    status=WorkflowOutputProjectionJobStatus.RUNNING.value,
                    started_at=datetime.now(UTC) - timedelta(hours=1),
                    completed_at=None,
                    last_error=None,
                )
            )
            await session.commit()

            operations = WorkflowOutputProjectionOperationsService(
                projection_service=service,
                projection_job_repository=PostgresWorkflowOutputProjectionJobRepository(
                    session
                ),
            )
            recovered = await operations.retry_projection(
                WorkflowOutputProjectionRetryRequest(
                    workflow_name=workflow_name,
                    execution_id=stale_execution_id,
                    statuses=(WorkflowOutputProjectionStatus.FAILED,),
                    stale_running_started_before=datetime.now(UTC)
                    - timedelta(minutes=1),
                )
            )

        assert recovered.recovered_stale_running_jobs == 1
        assert recovered.matched_jobs == 1
        assert recovered.retried_jobs == 1
        assert recovered.summaries[0].succeeded_jobs == 1

        async with postgres_session_factory() as session:
            jobs = await PostgresWorkflowOutputProjectionJobRepository(
                session
            ).list_jobs(
                workflow_name=workflow_name,
                execution_id=stale_execution_id,
            )
            assert len(jobs) == 1
            assert jobs[0].status is WorkflowOutputProjectionJobStatus.SUCCEEDED
            assert jobs[0].attempt_count == 2
    finally:
        await _cleanup_projection_test_data(
            postgres_session_factory,
            workflow_name=workflow_name,
            execution_ids=(failed_execution_id, stale_execution_id),
            account_ids=(),
        )


@dataclass(frozen=True, slots=True)
class ToggleProjector:
    projector_name: str = _TEST_PROJECTOR_NAME
    output_contract: str = _TEST_OUTPUT_CONTRACT
    should_fail: bool = False
    records_written: int = 0

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        if self.should_fail:
            raise RuntimeError("Intentional projection failure for integration test.")
        return WorkflowOutputProjectionOutcome(
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            projector_name=self.projector_name,
            node_name=request.node_output.node_name,
            output_contract=self.output_contract,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            source_fingerprint=request.source_fingerprint,
            records_written=self.records_written,
            message="PostgreSQL integration test projection succeeded.",
        )


def _portfolio_projection_service(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> WorkflowOutputProjectionService:
    return _projection_service(
        session,
        session_factory,
        registrations=(_portfolio_registration(session),),
    )


def _projection_service(
    session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    registrations: tuple[WorkflowOutputProjectorRegistration, ...],
) -> WorkflowOutputProjectionService:
    return WorkflowOutputProjectionService(
        completed_run_archive=PostgresCompletedRunArchive(session_factory),
        projection_job_repository=PostgresWorkflowOutputProjectionJobRepository(
            session
        ),
        registry=WorkflowOutputProjectionRegistry(registrations),
    )


def _portfolio_registration(
    session: AsyncSession,
) -> WorkflowOutputProjectorRegistration:
    return build_portfolio_state_projector_registration(
        PortfolioPersistenceService(
            PostgresPortfolioExpansionPersistenceRepository(session),
            PostgresPortfolioStateRepository(session),
        ),
    )


def _test_registration(
    *,
    projector: ToggleProjector,
    output_contract: str,
    projector_name: str,
    node_name: str,
) -> WorkflowOutputProjectorRegistration:
    return WorkflowOutputProjectorRegistration(
        projector_name=projector_name,
        output_contract=output_contract,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        projector=projector,
        supported_node_names=(node_name,),
    )


async def _archive_bundle(
    session_factory: async_sessionmaker[AsyncSession],
    bundle: CompletedRunBundle,
) -> None:
    await PostgresCompletedRunArchive(session_factory).archive_run(bundle)


def _bundle(
    *,
    run_id: str,
    workflow_name: str,
    execution_id: str,
    account_id: str,
    execution_mode: CompletedRunExecutionMode = CompletedRunExecutionMode.NORMAL,
    extra_nodes: tuple[CompletedNodeOutputRecord, ...] = (),
) -> CompletedRunBundle:
    nodes = (
        _portfolio_node(
            run_id=run_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            account_id=account_id,
        ),
        *extra_nodes,
    )
    return CompletedRunBundle(
        run=_run(
            run_id=run_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            execution_mode=execution_mode,
            node_count=len(nodes),
            completed_node_count=len(nodes),
        ),
        node_outputs=nodes,
    )


def _custom_bundle(
    *,
    run_id: str,
    workflow_name: str,
    execution_id: str,
    node_name: str,
    output_contract: str,
) -> CompletedRunBundle:
    return CompletedRunBundle(
        run=_run(
            run_id=run_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            execution_mode=CompletedRunExecutionMode.NORMAL,
            node_count=1,
            completed_node_count=1,
        ),
        node_outputs=(
            _test_node(
                run_id=run_id,
                workflow_name=workflow_name,
                execution_id=execution_id,
                node_name=node_name,
                output_contract=output_contract,
            ),
        ),
    )


def _run(
    *,
    run_id: str,
    workflow_name: str,
    execution_id: str,
    execution_mode: CompletedRunExecutionMode,
    node_count: int,
    completed_node_count: int,
) -> CompletedRunRecord:
    return CompletedRunRecord(
        run_id=run_id,
        workflow_name=workflow_name,
        workflow_id=f"workflow-{run_id}",
        execution_id=execution_id,
        runtime_id=f"runtime-{run_id}",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 35, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=node_count,
        completed_node_count=completed_node_count,
        failed_node_count=0,
        execution_mode=execution_mode,
    )


def _portfolio_node(
    *,
    run_id: str,
    workflow_name: str,
    execution_id: str,
    account_id: str,
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id=f"node-output-portfolio-{run_id}",
        run_id=run_id,
        workflow_name=workflow_name,
        execution_id=execution_id,
        node_name="portfolio_state_builder",
        node_type="portfolio_state",
        output_contract=PORTFOLIO_STATE_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=_portfolio_outputs(account_id),
        metadata={
            "quality_status": "normal",
            "risk_authority": _authority_metadata(),
        },
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _test_node(
    *,
    run_id: str,
    workflow_name: str,
    execution_id: str,
    node_name: str,
    output_contract: str,
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id=f"node-output-{node_name}-{run_id}",
        run_id=run_id,
        workflow_name=workflow_name,
        execution_id=execution_id,
        node_name=node_name,
        node_type="test_projection",
        output_contract=output_contract,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs={"value": "ok"},
        metadata={
            "quality_status": "normal",
            "risk_authority": _authority_metadata(),
        },
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 32, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 33, tzinfo=UTC),
        duration_seconds=60.0,
    )


def _portfolio_outputs(account_id: str) -> JsonObject:
    return {
        "canonical_portfolio_state": {
            "account_id": account_id,
            "timestamp": "2026-07-10T13:30:00+00:00",
            "equity": 100_000.0,
            "peak_equity": 105_000.0,
            "portfolio_value": 100_000.0,
            "cash": 15_000.0,
            "buying_power": 40_000.0,
            "last_equity": 99_000.0,
            "cash_ratio": 0.15,
            "buying_power_ratio": 0.40,
            "drawdown_absolute": 5_000.0,
            "drawdown_percent": 0.05,
            "capital_base": 95_000.0,
            "equity_retention_ratio": 1.0,
            "long_market_value": 85_000.0,
            "short_market_value": 0.0,
            "gross_market_value": 85_000.0,
            "net_market_value": 85_000.0,
            "gross_exposure": 0.85,
            "net_exposure": 0.85,
            "long_exposure": 0.85,
            "short_exposure": 0.0,
            "leverage": 1.0,
            "largest_position_pct": 0.70,
            "concentration_score": 0.40,
            "diversification_score": 0.60,
            "beta_exposure": 1.05,
            "beta_risk": 0.18,
            "portfolio_heat": 0.22,
            "risk_intensity": 0.33,
            "position_count": 2,
            "portfolio_regime": "balanced",
            "directional_bias": "long",
            "account_health": "healthy",
            "sector_exposure": {"ETF": 0.70, "Technology": 0.15},
            "asset_class_exposure": {"equity": 0.85},
            "risk_signals": {"portfolio_risk_normal": True},
            "schema_version": 2,
        },
        "positions": [
            {
                "symbol": "SPY",
                "quantity": 100.0,
                "market_value": 70_000.0,
                "cost_basis": 60_000.0,
                "exposure_weight": 0.70,
                "sector": "ETF",
                "theme": "index",
                "beta": 1.0,
            },
            {
                "symbol": "AAPL",
                "quantity": 50.0,
                "market_value": 15_000.0,
                "cost_basis": 12_000.0,
                "exposure_weight": 0.15,
                "sector": "Technology",
                "theme": "mega_cap",
                "beta": 1.2,
            },
        ],
        "exposures": {
            "gross_exposure": 0.85,
            "net_exposure": 0.85,
            "long_exposure": 0.85,
            "short_exposure": 0.0,
            "leverage": 1.0,
            "gross_market_value": 85_000.0,
            "net_market_value": 85_000.0,
            "long_market_value": 85_000.0,
            "short_market_value": 0.0,
            "sector_exposure": {"ETF": 0.70, "Technology": 0.15},
            "asset_class_exposure": {"equity": 0.85},
        },
        "risk_metrics": {
            "drawdown_percent": 0.05,
            "concentration_score": 0.40,
            "risk_intensity": 0.33,
            "beta_exposure": 1.05,
            "account_health": "healthy",
        },
        "allocation_data": {
            "positions": [
                {"symbol": "SPY", "current_weight": 0.70, "market_value": 70_000.0},
                {"symbol": "AAPL", "current_weight": 0.15, "market_value": 15_000.0},
            ],
            "sector_exposure": {"ETF": 0.70, "Technology": 0.15},
            "asset_class_exposure": {"equity": 0.85},
        },
        "equity_history_points": [
            {
                "account_id": account_id,
                "source": "alpaca",
                "timeframe": "1D",
                "observed_at": "2026-07-09T00:00:00+00:00",
                "equity": 99_000.0,
                "profit_loss": 1_000.0,
                "profit_loss_pct": 0.0102,
                "base_value": 98_000.0,
            },
            {
                "account_id": account_id,
                "source": "alpaca",
                "timeframe": "1D",
                "observed_at": "2026-07-10T00:00:00+00:00",
                "equity": 100_000.0,
                "profit_loss": 2_000.0,
                "profit_loss_pct": 0.0204,
                "base_value": 98_000.0,
            },
        ],
        "provider_source": "alpaca",
        "history_period": "1A",
        "history_timeframe": "1D",
    }


def _authority_metadata() -> JsonObject:
    return cast(
        JsonObject,
        classify_risk_authority(
            RiskAuthorityClassificationInput(
                content_type=AiOutputContentType.DURABLE_RECORD,
                authority_effect=AuthorityEffect.CANONICAL_RECORD,
                canonical_owner=CanonicalOwner.WORKFLOW_OUTPUT_CURATION,
                source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
                durable_authority=True,
            )
        ).to_metadata(),
    )


async def _assert_portfolio_counts(
    session: AsyncSession,
    *,
    account_id: str,
    state_history: int,
    state_latest: int,
    equity_history: int,
    position_history: int,
    position_latest: int,
    exposures: int,
    risk: int,
    allocations: int,
) -> None:
    assert (
        await _count(
            session,
            PortfolioStateHistoryModel,
            PortfolioStateHistoryModel.account_id == account_id,
        )
        == state_history
    )
    assert (
        await _count(
            session,
            PortfolioStateLatestModel,
            PortfolioStateLatestModel.account_id == account_id,
        )
        == state_latest
    )
    assert (
        await _count(
            session,
            PortfolioEquityHistoryPointModel,
            PortfolioEquityHistoryPointModel.account_id == account_id,
        )
        == equity_history
    )
    assert (
        await _count(
            session,
            PortfolioPositionHistoryModel,
            PortfolioPositionHistoryModel.account_id == account_id,
        )
        == position_history
    )
    assert (
        await _count(
            session,
            PortfolioPositionLatestModel,
            PortfolioPositionLatestModel.account_id == account_id,
        )
        == position_latest
    )
    assert (
        await _count(
            session,
            PortfolioExposureSnapshotModel,
            PortfolioExposureSnapshotModel.account_id == account_id,
        )
        == exposures
    )
    assert (
        await _count(
            session,
            PortfolioRiskSnapshotModel,
            PortfolioRiskSnapshotModel.account_id == account_id,
        )
        == risk
    )
    assert (
        await _count(
            session,
            PortfolioAllocationSnapshotModel,
            PortfolioAllocationSnapshotModel.account_id == account_id,
        )
        == allocations
    )


async def _projection_job_count(
    session: AsyncSession,
    *,
    workflow_name: str,
    execution_id: str,
    status: WorkflowOutputProjectionJobStatus | None = None,
) -> int:
    conditions = [
        WorkflowOutputProjectionJobModel.workflow_name == workflow_name,
        WorkflowOutputProjectionJobModel.execution_id == execution_id,
    ]
    if status is not None:
        conditions.append(WorkflowOutputProjectionJobModel.status == status.value)
    return await _count(session, WorkflowOutputProjectionJobModel, *conditions)


async def _count(
    session: AsyncSession,
    model: type[Any],
    *conditions: Any,
) -> int:
    result = await session.scalar(
        select(func.count()).select_from(model).where(*conditions)
    )
    return int(result or 0)


async def _cleanup_projection_test_data(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    workflow_name: str,
    execution_ids: tuple[str, ...],
    account_ids: tuple[str, ...],
) -> None:
    async with session_factory() as session:
        for account_id in account_ids:
            await _delete_portfolio_records(session, account_id)
        await session.execute(
            delete(CompletedWorkflowRunModel).where(
                CompletedWorkflowRunModel.workflow_name == workflow_name,
                CompletedWorkflowRunModel.execution_id.in_(execution_ids),
            )
        )
        await session.commit()


async def _delete_portfolio_records(
    session: AsyncSession,
    account_id: str,
) -> None:
    for model in (
        PortfolioAllocationSnapshotModel,
        PortfolioRiskSnapshotModel,
        PortfolioExposureSnapshotModel,
        PortfolioPositionLatestModel,
        PortfolioPositionHistoryModel,
        PortfolioEquityHistoryPointModel,
        PortfolioStateLatestModel,
        PortfolioStateHistoryModel,
    ):
        await session.execute(delete(model).where(model.account_id == account_id))


def _unique_name(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
