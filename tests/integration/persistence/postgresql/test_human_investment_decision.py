"""Governance decision admission and restart reconstruction against PostgreSQL."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import DBAPIError

from polaris.application.decisions import (
    ApplySubstantiveResolutionCommand,
    DecisionCommandEnvelope,
    DecisionInitiationService,
    DecisionOrdinaryWorkService,
    ExpectedDecisionVersion,
    InitiateDecisionCommand,
)
from polaris.application.evidence.claims import (
    ClaimCatalogResolver,
    ClaimNotKnownAtCutoff,
    ResolvedClaimMembership,
)
from polaris.application.evidence.context_versions import (
    ContextNoBasis,
    ContextNoBasisReason,
)
from polaris.application.governance_context import GovernanceContextOwner
from polaris.application.human_investment_decision import HumanInvestmentDecisionService
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    DecisionLifecycleDisposition,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    HumanInvestmentDecisionEffect,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence import InvestmentAuthorityRegimeId
from polaris.domain.evidence.context_versions import BasisScopeKey, ContextSelectionRole
from polaris.domain.evidence.judgments import (
    ClaimId,
    EvidenceUse,
    HumanInvestmentDecisionRef,
    JudgmentWideEvidenceScope,
)
from polaris.domain.governance_authority import (
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
)
from polaris.domain.governance_claim_catalog import (
    GovernanceClaim,
    GovernanceClaimCatalog,
)
from polaris.domain.governance_judgment_history import (
    HumanDecisionTargetCorrectionDraft,
    HumanDecisionTargetEffect,
)
from polaris.domain.governance_regime_history import (
    AuthorityRegimeCorrectionDraft,
    AuthorityRegimeStatus,
)
from polaris.domain.human_investment_decision import (
    HumanInvestmentDecision,
    HumanInvestmentDecisionDraft,
    InvalidHumanInvestmentDecision,
)
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.portfolio import PortfolioId
from polaris.infrastructure.persistence.postgresql import (
    PostgresDecisionStore,
    PostgresGovernanceStore,
    create_postgres_engine,
    create_postgres_human_decision_service,
)
from polaris.infrastructure.persistence.postgresql.governance import (
    HumanDecisionConflict,
)
from polaris.infrastructure.persistence.postgresql.governance_claim_catalog import (
    PostgresGovernanceClaimCatalogStore,
)
from polaris.infrastructure.persistence.postgresql.governance_history import (
    PostgresHumanDecisionTargetHistoryStore,
)
from polaris.infrastructure.persistence.postgresql.governance_regime_history import (
    PostgresAuthorityRegimeHistoryStore,
)
from polaris.infrastructure.persistence.postgresql.intelligence_contract_codec import (
    contract_value_payload,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    authority_regime_corrections,
    human_decision_act_publications,
    human_decision_target_corrections,
    human_investment_decisions,
)

from .conftest import PostgresTestTarget

AT = datetime(2026, 11, 1, 12, tzinfo=UTC)
EMPTY_CATALOG = GovernanceClaimCatalog(())


async def _record(
    service: HumanInvestmentDecisionService,
    operation: OperationId,
    draft: HumanInvestmentDecisionDraft,
    version: DecisionVersion,
) -> HumanInvestmentDecision:
    return await service.record(
        operation, draft, version, initial_claim_catalog=EMPTY_CATALOG
    )


async def _scenario(target: PostgresTestTarget) -> None:
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    portfolio_id = PortfolioId(uuid4())
    actor = KnownActorAttribution(ActorId(uuid4()))
    try:
        decisions = PostgresDecisionStore(engine)
        # duplicate-code: This independent Governance persistence proof
        # initiates a real Decision; sharing the sibling test's setup would
        # make both proofs depend on one fixture's command construction.
        # arid: disable
        accepted = await DecisionInitiationService(
            reader=decisions, store=decisions, now=lambda: AT
        ).initiate(
            InitiateDecisionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "human-479"),
                    effective_at=AT,
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(),
                ),
                need_statement="Choose SPY exposure",
                subject=DecisionSubject("Increase, hold, or reduce SPY"),
                scope=DecisionScope.established(portfolio_id),
            )
        )
        # arid: enable
        state = await decisions.load_decision_for_command(
            accepted.decision_id, known_at=AT
        )
        assert state is not None
        regime = InvestmentAuthorityRegime(
            InvestmentAuthorityRegimeId(uuid4()),
            actor.actor_id,
            portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            AT - timedelta(days=1),
            AT + timedelta(days=1),
        )
        store = PostgresGovernanceStore(engine)
        await store.install_regime(regime)
        regime_store = PostgresAuthorityRegimeHistoryStore(engine)
        installed = await regime_store.load(regime.regime_id)
        assert installed is not None
        assert installed.revisions[-1].value == 1
        service = create_postgres_human_decision_service(engine, now=lambda: AT)
        draft = HumanInvestmentDecisionDraft(
            decision_ref=HumanInvestmentDecisionRef(uuid4()),
            investment_decision_id=accepted.decision_id,
            portfolio_id=portfolio_id,
            actor=actor,
            choice=EconomicDisposition.HOLD,
            effect=HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
            authority_regime_id=regime.regime_id,
            material_rationale="Hold until the next decision horizon",
        )
        operation = OperationId(uuid4())
        fact = await _record(service, operation, draft, state.decision.version)
        catalog_store = PostgresGovernanceClaimCatalogStore(engine)
        initial_catalog = await catalog_store.load_claim_catalog(fact.decision_ref)
        assert len(initial_catalog) == 1
        assert not initial_catalog[0].claim_ids
        assert initial_catalog[0].version.value == 1
        assert fact.made_at == AT
        assert await _record(service, operation, draft, state.decision.version) == fact
        assert await service.get(fact.decision_ref) == fact
        target_store = PostgresHumanDecisionTargetHistoryStore(engine)
        target_history = await target_store.load(fact.decision_ref)
        assert target_history is not None
        initial = target_history.select(
            target_history.root_known_at, target_history.root_known_at
        )
        assert initial.version.revision.value == 1
        assert initial.assertion == fact
        corrected = replace(fact, material_rationale="Corrected recorded rationale")
        correction = HumanDecisionTargetCorrectionDraft(
            uuid4(),
            fact.decision_ref,
            fact.decision_ref,
            actor,
            "Correct the recorded rationale",
            AT,
            HumanDecisionTargetEffect.REVISE,
            corrected,
            GovernanceClaimCatalog(
                (
                    GovernanceClaim(
                        ClaimId(uuid4()), "Hold exposure pending review", frozenset()
                    ),
                )
            ),
        )
        correction_operation = OperationId(uuid4())
        target_history = await target_store.append(correction_operation, correction)
        assert target_history.revisions[-1].value == 2
        catalog_history = await catalog_store.load_claim_catalog(fact.decision_ref)
        assert len(catalog_history) == 2
        claim_id = correction.catalog.claims[0].claim_id
        claim_resolver = ClaimCatalogResolver(catalog_store)
        assert isinstance(
            await claim_resolver.resolve(
                fact.decision_ref,
                claim_id,
                effective_at=AT,
                known_at=initial_catalog[0].recorded_at,
            ),
            ClaimNotKnownAtCutoff,
        )
        # duplicate-code: Cutoff and current catalog assertions independently exercise
        # the same resolver with distinct knowledge times.
        # arid: disable
        assert isinstance(
            await claim_resolver.resolve(
                fact.decision_ref,
                claim_id,
                effective_at=AT,
                # arid: enable
                known_at=catalog_history[1].recorded_at,
            ),
            ResolvedClaimMembership,
        )
        assert (
            await target_store.append(correction_operation, correction)
            == target_history
        )
        current = target_history.select(
            target_history.corrections[-1].known_at,
            target_history.corrections[-1].known_at,
        )
        assert current.assertion == corrected
        assert (
            target_history.select(
                current.effective_at, target_history.root_known_at
            ).assertion
            == fact
        )
        assert await service.get(fact.decision_ref) == fact
        unarchived = HumanDecisionTargetCorrectionDraft(
            uuid4(),
            fact.decision_ref,
            correction.correction_id,
            actor,
            "Correct the correction's recorded rationale",
            AT,
            HumanDecisionTargetEffect.REVISE,
            replace(fact, material_rationale="Second corrected rationale"),
        )
        async with engine.begin() as connection:
            await connection.execute(
                insert(human_decision_target_corrections).values(
                    correction_id=unarchived.correction_id,
                    operation_id=uuid4(),
                    decision_ref=fact.decision_ref.value,
                    sequence=2,
                    effective_at=unarchived.effective_at,
                    draft=contract_value_payload(unarchived),
                )
            )
            before_commit = await connection.scalar(select(func.clock_timestamp()))
            assert isinstance(before_commit, datetime)
            await asyncio.sleep(0.03)
        async with engine.connect() as connection:
            # duplicate-code: This assertion proves an unarchived correction
            # is recovered from WAL, independently of the root publication.
            # arid: disable
            assert (
                await connection.scalar(
                    select(human_decision_act_publications.c.act_id).where(
                        human_decision_act_publications.c.act_id
                        == unarchived.correction_id
                    )
                )
                is None
            )
            # arid: enable
        target_history = await target_store.load(fact.decision_ref)
        assert target_history is not None
        committed_at = target_history.corrections[-1].known_at
        assert committed_at > before_commit
        assert target_history.select(committed_at, before_commit).assertion == corrected
        assert (
            target_history.select(committed_at, committed_at).assertion
            == unarchived.replacement
        )
        with pytest.raises(InvalidHumanInvestmentDecision, match="another request"):
            await _record(
                service,
                operation,
                replace(draft, material_rationale="Changed"),
                state.decision.version,
            )
        with pytest.raises(HumanDecisionConflict, match="version changed"):
            await _record(
                service,
                OperationId(uuid4()),
                replace(draft, decision_ref=HumanInvestmentDecisionRef(uuid4())),
                DecisionVersion(999),
            )
        async with engine.connect() as connection:
            rows = (
                (await connection.execute(select(human_investment_decisions)))
                .mappings()
                .all()
            )
            assert len(rows) == 1
            assert rows[0]["choice"] == "hold"
            assert rows[0]["effect"] == "substantively_resolving"
            assert (
                await connection.scalar(
                    select(human_decision_act_publications.c.act_id).where(
                        human_decision_act_publications.c.act_id
                        == fact.decision_ref.value
                    )
                )
                == fact.decision_ref.value
            )
            correction_ids = set(
                (
                    await connection.execute(
                        select(human_decision_target_corrections.c.correction_id)
                    )
                ).scalars()
            )
            assert correction_ids == {
                correction.correction_id,
                unarchived.correction_id,
            }
        with pytest.raises(DBAPIError, match="immutable Governance fact"):
            async with engine.begin() as connection:
                await connection.execute(
                    update(human_investment_decisions)
                    .where(
                        human_investment_decisions.c.decision_ref
                        == fact.decision_ref.value
                    )
                    .values(material_rationale="rewritten")
                )
        basis = await service.trusted_basis(fact.decision_ref, accepted.decision_id)
        assert basis is not None
        with pytest.raises(InvalidHumanInvestmentDecision, match="another Decision"):
            await service.trusted_basis(
                fact.decision_ref, type(accepted.decision_id)(uuid4())
            )
        await DecisionOrdinaryWorkService(
            store=decisions, now=lambda: AT + timedelta(seconds=1)
        ).apply_substantive_resolution(
            ApplySubstantiveResolutionCommand(
                # duplicate-code: This Governance-to-Decisions proof owns a
                # distinct real lifecycle command with its own actor and basis.
                # arid: disable
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(
                        TriggerKind.HUMAN_REQUEST, "human-479-hold"
                    ),
                    effective_at=AT + timedelta(seconds=1),
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(
                        {
                            ExpectedDecisionVersion(
                                accepted.decision_id, state.decision.version
                            )
                        }
                    ),
                ),
                # arid: enable
                decision_id=accepted.decision_id,
                basis=basis,
            )
        )
        resolved = await decisions.load_decision_for_command(
            accepted.decision_id, known_at=AT + timedelta(seconds=1)
        )
        assert resolved is not None
        assert (
            resolved.decision.lifecycle_interpretation.disposition
            is DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
        )
        async with engine.connect() as connection:
            action_intent_tables = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = current_schema() "
                    "AND table_name LIKE '%action_intent%'"
                )
            )
        assert action_intent_tables == 0
        key = BasisScopeKey(
            accepted.decision_id,
            fact.decision_ref,
            JudgmentWideEvidenceScope(),
            EvidenceUse.JUDGMENT_BASIS,
        )
        owner = GovernanceContextOwner(regime_store, target_store)
        before_correction = await owner.read_at(
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=AT,
            known_at=target_history.root_known_at,
        )
        assert not isinstance(before_correction, ContextNoBasis)
        assert before_correction.facts[0].reference.revision.value == 1
        contested = AuthorityRegimeCorrectionDraft(
            uuid4(),
            regime.regime_id,
            actor,
            "authority now contested",
            AT,
            AuthorityRegimeStatus.CONTESTED,
            None,
        )
        revised_regime = await regime_store.append(OperationId(uuid4()), contested)
        assert revised_regime.revisions[-1].value == 2
        assert await store.authority_regime(regime.regime_id) is None
        after_correction = await owner.read_at(
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=AT,
            known_at=revised_regime.corrections[-1].known_at,
        )
        assert isinstance(after_correction, ContextNoBasis)
        assert after_correction.reason is ContextNoBasisReason.CONTESTED
        recovered_draft = AuthorityRegimeCorrectionDraft(
            uuid4(),
            regime.regime_id,
            actor,
            "authoritative review restored power",
            AT,
            AuthorityRegimeStatus.DETERMINATE,
            regime,
        )
        async with engine.begin() as connection:
            await connection.execute(
                insert(authority_regime_corrections).values(
                    correction_id=recovered_draft.correction_id,
                    operation_id=uuid4(),
                    regime_id=regime.regime_id.value,
                    sequence=2,
                    effective_at=AT,
                    draft=contract_value_payload(recovered_draft),
                )
            )
            before_regime_commit = await connection.scalar(
                select(func.clock_timestamp())
            )
            assert isinstance(before_regime_commit, datetime)
            await asyncio.sleep(0.03)
        revised_regime = await regime_store.load(regime.regime_id)
        assert revised_regime is not None
        assert revised_regime.revisions[-1].value == 3
        assert revised_regime.corrections[-1].known_at > before_regime_commit
        assert (
            revised_regime.select(AT, before_regime_commit).status
            is AuthorityRegimeStatus.CONTESTED
        )
        assert (
            revised_regime.select(AT, revised_regime.corrections[-1].known_at).regime
            == regime
        )
        store_now = datetime.now(UTC)
        later_regime = replace(
            regime,
            regime_id=InvestmentAuthorityRegimeId(uuid4()),
            effective_from=store_now - timedelta(hours=1),
            effective_until=store_now + timedelta(days=1),
        )
        await store.install_regime(later_regime)
        await regime_store.append(
            OperationId(uuid4()),
            AuthorityRegimeCorrectionDraft(
                uuid4(),
                later_regime.regime_id,
                actor,
                "backdated power under a later correction",
                store_now - timedelta(minutes=30),
                AuthorityRegimeStatus.DETERMINATE,
                replace(later_regime, effective_from=AT - timedelta(days=1)),
            ),
        )
        with pytest.raises(InvalidHumanInvestmentDecision, match="unestablished"):
            await target_store.append(
                OperationId(uuid4()),
                HumanDecisionTargetCorrectionDraft(
                    uuid4(),
                    fact.decision_ref,
                    unarchived.correction_id,
                    actor,
                    "correct authority at the historical act time",
                    store_now,
                    HumanDecisionTargetEffect.REVISE,
                    replace(
                        fact,
                        authority_regime_id=later_regime.regime_id,
                        material_rationale="Later regime cannot authorize this act",
                    ),
                ),
            )
    finally:
        await engine.dispose()

    # duplicate-code: Each owner has a separate restart reconstruction proof;
    # sharing this scaffold would couple their independent persistence checks.
    # arid: disable
    restarted = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        service = create_postgres_human_decision_service(restarted)
        assert await service.get(fact.decision_ref) == fact
        assert await service.history(accepted.decision_id) == (fact,)
        target_history_after_restart = await PostgresHumanDecisionTargetHistoryStore(
            restarted
        ).load(fact.decision_ref)
        assert target_history_after_restart == target_history
        assert (
            await PostgresGovernanceClaimCatalogStore(restarted).load_claim_catalog(
                fact.decision_ref
            )
            == catalog_history
        )
        assert (
            await PostgresAuthorityRegimeHistoryStore(restarted).load(regime.regime_id)
            == revised_regime
        )
    finally:
        await restarted.dispose()
    # arid: enable


def test_human_hold_is_durable_and_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_scenario(postgres_target))
