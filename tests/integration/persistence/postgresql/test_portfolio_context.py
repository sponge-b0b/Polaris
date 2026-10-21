"""Portfolio context owner history survives a PostgreSQL adapter restart."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update
from sqlalchemy.exc import DBAPIError

from polaris.application.evidence.context_versions import (
    ContextContribution,
    ResolvedContextSelection,
)
from polaris.application.portfolio_context import (
    PortfolioContextCommit,
    PortfolioContextFactAct,
    PortfolioContextOwner,
    PortfolioContextSelectionAct,
)
from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextSelectionRole,
    PortfolioBoundaryId,
    PortfolioBoundaryRevision,
    PortfolioBoundaryVersionRef,
)
from polaris.domain.evidence.judgments import (
    EvidenceUse,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
)
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId
from polaris.domain.portfolio_context import PortfolioBoundaryMeaning
from polaris.infrastructure.persistence.postgresql import (
    PostgresPortfolioContextHistoryStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    portfolio_context_commits,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store


def test_context_versions_and_selection_survive_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        at = datetime(2026, 1, 1, tzinfo=UTC)
        later = at + timedelta(days=1)
        next_day = later + timedelta(days=1)
        # duplicate-code: the restart proof constructs its own Evidence scope.
        # arid: disable
        key = BasisScopeKey(
            InvestmentDecisionId(uuid4()),
            InvestmentViewRef(uuid4()),
            JudgmentWideEvidenceScope(),
            EvidenceUse.JUDGMENT_BASIS,
        )
        # arid: enable
        root = PortfolioBoundaryId(uuid4())
        role = ContextSelectionRole.PORTFOLIO_BOUNDARY
        initial = PortfolioBoundaryMeaning(
            PortfolioId(uuid4()), FinancialInstrumentId(uuid4()), "SPY only"
        )
        first_ref = PortfolioBoundaryVersionRef(root, PortfolioBoundaryRevision(1))
        first_fact = PortfolioContextFactAct(
            uuid4(),
            first_ref,
            initial,
            at,
            at,
            "Portfolio boundary owner",
            frozenset({ContextContribution.APPLICABILITY}),
        )
        first_selection = PortfolioContextSelectionAct(
            uuid4(),
            key,
            role,
            frozenset({root}),
            at,
            at,
            "material Portfolio boundary for this exact Evidence key",
        )
        # duplicate-code: separate store lifetimes prove the restart boundary.
        # arid: disable
        async with postgres_store(
            postgres_target, PostgresPortfolioContextHistoryStore
        ) as (engine, store):
            owner = PortfolioContextOwner(store)
            await owner.commit(
                PortfolioContextCommit(uuid4(), at, (first_fact,), (first_selection,))
            )
            assert await postgres_row_counts(engine, portfolio_context_commits) == (1,)
        # arid: enable
        async with postgres_store(
            postgres_target, PostgresPortfolioContextHistoryStore
        ) as (engine, store):
            owner = PortfolioContextOwner(store)
            previous = await owner.read_at(key, role, effective_at=at, known_at=at)
            assert type(previous) is ResolvedContextSelection
            assert previous.facts[0].reference == first_ref
            corrected = PortfolioBoundaryMeaning(
                initial.portfolio_id,
                initial.instrument_id,
                "SPY plus cash inside one Portfolio",
            )
            next_ref = PortfolioBoundaryVersionRef(root, PortfolioBoundaryRevision(2))
            await owner.commit(
                PortfolioContextCommit(
                    uuid4(),
                    later,
                    (
                        PortfolioContextFactAct(
                            uuid4(),
                            next_ref,
                            corrected,
                            later,
                            later,
                            "Portfolio boundary correction",
                            frozenset({ContextContribution.APPLICABILITY}),
                        ),
                    ),
                    (),
                )
            )
            current = await owner.read_at(key, role, effective_at=later, known_at=later)
            historical = await owner.read_at(key, role, effective_at=at, known_at=at)
            assert type(current) is ResolvedContextSelection
            assert type(historical) is ResolvedContextSelection
            assert current.facts[0].reference == next_ref
            assert historical.facts[0].reference == first_ref
            assert current.guard == historical.guard
            assert await postgres_row_counts(engine, portfolio_context_commits) == (2,)
            other_key = replace(key, decision_id=InvestmentDecisionId(uuid4()))
            await owner.commit(
                PortfolioContextCommit(
                    uuid4(),
                    next_day,
                    (),
                    (
                        PortfolioContextSelectionAct(
                            uuid4(),
                            other_key,
                            role,
                            frozenset({root}),
                            next_day,
                            next_day,
                            "same boundary used by another exact Evidence key",
                        ),
                    ),
                )
            )
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        update(portfolio_context_commits).values(
                            known_at=later + timedelta(hours=1)
                        )
                    )
        async with postgres_store(
            postgres_target, PostgresPortfolioContextHistoryStore
        ) as (_, store):
            owner = PortfolioContextOwner(store)
            first_key = await owner.read_at(
                key, role, effective_at=next_day, known_at=next_day
            )
            second_key = await owner.read_at(
                other_key, role, effective_at=next_day, known_at=next_day
            )
            assert type(first_key) is ResolvedContextSelection
            assert type(second_key) is ResolvedContextSelection
            assert first_key.facts[0].reference == next_ref
            assert first_key.guard == current.guard
            assert second_key.facts[0].reference == next_ref

    asyncio.run(scenario())
