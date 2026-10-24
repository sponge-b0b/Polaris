"""Atomic append and reconstruction of Intelligence-owned target acts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentHistoryUnavailable,
)
from polaris.domain.evidence.judgments import (
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceJudgmentAct,
    IntelligenceJudgmentHistory,
    IntelligenceJudgmentRoot,
    InvalidIntelligenceJudgmentHistory,
)

from .intelligence_contract_codec import (
    contract_value_from_payload,
    contract_value_payload,
)
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import investment_intelligence_judgment_acts

INTELLIGENCE_OWNER_LOCK = 6_934_842_191_352_427_103
_ROOT_TYPES = {
    InvestmentHypothesisRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    InvestmentRecommendationRef,
    RecommendationWithholdingJudgmentRef,
}


def _root_identity(root: IntelligenceJudgmentRoot) -> tuple[str, UUID]:
    if type(root) not in _ROOT_TYPES:
        raise TypeError("root must be an Investment Intelligence Evidence target")
    return type(root).__name__, root.value


def _act_values(
    act: IntelligenceJudgmentAct,
    sequence: int,
    history: IntelligenceJudgmentHistory,
) -> dict[str, object]:
    family, root_id = _root_identity(act.root)
    assertion = history.acts[0].assertion
    if assertion is None:
        raise InvalidIntelligenceJudgmentHistory("initial assertion is missing")
    target_revision, catalog_version = history.versions[-1]
    return {
        "act_id": act.act_id,
        "target_family": family,
        "target_id": root_id,
        "decision_id": assertion.decision_id.value,
        "sequence": sequence,
        "effective_at": act.effective_at,
        "recorded_at": act.recorded_at,
        "known_at": act.known_at,
        "judgment_revision": target_revision.value,
        "claim_catalog_version": catalog_version.value,
        "act": contract_value_payload(act),
    }


async def _load(
    connection: AsyncConnection, root: IntelligenceJudgmentRoot
) -> IntelligenceJudgmentHistory | None:
    family, root_id = _root_identity(root)
    # duplicate-code: Sharing would couple distinct owner schemas.
    # arid: disable
    rows = (
        (
            await connection.execute(
                select(investment_intelligence_judgment_acts)
                .where(
                    investment_intelligence_judgment_acts.c.target_family == family,
                    investment_intelligence_judgment_acts.c.target_id == root_id,
                )
                .order_by(investment_intelligence_judgment_acts.c.sequence)
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None
    # arid: enable
    history: IntelligenceJudgmentHistory | None = None
    for expected_sequence, row in enumerate(rows, start=1):
        act = contract_value_from_payload(row["act"])
        if not isinstance(act, IntelligenceJudgmentAct) or act.root != root:
            raise InvalidIntelligenceJudgmentHistory("stored act has wrong typed root")
        if (
            row["act_id"] != act.act_id
            or row["sequence"] != expected_sequence
            or row["effective_at"] != act.effective_at
            or row["recorded_at"] != act.recorded_at
            or row["known_at"] != act.known_at
        ):
            raise InvalidIntelligenceJudgmentHistory("stored act metadata differs")
        history = (
            IntelligenceJudgmentHistory.form(act)
            if history is None
            else history.append(act)
        )
        initial = history.acts[0].assertion
        if initial is None or row["decision_id"] != initial.decision_id.value:
            raise InvalidIntelligenceJudgmentHistory("stored Decision identity differs")
        revision, catalog_version = history.versions[-1]
        if (
            row["judgment_revision"] != revision.value
            or row["claim_catalog_version"] != catalog_version.value
        ):
            raise InvalidIntelligenceJudgmentHistory("stored owner versions differ")
    return history


async def insert_initial_intelligence_act(
    connection: AsyncConnection, act: IntelligenceJudgmentAct
) -> IntelligenceJudgmentHistory:
    """Join the initial target and complete catalog to the forming write."""
    history = IntelligenceJudgmentHistory.form(act)
    await connection.execute(
        insert(investment_intelligence_judgment_acts).values(
            _act_values(act, 1, history)
        )
    )
    return history


class PostgresIntelligenceJudgmentHistoryStore:
    """Revalidate same-root correction history under the owner write lock."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        validation_connection: AsyncConnection | None = None,
    ) -> None:
        require_qualified_postgres_runtime()
        # duplicate-code: Sharing would couple distinct owner schemas.
        # arid: disable
        if (
            validation_connection is not None
            and validation_connection.engine is not engine
        ):
            raise ValueError("validation connection must use the owner engine")
        # arid: enable
        self._engine = engine
        self._validation_connection = validation_connection

    # duplicate-code: Sharing would couple distinct owner schemas.
    # arid: disable
    def for_validation(
        self, connection: AsyncConnection
    ) -> PostgresIntelligenceJudgmentHistoryStore:
        if not connection.in_transaction():
            raise ValueError("owner validation requires an open write transaction")
        return PostgresIntelligenceJudgmentHistoryStore(
            self._engine, validation_connection=connection
        )

    async def load(
        self, root: IntelligenceJudgmentRoot
    ) -> IntelligenceJudgmentHistory | None:
        if self._validation_connection is not None:
            connection = self._validation_connection
            if not connection.in_transaction():
                raise IntelligenceJudgmentHistoryUnavailable(
                    "owner validation transaction is closed"
                )
            try:
                await connection.execute(
                    select(investment_intelligence_judgment_acts.c.act_id)
                    .where(
                        investment_intelligence_judgment_acts.c.target_family
                        == type(root).__name__,
                        investment_intelligence_judgment_acts.c.target_id == root.value,
                    )
                    .with_for_update(read=True)
                )
                return await _load(connection, root)
            except SQLAlchemyError as error:
                raise IntelligenceJudgmentHistoryUnavailable(
                    "owner history validation read failed"
                ) from error
        try:
            async with self._engine.connect() as connection:
                return await _load(connection, root)
        except SQLAlchemyError as error:
            raise IntelligenceJudgmentHistoryUnavailable(
                "owner history read failed"
            ) from error

    # arid: enable

    async def append(self, act: IntelligenceJudgmentAct) -> IntelligenceJudgmentHistory:
        if self._validation_connection is not None:
            raise ValueError("validation reader cannot append owner acts")
        if type(act) is not IntelligenceJudgmentAct:
            raise TypeError("correction must be a typed owner act")
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    select(func.pg_advisory_xact_lock(INTELLIGENCE_OWNER_LOCK))
                )
                history = await _load(connection, act.root)
                if history is None:
                    raise InvalidIntelligenceJudgmentHistory("target root is missing")
                updated = history.append(act)
                await connection.execute(
                    insert(investment_intelligence_judgment_acts).values(
                        _act_values(act, len(updated.acts), updated)
                    )
                )
                return updated
        except IntegrityError as error:
            raise InvalidIntelligenceJudgmentHistory(
                "owner act identity or sequence already exists"
            ) from error
        except SQLAlchemyError as error:
            raise IntelligenceJudgmentHistoryUnavailable(
                "owner correction append failed"
            ) from error
