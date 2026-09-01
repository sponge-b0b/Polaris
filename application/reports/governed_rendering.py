from __future__ import annotations

from application.presentation.governed_result import GovernedPresentationResult
from application.reports.morning_report_models import MorningReportDocument
from application.reports.morning_report_renderer import (
    MorningReportMarkdownRenderer as LegacyMorningReportMarkdownRenderer,
)


class MorningReportMarkdownRenderer:
    """Serialize only a report the application already governed for presentation."""

    def __init__(self) -> None:
        self._renderer = LegacyMorningReportMarkdownRenderer()

    def render(
        self,
        governed_result: GovernedPresentationResult[MorningReportDocument],
    ) -> str:
        if not isinstance(governed_result, GovernedPresentationResult):
            raise TypeError(
                "MorningReportMarkdownRenderer requires a governed presentation result."
            )
        return self._renderer.render(governed_result.require_presentable_payload())


__all__ = ["MorningReportMarkdownRenderer"]
