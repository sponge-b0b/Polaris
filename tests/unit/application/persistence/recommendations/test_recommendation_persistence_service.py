from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.persistence.audit.audit_emission import PersistenceAuditEmission
from application.persistence.recommendations import (
    RecommendationPersistenceFilters,
    RecommendationPersistenceService,
    TradeSetupPersistenceFilters,
    WatchlistPersistenceFilters,
)
from core.storage.persistence.audit import PersistenceAuditEventResult
from core.storage.persistence.recommendations import (
    RecommendationOutcomeRecord,
    RecommendationPersistenceBundle,
    RecommendationPersistenceResult,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    WatchlistItemRecord,
)


class FakeRecommendationRepository:
    def __init__(
        self,
        *,
        recommendation: RecommendationRecord | None = None,
        rationales: Sequence[RecommendationRationaleRecord] = (),
        outcomes: Sequence[RecommendationOutcomeRecord] = (),
        trade_setups: Sequence[TradeSetupRecord] = (),
        watchlist_items: Sequence[WatchlistItemRecord] = (),
    ) -> None:
        self.bundle: RecommendationPersistenceBundle | None = None
        self.recommendation = recommendation
        self.rationales = tuple(rationales)
        self.outcomes = tuple(outcomes)
        self.trade_setups = tuple(trade_setups)
        self.watchlist_items = tuple(watchlist_items)
        self.recommendation_filters: dict[str, str | None] | None = None
        self.trade_setup_filters: dict[str, str | None] | None = None
        self.watchlist_filters: dict[str, str | None] | None = None

    async def persist_recommendation_bundle(
        self,
        bundle: RecommendationPersistenceBundle,
    ) -> RecommendationPersistenceResult:
        self.bundle = bundle
        return RecommendationPersistenceResult.succeeded(
            recommendation_id=bundle.recommendation.recommendation_id,
            records_persisted=1
            + len(bundle.rationales)
            + len(bundle.outcomes)
            + len(bundle.trade_setups)
            + len(bundle.watchlist_items),
        )

    async def get_recommendation(
        self,
        recommendation_id: str,
    ) -> RecommendationRecord | None:
        if self.recommendation is None:
            return None
        if self.recommendation.recommendation_id != recommendation_id:
            return None
        return self.recommendation

    async def list_recommendations(
        self,
        *,
        symbol: str | None = None,
        status: str | None = None,
        execution_id: str | None = None,
    ) -> Sequence[RecommendationRecord]:
        self.recommendation_filters = {
            "symbol": symbol,
            "status": status,
            "execution_id": execution_id,
        }
        if self.recommendation is None:
            return ()
        return (self.recommendation,)

    async def list_rationales(
        self,
        recommendation_id: str,
    ) -> Sequence[RecommendationRationaleRecord]:
        return tuple(
            rationale
            for rationale in self.rationales
            if rationale.recommendation_id == recommendation_id
        )

    async def list_outcomes(
        self,
        recommendation_id: str,
    ) -> Sequence[RecommendationOutcomeRecord]:
        return tuple(
            outcome
            for outcome in self.outcomes
            if outcome.recommendation_id == recommendation_id
        )

    async def list_trade_setups(
        self,
        *,
        recommendation_id: str | None = None,
        symbol: str | None = None,
    ) -> Sequence[TradeSetupRecord]:
        self.trade_setup_filters = {
            "recommendation_id": recommendation_id,
            "symbol": symbol,
        }
        return self.trade_setups

    async def list_watchlist_items(
        self,
        *,
        recommendation_id: str | None = None,
        symbol: str | None = None,
        status: str | None = None,
    ) -> Sequence[WatchlistItemRecord]:
        self.watchlist_filters = {
            "recommendation_id": recommendation_id,
            "symbol": symbol,
            "status": status,
        }
        return self.watchlist_items


class RecordingAuditEmitter:
    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail
        self.emissions: list[PersistenceAuditEmission] = []

    async def emit(
        self,
        emission: PersistenceAuditEmission,
    ) -> PersistenceAuditEventResult | None:
        if self.fail:
            raise RuntimeError("audit failure")
        self.emissions.append(
            emission,
        )
        return None

    async def emit_many(
        self,
        emissions: Sequence[PersistenceAuditEmission],
    ) -> Sequence[PersistenceAuditEventResult | None]:
        if self.fail:
            raise RuntimeError("audit failure")
        self.emissions.extend(
            emissions,
        )
        return tuple(None for _ in emissions)


@pytest.mark.asyncio
async def test_recommendation_persistence_service_persists_typed_bundle() -> None:
    repository = FakeRecommendationRepository()
    service = RecommendationPersistenceService(repository)

    result = await service.persist(
        _recommendation(),
        rationales=(_rationale(),),
        outcomes=(_outcome(),),
        trade_setups=(_trade_setup(),),
        watchlist_items=(_watchlist_item(),),
    )

    assert result.success is True
    assert result.records_persisted == 5
    assert repository.bundle is not None
    assert repository.bundle.recommendation.recommendation_id == "rec-1"
    assert repository.bundle.rationales[0].rationale_text == "Full rationale text."
    assert repository.bundle.outcomes[0].outcome == "profitable"
    assert repository.bundle.trade_setups[0].setup_id == "rec-1:setup:swing"
    assert (
        repository.bundle.watchlist_items[0].watchlist_item_id
        == "rec-1:watchlist:primary"
    )


@pytest.mark.asyncio
async def test_recommendation_persistence_service_persists_existing_bundle() -> None:
    repository = FakeRecommendationRepository()
    service = RecommendationPersistenceService(repository)
    bundle = RecommendationPersistenceBundle(
        recommendation=_recommendation(),
        rationales=(_rationale(),),
    )

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 2
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_recommendation_persistence_service_emits_non_fatal_audit_events() -> (
    None
):
    repository = FakeRecommendationRepository()
    audit_emitter = RecordingAuditEmitter()
    service = RecommendationPersistenceService(
        repository,
        audit_emitter,
    )

    result = await service.persist(
        _recommendation(),
        rationales=(_rationale(),),
        outcomes=(_outcome(),),
        trade_setups=(_trade_setup(),),
        watchlist_items=(_watchlist_item(),),
    )

    assert result.success is True
    assert [emission.entity_type for emission in audit_emitter.emissions] == [
        "recommendation",
        "recommendation_rationale",
        "recommendation_outcome",
        "trade_setup",
        "watchlist_item",
    ]
    assert [emission.entity_id for emission in audit_emitter.emissions] == [
        "rec-1",
        "rec-1:rationale:primary",
        "rec-1:outcome:day-1",
        "rec-1:setup:swing",
        "rec-1:watchlist:primary",
    ]
    assert all(emission.action == "persist" for emission in audit_emitter.emissions)
    assert audit_emitter.emissions[0].metadata["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_recommendation_persistence_service_does_not_fail_primary_write_when_audit_fails() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    repository = FakeRecommendationRepository()
    service = RecommendationPersistenceService(
        repository,
        RecordingAuditEmitter(
            fail=True,
        ),
    )

    result = await service.persist_bundle(
        RecommendationPersistenceBundle(
            recommendation=_recommendation(),
            rationales=(_rationale(),),
        )
    )

    assert result.success is True
    assert result.records_persisted == 2
    assert repository.bundle is not None
    assert repository.bundle.recommendation.recommendation_id == "rec-1"


@pytest.mark.asyncio
async def test_recommendation_persistence_service_rehydrates_full_bundle() -> None:
    repository = FakeRecommendationRepository(
        recommendation=_recommendation(),
        rationales=(_rationale(),),
        outcomes=(_outcome(),),
        trade_setups=(_trade_setup(),),
        watchlist_items=(_watchlist_item(),),
    )
    service = RecommendationPersistenceService(repository)

    bundle = await service.get_bundle("rec-1")

    assert bundle is not None
    assert bundle.recommendation.recommendation_id == "rec-1"
    assert len(bundle.rationales) == 1
    assert len(bundle.outcomes) == 1
    assert len(bundle.trade_setups) == 1
    assert len(bundle.watchlist_items) == 1
    assert repository.trade_setup_filters == {
        "recommendation_id": "rec-1",
        "symbol": None,
    }
    assert repository.watchlist_filters == {
        "recommendation_id": "rec-1",
        "symbol": None,
        "status": None,
    }


@pytest.mark.asyncio
async def test_recommendation_persistence_service_returns_none_for_missing_bundle() -> (
    None
):
    repository = FakeRecommendationRepository()
    service = RecommendationPersistenceService(repository)

    bundle = await service.get_bundle("missing")

    assert bundle is None


@pytest.mark.asyncio
async def test_recommendation_persistence_service_uses_typed_filters() -> None:
    repository = FakeRecommendationRepository(recommendation=_recommendation())
    service = RecommendationPersistenceService(repository)

    recommendations = await service.list_recommendations(
        RecommendationPersistenceFilters(
            symbol="AAPL",
            status="active",
            execution_id="exec-1",
        )
    )
    setups = await service.list_trade_setups(
        TradeSetupPersistenceFilters(
            recommendation_id="rec-1",
            symbol="AAPL",
        )
    )
    items = await service.list_watchlist_items(
        WatchlistPersistenceFilters(
            recommendation_id="rec-1",
            symbol="AAPL",
            status="active",
        )
    )

    assert len(recommendations) == 1
    assert setups == ()
    assert items == ()
    assert repository.recommendation_filters == {
        "symbol": "AAPL",
        "status": "active",
        "execution_id": "exec-1",
    }
    assert repository.trade_setup_filters == {
        "recommendation_id": "rec-1",
        "symbol": "AAPL",
    }
    assert repository.watchlist_filters == {
        "recommendation_id": "rec-1",
        "symbol": "AAPL",
        "status": "active",
    }


def _recommendation() -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id="rec-1",
        symbol="AAPL",
        bias="bullish",
        confidence=0.82,
        setup_quality=0.75,
        risk_score=0.25,
        risk_level="moderate",
        time_horizon="swing",
        status="active",
        created_at=_timestamp(),
    )


def _rationale() -> RecommendationRationaleRecord:
    return RecommendationRationaleRecord(
        rationale_id="rec-1:rationale:primary",
        recommendation_id="rec-1",
        rationale_type="primary",
        rationale_text="Full rationale text.",
        confidence=0.8,
        created_at=_timestamp(),
    )


def _outcome() -> RecommendationOutcomeRecord:
    return RecommendationOutcomeRecord(
        outcome_id="rec-1:outcome:day-1",
        recommendation_id="rec-1",
        evaluated_at=_timestamp(),
        human_action="accepted",
        outcome="profitable",
        outcome_return=0.03,
        outcome_notes="Followed plan.",
    )


def _trade_setup() -> TradeSetupRecord:
    return TradeSetupRecord(
        setup_id="rec-1:setup:swing",
        recommendation_id="rec-1",
        symbol="AAPL",
        setup_type="breakout",
        bias="bullish",
        setup_quality=0.78,
        confidence=0.81,
        risk_score=0.24,
        risk_reward_ratio=2.5,
        time_horizon="swing",
        created_at=_timestamp(),
    )


def _watchlist_item() -> WatchlistItemRecord:
    return WatchlistItemRecord(
        watchlist_item_id="rec-1:watchlist:primary",
        recommendation_id="rec-1",
        symbol="AAPL",
        reason="High-quality setup with clear risk controls.",
        priority=1,
        status="active",
        bias="bullish",
        confidence=0.8,
        setup_quality=0.77,
        created_at=_timestamp(),
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
