"""Append-only PostgreSQL storage for hypothetical Portfolio consequences."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from sqlalchemy import func, insert, select, text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.portfolio_consequences import (
    PortfolioConsequenceConflict,
    PortfolioConsequenceService,
    PortfolioConsequenceStoreFailure,
    require_initial_claim_catalogs,
)
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
)
from polaris.domain.evidence.judgments import ProjectedPortfolioConsequenceRef
from polaris.domain.portfolio import PortfolioStateId
from polaris.domain.portfolio_consequences import (
    ProjectedChange,
    ProjectedPortfolioConsequence,
    RecordedProjectedPortfolioConsequence,
)
from polaris.domain.portfolio_judgment_history import PortfolioClaimCatalog

from .codec import actor_columns, actor_from_columns
from .codec_support import uuid_value
from .investment_intelligence import (
    PostgresInvestmentIntelligenceStore,
    _material_alternatives_for_decision,
)
from .portfolio_states import PostgresPortfolioStateStore
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    projected_portfolio_consequences,
)


def _change(value: object, reason: object) -> ProjectedChange | None:
    if value is None and reason is None:
        return None
    return ProjectedChange(
        value=None if value is None else Decimal(str(value)),
        unresolved_reason=reason,
    )


def _from_row(row: RowMapping) -> RecordedProjectedPortfolioConsequence:
    consequence = ProjectedPortfolioConsequence(
        consequence_id=ProjectedPortfolioConsequenceRef(
            uuid_value(row["consequence_id"], "consequence_id")
        ),
        alternative=DecisionAlternativeVersionRef(
            DecisionAlternativeId(uuid_value(row["alternative_id"], "alternative_id")),
            DecisionAlternativeRevision(row["alternative_revision"]),
        ),
        source_state_id=PortfolioStateId(
            uuid_value(row["source_state_id"], "source_state_id")
        ),
        source_as_of=row["source_as_of"],
        horizon=InvestmentHorizon(row["horizon"]),
        scenario=row["scenario"],
        assumptions=tuple(row["assumptions"]),
        exposure_change=_change(row["exposure_change"], row["exposure_unresolved"]),
        allocation_change=_change(
            row["allocation_change"], row["allocation_unresolved"]
        ),
        cash_effect=_change(row["cash_effect"], row["cash_unresolved"]),
        economic_benefits=tuple(row["economic_benefits"]),
        adverse_possibilities=tuple(row["adverse_possibilities"]),
        material_risk_changes=tuple(row["material_risk_changes"]),
        attribution=actor_from_columns(row),
        formed_at=row["formed_at"],
        uncertainty=row["uncertainty"],
    )
    return RecordedProjectedPortfolioConsequence(
        consequence=consequence, known_at=row["known_at"]
    )


def _values(item: ProjectedPortfolioConsequence) -> dict[str, object]:
    def change_value(change: ProjectedChange | None) -> Decimal | None:
        return None if change is None else change.value

    def unresolved(change: ProjectedChange | None) -> str | None:
        return None if change is None else change.unresolved_reason

    return {
        "consequence_id": item.consequence_id.value,
        "alternative_id": item.alternative.root.value,
        "alternative_revision": item.alternative.revision.value,
        "source_state_id": item.source_state_id.value,
        "source_as_of": item.source_as_of,
        "horizon": item.horizon.value,
        "scenario": item.scenario,
        "assumptions": list(item.assumptions),
        "exposure_change": change_value(item.exposure_change),
        "exposure_unresolved": unresolved(item.exposure_change),
        "allocation_change": change_value(item.allocation_change),
        "allocation_unresolved": unresolved(item.allocation_change),
        "cash_effect": change_value(item.cash_effect),
        "cash_unresolved": unresolved(item.cash_effect),
        "economic_benefits": list(item.economic_benefits),
        "adverse_possibilities": list(item.adverse_possibilities),
        "material_risk_changes": list(item.material_risk_changes),
        "formed_at": item.formed_at,
        "known_at": func.clock_timestamp(),
        "uncertainty": item.uncertainty,
        **actor_columns(item.attribution),
    }


class PostgresPortfolioConsequenceStore:
    """Atomically append complete material Alternative sets; never overwrite them."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def append_batch(
        self,
        decision_id: InvestmentDecisionId,
        consequences: tuple[ProjectedPortfolioConsequence, ...],
        initial_claim_catalogs: Mapping[
            ProjectedPortfolioConsequenceRef, PortfolioClaimCatalog
        ],
    ) -> tuple[RecordedProjectedPortfolioConsequence, ...]:
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("decision_id must be InvestmentDecisionId")
        if not consequences:
            raise ValueError("consequences are required")
        catalogs = require_initial_claim_catalogs(consequences, initial_claim_catalogs)
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    text(
                        "LOCK TABLE decision_alternatives, "
                        "decision_alternative_revisions IN SHARE MODE"
                    )
                )
                owner_set = await _material_alternatives_for_decision(
                    connection, decision_id
                )
                expected = {
                    (item.alternative_id.value, item.revision) for item in owner_set
                }
                actual = {
                    (item.alternative.root.value, item.alternative.revision.value)
                    for item in consequences
                }
                if not expected or actual != expected:
                    raise PortfolioConsequenceConflict(
                        "Consequence set is stale or incomplete for Decision"
                    )
                result = await connection.execute(
                    insert(projected_portfolio_consequences)
                    .values([_values(item) for item in consequences])
                    .returning(projected_portfolio_consequences)
                )
                rows = result.mappings().all()
                from .portfolio_judgment_history import (
                    insert_initial_portfolio_judgment_act,
                )

                for row in rows:
                    await insert_initial_portfolio_judgment_act(
                        connection,
                        _from_row(row).consequence,
                        row["known_at"],
                        catalogs[
                            ProjectedPortfolioConsequenceRef(
                                uuid_value(row["consequence_id"], "consequence_id")
                            )
                        ],
                    )
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise PortfolioConsequenceConflict(
                    "Consequence identity already exists"
                ) from exc
            raise PortfolioConsequenceStoreFailure("Consequence append failed") from exc
        except SQLAlchemyError as exc:
            raise PortfolioConsequenceStoreFailure("Consequence append failed") from exc
        recorded = {row["consequence_id"]: _from_row(row) for row in rows}
        return tuple(recorded[item.consequence_id.value] for item in consequences)

    async def get(
        self, consequence_id: ProjectedPortfolioConsequenceRef
    ) -> RecordedProjectedPortfolioConsequence | None:
        try:
            async with self._engine.connect() as connection:
                result = await connection.execute(
                    select(projected_portfolio_consequences).where(
                        projected_portfolio_consequences.c.consequence_id
                        == consequence_id.value
                    )
                )
                row = result.mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PortfolioConsequenceStoreFailure("Consequence read failed") from exc
        return None if row is None else _from_row(row)


def create_postgres_portfolio_consequence_service(
    engine: AsyncEngine,
) -> PortfolioConsequenceService:
    """Compose the production producer with owner-issued Alternative and State reads."""
    return PortfolioConsequenceService(
        PostgresPortfolioStateStore(engine),
        PostgresPortfolioConsequenceStore(engine),
        PostgresInvestmentIntelligenceStore(engine),
    )
