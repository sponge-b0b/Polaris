"""Focused durable correction proof shared by the two Portfolio target families."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.evidence.claims import InvalidClaimHistory
from polaris.application.evidence.judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentInvalidHistory,
)
from polaris.application.evidence.owner_meaning import (
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    TargetJudgmentMeaning,
)
from polaris.application.portfolio_judgment_history import (
    PortfolioJudgmentClaimResolver,
    PortfolioJudgmentMeaningReader,
    PortfolioJudgmentTargetReader,
)
from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.judgments import (
    ClaimId,
    EvidenceUse,
    JudgmentWideEvidenceScope,
)
from polaris.domain.evidence.observations import EvidenceObservationId
from polaris.domain.portfolio_judgment_history import (
    InvalidPortfolioJudgmentHistory,
    PendingDisposition,
    PendingResolution,
    PortfolioClaim,
    PortfolioClaimCatalog,
    PortfolioJudgmentAct,
    PortfolioJudgmentAssertion,
    PortfolioJudgmentLane,
)
from polaris.infrastructure.persistence.postgresql.portfolio_judgment_history import (
    PostgresPortfolioJudgmentHistoryStore,
)
from polaris.infrastructure.persistence.postgresql.schema import portfolio_judgment_acts


def _root(assertion: PortfolioJudgmentAssertion):
    return getattr(assertion, "consequence_id", None) or assertion.assessment_id


def _catalog(proposition: str) -> PortfolioClaimCatalog:
    return PortfolioClaimCatalog(
        (
            PortfolioClaim(
                ClaimId(uuid4()),
                proposition,
                frozenset({EvidenceObservationId(uuid4())}),
            ),
        )
    )


async def prove_durable_corrections(
    engine: AsyncEngine,
    assertion: PortfolioJudgmentAssertion,
    disposition: PendingDisposition,
) -> None:
    root = _root(assertion)
    store = PostgresPortfolioJudgmentHistoryStore(engine)
    history = await store.load(root)
    assert history is not None
    assert len(history.acts) == 1
    assert history.acts[0].assertion == assertion
    assert history.acts[0].catalog == PortfolioClaimCatalog(())
    initial = history.acts[0]
    k1 = initial.known_at + timedelta(minutes=1)
    k2 = initial.known_at + timedelta(minutes=2)
    t3 = initial.known_at + timedelta(days=3)
    future = PortfolioJudgmentAct(
        uuid4(),
        root,
        assertion.attribution,
        "future owner correction",
        t3,
        k1,
        k1,
        (initial.act_id,),
        assertion=replace(assertion, scenario="Future B scenario"),
        catalog=_catalog("Future B proposition"),
        target_predecessor=initial.act_id,
        catalog_predecessor=initial.act_id,
    )
    async with engine.begin() as dependent_write:
        enrolled = store.for_validation(dependent_write)
        assert await enrolled.load(root) == history
        with pytest.raises(ValueError, match="cannot append"):
            await enrolled.append(future)
        waiting_correction = asyncio.create_task(store.append(future))
        await asyncio.sleep(0.05)
        assert not waiting_correction.done()
    history = await waiting_correction
    assert history.select(k1, k1).assertion == assertion
    assert history.select(t3, k1).assertion == future.assertion
    assert history.versions[-1][0].value == 1
    assert history.versions[-1][1].value == 1
    interim_until = t3 if disposition is PendingDisposition.RETAIN else None
    immediate = PortfolioJudgmentAct(
        uuid4(),
        root,
        assertion.attribution,
        "immediate owner correction",
        k2,
        k2,
        k2,
        (initial.act_id, future.act_id),
        assertion=replace(assertion, scenario="Immediate C scenario"),
        catalog=_catalog("Immediate C proposition"),
        target_predecessor=initial.act_id,
        catalog_predecessor=initial.act_id,
        pending_resolutions=tuple(
            PendingResolution(lane, future.act_id, disposition)
            for lane in PortfolioJudgmentLane
        ),
        target_interim_until=interim_until,
        catalog_interim_until=interim_until,
    )
    bad = replace(
        immediate,
        pending_resolutions=(),
        target_interim_until=None,
        catalog_interim_until=None,
    )
    with pytest.raises(InvalidPortfolioJudgmentHistory, match="pending"):
        await store.append(bad)
    unchanged = await store.load(root)
    assert unchanged == history
    history = await store.append(immediate)
    assert history.versions[-1][0].value == 2
    assert history.versions[-1][1].value == 2
    assert history.select(t3, k1).assertion == future.assertion
    assert history.select(k2, k2).assertion == immediate.assertion
    expected = future if disposition is PendingDisposition.RETAIN else immediate
    assert history.select(t3, t3).assertion == expected.assertion
    assert history.select(t3, t3).catalog == expected.catalog
    assert history.select(t3, t3).judgment_revision.value == 2
    restarted = PostgresPortfolioJudgmentHistoryStore(engine)
    assert await restarted.load(root) == history
    async with engine.connect() as connection:
        count = await connection.scalar(
            select(func.count()).select_from(portfolio_judgment_acts)
        )
    assert count is not None and count >= 3
    with pytest.raises(DBAPIError):
        async with engine.begin() as connection:
            await connection.execute(
                update(portfolio_judgment_acts)
                .where(portfolio_judgment_acts.c.act_id == future.act_id)
                .values(judgment_revision=99)
            )
    target_reader = PortfolioJudgmentTargetReader(restarted)
    before_corruption = await target_reader.read_at(root, effective_at=k2, known_at=k2)
    assert isinstance(before_corruption, ResolvedTargetJudgment)
    async with engine.connect() as connection:
        row = (
            (
                await connection.execute(
                    select(portfolio_judgment_acts).where(
                        portfolio_judgment_acts.c.act_id == immediate.act_id
                    )
                )
            )
            .mappings()
            .one()
        )
    catalog = immediate.catalog
    assert catalog is not None
    # duplicate-code: durable malformed-row proof constructs its own exact
    # Evidence key so unit and PostgreSQL falsifiers remain independent.
    # arid: disable
    key = BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        root,
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )
    # arid: enable
    for corruption in ("missing basis", "null basis", "null proposition"):
        malformed = dict(row)
        malformed["act_id"] = uuid4()
        malformed["sequence"] = len(history.acts) + 1
        payload = dict(row["act"])
        if corruption == "missing basis":
            payload.pop("basis")
        elif corruption == "null basis":
            payload["basis"] = None
        else:
            claims = [dict(claim) for claim in payload["catalog"]]
            claims[0]["proposition"] = None
            payload["catalog"] = claims
        malformed["act"] = payload
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(
                    insert(portfolio_judgment_acts).values(**malformed)
                )
                invalid_store = restarted.for_validation(connection)
                assert isinstance(
                    await PortfolioJudgmentTargetReader(invalid_store).read_at(
                        root, effective_at=k2, known_at=k2
                    ),
                    TargetJudgmentInvalidHistory,
                ), corruption
                claim = await PortfolioJudgmentClaimResolver(invalid_store).resolve(
                    root, catalog.claims[0].claim_id, effective_at=k2, known_at=k2
                )
                assert isinstance(claim, InvalidClaimHistory), corruption
                meaning = await PortfolioJudgmentMeaningReader(invalid_store).read_at(
                    key,
                    TargetJudgmentMeaning(before_corruption.version),
                    effective_at=k2,
                    known_at=k2,
                    read_at=k2,
                )
                assert isinstance(meaning, OwnerMeaningNoBasis), corruption
                assert meaning.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY
            finally:
                await transaction.rollback()
