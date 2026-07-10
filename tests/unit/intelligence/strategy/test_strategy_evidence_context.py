from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from intelligence.strategy.hypothesis import StrategyEvidenceContext
from intelligence.strategy.hypothesis import StrategyEvidenceInputQuality
from intelligence.strategy.hypothesis import StrategyEvidenceInputStatus
from intelligence.strategy.hypothesis import StrategyEvidenceItem
from intelligence.strategy.hypothesis import StrategyPerspective


def _evidence(
    evidence_id: str,
    value: float,
    supports: tuple[StrategyPerspective, ...],
) -> StrategyEvidenceItem:
    return StrategyEvidenceItem(
        evidence_id=evidence_id,
        source="technical_analysis",
        name=evidence_id,
        observed_value=value,
        strength=0.7,
        reliability=0.8,
        supports=supports,
    )


def test_strategy_evidence_context_round_trips_with_explicit_quality_flags() -> None:
    context = StrategyEvidenceContext(
        symbol="SPY",
        as_of="2026-07-10T13:30:00Z",
        required_evidence=(
            _evidence("technical.trend", 0.62, (StrategyPerspective.BULL,)),
        ),
        optional_evidence=(
            _evidence("news.sentiment", 0.41, (StrategyPerspective.SIDEWAYS,)),
        ),
        input_quality=(
            StrategyEvidenceInputQuality(
                input_name="technical_analysis",
                required=True,
                status=StrategyEvidenceInputStatus.AVAILABLE,
                evidence_ids=("technical.trend",),
            ),
            StrategyEvidenceInputQuality(
                input_name="market_events",
                required=False,
                status=StrategyEvidenceInputStatus.MISSING,
                reason="No high-impact event data available for this replay window.",
            ),
        ),
    )

    restored = StrategyEvidenceContext.from_dict(context.to_dict())

    assert restored == context
    assert restored.has_missing_required_inputs is False
    assert restored.evidence_by_id()["technical.trend"].observed_value == 0.62
    assert restored.to_dict()["evidence_fingerprint"] == context.evidence_fingerprint()


def test_evidence_context_fingerprint_is_stable_across_input_ordering() -> None:
    trend = _evidence("technical.trend", 0.62, (StrategyPerspective.BULL,))
    breadth = _evidence("technical.breadth", 0.71, (StrategyPerspective.BULL,))
    sentiment = _evidence("news.sentiment", 0.41, (StrategyPerspective.SIDEWAYS,))
    technical_quality = StrategyEvidenceInputQuality(
        input_name="technical_analysis",
        required=True,
        status=StrategyEvidenceInputStatus.AVAILABLE,
        evidence_ids=("technical.trend", "technical.breadth"),
    )
    news_quality = StrategyEvidenceInputQuality(
        input_name="news_analysis",
        required=False,
        status=StrategyEvidenceInputStatus.DEGRADED,
        reason="Only partial headline coverage was available.",
        evidence_ids=("news.sentiment",),
    )

    first = StrategyEvidenceContext(
        symbol="SPY",
        as_of="2026-07-10T13:30:00Z",
        required_evidence=(trend, breadth),
        optional_evidence=(sentiment,),
        input_quality=(technical_quality, news_quality),
    )
    second = StrategyEvidenceContext(
        symbol="SPY",
        as_of="2026-07-10T13:30:00Z",
        required_evidence=(breadth, trend),
        optional_evidence=(sentiment,),
        input_quality=(news_quality, technical_quality),
    )

    assert first.to_canonical_json() == second.to_canonical_json()
    assert first.evidence_fingerprint() == second.evidence_fingerprint()
    assert [item.evidence_id for item in second.required_evidence] == [
        "technical.breadth",
        "technical.trend",
    ]


def test_missing_required_inputs_are_explicit_quality_flags() -> None:
    context = StrategyEvidenceContext(
        symbol="SPY",
        required_evidence=(),
        input_quality=(
            StrategyEvidenceInputQuality(
                input_name="technical_analysis",
                required=True,
                status=StrategyEvidenceInputStatus.MISSING,
                reason="Technical analysis node did not produce output.",
            ),
        ),
    )

    assert context.has_missing_required_inputs is True
    assert context.to_dict()["input_quality"] == [
        {
            "input_name": "technical_analysis",
            "required": True,
            "status": "missing",
            "reason": "Technical analysis node did not produce output.",
            "evidence_ids": [],
        }
    ]


def test_degraded_required_inputs_are_explicit_quality_flags() -> None:
    context = StrategyEvidenceContext(
        symbol="SPY",
        required_evidence=(
            _evidence("technical.trend", 0.35, (StrategyPerspective.BEAR,)),
        ),
        input_quality=(
            StrategyEvidenceInputQuality(
                input_name="technical_analysis",
                required=True,
                status=StrategyEvidenceInputStatus.DEGRADED,
                reason="Breadth fields were unavailable.",
                evidence_ids=("technical.trend",),
            ),
        ),
    )

    assert context.has_degraded_required_inputs is True
    assert context.has_missing_required_inputs is False


def test_context_rejects_duplicate_evidence_ids() -> None:
    duplicate = _evidence("technical.trend", 0.62, (StrategyPerspective.BULL,))

    with pytest.raises(ValueError, match="duplicate strategy evidence_id"):
        StrategyEvidenceContext(
            symbol="SPY",
            required_evidence=(duplicate,),
            optional_evidence=(duplicate,),
        )


def test_context_and_quality_flags_are_immutable_and_validate_missing_reason() -> None:
    quality = StrategyEvidenceInputQuality(
        input_name="technical_analysis",
        required=True,
        status=StrategyEvidenceInputStatus.AVAILABLE,
    )
    context = StrategyEvidenceContext(
        symbol="SPY",
        required_evidence=(),
        input_quality=(quality,),
    )

    with pytest.raises(FrozenInstanceError):
        context.symbol = "QQQ"  # type: ignore[misc]
    with pytest.raises(ValueError, match="must include a reason"):
        StrategyEvidenceInputQuality(
            input_name="technical_analysis",
            required=True,
            status=StrategyEvidenceInputStatus.MISSING,
        )
    with pytest.raises(ValueError):
        StrategyEvidenceContext(symbol=" ", required_evidence=())
