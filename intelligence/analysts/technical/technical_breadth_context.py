from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from core.utils.utils import (
    _clamp,
    _safe_bool,
    _safe_float,
)


@dataclass(
    frozen=True,
    slots=True,
)
class TechnicalBreadthContext:
    """
    Typed intelligence-layer view of serialized technical breadth output.

    Runtime nodes serialize technical service outputs as dictionaries at the
    runtime boundary. Downstream intelligence components should immediately
    convert those payloads into this typed context instead of repeatedly
    hand-reading fragile dict keys.
    """

    has_breadth_data: bool = False
    breadth_regime: str = "unavailable"
    risk_regime: str = "unknown"
    breadth_score: float = 0.0
    breadth_risk_score: float = 0.5
    participation_score: float = 0.0
    leadership_score: float = 0.0
    mcclellan_score: float = 0.0
    divergence_score: float = 0.0
    price_ad_divergence: bool = False
    breadth_percent: float = 0.0
    pct_above_50dma: float = 0.0
    pct_above_200dma: float = 0.0
    new_high_low_diff: float = 0.0
    mcclellan_oscillator: float = 0.0

    @classmethod
    def unavailable(
        cls,
    ) -> TechnicalBreadthContext:
        return cls()

    @property
    def is_weak(
        self,
    ) -> bool:
        if not self.has_breadth_data:
            return False

        return (
            self.breadth_score <= -0.25
            or self.breadth_risk_score >= 0.65
            or self.participation_score <= -0.25
            or self.leadership_score <= -0.25
            or self.mcclellan_score <= -0.25
            or self.price_ad_divergence
        )

    @property
    def is_strong(
        self,
    ) -> bool:
        if not self.has_breadth_data:
            return False

        return (
            self.breadth_score >= 0.25
            and self.breadth_risk_score <= 0.40
            and self.participation_score >= 0.15
            and self.leadership_score >= 0.0
            and not self.price_ad_divergence
        )

    @property
    def confirmation_score(
        self,
    ) -> float:
        if not self.has_breadth_data:
            return 0.0

        score = (
            self.breadth_score * 0.40
            + self.participation_score * 0.25
            + self.leadership_score * 0.20
            + self.mcclellan_score * 0.15
        )

        if self.price_ad_divergence:
            score -= 0.20

        return _clamp(
            score,
            lower=-1.0,
            upper=1.0,
        )

    @property
    def risk_pressure(
        self,
    ) -> float:
        if not self.has_breadth_data:
            return 0.0

        pressure = self.breadth_risk_score

        if self.participation_score < 0.0:
            pressure += min(
                0.20,
                abs(self.participation_score) * 0.20,
            )

        if self.leadership_score < 0.0:
            pressure += min(
                0.15,
                abs(self.leadership_score) * 0.15,
            )

        if self.mcclellan_score < 0.0:
            pressure += min(
                0.15,
                abs(self.mcclellan_score) * 0.15,
            )

        if self.price_ad_divergence:
            pressure += 0.15

        return _clamp(
            pressure,
            lower=0.0,
            upper=1.0,
        )

    def risk_flags(
        self,
    ) -> tuple[str, ...]:
        if not self.has_breadth_data:
            return ()

        flags: list[str] = []

        if self.breadth_score <= -0.25:
            flags.append(
                "weak_market_breadth",
            )

        if self.breadth_risk_score >= 0.65:
            flags.append(
                "elevated_breadth_risk",
            )

        if self.participation_score <= -0.25:
            flags.append(
                "weak_market_participation",
            )

        if self.leadership_score <= -0.25:
            flags.append(
                "narrow_market_leadership",
            )

        if self.mcclellan_score <= -0.25:
            flags.append(
                "deteriorating_mcclellan_breadth",
            )

        if self.price_ad_divergence:
            flags.append(
                "price_ad_divergence",
            )

        return tuple(
            dict.fromkeys(
                flags,
            )
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "has_breadth_data": self.has_breadth_data,
            "breadth_regime": self.breadth_regime,
            "risk_regime": self.risk_regime,
            "breadth_score": self.breadth_score,
            "breadth_risk_score": self.breadth_risk_score,
            "participation_score": self.participation_score,
            "leadership_score": self.leadership_score,
            "mcclellan_score": self.mcclellan_score,
            "divergence_score": self.divergence_score,
            "price_ad_divergence": self.price_ad_divergence,
            "breadth_percent": self.breadth_percent,
            "pct_above_50dma": self.pct_above_50dma,
            "pct_above_200dma": self.pct_above_200dma,
            "new_high_low_diff": self.new_high_low_diff,
            "mcclellan_oscillator": self.mcclellan_oscillator,
            "confirmation_score": self.confirmation_score,
            "risk_pressure": self.risk_pressure,
            "risk_flags": list(
                self.risk_flags(),
            ),
        }


def extract_technical_breadth_context(
    technical_output: Mapping[str, Any] | None,
) -> TechnicalBreadthContext:
    """
    Extract breadth context from a serialized technical_agent node output.

    Expected shape is the runtime node output dictionary:
    {"outputs": {"features": {...}}}. The helper also accepts the inner
    outputs dictionary for convenience during tests and later node refactors.
    """

    if not technical_output:
        return TechnicalBreadthContext.unavailable()

    outputs = _as_mapping(
        technical_output.get(
            "outputs",
        )
    )

    if outputs:
        features = _as_mapping(
            outputs.get(
                "features",
            )
        )
    else:
        features = _as_mapping(
            technical_output.get(
                "features",
            )
        )

    return extract_technical_breadth_context_from_features(
        features,
    )


def extract_technical_breadth_context_from_features(
    features: Mapping[str, Any] | None,
) -> TechnicalBreadthContext:
    if not features:
        return TechnicalBreadthContext.unavailable()

    breadth_state = _as_mapping(
        features.get(
            "breadth_state",
        )
    )
    breadth = _as_mapping(
        features.get(
            "breadth",
        )
    )
    market_context = _as_mapping(
        features.get(
            "market_context",
        )
    )

    source = breadth_state or breadth
    has_breadth = _safe_bool(
        _first_present(
            source,
            market_context,
            key="has_breadth_data",
            fallback_key="has_breadth",
            default=False,
        )
    )

    if not has_breadth:
        return TechnicalBreadthContext.unavailable()

    return TechnicalBreadthContext(
        has_breadth_data=True,
        breadth_regime=str(
            _first_present(
                source,
                breadth,
                market_context,
                key="breadth_regime",
                default="neutral",
            )
        ),
        risk_regime=str(
            _first_present(
                source,
                breadth,
                key="risk_regime",
                default="unknown",
            )
        ),
        breadth_score=_safe_float(
            _first_present(
                source,
                breadth,
                key="breadth_score",
                default=0.0,
            )
        ),
        breadth_risk_score=_safe_float(
            _first_present(
                source,
                breadth,
                key="breadth_risk_score",
                default=0.5,
            ),
            default=0.5,
        ),
        participation_score=_safe_float(
            _first_present(
                source,
                breadth,
                key="participation_score",
                default=0.0,
            )
        ),
        leadership_score=_safe_float(
            _first_present(
                source,
                breadth,
                key="leadership_score",
                default=0.0,
            )
        ),
        mcclellan_score=_safe_float(
            _first_present(
                source,
                breadth,
                key="mcclellan_score",
                default=0.0,
            )
        ),
        divergence_score=_safe_float(
            _first_present(
                source,
                breadth,
                key="divergence_score",
                default=0.0,
            )
        ),
        price_ad_divergence=_safe_bool(
            _first_present(
                source,
                breadth,
                market_context,
                key="price_ad_divergence",
                default=False,
            )
        ),
        breadth_percent=_safe_float(
            _first_present(
                source,
                breadth,
                market_context,
                key="breadth_percent",
                default=0.0,
            )
        ),
        pct_above_50dma=_safe_float(
            _first_present(
                source,
                breadth,
                market_context,
                key="pct_above_50dma",
                default=0.0,
            )
        ),
        pct_above_200dma=_safe_float(
            _first_present(
                source,
                breadth,
                market_context,
                key="pct_above_200dma",
                default=0.0,
            )
        ),
        new_high_low_diff=_safe_float(
            _first_present(
                source,
                breadth,
                market_context,
                key="new_high_low_diff",
                default=0.0,
            )
        ),
        mcclellan_oscillator=_safe_float(
            _first_present(
                source,
                breadth,
                market_context,
                key="mcclellan_oscillator",
                default=0.0,
            )
        ),
    )


def _first_present(
    *sources: Mapping[str, Any],
    key: str,
    fallback_key: str | None = None,
    default: Any = None,
) -> Any:
    for source in sources:
        if key in source and source[key] is not None:
            return source[key]

        if (
            fallback_key is not None
            and fallback_key in source
            and source[fallback_key] is not None
        ):
            return source[fallback_key]

    return default


def _as_mapping(
    value: Any,
) -> Mapping[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return value

    return {}
