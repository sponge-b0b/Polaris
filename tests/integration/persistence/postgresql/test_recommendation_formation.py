"""Recommendation finality consumes real Portfolio and Intelligence owner facts."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from polaris.application.decisions import (
    DecisionCommandEnvelope,
    DecisionInitiationService,
    InitiateDecisionCommand,
)
from polaris.application.evidence.current_basis import CurrentEvidenceBasis
from polaris.application.investment_intelligence import (
    FIRST_R3_SPY_INSTRUMENT_ID,
    InvestmentIntelligenceService,
    JudgmentReceipt,
)
from polaris.application.investment_recommendation import (
    InvestmentRecommendationService,
    RecommendationSupportKind,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import (
    DecisionScope,
    DecisionSubject,
    OperationId,
    TechnicalProvenance,
    TriggerKind,
    TriggerProvenance,
)
from polaris.domain.evidence.judgments import (
    InvestmentRecommendationRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    RecommendationWithholdingJudgmentRef,
)
from polaris.domain.intelligence_judgment_history import (
    IntelligenceClaimCatalog,
    IntelligenceJudgmentAct,
    IntelligenceJudgmentStatus,
)
from polaris.domain.investment_intelligence import (
    ChallengeDisposition,
    EconomicDisposition,
    InvalidInvestmentJudgment,
    InvestmentView,
    MeaningfulChallengeResult,
    R3InvestmentSlice,
)
from polaris.domain.investment_recommendation import (
    AlternativeConsequence,
    InvestmentRecommendation,
    RecommendationWithholdingJudgment,
)
from polaris.domain.portfolio import PortfolioStateId, RecordedPortfolioState
from polaris.domain.portfolio_judgment_history import (
    PortfolioClaimCatalog,
    PortfolioJudgmentAct,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresCurrentBasisReader,
    PostgresDecisionStore,
    PostgresIntelligenceJudgmentHistoryStore,
    PostgresInvestmentIntelligenceStore,
    PostgresPortfolioJudgmentHistoryStore,
    PostgresPortfolioStateStore,
    create_postgres_engine,
    create_postgres_portfolio_consequence_service,
    create_postgres_portfolio_risk_service,
)
from polaris.infrastructure.persistence.postgresql.intelligence_contract_codec import (
    register_owner_value_type,
)
from tests.domain.test_portfolio_consequences import (
    NOW,
    _alternatives,
    _consequences,
    _state,
)
from tests.domain.test_portfolio_risk import _support

from .conftest import PostgresTestTarget
from .test_intelligence_basis_commit import (
    _query_for_intelligence_target,
    _Relationship,
    _Universe,
)


class _PerTargetQuery:
    def __init__(self, queries) -> None:
        self.queries = queries

    async def read(self, key, *, at):
        return await self.queries[key.target].read(key, at=at)

    async def verify_owner_meaning(self, basis, *, validation_at):
        return await self.queries[basis.key.target].verify_owner_meaning(
            basis, validation_at=validation_at
        )


async def _scenario(target: PostgresTestTarget) -> None:
    register_owner_value_type(_Relationship)
    register_owner_value_type(_Universe)
    engine = create_postgres_engine(target.database_url, schema=target.schema)
    try:
        source = _state()
        await PostgresPortfolioStateStore(engine).append(source.state)
        actor = KnownActorAttribution(ActorId(uuid4()))
        decision_store = PostgresDecisionStore(engine)
        # duplicate-code: Sharing would couple Risk falsifiers.
        # arid: disable
        accepted = await DecisionInitiationService(
            reader=decision_store, store=decision_store, now=lambda: NOW
        ).initiate(
            InitiateDecisionCommand(
                envelope=DecisionCommandEnvelope(
                    operation_id=OperationId(uuid4()),
                    actor_attribution=actor,
                    trigger=TriggerProvenance(TriggerKind.HUMAN_REQUEST, "user-399"),
                    effective_at=NOW,
                    technical_provenance=TechnicalProvenance(),
                    expected_versions=frozenset(),
                ),
                need_statement="Choose SPY exposure",
                subject=DecisionSubject("Increase, hold, or reduce SPY"),
                scope=DecisionScope.established(source.state.portfolio_id),
            )
        )
        # arid: enable
        decision_state = await decision_store.load_decision_for_command(
            accepted.decision_id, known_at=NOW
        )
        assert decision_state is not None
        decision = decision_state.decision
        intelligence = PostgresInvestmentIntelligenceStore(engine)
        foundation = InvestmentIntelligenceService(intelligence)
        alternatives = _alternatives(source, decision.decision_id)
        await foundation.record_alternatives(
            OperationId(uuid4()), decision, alternatives
        )
        consequences = _consequences(source, alternatives)
        await create_postgres_portfolio_consequence_service(engine).produce(
            decision_id=decision.decision_id,
            source_state_id=source.state.state_id,
            consequences=consequences,
            initial_claim_catalogs={
                item.consequence_id: PortfolioClaimCatalog(()) for item in consequences
            },
        )
        risk = await create_postgres_portfolio_risk_service(engine).assess(
            assessment_id=PortfolioRiskAssessmentRef(uuid4()),
            # duplicate-code: Sharing would couple Risk falsifiers.
            # arid: disable
            source_state_id=source.state.state_id,
            projected_consequence_id=None,
            horizon=InvestmentHorizon("one quarter"),
            scenario="SPY downside over one quarter",
            support=_support(),
            attribution=actor,
            formed_at=NOW,
            initial_claim_catalog=PortfolioClaimCatalog(()),
        )
        # arid: enable
        # duplicate-code: Sharing would couple Risk falsifiers.
        # arid: disable
        view = InvestmentView(
            InvestmentViewRef(uuid4()),
            decision.decision_id,
            R3InvestmentSlice(
                # arid: enable
                source.state.portfolio_id,
                FIRST_R3_SPY_INSTRUMENT_ID,
                InvestmentHorizon("one quarter"),
            ),
            "Current State supports a measured SPY comparison",
            actor,
            NOW,
            (),
            ("cash remains available",),
            "returns remain uncertain",
            "holding cash is a plausible interpretation",
            ("liquidity deteriorates",),
        )
        await foundation.record_view(OperationId(uuid4()), decision, view)
        challenge = MeaningfulChallengeResult(
            MeaningfulChallengeResultRef(uuid4()),
            # duplicate-code: Sharing would couple Risk falsifiers.
            # arid: disable
            view.view_id,
            decision.decision_id,
            actor,
            NOW,
            # arid: enable
            "The trend could reverse",
            (),
            "The cash assumption may fail",
            ChallengeDisposition.QUALIFIED,
            "The comparison remains conditional on liquidity",
        )
        await foundation.record_challenge(
            OperationId(uuid4()), challenge, decision.version
        )
        owner_store = PostgresIntelligenceJudgmentHistoryStore(engine)
        queries = {}
        bases = []
        for root in (view.view_id, challenge.challenge_id):
            query, key = _query_for_intelligence_target(
                decision_store, owner_store, decision.decision_id, root
            )
            basis = await query.read(key, at=datetime.now(UTC))
            assert isinstance(basis, CurrentEvidenceBasis)
            queries[root] = query
            bases.append(basis)
        recommendation = InvestmentRecommendation(
            recommendation_id=InvestmentRecommendationRef(uuid4()),
            decision_id=decision.decision_id,
            horizon=InvestmentHorizon("one quarter"),
            disposition=EconomicDisposition.INCREASE,
            view_ids=(view.view_id,),
            alternatives=tuple(item.alternative for item in consequences),
            material_evidence=(),
            challenge_ids=(challenge.challenge_id,),
            uncertainty="Market path remains uncertain",
            source_state_id=source.state.state_id,
            consequences=tuple(
                AlternativeConsequence(item.alternative, item.consequence_id)
                for item in consequences
            ),
            risk_assessment_ids=(risk.assessment.assessment_id,),
            material_assumptions=("cash remains adequate",),
            invalidation_conditions=("liquidity falls",),
            review_condition_refs=(),
            proposed_action_refs=(),
            actor_attribution=actor,
            formed_at=datetime.now(UTC),
        )
        query = _PerTargetQuery(queries)
        recommender = InvestmentRecommendationService(
            PostgresInvestmentIntelligenceStore(
                engine, basis_reader=PostgresCurrentBasisReader(engine, query)
            )
        )
        receipt = await recommender.recommend(
            OperationId(uuid4()),
            recommendation,
            decision.version,
            tuple(bases),
            IntelligenceClaimCatalog(()),
        )
        assert isinstance(receipt, JudgmentReceipt)
        assert (await recommender.history(decision.decision_id)) == (recommendation,)
        assert (
            await recommender.current_support(decision.decision_id)
        ).kind is RecommendationSupportKind.SUPPORTED

        history = await owner_store.load(recommendation.recommendation_id)
        assert history is not None
        initial = history.acts[0]
        corrected_at = datetime.now(UTC)
        await owner_store.append(
            IntelligenceJudgmentAct(
                act_id=uuid4(),
                root=recommendation.recommendation_id,
                attribution=actor,
                basis="Recommendation support withdrawn after review",
                effective_at=corrected_at,
                recorded_at=corrected_at,
                known_at=corrected_at,
                ancestry=(initial.act_id,),
                target_predecessor=initial.act_id,
                compatible_opposite_acts=(initial.act_id,),
                target_status=IntelligenceJudgmentStatus.WITHDRAWN,
            )
        )
        withdrawn = await recommender.current_support(decision.decision_id)
        assert withdrawn.kind is RecommendationSupportKind.UNSUPPORTED
        assert withdrawn.latest == recommendation

        portfolio_owner = PostgresPortfolioJudgmentHistoryStore(engine)
        risk_history = await portfolio_owner.load(risk.assessment.assessment_id)
        assert risk_history is not None
        risk_initial = risk_history.acts[0]
        corrected_at = datetime.now(UTC)
        risk_contest = PortfolioJudgmentAct(
            uuid4(),
            risk.assessment.assessment_id,
            actor,
            "Risk support contested before Recommendation formation",
            corrected_at,
            corrected_at,
            corrected_at,
            (risk_initial.act_id,),
            target_predecessor=risk_initial.act_id,
            compatible_opposite_acts=(risk_initial.act_id,),
            contested_target=True,
        )
        await portfolio_owner.append(risk_contest)
        with pytest.raises(InvalidInvestmentJudgment, match="Portfolio Risk"):
            # duplicate-code: Risk and consequence need separate falsifiers.
            # arid: disable
            await recommender.recommend(
                OperationId(uuid4()),
                replace(
                    recommendation,
                    recommendation_id=InvestmentRecommendationRef(uuid4()),
                    formed_at=datetime.now(UTC),
                ),
                decision.version,
                tuple(bases),
                IntelligenceClaimCatalog(()),
            )
            # arid: enable
        risk_restored_at = datetime.now(UTC)
        await portfolio_owner.append(
            PortfolioJudgmentAct(
                uuid4(),
                risk.assessment.assessment_id,
                actor,
                "Risk support restored before Recommendation formation",
                risk_restored_at,
                risk_restored_at,
                risk_restored_at,
                (risk_initial.act_id, risk_contest.act_id),
                assertion=risk.assessment,
                target_predecessor=risk_contest.act_id,
                compatible_opposite_acts=(risk_initial.act_id,),
            )
        )
        consequence_history = await portfolio_owner.load(consequences[0].consequence_id)
        assert consequence_history is not None
        consequence_initial = consequence_history.acts[0]
        corrected_at = datetime.now(UTC)
        await portfolio_owner.append(
            PortfolioJudgmentAct(
                uuid4(),
                consequences[0].consequence_id,
                actor,
                "Consequence contested before Recommendation formation",
                corrected_at,
                corrected_at,
                corrected_at,
                (consequence_initial.act_id,),
                target_predecessor=consequence_initial.act_id,
                compatible_opposite_acts=(consequence_initial.act_id,),
                contested_target=True,
            )
        )
        with pytest.raises(InvalidInvestmentJudgment, match="attributable consequence"):
            # duplicate-code: Consequence correction must fail independently of Risk.
            # arid: disable
            await recommender.recommend(
                OperationId(uuid4()),
                replace(
                    recommendation,
                    recommendation_id=InvestmentRecommendationRef(uuid4()),
                    formed_at=datetime.now(UTC),
                ),
                decision.version,
                tuple(bases),
                IntelligenceClaimCatalog(()),
            )
            # arid: enable

        changed_state = replace(
            source.state,
            state_id=PortfolioStateId(uuid4()),
            source=replace(source.state.source, record_reference="snapshot-2"),
            cash=Decimal("50000"),
            position_value=Decimal("50000"),
            exposure_value=Decimal("50000"),
            allocation_fraction=Decimal("0.5"),
        )
        await PostgresPortfolioStateStore(engine).append(changed_state)
        changed_source = RecordedPortfolioState(changed_state, source.known_at)
        changed_consequences = _consequences(changed_source, alternatives)
        await create_postgres_portfolio_consequence_service(engine).produce(
            decision_id=decision.decision_id,
            source_state_id=changed_state.state_id,
            consequences=changed_consequences,
            initial_claim_catalogs={
                item.consequence_id: PortfolioClaimCatalog(())
                for item in changed_consequences
            },
        )
        risk_service = create_postgres_portfolio_risk_service(engine)
        changed_risk = await risk_service.assess(
            # duplicate-code: Sharing would couple Risk falsifiers.
            # arid: disable
            assessment_id=PortfolioRiskAssessmentRef(uuid4()),
            source_state_id=changed_state.state_id,
            projected_consequence_id=None,
            horizon=InvestmentHorizon("one quarter"),
            # arid: enable
            scenario="SPY downside for lower exposure",
            support=_support(),
            attribution=actor,
            formed_at=NOW,
            initial_claim_catalog=PortfolioClaimCatalog(()),
        )
        assert changed_risk.assessment.dimensions != risk.assessment.dimensions
        changed_recommendation = replace(
            recommendation,
            recommendation_id=InvestmentRecommendationRef(uuid4()),
            disposition=EconomicDisposition.REDUCE,
            source_state_id=changed_state.state_id,
            consequences=tuple(
                AlternativeConsequence(item.alternative, item.consequence_id)
                for item in changed_consequences
            ),
            risk_assessment_ids=(changed_risk.assessment.assessment_id,),
            formed_at=datetime.now(UTC),
        )
        assert isinstance(
            await recommender.recommend(
                OperationId(uuid4()),
                changed_recommendation,
                decision.version,
                tuple(bases),
                IntelligenceClaimCatalog(()),
            ),
            JudgmentReceipt,
        )
        assert (
            await recommender.current_support(decision.decision_id)
        ).latest == changed_recommendation

        unresolved_risk = await risk_service.assess(
            assessment_id=PortfolioRiskAssessmentRef(uuid4()),
            source_state_id=changed_state.state_id,
            projected_consequence_id=None,
            horizon=InvestmentHorizon("one quarter"),
            scenario="SPY downside without a supported estimate",
            # duplicate-code: Sharing would couple Risk falsifiers.
            # arid: disable
            support=_support(downside=None),
            attribution=actor,
            formed_at=NOW,
            initial_claim_catalog=PortfolioClaimCatalog(()),
        )
        # arid: enable
        with pytest.raises(InvalidInvestmentJudgment, match="unresolved"):
            await recommender.recommend(
                OperationId(uuid4()),
                replace(
                    changed_recommendation,
                    recommendation_id=InvestmentRecommendationRef(uuid4()),
                    risk_assessment_ids=(unresolved_risk.assessment.assessment_id,),
                    formed_at=datetime.now(UTC),
                ),
                decision.version,
                tuple(bases),
                IntelligenceClaimCatalog(()),
            )

        withholding = RecommendationWithholdingJudgment(
            RecommendationWithholdingJudgmentRef(uuid4()),
            decision.decision_id,
            InvestmentHorizon("one quarter"),
            "The latest formation attempt has unresolved Risk support",
            actor,
            datetime.now(UTC),
        )
        await recommender.withhold(
            OperationId(uuid4()),
            withholding,
            decision.version,
            IntelligenceClaimCatalog(()),
        )
        assert (
            await recommender.current_support(decision.decision_id)
        ).kind is RecommendationSupportKind.WITHHELD
    finally:
        await engine.dispose()


def test_recommendation_uses_portfolio_and_risk_before_finality(
    postgres_target: PostgresTestTarget,
) -> None:
    asyncio.run(_scenario(postgres_target))
