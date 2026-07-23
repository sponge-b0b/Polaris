from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
    extract_technical_breadth_context,
)
from intelligence.strategy.hypothesis.context import (
    StrategyEvidenceContext,
    StrategyEvidenceInputQuality,
    StrategyEvidenceInputStatus,
)
from intelligence.strategy.hypothesis.contracts import (
    StrategyJsonScalar,
    StrategyPerspective,
)
from intelligence.strategy.hypothesis.evidence import StrategyEvidenceItem


@dataclass(frozen=True, slots=True)
class _EvidenceSpec:
    evidence_id: str
    source: str
    name: str
    value_path: tuple[str, ...]
    confidence_path: tuple[str, ...] = ("confidence",)


_OPTIONAL_INPUTS: tuple[str, ...] = (
    "macro_analysis",
    "fundamental_agent",
    "news_agent",
    "risk_aggregator_agent",
    "portfolio_state_builder",
    "market_events",
)

_SENTIMENT_SPECS: tuple[_EvidenceSpec, ...] = (
    _EvidenceSpec(
        evidence_id="sentiment.directional_score",
        source="sentiment_agent",
        name="Sentiment directional score",
        value_path=("directional_score",),
    ),
    _EvidenceSpec(
        evidence_id="sentiment.momentum",
        source="sentiment_agent",
        name="Sentiment momentum",
        value_path=("features", "momentum"),
    ),
    _EvidenceSpec(
        evidence_id="sentiment.stability",
        source="sentiment_agent",
        name="Sentiment stability",
        value_path=("features", "stability"),
    ),
    _EvidenceSpec(
        evidence_id="sentiment.divergence",
        source="sentiment_agent",
        name="Sentiment divergence",
        value_path=("features", "divergence", "avg_divergence"),
    ),
)

_TECHNICAL_SPECS: tuple[_EvidenceSpec, ...] = (
    _EvidenceSpec(
        evidence_id="technical.directional_score",
        source="technical_agent",
        name="Technical directional score",
        value_path=("directional_score",),
    ),
    _EvidenceSpec(
        evidence_id="technical.trend_strength",
        source="technical_agent",
        name="Technical trend strength",
        value_path=("features", "trend", "trend_strength"),
    ),
    _EvidenceSpec(
        evidence_id="technical.volatility_score",
        source="technical_agent",
        name="Technical volatility score",
        value_path=("features", "volatility", "volatility_score"),
    ),
    _EvidenceSpec(
        evidence_id="technical.regime",
        source="technical_agent",
        name="Technical regime",
        value_path=("features", "regime", "regime"),
    ),
)

_OPTIONAL_SPECS: Mapping[str, tuple[_EvidenceSpec, ...]] = {
    "macro_analysis": (
        _EvidenceSpec(
            evidence_id="macro.directional_score",
            source="macro_analysis",
            name="Macro directional score",
            value_path=("directional_score",),
        ),
        _EvidenceSpec(
            evidence_id="macro.regime",
            source="macro_analysis",
            name="Macro regime",
            value_path=("regime",),
        ),
    ),
    "fundamental_agent": (
        _EvidenceSpec(
            evidence_id="fundamental.directional_score",
            source="fundamental_agent",
            name="Fundamental directional score",
            value_path=("directional_score",),
        ),
    ),
    "news_agent": (
        _EvidenceSpec(
            evidence_id="news.directional_score",
            source="news_agent",
            name="News directional score",
            value_path=("directional_score",),
        ),
    ),
    "risk_aggregator_agent": (
        _EvidenceSpec(
            evidence_id="risk.pressure",
            source="risk_aggregator_agent",
            name="Risk pressure",
            value_path=("features", "risk_pressure"),
        ),
        _EvidenceSpec(
            evidence_id="risk.composite",
            source="risk_aggregator_agent",
            name="Composite risk",
            value_path=("features", "composite_risk"),
        ),
    ),
    "portfolio_state_builder": (
        _EvidenceSpec(
            evidence_id="portfolio.scale_factor",
            source="portfolio_state_builder",
            name="Portfolio scale factor",
            value_path=("features", "scale_factor"),
        ),
        _EvidenceSpec(
            evidence_id="portfolio.status",
            source="portfolio_state_builder",
            name="Portfolio status",
            value_path=("features", "status"),
        ),
        _EvidenceSpec(
            evidence_id="portfolio.heat",
            source="portfolio_state_builder",
            name="Portfolio heat",
            value_path=("features", "risk_features", "portfolio_heat"),
        ),
    ),
    "market_events": (
        _EvidenceSpec(
            evidence_id="market_events.pressure",
            source="market_events",
            name="Market event pressure",
            value_path=("features", "event_pressure"),
        ),
        _EvidenceSpec(
            evidence_id="market_events.bias",
            source="market_events",
            name="Market event bias",
            value_path=("features", "event_bias"),
        ),
        _EvidenceSpec(
            evidence_id="market_events.volatility",
            source="market_events",
            name="Market event volatility",
            value_path=("features", "event_volatility"),
        ),
    ),
}

_NODE_ALIASES: Mapping[str, tuple[str, ...]] = {
    "macro_analysis": ("macro_analysis", "macro_agent"),
    "market_events": ("market_events", "market_events_agent", "market_events_service"),
}


def normalize_strategy_evidence_context(
    node_outputs: Mapping[str, object],
    *,
    symbol: str = "SPY",
    as_of: str | None = None,
) -> StrategyEvidenceContext:
    """Normalize runtime node outputs into one typed strategy evidence context.

    The strategy perspective agents historically read runtime output dictionaries
    independently. This policy performs that runtime-boundary parsing once and
    returns typed evidence plus explicit input quality flags. It does not persist
    or mutate workflow state.
    """

    required_evidence: list[StrategyEvidenceItem] = []
    optional_evidence: list[StrategyEvidenceItem] = []
    input_quality: list[StrategyEvidenceInputQuality] = []

    sentiment_output = _resolve_outputs(node_outputs, "sentiment_agent")
    sentiment_items = _items_from_specs(_SENTIMENT_SPECS, sentiment_output)
    required_evidence.extend(sentiment_items)
    input_quality.append(
        _quality(
            input_name="sentiment_agent",
            required=True,
            raw_output=sentiment_output,
            evidence_items=sentiment_items,
        )
    )

    technical_raw = _resolve_raw_node_output(node_outputs, "technical_agent")
    technical_output = _unwrap_outputs(technical_raw)
    technical_items = _items_from_specs(_TECHNICAL_SPECS, technical_output)
    technical_items.extend(_technical_breadth_items(technical_raw, technical_output))
    required_evidence.extend(technical_items)
    input_quality.append(
        _quality(
            input_name="technical_agent",
            required=True,
            raw_output=technical_output,
            evidence_items=technical_items,
        )
    )

    for input_name in _OPTIONAL_INPUTS:
        raw_output = _resolve_outputs(node_outputs, input_name)
        items = _items_from_specs(_OPTIONAL_SPECS[input_name], raw_output)
        optional_evidence.extend(items)
        input_quality.append(
            _quality(
                input_name=input_name,
                required=False,
                raw_output=raw_output,
                evidence_items=items,
            )
        )

    return StrategyEvidenceContext(
        symbol=symbol,
        as_of=as_of,
        required_evidence=tuple(required_evidence),
        optional_evidence=tuple(optional_evidence),
        input_quality=tuple(input_quality),
    )


def _items_from_specs(
    specs: Sequence[_EvidenceSpec],
    output: Mapping[str, object],
) -> list[StrategyEvidenceItem]:
    if not output:
        return []

    confidence = _unit_float(_nested_value(output, ("confidence",)), default=0.5)
    items: list[StrategyEvidenceItem] = []

    for spec in specs:
        observed_value = _scalar_value(_nested_value(output, spec.value_path))
        if observed_value is None:
            continue
        strength = _strength_for_value(observed_value)
        reliability = _unit_float(
            _nested_value(output, spec.confidence_path),
            default=confidence,
        )
        supports, contradicts = _perspectives_for_value(
            evidence_id=spec.evidence_id,
            observed_value=observed_value,
        )
        items.append(
            StrategyEvidenceItem(
                evidence_id=spec.evidence_id,
                source=spec.source,
                name=spec.name,
                observed_value=observed_value,
                strength=strength,
                reliability=reliability,
                supports=supports,
                contradicts=contradicts,
            )
        )

    return items


def _technical_breadth_items(
    technical_raw: object,
    technical_output: Mapping[str, object],
) -> list[StrategyEvidenceItem]:
    if not technical_raw and not technical_output:
        return []

    if isinstance(technical_raw, Mapping):
        breadth_context = extract_technical_breadth_context(technical_raw)
    else:
        breadth_context = extract_technical_breadth_context(technical_output)

    if not breadth_context.has_breadth_data:
        return []

    reliability = _unit_float(
        _nested_value(technical_output, ("confidence",)), default=0.5
    )
    return [
        _breadth_item(
            breadth_context=breadth_context,
            evidence_id="technical.breadth.confirmation_score",
            name="Technical breadth confirmation score",
            observed_value=breadth_context.confirmation_score,
            reliability=reliability,
        ),
        _breadth_item(
            breadth_context=breadth_context,
            evidence_id="technical.breadth.risk_pressure",
            name="Technical breadth risk pressure",
            observed_value=breadth_context.risk_pressure,
            reliability=reliability,
        ),
        _breadth_item(
            breadth_context=breadth_context,
            evidence_id="technical.breadth.participation_score",
            name="Technical breadth participation score",
            observed_value=breadth_context.participation_score,
            reliability=reliability,
        ),
        _breadth_item(
            breadth_context=breadth_context,
            evidence_id="technical.breadth.leadership_score",
            name="Technical breadth leadership score",
            observed_value=breadth_context.leadership_score,
            reliability=reliability,
        ),
    ]


def _breadth_item(
    *,
    breadth_context: TechnicalBreadthContext,
    evidence_id: str,
    name: str,
    observed_value: float,
    reliability: float,
) -> StrategyEvidenceItem:
    supports, contradicts = _perspectives_for_value(
        evidence_id=evidence_id,
        observed_value=observed_value,
    )
    return StrategyEvidenceItem(
        evidence_id=evidence_id,
        source="technical_agent",
        name=name,
        observed_value=observed_value,
        strength=_strength_for_value(observed_value),
        reliability=reliability,
        supports=supports,
        contradicts=contradicts,
        explanation=(
            f"breadth_regime={breadth_context.breadth_regime}; "
            f"risk_regime={breadth_context.risk_regime}"
        ),
    )


def _quality(
    *,
    input_name: str,
    required: bool,
    raw_output: Mapping[str, object],
    evidence_items: Sequence[StrategyEvidenceItem],
) -> StrategyEvidenceInputQuality:
    evidence_ids = tuple(item.evidence_id for item in evidence_items)
    if evidence_items:
        return StrategyEvidenceInputQuality(
            input_name=input_name,
            required=required,
            status=StrategyEvidenceInputStatus.AVAILABLE,
            evidence_ids=evidence_ids,
        )
    if raw_output:
        return StrategyEvidenceInputQuality(
            input_name=input_name,
            required=required,
            status=StrategyEvidenceInputStatus.DEGRADED,
            reason=f"{input_name} output did not contain strategy evidence fields.",
            evidence_ids=evidence_ids,
        )
    return StrategyEvidenceInputQuality(
        input_name=input_name,
        required=required,
        status=StrategyEvidenceInputStatus.MISSING,
        reason=f"{input_name} did not produce runtime output.",
        evidence_ids=evidence_ids,
    )


def _resolve_outputs(
    node_outputs: Mapping[str, object],
    input_name: str,
) -> Mapping[str, object]:
    return _unwrap_outputs(_resolve_raw_node_output(node_outputs, input_name))


def _resolve_raw_node_output(
    node_outputs: Mapping[str, object],
    input_name: str,
) -> object:
    for candidate in _NODE_ALIASES.get(input_name, (input_name,)):
        value = node_outputs.get(candidate)
        if value is not None:
            return value
    return None


def _unwrap_outputs(raw_output: object) -> Mapping[str, object]:
    object_outputs = getattr(raw_output, "outputs", None)
    if isinstance(object_outputs, Mapping):
        return object_outputs
    if isinstance(raw_output, Mapping):
        nested_outputs = raw_output.get("outputs")
        if isinstance(nested_outputs, Mapping):
            return nested_outputs
        return raw_output
    return {}


def _nested_value(
    source: Mapping[str, object],
    path: tuple[str, ...],
) -> object:
    value: object = source
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _scalar_value(value: object) -> StrategyJsonScalar:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and isfinite(value):
        return value
    return None


def _strength_for_value(value: StrategyJsonScalar) -> float:
    if isinstance(value, bool) or value is None:
        return 1.0 if value is True else 0.0
    if isinstance(value, (int, float)):
        return _unit_float(abs(float(value)), default=0.0)
    if value:
        return 0.5
    return 0.0


def _unit_float(value: object, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float, str)):
        try:
            numeric = float(value)
        except ValueError:
            numeric = default
    else:
        numeric = default
    if not isfinite(numeric):
        numeric = default
    return min(1.0, max(0.0, numeric))


def _perspectives_for_value(  # noqa: C901
    *,
    evidence_id: str,
    observed_value: StrategyJsonScalar,
) -> tuple[tuple[StrategyPerspective, ...], tuple[StrategyPerspective, ...]]:
    if isinstance(observed_value, bool) or observed_value is None:
        return (), ()
    if isinstance(observed_value, str):
        return _perspectives_for_text(observed_value)
    if not isinstance(observed_value, (int, float)):
        return (), ()

    numeric = float(observed_value)
    if evidence_id in {
        "risk.pressure",
        "risk.composite",
        "portfolio.heat",
        "technical.breadth.risk_pressure",
        "market_events.pressure",
        "market_events.volatility",
    }:
        if numeric >= 0.65:
            return (StrategyPerspective.BEAR,), (StrategyPerspective.BULL,)
        if numeric <= 0.35:
            return (StrategyPerspective.BULL,), (StrategyPerspective.BEAR,)
        return (StrategyPerspective.SIDEWAYS,), ()

    if evidence_id == "portfolio.scale_factor":
        if numeric >= 0.75:
            return (StrategyPerspective.BULL,), ()
        if numeric <= 0.35:
            return (StrategyPerspective.BEAR,), (StrategyPerspective.BULL,)
        return (StrategyPerspective.SIDEWAYS,), ()

    if numeric > 0.05:
        return (StrategyPerspective.BULL,), (StrategyPerspective.BEAR,)
    if numeric < -0.05:
        return (StrategyPerspective.BEAR,), (StrategyPerspective.BULL,)
    return (StrategyPerspective.SIDEWAYS,), ()


def _perspectives_for_text(
    value: str,
) -> tuple[tuple[StrategyPerspective, ...], tuple[StrategyPerspective, ...]]:
    normalized = value.strip().lower()
    if "bull" in normalized or normalized in {"risk_on", "offensive", "approved"}:
        return (StrategyPerspective.BULL,), (StrategyPerspective.BEAR,)
    if "bear" in normalized or normalized in {"risk_off", "defensive", "blocked"}:
        return (StrategyPerspective.BEAR,), (StrategyPerspective.BULL,)
    if "sideways" in normalized or "neutral" in normalized or "range" in normalized:
        return (StrategyPerspective.SIDEWAYS,), ()
    return (), ()
