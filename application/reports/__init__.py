"""Morning report domain models and rendering utilities."""

from application.reports.authority import (
    ReportAuthorityFailureMode,
    ReportAuthorityViolationError,
    morning_report_authority,
    report_authority_metadata,
)
from application.reports.morning_report_assembler import MorningReportAssembler
from application.reports.morning_report_models import (
    MorningReportDocument,
    ReportBullet,
    ReportMetric,
    ReportSection,
    ReportTable,
    ReportTableRow,
    format_confidence,
    format_currency,
    format_percent,
    format_regime,
    format_score,
)
from application.reports.morning_report_persistence import (
    MorningReportPersistenceMapper,
    MorningReportPersistenceService,
    ReportArtifactReference,
)
from application.reports.morning_report_renderer import MorningReportMarkdownRenderer
from application.reports.morning_report_sections import (
    first_score,
    first_text,
    get_execution_id,
    get_node_metadata,
    get_node_outputs,
    get_symbol,
    get_workflow_status,
    safe_list,
    safe_mapping,
    safe_score,
    summarize_long_text,
)

__all__ = [
    "MorningReportAssembler",
    "MorningReportDocument",
    "MorningReportMarkdownRenderer",
    "MorningReportPersistenceMapper",
    "MorningReportPersistenceService",
    "ReportArtifactReference",
    "ReportAuthorityFailureMode",
    "ReportAuthorityViolationError",
    "ReportBullet",
    "ReportMetric",
    "ReportSection",
    "ReportTable",
    "ReportTableRow",
    "format_confidence",
    "morning_report_authority",
    "report_authority_metadata",
    "format_currency",
    "format_percent",
    "format_regime",
    "format_score",
    "first_score",
    "first_text",
    "get_execution_id",
    "get_node_metadata",
    "get_node_outputs",
    "get_symbol",
    "get_workflow_status",
    "safe_list",
    "safe_mapping",
    "safe_score",
    "summarize_long_text",
]
