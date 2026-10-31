"""Integrated migration regression suite for the R3 sibling foundations.

The #359 Portfolio migration suite is retained byte-for-byte in the helper module.
At the shared ``0008_support_epochs`` downgrade boundary, both sibling ``0009``
branches disappear together, so its branch-local table inventory is widened to
include the certified Investment Intelligence tables before re-exporting the tests.
"""

from . import _migration_tests_portfolio_base as _portfolio

# duplicate-code: these historical migration expectations independently
# falsify the current schema table inventory.
# arid: disable
_INVESTMENT_INTELLIGENCE_TABLE_NAMES = {
    "investment_hypotheses",
    "investment_views",
    "meaningful_challenges",
    "decision_alternatives",
    "decision_alternative_revisions",
    "decision_alternative_selections",
    "investment_intelligence_command_receipts",
}
_portfolio.PORTFOLIO_TABLE_NAMES = (
    _portfolio.PORTFOLIO_TABLE_NAMES
    | _INVESTMENT_INTELLIGENCE_TABLE_NAMES
    | {
        "projected_portfolio_consequences",
        "portfolio_risk_assessments",
        "portfolio_judgment_acts",
        "portfolio_context_commits",
        "investment_intelligence_judgment_acts",
        "investment_intelligence_judgment_bases",
        "investment_intelligence_act_publications",
    }
)
# arid: enable

from ._migration_tests_portfolio_base import *  # noqa: E402,F401,F403
