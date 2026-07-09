# Plan: Convert Morning Report Workflow Output Into Human-Readable Financial Report

## Goal

Transform the current `morning_report` workflow output from raw runtime node dumps into a professional financial report suitable for human consumption.

Current output is technically complete but not report-ready because it exposes:

- raw `RuntimeNodeOutput`
- nested JSON-like payloads
- execution metadata noise
- raw articles and raw sentiment feeds
- long unstructured LLM responses
- no executive summary
- no visual hierarchy
- no unified recommendation section
- no clean risk/market/portfolio interpretation

The new output should read like a professional morning market briefing, not a runtime debug log.

---

## Architecture Rule

Do not change the runtime output contract.

Keep these canonical machine-facing structures:

```text
RuntimeNodeOutput
WorkflowResult
node_outputs
execution_metadata

Add a report rendering layer above the runtime.

Correct architecture:

Workflow Runtime
    -> RuntimeNodeOutput
        -> MorningReportAssembler
            -> MorningReportDocument
                -> Markdown / HTML / PDF / CLI Renderers

Do not make runtime nodes responsible for final report formatting.

Proposed Package

Create:

application/reports/
├── morning/
│   ├── morning_report_assembler.py
│   ├── morning_report_models.py
│   ├── morning_report_renderer.py
│   ├── morning_report_sections.py
│   └── __init__.py
└── __init__.py

Optional later:

application/reports/renderers/
├── markdown_renderer.py
├── html_renderer.py
└── pdf_renderer.py

Step 1: Define Morning Report Models

Create:

application/reports/morning/morning_report_models.py

Use typed dataclasses, not raw dict[str, Any].

Recommended models:

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportScore:
    label: str
    score: float | None
    confidence: float | None
    regime: str | None


@dataclass(frozen=True, slots=True)
class ReportSection:
    title: str
    summary: str
    bullets: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class MorningReportDocument:
    title: str
    subtitle: str
    symbol: str
    execution_id: str
    generated_at: str
    executive_summary: ReportSection
    portfolio: ReportSection
    macro: ReportSection
    technical: ReportSection | None
    news: ReportSection | None
    sentiment: ReportSection | None
    risks: ReportSection
    recommendations: ReportSection
    appendix: ReportSection | None = None

Rules:

Models are human-report abstractions.
Do not store full raw node dumps in main report sections.
Raw data may be placed in optional appendix only.

Step 2: Build Node Output Extraction Helpers

Create:

application/reports/morning/morning_report_sections.py

Purpose:

Extract clean fields from runtime node outputs.

Needed helpers:

def get_node_outputs(
    workflow_result: dict[str, Any],
    node_name: str,
) -> dict[str, Any]:
    ...


def get_node_metadata(
    workflow_result: dict[str, Any],
    node_name: str,
) -> dict[str, Any]:
    ...


def safe_score(
    value: Any,
) -> float | None:
    ...


def safe_list(
    value: Any,
) -> tuple[str, ...]:
    ...


def summarize_long_text(
    text: str,
    max_chars: int = 1200,
) -> str:
    ...

Must support nodes like:

portfolio_state_builder
fundamental_agent
technical_agent
news_agent
sentiment_agent
risk agents
strategy agents
portfolio_manager_agent

Step 3: Build MorningReportAssembler

Create:

application/reports/morning/morning_report_assembler.py

Responsibility:

Convert raw workflow result into MorningReportDocument.

API:

class MorningReportAssembler:
    def assemble(
        self,
        workflow_result: dict[str, Any],
    ) -> MorningReportDocument:
        ...

Assembler should produce these sections:

1. Executive Summary
2. Portfolio Snapshot
3. Macro / Fundamental Backdrop
4. Technical Setup
5. News & Sentiment
6. Risk Assessment
7. Recommended Action Plan
8. Watchlist / Catalysts
9. Appendix

Step 4: Executive Summary Logic

Executive summary should synthesize the major signals.

Inputs:

portfolio_state_builder.outputs
fundamental_agent.outputs
technical_agent.outputs
news_agent.outputs
sentiment_agent.outputs
risk agents outputs
strategy synthesis outputs
portfolio manager outputs

Output should include:

Market Bias
Risk Posture
Portfolio Posture
Primary Opportunity
Primary Risk
Recommended Action

Example format:

## Executive Summary

**Market Bias:** Defensive / Neutral  
**Risk Posture:** Elevated  
**Portfolio Posture:** High cash, low exposure  
**Recommended Action:** Maintain caution; wait for technical confirmation before adding risk.

The morning workflow shows a risk-off macro backdrop, neutral news relevance, muted sentiment, and a defensive portfolio state with high cash levels. The platform does not recommend aggressive positioning until liquidity and technical confirmation improve.

Step 5: Portfolio Snapshot Section

Extract from:

portfolio_state_builder.outputs.features.equity_state
portfolio_state_builder.outputs.features.portfolio_state
portfolio_state_builder.outputs.features.risk_features

Render as clean financial summary.

Include:

Equity
Cash
Cash %
Portfolio value
Gross exposure
Net exposure
Largest position %
Risk intensity
Portfolio heat
Portfolio regime

Example:

## Portfolio Snapshot

| Metric | Value |
|---|---:|
| Equity | $100,104.20 |
| Cash | $92,604.50 |
| Cash Allocation | 92.5% |
| Gross Exposure | 7.5% |
| Net Exposure | 7.5% |
| Risk Intensity | 4.9% |
| Portfolio Regime | Flat |

Do not display raw features JSON.

Step 6: Macro / Fundamental Section

Extract from:

fundamental_agent.outputs
fundamental_agent.outputs.features.macro_state
fundamental_agent.outputs.llm_response

Render:

Macro Score
Macro Regime
Fed Stance
Inflation Regime
Liquidity Regime
Yield Curve Regime
Directional Score
Confidence

Use LLM response only as source material, not raw full dump unless appendix is enabled.

Example:

## Macro Backdrop

**Macro Regime:** Crisis Risk-Off  
**Fed Stance:** Hawkish  
**Liquidity:** Liquidity Crunch  
**Inflation:** High but cooling  
**Yield Curve:** Flat Curve  
**Directional Score:** -0.30  
**Confidence:** 40%

The macro backdrop remains defensive. Liquidity stress and hawkish policy pressure outweigh the benefit of cooling inflation. The yield curve remains flat, keeping recession-risk interpretation elevated.

Step 7: Technical Setup Section

If technical_agent exists, extract:

technical_score
trend
volatility
breadth
regime
snapshot
market_context

Render:

Technical Score
Trend Regime
Volatility Regime
Breadth Regime
Support / Resistance if available
RSI
MACD
VIX
VVIX
AD Line trend

Example:

## Technical Setup

**Technical Bias:** Neutral  
**Trend:** Mixed  
**Volatility Regime:** Normal  
**Breadth:** Deteriorating  
**Technical Score:** 0.12  
**Confidence:** 63%

Technical conditions do not yet confirm a high-conviction directional setup. Volatility is manageable, but breadth confirmation remains weak.

If technical node missing, render:

## Technical Setup

Technical analysis was not available in this run.

Step 8: News & Sentiment Section

Extract from:

news_agent.outputs
sentiment_agent.outputs

Do not print all raw articles.

Show:

Top themes
Market relevance
Top 3 headlines
News risks
Sentiment regime
Composite sentiment
Confidence

Provide hyper-links for Top 3 headlines

Example:

## News & Sentiment

**News Relevance:** Neutral  
**Sentiment:** Neutral / Choppy  
**Sentiment Score:** 0.05  
**Confidence:** 35%

Key themes:
- ECB hawkishness vs. US rate-cut expectations
- Inflation persistence
- Cross-asset volatility risk

Top headlines:
1. UK gilt yields retreat as political drama eases.
2. ECB officials remain focused on inflation.
3. US equity stories remain more stock-specific than broad-index bullish.

Raw article feeds should move to appendix or be omitted.

Step 9: Risk Assessment Section

Aggregate risk from:

portfolio_state_builder.risk_features
fundamental_agent.risks
news_agent.risks
sentiment_agent features
technical volatility analysis
risk agents if present

Render:

Primary risks
Risk severity
Portfolio risk posture
Macro risk
Liquidity risk
Volatility risk
Concentration risk

Example:

## Risk Assessment

**Overall Risk Posture:** Elevated / Defensive

Primary risks:
- Hawkish Fed policy keeps valuation pressure elevated.
- Liquidity regime remains risk-off.
- Inflation remains high despite cooling trend.
- Cross-asset volatility may increase if European rate expectations shift.
- Portfolio is low exposure and currently defensively positioned.

Step 10: Recommended Action Plan Section

Create a clear action section for the human user.

This should not say “execute trade automatically.”

Use:

Observe
Wait
Prepare
Reduce
Avoid
Consider
Monitor

Example:

## Recommended Action Plan

1. **Maintain defensive posture** while macro liquidity remains stressed.
2. **Do not add aggressive long exposure** until technical confirmation improves.
3. **Monitor Fed/rate expectations** as the primary macro catalyst.
4. **Watch VIX and breadth** for signs of risk-on confirmation.
5. **Keep cash available** for higher-conviction setups.

Rules:

No automated execution language.
No broker-order instruction unless explicitly produced by portfolio manager and approved by user.
Keep recommendations framed as decision support.

Step 11: Build Markdown Renderer

Create:

application/reports/morning/morning_report_renderer.py

API:

class MorningReportMarkdownRenderer:
    def render(
        self,
        document: MorningReportDocument,
    ) -> str:
        ...

Renderer should output professional markdown:

# Morning Market Report: SPY

**Execution:** ...
**Generated:** ...
**Status:** Succeeded

---

## Executive Summary
...

## Portfolio Snapshot
...

## Macro Backdrop
...

## Technical Setup
...

## News & Sentiment
...

## Risk Assessment
...

## Recommended Action Plan
...

## Appendix
...

Add formatting helpers:

def format_percent(value: float | None) -> str:
    ...


def format_currency(value: float | None) -> str:
    ...


def format_score(value: float | None) -> str:
    ...


def format_confidence(value: float | None) -> str:
    ...


def format_regime(value: str | None) -> str:
    ...

Step 12: Add Morning Report Service

Optional but recommended.

Create:

application/reports/morning/morning_report_service.py

API:

class MorningReportService:
    def __init__(
        self,
        assembler: MorningReportAssembler,
        renderer: MorningReportMarkdownRenderer,
    ) -> None:
        ...

    def render_markdown(
        self,
        workflow_result: dict[str, Any],
    ) -> str:
        ...

This keeps report generation reusable by:

CLI
web UI
email sender
PDF exporter
storage artifact writer

Step 13: Integrate Report Rendering Into Morning Report Workflow Output

Do not replace raw runtime result.

Add a rendered artifact.

At workflow completion:

raw workflow result remains machine output
morning report markdown becomes human output artifact

Possible locations:

storage/reports/morning/{execution_id}.md
storage/artifacts/runtime/{execution_id}/morning_report.md

If the workflow has artifact support, write:

artifacts={
    "morning_report_markdown": path,
}

or:

outputs={
    "report_markdown": markdown_report,
}

Prefer artifact for large reports.

Step 14: CLI Output Behavior

CLI should display:

path to markdown report
short summary

Example:

Morning report completed.

Report:
storage/reports/morning/49cf19fcb63449f785934a0461285042.md

Summary:
Market bias: Defensive / Neutral
Risk posture: Elevated
Recommended action: Maintain caution; wait for confirmation.

CLI should not print full raw node dumps by default.

Add the CLI options:

--raw
--json
--markdown
--output-file

Step 15: Tests

Create unit tests:

tests/unit/application/reports/morning/test_morning_report_assembler.py
tests/unit/application/reports/morning/test_morning_report_renderer.py

Test:

Assembler extracts portfolio snapshot.
Assembler extracts macro section.
Assembler extracts news/sentiment themes.
Assembler handles missing technical node.
Assembler handles missing risk node.
Renderer outputs markdown sections.
Renderer does not include raw RuntimeNodeOutput JSON by default.
Renderer includes execution_id.
Renderer includes recommendations.

Create integration test:

tests/integration/reports/test_morning_report_rendering.py

Test:

Given sample workflow result:
    report markdown renders successfully
    contains Executive Summary
    contains Portfolio Snapshot
    contains Macro Backdrop
    contains News & Sentiment
    contains Risk Assessment
    contains Recommended Action Plan
    does not dump raw node JSON

Step 16: Report Quality Requirements

The final report must be:

human-readable
professionally structured
sectioned
concise
decision-support oriented
portfolio-aware
risk-aware
macro-aware
not raw JSON
not runtime-debug output

The final report must include:

Executive Summary
Portfolio Snapshot
Macro Backdrop
Technical Setup
News & Sentiment
Risk Assessment
Recommended Action Plan
Appendix optional

The final report must not include:

raw RuntimeNodeOutput dumps
full raw article lists
full raw sentiment feeds
deep nested JSON
execution metadata noise
stack traces unless failure report

Step 17: Recommended Implementation Order

1. Create morning_report_models.py
2. Create morning_report_sections.py
3. Create morning_report_assembler.py
4. Create morning_report_renderer.py
5. Create morning_report_service.py
6. Add unit tests for assembler.
7. Add unit tests for renderer.
8. Add integration test using sample workflow output.
9. Wire renderer into morning_report workflow or CLI.
10. Write markdown report artifact.
11. Update CLI to show report path and summary.
12. Keep raw output available behind --raw or debug mode only.

Success Criteria

Morning report renders as professional markdown.
Raw node dumps are no longer the default human output.
Runtime result contract remains unchanged.
Report is generated from canonical RuntimeNodeOutput.outputs.
Missing sections degrade gracefully.
Report includes clear recommendations.
Report can be written to a markdown artifact.
CLI can show a short completion summary and report path.

---

## Agent Addendum — Implementation Plan

### Summary

Convert `polaris morning-report --format console` and markdown output from runtime/debug-style node dumps into a full human-readable financial report by adding a report assembly/rendering layer above runtime output. Preserve the runtime contract and keep raw node output available only through an explicit raw/debug path.

### Key Changes

- Add an application-level morning report layer under `application/reports/morning/` with typed report models, extraction helpers, an assembler, and a markdown/console-ready renderer.
- Introduce typed report concepts such as `MorningReportDocument`, `ReportSection`, and `ReportMetric`; use dictionaries only when reading runtime boundary data.
- Render full professional report output by default for `morning-report` console/markdown formats:
  - Executive Summary
  - Portfolio Snapshot
  - Macro / Fundamental Backdrop
  - Technical Setup
  - News & Sentiment
  - Risk Assessment
  - Recommended Action Plan
  - Optional Appendix / Run Details
- Keep `WorkflowRenderEnvelope`, `RuntimeNodeOutput`, `node_outputs`, and runtime persistence unchanged.
- Add `--raw/--no-raw` to morning-report output so legacy runtime/node dump rendering remains available when explicitly requested.
- Use existing `--output` behavior to save the rendered report; defer new artifact-storage wiring unless later requested.

### Step-by-Step Implementation Sequence

Each step should be implemented independently, validated, summarized, and then stop for user review before beginning the next step.

- [x] **Step 1: Append plan addendum**
  - Append this implementation plan to `.agent/plans/plan_morning_report_output_into_financial_report.md`.
  - Keep the original plan separate and unchanged.

- [x] **Step 2: Create report models**
  - Add immutable/slotted dataclasses for report document, sections, metrics, bullets, and table rows.
  - Add formatting helpers for currency, percent, score, confidence, and regime labels.

- [x] **Step 3: Create extraction helpers**
  - Add safe helpers to read node outputs from either raw workflow results or `WorkflowRenderEnvelope.to_dict()` shape.
  - Include graceful handling for missing nodes, failed nodes, malformed values, and long text truncation.

- [x] **Step 4: Assemble core sections**
  - Build `MorningReportAssembler`.
  - First produce Executive Summary and Portfolio Snapshot from available portfolio, strategy, risk, and execution guard outputs.
  - Ensure no raw `RuntimeNodeOutput` JSON appears in report sections.

- [x] **Step 5: Render initial report**
  - Add `MorningReportMarkdownRenderer`.
  - Render title, run metadata, Executive Summary, Portfolio Snapshot, and a concise Run Status section.

- [x] **Step 6: Expand intelligence sections**
  - Add Macro / Fundamental, Technical Setup, and News & Sentiment sections.
  - Render full LLM response text without summarizing or truncating it.
  - Keep raw article payloads concise unless explicit full article output is later requested.

- [x] **Step 7: Add risk and action plan sections**
  - Add Risk Assessment and Recommended Action Plan.
  - Frame all recommendations as decision support, never autonomous execution instructions.

- [x] **Step 8: Wire CLI rendering**
  - Update `morning-report` console/markdown output to use the new report renderer by default.
  - Add `--raw/--no-raw`; when `--raw` is set, use the existing generic workflow rendering.
  - Keep JSON output machine-oriented and unchanged unless a later step explicitly adds a report JSON shape.

- [x] **Step 9: Add unit tests**
  - Test assembler extraction for portfolio, macro, technical, news/sentiment, risk, and recommendations.
  - Test missing-node degradation.
  - Test renderer includes professional report sections and excludes raw runtime JSON by default.

- [x] **Step 10: Add CLI/integration coverage and validation**
  - Test `morning-report --format console` renders the full report.
  - Test `morning-report --format markdown` renders markdown sections.
  - Test `--raw` still exposes legacy runtime details.
  - Run targeted pytest, ruff, mypy where appropriate, then `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .`.

### Test Plan

- Unit tests for report models, extraction helpers, assembler, and renderer.
- CLI tests for default human-readable output and raw fallback behavior.
- Regression test ensuring default console/markdown output does **not** include `Runtime Node Outputs`, full raw node JSON, full article feeds, or execution metadata noise.
- Missing-data tests for absent technical/news/risk nodes.
- Validation commands per step:
  - targeted `pytest`
  - `ruff check`
  - targeted `mypy --explicit-package-bases --follow-imports=skip`
  - `GRAPHIFY_VIZ_NODE_LIMIT=6000 graphify update .` after code changes

### Assumptions and Defaults

- Default console output should render the **full professional financial report**, not only a summary/path.
- Raw runtime output remains available via `--raw`.
- Runtime contracts and workflow node outputs remain unchanged.
- The report layer consumes runtime output and produces human-facing presentation.
- Report artifacts are deferred for now because existing `--output` already supports saving rendered output.
- Implementation must proceed one step at a time, pausing after each completed step for user review before continuing.
### Revision — Full LLM Response Rendering

- User preference supersedes the original Step 6 truncation note.
- Do not summarize or truncate LLM response text in the morning report.
- Continue to avoid raw `RuntimeNodeOutput` dumps; preserve full LLM text inside typed report sections.

