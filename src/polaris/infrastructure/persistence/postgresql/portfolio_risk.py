"""Append-only PostgreSQL storage for Portfolio Risk assessments."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, insert, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.portfolio_risk import (
    PortfolioRiskConflict,
    PortfolioRiskService,
    PortfolioRiskStoreFailure,
)
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.evidence.judgments import (
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
)
from polaris.domain.evidence.observations import EvidenceObservationId
from polaris.domain.portfolio import PortfolioStateId
from polaris.domain.portfolio_judgment_history import PortfolioClaimCatalog
from polaris.domain.portfolio_risk import (
    PortfolioRiskAssessment,
    RecordedPortfolioRiskAssessment,
    RiskDimension,
    RiskDimensionKind,
    RiskSupport,
)

from .codec import actor_columns, actor_from_columns
from .codec_support import uuid_value
from .portfolio_consequences import PostgresPortfolioConsequenceStore
from .portfolio_states import PostgresPortfolioStateStore
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import portfolio_risk_assessments, projected_portfolio_consequences


def _dimension_json(dimension: RiskDimension) -> dict[str, str | None]:
    return {
        "kind": dimension.kind.value,
        "value": None if dimension.value is None else str(dimension.value),
        "unresolved_reason": dimension.unresolved_reason,
    }


def _from_row(row: RowMapping) -> RecordedPortfolioRiskAssessment:
    dimensions = tuple(
        RiskDimension(
            kind=RiskDimensionKind(item["kind"]),
            value=None if item["value"] is None else Decimal(item["value"]),
            unresolved_reason=item["unresolved_reason"],
        )
        for item in row["dimensions"]
    )
    consequence_id = row["projected_consequence_id"]
    assessment = PortfolioRiskAssessment(
        assessment_id=PortfolioRiskAssessmentRef(
            uuid_value(row["assessment_id"], "assessment_id")
        ),
        source_state_id=PortfolioStateId(
            uuid_value(row["source_state_id"], "source_state_id")
        ),
        source_as_of=row["source_as_of"],
        projected_consequence_id=(
            None
            if consequence_id is None
            else ProjectedPortfolioConsequenceRef(
                uuid_value(consequence_id, "projected_consequence_id")
            )
        ),
        horizon=InvestmentHorizon(row["horizon"]),
        scenario=row["scenario"],
        support=RiskSupport(
            basis=row["support_basis"],
            evidence=tuple(
                EvidenceObservationId(uuid_value(item, "evidence_id"))
                for item in row["evidence_ids"]
            ),
            material_dimensions=tuple(item.kind for item in dimensions),
            assumptions=tuple(row["assumptions"]),
            downside_fraction=row["downside_fraction"],
            market_volatility_fraction=row["market_volatility_fraction"],
            objective_shortfall_amount=row["objective_shortfall_amount"],
            uncertainty=tuple(row["support_uncertainty"]),
        ),
        dimensions=dimensions,
        uncertainty=tuple(row["uncertainty"]),
        attribution=actor_from_columns(row),
        formed_at=row["formed_at"],
    )
    return RecordedPortfolioRiskAssessment(assessment, row["known_at"])


def _values(assessment: PortfolioRiskAssessment) -> dict[str, object]:
    return {
        "assessment_id": assessment.assessment_id.value,
        "source_state_id": assessment.source_state_id.value,
        "source_as_of": assessment.source_as_of,
        "projected_consequence_id": (
            None
            if assessment.projected_consequence_id is None
            else assessment.projected_consequence_id.value
        ),
        "horizon": assessment.horizon.value,
        "scenario": assessment.scenario,
        "support_basis": assessment.support.basis,
        "evidence_ids": [item.value for item in assessment.support.evidence],
        "assumptions": list(assessment.support.assumptions),
        "downside_fraction": assessment.support.downside_fraction,
        "market_volatility_fraction": assessment.support.market_volatility_fraction,
        "objective_shortfall_amount": assessment.support.objective_shortfall_amount,
        "support_uncertainty": list(assessment.support.uncertainty),
        "dimensions": [_dimension_json(item) for item in assessment.dimensions],
        "uncertainty": list(assessment.uncertainty),
        "formed_at": assessment.formed_at,
        "known_at": func.clock_timestamp(),
        **actor_columns(assessment.attribution),
    }


class PostgresPortfolioRiskStore:
    """Store immutable assessment roots and preserve exact historical reads."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def append(
        self,
        assessment: PortfolioRiskAssessment,
        initial_claim_catalog: PortfolioClaimCatalog,
    ) -> RecordedPortfolioRiskAssessment:
        if type(assessment) is not PortfolioRiskAssessment:
            raise TypeError("assessment must be PortfolioRiskAssessment")
        if type(initial_claim_catalog) is not PortfolioClaimCatalog:
            raise TypeError("initial_claim_catalog must be PortfolioClaimCatalog")
        try:
            async with self._engine.begin() as connection:
                if assessment.projected_consequence_id is not None:
                    exact_projection = await connection.scalar(
                        select(projected_portfolio_consequences.c.consequence_id).where(
                            projected_portfolio_consequences.c.consequence_id
                            == assessment.projected_consequence_id.value,
                            projected_portfolio_consequences.c.source_state_id
                            == assessment.source_state_id.value,
                            projected_portfolio_consequences.c.source_as_of
                            == assessment.source_as_of,
                            projected_portfolio_consequences.c.horizon
                            == assessment.horizon.value,
                        )
                    )
                    if exact_projection is None:
                        raise PortfolioRiskConflict(
                            "projected Risk basis differs from its consequence"
                        )
                result = await connection.execute(
                    insert(portfolio_risk_assessments)
                    .values(_values(assessment))
                    .returning(portfolio_risk_assessments)
                )
                row = result.mappings().one()
                from .portfolio_judgment_history import (
                    insert_initial_portfolio_judgment_act,
                )

                await insert_initial_portfolio_judgment_act(
                    connection,
                    _from_row(row).assessment,
                    row["known_at"],
                    initial_claim_catalog,
                )
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise PortfolioRiskConflict(
                    "Portfolio Risk Assessment identity already exists"
                ) from exc
            raise PortfolioRiskStoreFailure("Portfolio Risk append failed") from exc
        except SQLAlchemyError as exc:
            raise PortfolioRiskStoreFailure("Portfolio Risk append failed") from exc
        return _from_row(row)

    async def get(
        self, assessment_id: PortfolioRiskAssessmentRef
    ) -> RecordedPortfolioRiskAssessment | None:
        if type(assessment_id) is not PortfolioRiskAssessmentRef:
            raise TypeError("assessment_id must be PortfolioRiskAssessmentRef")
        try:
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    select(portfolio_risk_assessments).where(
                        portfolio_risk_assessments.c.assessment_id
                        == assessment_id.value
                    )
                )
                row = result.mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PortfolioRiskStoreFailure("Portfolio Risk read failed") from exc
        return None if row is None else _from_row(row)


def create_postgres_portfolio_risk_service(
    engine: AsyncEngine,
) -> PortfolioRiskService:
    """Compose Risk production with exact actual and hypothetical source reads."""
    return PortfolioRiskService(
        PostgresPortfolioStateStore(engine),
        PostgresPortfolioConsequenceStore(engine),
        PostgresPortfolioRiskStore(engine),
    )
