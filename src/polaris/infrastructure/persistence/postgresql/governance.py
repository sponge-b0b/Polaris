"""PostgreSQL owner store for minimum R3 Governance authority acts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.human_investment_decision import HumanInvestmentDecisionService
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
    OperationId,
)
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.evidence.judgments import (
    HumanInvestmentDecisionRef,
    InvestmentRecommendationRef,
)
from polaris.domain.governance_authority import (
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
)
from polaris.domain.human_investment_decision import (
    ConsideredRecommendation,
    HumanDecisionChoice,
    HumanInvestmentDecision,
    InvalidHumanInvestmentDecision,
    RecommendationRelationship,
    require_human_decision_authority,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.portfolio import PortfolioId

from .investment_intelligence import PostgresInvestmentIntelligenceStore
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    governance_authority_regimes,
    human_investment_decisions,
    investment_decisions,
    investment_intelligence_judgment_acts,
)


class HumanDecisionConflict(InvalidHumanInvestmentDecision):
    """The command identity or governing Decision changed."""


class HumanDecisionStoreUnavailable(RuntimeError):
    """Governance fact storage could not be read or committed."""


def _regime_from_row(row: RowMapping) -> InvestmentAuthorityRegime:
    return InvestmentAuthorityRegime(
        InvestmentAuthorityRegimeId(UUID(str(row["regime_id"]))),
        ActorId(UUID(str(row["actor_id"]))),
        PortfolioId(UUID(str(row["portfolio_id"]))),
        InvestmentAuthorityPower(row["power"]),
        row["effective_from"],
        row["effective_until"],
    )


async def _load_regime(
    connection: AsyncConnection, regime_id: InvestmentAuthorityRegimeId
) -> InvestmentAuthorityRegime | None:
    row = (
        (
            await connection.execute(
                select(governance_authority_regimes).where(
                    governance_authority_regimes.c.regime_id == regime_id.value
                )
            )
        )
        .mappings()
        .first()
    )
    return None if row is None else _regime_from_row(row)


def _decision_from_row(row: RowMapping) -> HumanInvestmentDecision:
    raw_links = row["recommendations"]
    if not isinstance(raw_links, list):
        raise HumanDecisionStoreUnavailable("stored Recommendation links are invalid")
    return HumanInvestmentDecision(
        decision_ref=HumanInvestmentDecisionRef(UUID(str(row["decision_ref"]))),
        investment_decision_id=InvestmentDecisionId(
            UUID(str(row["investment_decision_id"]))
        ),
        portfolio_id=PortfolioId(UUID(str(row["portfolio_id"]))),
        actor=KnownActorAttribution(ActorId(UUID(str(row["actor_id"])))),
        made_at=row["made_at"],
        choice=(
            HumanDecisionChoice.DEFERRAL
            if row["choice"] == "deferral"
            else EconomicDisposition(row["choice"])
        ),
        effect=HumanInvestmentDecisionEffect(row["effect"]),
        authority_regime_id=InvestmentAuthorityRegimeId(UUID(str(row["regime_id"]))),
        recommendations=tuple(
            ConsideredRecommendation(
                InvestmentRecommendationRef(UUID(str(item["recommendation_id"]))),
                RecommendationRelationship(item["relationship"]),
            )
            for item in raw_links
        ),
        material_rationale=row["material_rationale"],
    )


async def _require_decision_state(
    connection: AsyncConnection,
    decision: HumanInvestmentDecision,
    expected: DecisionVersion,
) -> None:
    state = (
        (
            await connection.execute(
                select(investment_decisions)
                .where(
                    investment_decisions.c.decision_id
                    == decision.investment_decision_id.value
                )
                .with_for_update()
            )
        )
        .mappings()
        .first()
    )
    if state is None:
        raise InvalidHumanInvestmentDecision(
            "governing Investment Decision does not exist"
        )
    if state["decision_version"] != expected.value:
        raise HumanDecisionConflict("governing Decision version changed")
    if (
        state["scope_completeness"] != "established"
        or set(state["scope_portfolio_ids"]) != {decision.portfolio_id.value}
        or state["lifecycle_disposition"] != "unresolved"
        or state["applicability"] != "operative"
    ):
        raise InvalidHumanInvestmentDecision(
            "governing Decision scope or applicability is not R3-eligible"
        )


async def _require_recommendation_links(
    connection: AsyncConnection, decision: HumanInvestmentDecision
) -> None:
    if not decision.recommendations:
        return
    refs = {item.recommendation_id.value for item in decision.recommendations}
    rows = (
        (
            await connection.execute(
                select(investment_intelligence_judgment_acts.c.target_id).where(
                    investment_intelligence_judgment_acts.c.target_family
                    == "InvestmentRecommendationRef",
                    investment_intelligence_judgment_acts.c.decision_id
                    == decision.investment_decision_id.value,
                    investment_intelligence_judgment_acts.c.sequence == 1,
                    investment_intelligence_judgment_acts.c.target_id.in_(refs),
                )
            )
        )
        .scalars()
        .all()
    )
    if {UUID(str(item)) for item in rows} != refs:
        raise InvalidHumanInvestmentDecision(
            "materially considered Recommendation is unavailable"
        )


async def _operation_row(
    connection: AsyncConnection, operation_id: OperationId
) -> RowMapping | None:
    return (
        (
            await connection.execute(
                select(human_investment_decisions).where(
                    human_investment_decisions.c.operation_id == operation_id.value
                )
            )
        )
        .mappings()
        .first()
    )


class PostgresGovernanceStore:
    """Persist immutable Governance facts and check current Decision scope at commit."""

    def __init__(self, engine: AsyncEngine) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine

    async def install_regime(self, regime: InvestmentAuthorityRegime) -> None:
        """Install a trusted minimum regime as an immutable authority fact."""
        if type(regime) is not InvestmentAuthorityRegime:
            raise TypeError("regime must be InvestmentAuthorityRegime")
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    insert(governance_authority_regimes).values(
                        regime_id=regime.regime_id.value,
                        actor_id=regime.actor_id.value,
                        portfolio_id=regime.portfolio_id.value,
                        power=regime.power.value,
                        effective_from=regime.effective_from,
                        effective_until=regime.effective_until,
                    )
                )
        except IntegrityError as error:
            raise HumanDecisionConflict(
                "authority regime identity already exists"
            ) from error
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "authority regime write failed"
            ) from error

    async def authority_regime(
        self, regime_id: InvestmentAuthorityRegimeId
    ) -> InvestmentAuthorityRegime | None:
        if type(regime_id) is not InvestmentAuthorityRegimeId:
            raise TypeError("regime identity must be typed")
        try:
            async with self._engine.connect() as connection:
                return await _load_regime(connection, regime_id)
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "authority regime read failed"
            ) from error

    async def human_decision_for_operation(
        self, operation_id: OperationId
    ) -> tuple[HumanInvestmentDecision, DecisionVersion] | None:
        if type(operation_id) is not OperationId:
            raise TypeError("operation identity must be typed")
        try:
            async with self._engine.connect() as connection:
                row = await _operation_row(connection, operation_id)
                if row is None:
                    return None
                return (
                    _decision_from_row(row),
                    DecisionVersion(row["expected_decision_version"]),
                )
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "Human Decision operation read failed"
            ) from error

    async def record_human_decision(
        self,
        operation_id: OperationId,
        decision: HumanInvestmentDecision,
        expected_decision_version: DecisionVersion,
    ) -> HumanInvestmentDecision:
        from .governance_history import (
            archive_governance_act_commits,
            ensure_governance_commit_slot,
        )

        try:
            await ensure_governance_commit_slot(self._engine)
            async with self._engine.begin() as connection:
                await connection.execute(select(func.pg_advisory_xact_lock(479001)))
                prior = await _operation_row(connection, operation_id)
                if prior is not None:
                    prior_fact = _decision_from_row(prior)
                    if (
                        replace(prior_fact, made_at=decision.made_at) != decision
                        or prior["expected_decision_version"]
                        != expected_decision_version.value
                    ):
                        raise HumanDecisionConflict("operation ID has another request")
                    return prior_fact

                regime = await _load_regime(connection, decision.authority_regime_id)
                require_human_decision_authority(regime, decision)
                await _require_decision_state(
                    connection, decision, expected_decision_version
                )
                await _require_recommendation_links(connection, decision)
                trusted_now = await connection.scalar(select(func.clock_timestamp()))
                if (
                    not isinstance(trusted_now, datetime)
                    or decision.made_at > trusted_now
                ):
                    raise InvalidHumanInvestmentDecision(
                        "human act time is later than the durable store clock"
                    )
                await connection.execute(
                    insert(human_investment_decisions).values(
                        decision_ref=decision.decision_ref.value,
                        operation_id=operation_id.value,
                        investment_decision_id=decision.investment_decision_id.value,
                        portfolio_id=decision.portfolio_id.value,
                        actor_id=decision.actor.actor_id.value,
                        regime_id=decision.authority_regime_id.value,
                        made_at=decision.made_at,
                        recorded_at=datetime.now(UTC),
                        choice=decision.choice.value,
                        effect=decision.effect.value,
                        recommendations=[
                            {
                                "recommendation_id": str(item.recommendation_id.value),
                                "relationship": item.relationship.value,
                            }
                            for item in decision.recommendations
                        ],
                        material_rationale=decision.material_rationale,
                        expected_decision_version=expected_decision_version.value,
                    )
                )
            await archive_governance_act_commits(self._engine)
            return decision
        except IntegrityError as error:
            raise HumanDecisionConflict(
                "Human Decision identity already exists"
            ) from error
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "Human Decision write failed"
            ) from error

    async def human_decision(
        self, decision_ref: HumanInvestmentDecisionRef
    ) -> HumanInvestmentDecision | None:
        if type(decision_ref) is not HumanInvestmentDecisionRef:
            raise TypeError("Human Decision identity must be typed")
        try:
            # duplicate-code: Human-act lookup must reconstruct its own typed
            # authority fact rather than share a generic table reader.
            # arid: disable
            async with self._engine.connect() as connection:
                row = (
                    (
                        await connection.execute(
                            select(human_investment_decisions).where(
                                human_investment_decisions.c.decision_ref
                                == decision_ref.value
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                return None if row is None else _decision_from_row(row)
            # arid: enable
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable("Human Decision read failed") from error

    async def human_decision_history(
        self, decision_id: InvestmentDecisionId
    ) -> tuple[HumanInvestmentDecision, ...]:
        if type(decision_id) is not InvestmentDecisionId:
            raise TypeError("governing Decision identity must be typed")
        try:
            async with self._engine.connect() as connection:
                rows = (
                    (
                        await connection.execute(
                            select(human_investment_decisions)
                            .where(
                                human_investment_decisions.c.investment_decision_id
                                == decision_id.value
                            )
                            .order_by(
                                human_investment_decisions.c.recorded_at,
                                human_investment_decisions.c.decision_ref,
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
                return tuple(_decision_from_row(row) for row in rows)
        except SQLAlchemyError as error:
            raise HumanDecisionStoreUnavailable(
                "Human Decision history failed"
            ) from error


def create_postgres_human_decision_service(
    engine: AsyncEngine,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> HumanInvestmentDecisionService:
    """Compose the two production owner stores behind the shared command boundary."""
    return HumanInvestmentDecisionService(
        PostgresGovernanceStore(engine),
        PostgresInvestmentIntelligenceStore(engine),
        now=now,
    )
