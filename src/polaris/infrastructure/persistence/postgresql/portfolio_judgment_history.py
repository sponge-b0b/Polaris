"""Append-only PostgreSQL owner history for Portfolio Evidence targets."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import insert, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from polaris.application.portfolio_judgment_history import (
    PortfolioJudgmentHistoryUnavailable,
)
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.judgment_versions import JudgmentRevision
from polaris.domain.evidence.judgments import (
    ClaimId,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
)
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceCorrectionId,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
)
from polaris.domain.portfolio_consequences import ProjectedPortfolioConsequence
from polaris.domain.portfolio_judgment_history import (
    PendingDisposition,
    PendingResolution,
    PortfolioClaim,
    PortfolioClaimCatalog,
    PortfolioJudgmentAct,
    PortfolioJudgmentAssertion,
    PortfolioJudgmentHistory,
    PortfolioJudgmentLane,
    PortfolioJudgmentRoot,
)
from polaris.domain.portfolio_risk import PortfolioRiskAssessment

from .codec import actor_columns, actor_from_columns
from .codec_support import (
    iso_aware_datetime,
    json_object,
    json_safe,
    nonempty_string,
    uuid_value,
)
from .portfolio_consequences import _from_row as _consequence_from_row
from .portfolio_consequences import _values as _consequence_values
from .portfolio_risk import _from_row as _risk_from_row
from .portfolio_risk import _values as _risk_values
from .runtime_qualification import require_qualified_postgres_runtime
from .schema import (
    portfolio_judgment_acts,
    portfolio_risk_assessments,
    projected_portfolio_consequences,
)

# duplicate-code: this codec decodes the closed Portfolio support payload;
# sharing the domain's fact predicate would mix transport and domain concerns.
# arid: disable
_FACT_TYPES = {
    kind.__name__: kind
    for kind in (
        EvidenceObservationId,
        EvidenceBindingId,
        EvidenceSufficiencyAssessmentId,
        EvidenceCorrectionId,
    )
}
# arid: enable


def _assertion_payload(assertion: PortfolioJudgmentAssertion) -> dict[str, object]:
    if type(assertion) is ProjectedPortfolioConsequence:
        family = "consequence"
        values = _consequence_values(assertion)
    elif type(assertion) is PortfolioRiskAssessment:
        family = "risk"
        values = _risk_values(assertion)
    else:
        raise TypeError("assertion must be a Portfolio Evidence target")
    values.pop("known_at")
    return {"family": family, "values": cast(dict[str, object], json_safe(values))}


def _assertion_from_payload(
    payload: object, known_at: datetime
) -> PortfolioJudgmentAssertion:
    data = json_object(payload, "assertion")
    values = json_object(data.get("values"), "assertion values").copy()
    for field in ("source_as_of", "formed_at"):
        values[field] = iso_aware_datetime(values.get(field), field)
    values["known_at"] = known_at
    if data.get("family") == "consequence":
        return _consequence_from_row(cast(RowMapping, values)).consequence
    if data.get("family") == "risk":
        # duplicate-code: persisted Risk decimal decoding is independent of
        # domain validation of the finished assessment.
        # arid: disable
        for field in (
            "downside_fraction",
            "market_volatility_fraction",
            "objective_shortfall_amount",
        ):
            if values.get(field) is not None:
                values[field] = Decimal(str(values[field]))
        # arid: enable
        return _risk_from_row(cast(RowMapping, values)).assessment
    raise ValueError("unknown Portfolio assertion family")


def _catalog_payload(catalog: PortfolioClaimCatalog) -> list[dict[str, object]]:
    return [
        {
            "claim_id": str(claim.claim_id.value),
            "proposition": claim.proposition,
            "surviving_support": [
                {"kind": type(fact).__name__, "id": str(fact.value)}
                for fact in sorted(
                    claim.surviving_support,
                    key=lambda fact: (type(fact).__name__, str(fact.value)),
                )
            ],
        }
        for claim in catalog.claims
    ]


def _catalog_from_payload(payload: object) -> PortfolioClaimCatalog:
    if not isinstance(payload, list):
        raise ValueError("catalog must be a complete list")
    claims = []
    for item in payload:
        row = json_object(item, "claim")
        support = row.get("surviving_support")
        if not isinstance(support, list):
            raise ValueError("claim support must be a list")
        facts = []
        for value in support:
            fact = json_object(value, "claim fact")
            kind = _FACT_TYPES.get(fact.get("kind"))
            if kind is None:
                raise ValueError("unknown claim support fact")
            facts.append(kind(uuid_value(fact.get("id"), "fact id")))
        claims.append(
            PortfolioClaim(
                ClaimId(uuid_value(row.get("claim_id"), "claim_id")),
                nonempty_string(row.get("proposition"), "claim proposition"),
                frozenset(facts),
            )
        )
    return PortfolioClaimCatalog(tuple(claims))


def _act_payload(act: PortfolioJudgmentAct) -> dict[str, object]:
    return {
        "schema": "polaris.portfolio-judgment-act/v1",
        "attribution": json_safe(actor_columns(act.attribution)),
        "basis": act.basis,
        "ancestry": [str(item) for item in act.ancestry],
        "assertion": (
            None if act.assertion is None else _assertion_payload(act.assertion)
        ),
        "catalog": None if act.catalog is None else _catalog_payload(act.catalog),
        "target_predecessor": (
            None if act.target_predecessor is None else str(act.target_predecessor)
        ),
        "catalog_predecessor": (
            None if act.catalog_predecessor is None else str(act.catalog_predecessor)
        ),
        "pending_resolutions": [
            {
                "lane": item.lane.value,
                "pending_act_id": str(item.pending_act_id),
                "disposition": item.disposition.value,
            }
            for item in act.pending_resolutions
        ],
        "compatible_opposite_acts": [
            str(item) for item in act.compatible_opposite_acts
        ],
        "target_interim_until": (
            None
            if act.target_interim_until is None
            else act.target_interim_until.isoformat()
        ),
        "catalog_interim_until": (
            None
            if act.catalog_interim_until is None
            else act.catalog_interim_until.isoformat()
        ),
        "contested_target": act.contested_target,
        "contested_catalog": act.contested_catalog,
    }


def _optional_uuid(value: object, field: str) -> UUID | None:
    return None if value is None else uuid_value(value, field)


def _optional_time(value: object, field: str) -> datetime | None:
    return None if value is None else iso_aware_datetime(value, field)


def _act_from_row(row: RowMapping) -> PortfolioJudgmentAct:
    try:
        return _decode_act_row(row)
    except (KeyError, IndexError) as error:
        raise ValueError("incomplete Portfolio judgment act payload") from error


def _decode_act_row(row: RowMapping) -> PortfolioJudgmentAct:
    payload = json_object(row["act"], "act")
    if payload.get("schema") != "polaris.portfolio-judgment-act/v1":
        raise ValueError("unsupported Portfolio judgment act schema")
    consequence_id = row["consequence_id"]
    assessment_id = row["assessment_id"]
    root: PortfolioJudgmentRoot
    if consequence_id is not None and assessment_id is None:
        root = ProjectedPortfolioConsequenceRef(
            uuid_value(consequence_id, "consequence_id")
        )
    elif assessment_id is not None and consequence_id is None:
        root = PortfolioRiskAssessmentRef(uuid_value(assessment_id, "assessment_id"))
    else:
        raise ValueError("act must have exactly one typed Portfolio root")
    if "basis" not in payload:
        raise ValueError("incomplete Portfolio judgment act payload")
    resolutions = payload.get("pending_resolutions")
    compatible = payload.get("compatible_opposite_acts")
    ancestry = payload.get("ancestry")
    if (
        not isinstance(resolutions, list)
        or not isinstance(compatible, list)
        or not isinstance(ancestry, list)
    ):
        raise ValueError("act ancestry and resolutions must be complete lists")
    assertion = payload.get("assertion")
    catalog = payload.get("catalog")
    return PortfolioJudgmentAct(
        act_id=uuid_value(row["act_id"], "act_id"),
        root=root,
        attribution=actor_from_columns(
            json_object(payload.get("attribution"), "attribution")
        ),
        basis=nonempty_string(payload.get("basis"), "correction basis"),
        effective_at=row["effective_at"],
        recorded_at=row["recorded_at"],
        known_at=row["known_at"],
        ancestry=tuple(uuid_value(item, "ancestor") for item in ancestry),
        assertion=(
            None
            if assertion is None
            else _assertion_from_payload(assertion, row["known_at"])
        ),
        catalog=None if catalog is None else _catalog_from_payload(catalog),
        target_predecessor=_optional_uuid(
            payload.get("target_predecessor"), "target_predecessor"
        ),
        catalog_predecessor=_optional_uuid(
            payload.get("catalog_predecessor"), "catalog_predecessor"
        ),
        pending_resolutions=tuple(
            PendingResolution(
                PortfolioJudgmentLane(value["lane"]),
                uuid_value(value["pending_act_id"], "pending_act_id"),
                PendingDisposition(value["disposition"]),
            )
            for value in resolutions
        ),
        compatible_opposite_acts=tuple(
            uuid_value(item, "compatible act") for item in compatible
        ),
        target_interim_until=_optional_time(
            payload.get("target_interim_until"), "target_interim_until"
        ),
        catalog_interim_until=_optional_time(
            payload.get("catalog_interim_until"), "catalog_interim_until"
        ),
        contested_target=payload["contested_target"],
        contested_catalog=payload["contested_catalog"],
    )


def _act_values(
    act: PortfolioJudgmentAct,
    sequence: int,
    judgment_revision: JudgmentRevision,
    catalog_version: ClaimCatalogVersion,
) -> dict[str, object]:
    return {
        "act_id": act.act_id,
        "sequence": sequence,
        "consequence_id": (
            act.root.value
            if type(act.root) is ProjectedPortfolioConsequenceRef
            else None
        ),
        "assessment_id": (
            act.root.value if type(act.root) is PortfolioRiskAssessmentRef else None
        ),
        "effective_at": act.effective_at,
        "recorded_at": act.recorded_at,
        "known_at": act.known_at,
        "judgment_revision": judgment_revision.value,
        "claim_catalog_version": catalog_version.value,
        "act": _act_payload(act),
    }


async def insert_initial_portfolio_judgment_act(
    connection: AsyncConnection,
    assertion: PortfolioJudgmentAssertion,
    known_at: datetime,
    initial_claim_catalog: PortfolioClaimCatalog,
) -> None:
    """Join root creation and its declared complete catalog in one transaction."""
    if type(initial_claim_catalog) is not PortfolioClaimCatalog:
        raise TypeError("initial_claim_catalog must be PortfolioClaimCatalog")
    root = (
        assertion.consequence_id
        if type(assertion) is ProjectedPortfolioConsequence
        else assertion.assessment_id
    )
    initial = PortfolioJudgmentAct(
        act_id=uuid4(),
        root=root,
        attribution=assertion.attribution,
        basis=assertion.scenario,
        effective_at=assertion.formed_at,
        recorded_at=known_at,
        known_at=known_at,
        ancestry=(),
        assertion=assertion,
        catalog=initial_claim_catalog,
    )
    history = PortfolioJudgmentHistory.form(initial)
    await connection.execute(
        insert(portfolio_judgment_acts).values(
            _act_values(initial, 1, *history.versions[0])
        )
    )


class PostgresPortfolioJudgmentHistoryStore:
    """Serialize same-root correction admission under the immutable root row lock."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        validation_connection: AsyncConnection | None = None,
    ) -> None:
        require_qualified_postgres_runtime()
        self._engine = engine
        if (
            validation_connection is not None
            and validation_connection.engine is not engine
        ):
            raise ValueError("validation connection must use the owner engine")
        self._validation_connection = validation_connection

    def for_validation(
        self, connection: AsyncConnection
    ) -> PostgresPortfolioJudgmentHistoryStore:
        """Join a consuming write; its transaction retains a shared root lock."""
        if not connection.in_transaction():
            raise ValueError("owner validation requires an open write transaction")
        return PostgresPortfolioJudgmentHistoryStore(
            self._engine, validation_connection=connection
        )

    async def load(
        self, root: PortfolioJudgmentRoot
    ) -> PortfolioJudgmentHistory | None:
        if self._validation_connection is not None:
            connection = self._validation_connection
            if not connection.in_transaction():
                raise PortfolioJudgmentHistoryUnavailable(
                    "owner validation transaction is closed"
                )
            try:
                identity = _root_identity(root)
                await connection.scalar(
                    select(identity)
                    .where(identity == root.value)
                    .with_for_update(read=True)
                )
                return await _load(connection, root)
            except SQLAlchemyError as error:
                raise PortfolioJudgmentHistoryUnavailable(
                    "history validation read failed"
                ) from error
        try:
            async with self._engine.connect() as connection:
                return await _load(connection, root)
        except SQLAlchemyError as error:
            raise PortfolioJudgmentHistoryUnavailable("history read failed") from error

    async def append(self, act: PortfolioJudgmentAct) -> PortfolioJudgmentHistory:
        if self._validation_connection is not None:
            raise ValueError("validation reader cannot append owner acts")
        try:
            async with self._engine.begin() as connection:
                identity = _root_identity(act.root)
                locked = await connection.scalar(
                    select(identity).where(identity == act.root.value).with_for_update()
                )
                if locked is None:
                    raise ValueError("Portfolio judgment root does not exist")
                history = await _load(connection, act.root)
                if history is None:
                    raise ValueError("Portfolio judgment history is missing")
                changed = history.append(act)
                await connection.execute(
                    insert(portfolio_judgment_acts).values(
                        _act_values(act, len(changed.acts), *changed.versions[-1])
                    )
                )
                return changed
        except SQLAlchemyError as error:
            raise PortfolioJudgmentHistoryUnavailable(
                "history append failed"
            ) from error


def _root_identity(root: PortfolioJudgmentRoot):
    if type(root) is ProjectedPortfolioConsequenceRef:
        return projected_portfolio_consequences.c.consequence_id
    if type(root) is PortfolioRiskAssessmentRef:
        return portfolio_risk_assessments.c.assessment_id
    raise TypeError("root must be a Portfolio Evidence target")


async def _load(
    connection: AsyncConnection, root: PortfolioJudgmentRoot
) -> PortfolioJudgmentHistory | None:
    if type(root) is ProjectedPortfolioConsequenceRef:
        predicate = portfolio_judgment_acts.c.consequence_id == root.value
    elif type(root) is PortfolioRiskAssessmentRef:
        predicate = portfolio_judgment_acts.c.assessment_id == root.value
    else:
        raise TypeError("root must be a Portfolio Evidence target")
    rows = (
        (
            await connection.execute(
                select(portfolio_judgment_acts)
                .where(predicate)
                .order_by(portfolio_judgment_acts.c.sequence)
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return None
    first = _act_from_row(rows[0])
    if (
        rows[0]["sequence"] != 1
        or rows[0]["judgment_revision"] != 1
        or rows[0]["claim_catalog_version"] != 1
    ):
        raise ValueError("initial owner versions or sequence are invalid")
    history = PortfolioJudgmentHistory.form(first)
    for sequence, row in enumerate(rows[1:], start=2):
        if row["sequence"] != sequence:
            raise ValueError("Portfolio judgment act sequence is incomplete")
        history = history.append(_act_from_row(row))
        if (
            history.versions[-1][0].value != row["judgment_revision"]
            or history.versions[-1][1].value != row["claim_catalog_version"]
        ):
            raise ValueError("persisted owner versions contradict complete history")
    return history
