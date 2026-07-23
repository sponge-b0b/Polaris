from __future__ import annotations

from dishka import Provider, Scope, provide

from intelligence.attribution.attribution_engine import AttributionEngine


class IntelligenceAttributionDIProvider(Provider):
    """DI provider for attribution intelligence runtime nodes."""

    scope = Scope.APP

    @provide
    def provide_attribution_engine(
        self,
    ) -> AttributionEngine:
        return AttributionEngine()
