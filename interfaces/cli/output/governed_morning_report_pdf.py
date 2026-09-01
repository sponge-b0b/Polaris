from __future__ import annotations

from application.presentation.governed_result import GovernedPresentationResult
from application.reports.morning_report_models import MorningReportDocument
from interfaces.cli.output.pdf_output_renderer import (
    MorningReportPdfRenderer as LegacyMorningReportPdfRenderer,
)


class MorningReportPdfRenderer:
    """Serialize only an application-governed morning report as PDF."""

    def __init__(self) -> None:
        self._renderer = LegacyMorningReportPdfRenderer()

    def render(
        self,
        governed_result: GovernedPresentationResult[MorningReportDocument],
    ) -> bytes:
        if not isinstance(governed_result, GovernedPresentationResult):
            raise TypeError(
                "MorningReportPdfRenderer requires a governed presentation result."
            )
        return self._renderer.render(governed_result.require_presentable_payload())


__all__ = ["MorningReportPdfRenderer"]
