# Plan: Update CLI Output Formats, Defaults, and Add New Format Support

## Goal

Update the CLI workflow execution behavior so human-friendly console output, progress display, and interactive workflow control are the default behavior for every workflow run.

The obsolete flags are:

```text
--format console
--progress
--interactive-control
```

These should be removed because their behavior is now always enabled.

The new supported `--format` options are:

```text
html
json
markdown
pdf
```

For every workflow execution:

1. The CLI must always display output to stdout.
2. The CLI must always show progress by default.
3. The CLI must always enable interactive workflow control by default.
4. The CLI must create a formatted output file in the current working directory.
5. Output file name must be based on workflow name:

```text
<workflow_name>_<datetime>.html
<workflow_name>_<datetime>.json
<workflow_name>_<datetime>.md
<workflow_name>_<datetime>.pdf
```

For example: morning_report_2026-05-25T08:52:14.md

---

# Final CLI Behavior

## Default Behavior

Running a workflow with no output flags:

```bash
python -m cli run morning_report
```

Should behave like the old:

```bash
python -m cli run morning_report --format console --progress --interactive-control
```

Meaning:

```text
console output is shown
progress is shown
interactive controls are enabled
```

No output file is required unless `--format` is specified.

---

## HTML Output

Command:

```bash
python -m cli run morning_report --format html
```

Behavior:

```text
1. Display workflow result to stdout.
2. Show progress during execution.
3. Enable interactive control during execution.
4. Write ./morning_report_2026-05-25T08:52:14.html.
```
Important:

```text
HTML markup must not be printed to stdout.
```

For `--format html`, stdout should display a text readable version of the HTML file.


## JSON Output

Command:

```bash
python -m cli run morning_report --format json
```

Behavior:

```text
1. Display workflow result to stdout.
2. Show progress during execution.
3. Enable interactive control during execution.
4. Write ./morning_report_2026-05-25T08:52:14.json.
```

---

## Markdown Output

Command:

```bash
python -m cli run morning_report --format markdown
```

Behavior:

```text
1. Display rendered markdown report to stdout.
2. Show progress during execution.
3. Enable interactive control during execution.
4. Write ./morning_report_2026-05-25T08:52:14.md.
```

---

## PDF Output

Command:

```bash
python -m cli run morning_report --format pdf
```

Behavior:

```text
1. Display human-readable console output to stdout.
2. Show progress during execution.
3. Enable interactive control during execution.
4. Write ./morning_report_2026-05-25T08:52:14.pdf.
```

Important:

```text
PDF binary content must not be printed to stdout.
```

For `--format pdf`, stdout should display a readable pretty text version of the PDF.

---

# CLI Format Rules

## Supported Values

Update CLI parser so:

```text
--format html
--format json
--format markdown
--format pdf
```

are the only supported values.

Remove:

```text
--format console
```

Console output is now always enabled and no longer selectable.

---

## Obsolete Flags

Remove the following flags from CLI parser:

```text
--progress
--interactive-control
```

Their behavior should be enabled automatically for all workflow executions.

If backwards compatibility is desired, optionally keep these flags temporarily as hidden/no-op aliases with deprecation warnings.

Preferred final behavior:

```text
Remove them completely.
```

---

# Output File Naming

Formatted output files must be written to the current working directory.

Naming convention:

```text
html     -> <workflow_name>_<datetime>.html
json     -> <workflow_name>_<datetime>.json
markdown -> <workflow_name>_<datetime>.md
pdf      -> <workflow_name>_<datetime>.pdf
```

Examples:

```text
morning_report_2026-05-25T08:52:14.html
morning_report_2026-05-25T08:52:14.json
morning_report_2026-05-25T08:52:14.md
morning_report_2026-05-25T08:52:14.pdf
```

Implementation helper:

```python
def output_path_for_format(
    workflow_name: str,
    output_format: str,
) -> Path:
    extension_map = {
        "html": ".html",
        "json": ".json",
        "markdown": ".md",
        "pdf": ".pdf",
    }

    return Path.cwd() / f"{workflow_name}{extension_map[output_format]}"
```

---

# Output Architecture

Do not put formatting logic directly inside the workflow runtime.

Use a CLI/report output layer.

Preferred structure:

```text
cli/
├── output/
│   ├── workflow_output_formatter.py
│   ├── workflow_output_writer.py
│   ├── markdown_output_renderer.py
│   ├── html_output_renderer.py
│   ├── json_output_renderer.py
│   ├── pdf_output_renderer.py
│   └── __init__.py
```

If existing CLI output files already exist, update those instead of creating duplicate systems.

---

# Formatting Responsibilities

## Runtime

Runtime returns canonical machine output.

Do not change:

```text
WorkflowResult
RuntimeNodeOutput
node_outputs
execution_metadata
```

## Report Layer

Report layer converts workflow result into human-readable report objects.

For morning report, prefer:

```text
application/reports/morning/
```

Existing or planned report components:

```text
MorningReportAssembler
MorningReportDocument
MorningReportMarkdownRenderer
MorningReportService
```

## CLI Output Layer

CLI output layer:

```text
selects format
renders output
prints stdout summary/content
writes output file
```

---

# HTML Format

## HTML File

Write full structured workflow result or report result to:

```text
./<workflow_name>_<datetime>.html
```

Use pretty HTML formatting:

## HTML stdout

Print pretty HTML formatted text to stdout.

Do not print hyper-text markup language.


# JSON Format

## JSON File

Write full structured workflow result or report result to:

```text
./<workflow_name>_<datetime>.json
```

Use pretty formatting:

```python
json.dumps(
    data,
    indent=2,
    sort_keys=True,
    default=str,
)
```

## JSON stdout

Print the same JSON string to stdout.

Do not print raw Python objects.

---

# Markdown Format

## Markdown File

Write rendered markdown report to:

```text
./<workflow_name>_<datetime>.md
```

For `morning_report`, use the professional morning report renderer.

## Markdown stdout

Print the rendered markdown to stdout.

Do not print raw node dumps.

---

# PDF Format

## PDF File

Write rendered PDF report to:

```text
./<workflow_name>_<datetime>.pdf
```

PDF should be generated from markdown or report document content.

Preferred flow:

```text
WorkflowResult
    -> MorningReportDocument
        -> Markdown
            -> PDF
```

Do not generate PDF directly from raw runtime JSON.

---

## PDF stdout

Do not print PDF bytes.

Print a human-readable pretty text version of the PDF file.

---

# PDF Renderer Implementation Options

Use whichever dependency already exists in the project.

Preferred options:

```text
markdown -> HTML -> PDF
```

Possible libraries:

```text
weasyprint
reportlab
markdown
pypdf
```

If no PDF library is installed, add one using the project dependency manager.

Recommended:

```text
reportlab
```

because it is straightforward for structured reports and avoids browser dependencies.

If using ReportLab, create:

```text
cli/output/pdf_output_renderer.py
```

or:

```text
application/reports/renderers/pdf_renderer.py
```

Responsibilities:

```text
title
subtitle
section headings
paragraphs
bullet lists
tables
page breaks
footer with execution_id/date
```

Minimum viable PDF:

```text
Title
Execution metadata
Executive Summary
Portfolio Snapshot
Macro Backdrop
Technical Setup
News & Sentiment
Risk Assessment
Recommended Action Plan
```

---

# Progress and Interactive Control Defaults

Progress display should always be enabled.

Interactive control should always be enabled.

CLI should subscribe to runtime progress events by default:

```text
runtime.workflow.started
runtime.workflow.running
runtime.workflow.paused
runtime.workflow.resumed
runtime.workflow.cancelled
runtime.workflow.completed
runtime.workflow.failed
runtime.workflow.wave.started
runtime.workflow.wave.completed
runtime.node.started
runtime.node.completed
runtime.node.failed
```

Interactive controls should be available by default.

Suggested controls:

```text
p = pause
r = resume
c = cancel
q = cancel/quit
```

Control methods should call:

```python
runtime.facade.pause_workflow(...)
runtime.facade.resume_workflow(...)
runtime.facade.cancel_workflow(...)
runtime.facade.get_workflow_state(...)
```

Do not require users to pass flags to enable this.

---

# CLI Parser Changes

Find the CLI command that runs workflows.

Update parser:

## Before

```text
--format console|json|markdown
--progress
--interactive-control
```

## After

```text
--format html|json|markdown|pdf
```

Optional:

```text
--no-progress
--no-interactive-control
```

Do not add these unless explicitly desired.

Current requirement:

```text
progress and interactive control are always on
```

So do not add disable flags unless needed later.

---

# Backward Compatibility Decision

Preferred:

```text
Remove obsolete flags completely.
```

If tests or users still call them, update tests and documentation.

Optional transitional behavior:

```text
--progress accepted but ignored
--interactive-control accepted but ignored
--format console rejected with clear message
```

Recommended error for `--format console`:

```text
--format console is obsolete. Console output is now the default. Use --format html, json, markdown, or pdf to also write a formatted file.
```

---

# Output Writer

Create or update:

```text
WorkflowOutputWriter
```

Responsibilities:

```python
class WorkflowOutputWriter:
    def write(
        self,
        workflow_name: str,
        output_format: str,
        rendered_output: str | bytes,
    ) -> Path:
        ...
```

Rules:

```text
html     -> text
json     -> text
markdown -> text
pdf      -> text to stdout, bytes to file
```

Use current working directory:

```python
Path.cwd()
```

Overwrite behavior:

```text
Overwrite existing <workflow_name>_<datetime>.<ext> by default.
```

Optional later:

```text
--output-dir
--output-file
--no-overwrite
```

Do not implement unless needed now.

---

# Morning Report Integration

For `morning_report`, do not use raw workflow output as markdown/PDF.

Use:

```text
MorningReportService
```

Expected methods:

```python
render_markdown(workflow_result) -> str
render_pdf(workflow_result) -> bytes
render_summary(workflow_result) -> str
```

If `render_pdf` does not exist yet, implement through a PDF renderer.

For non-report workflows:

```text
json     -> structured workflow result
markdown -> generic markdown summary
pdf      -> generic PDF summary
```

Morning report should receive specialized formatting.

---

# Generic Workflow Markdown Fallback

If no workflow-specific report renderer exists, use generic markdown:

```markdown
# Workflow Report: <workflow_name>

**Status:** succeeded  
**Execution ID:** ...  

## Node Summary

| Node | Status | Duration | Confidence |
|---|---|---:|---:|

## Outputs

Summarized node outputs.
```

Do not dump raw deeply nested JSON unless user requests raw/debug.

---

# Tests

Add or update tests:

```text
tests/unit/cli/test_workflow_output_formats.py
tests/unit/cli/test_workflow_output_writer.py
tests/unit/cli/test_pdf_output_renderer.py
tests/unit/cli/test_html_output_renderer.py
tests/integration/cli/test_workflow_run_outputs.py
```

Test cases:

```text
--format html writes <workflow_name>_<datetime>.html
--format json writes <workflow_name>_<datetime>.json
--format markdown writes <workflow_name>_<datetime>.md
--format pdf writes <workflow_name>_<datetime>.pdf
--format html prints pretty text to stdout
--format json prints JSON to stdout
--format markdown prints markdown to stdout
--format pdf prints pretty text version of PDF to stdout, not PDF bytes
--format console is rejected or removed
--progress flag is removed or ignored
--interactive-control flag is removed or ignored
default run prints console output
progress events are displayed by default
interactive control is enabled by default
```

---

# Documentation Updates

Update CLI help text.

New help should communicate:

```text
Console output, progress, and interactive controls are enabled by default.

--format html      print pretty text and write ./<workflow_name>_<datetime>.html
--format json      print JSON and write ./<workflow_name>_<datetime>.json
--format markdown  print markdown and write ./<workflow_name>_<datetime>.md
--format pdf       print pretty text version of PDF and write ./<workflow_name>_<datetime>.pdf
```

Remove documentation references to:

```text
--format console
--progress
--interactive-control
```

---

# Implementation Order

1. Locate CLI workflow run command.
2. Remove `console` from `--format` choices.
3. Remove `--progress` flag.
4. Remove `--interactive-control` flag.
5. Ensure console output always happens by default.
6. Ensure progress display always happens by default.
7. Ensure interactive workflow control always happens by default.
8. Add `html, pdf` to `--format` choices.
9. Implement output path helper using `<workflow_name>_<datetime>.<ext>`.
10. Implement HTML renderer/writer.
11. Implement JSON renderer/writer.
12. Implement markdown renderer/writer.
13. Implement PDF renderer/writer.
14. Integrate MorningReportService for `morning_report` markdown/PDF output.
15. Add generic markdown/PDF fallback for other workflows.
16. Update stdout behavior for each format.
17. Add/update tests.
18. Update CLI help/docs.
19. Run full CLI and report test suite.

---

# Acceptance Criteria

- `--format console` is no longer needed.
- Console output is always displayed by default.
- Progress is always displayed by default.
- Interactive control is always enabled by default.
- `--progress` is removed or obsolete.
- `--interactive-control` is removed or obsolete.
- `--format html` prints pretty text to stdout and writes `./<workflow_name>_<datetime>.html`.
- `--format json` prints JSON to stdout and writes `./<workflow_name>_<datetime>.json`.
- `--format markdown` prints markdown to stdout and writes `./<workflow_name>_<datetime>.md`.
- `--format pdf` prints readable pretty text verion of PDF to stdout and writes `./<workflow_name>_<datetime>.pdf`.
- PDF bytes are never printed to stdout.
- Morning report markdown/PDF uses professional report renderer, not raw runtime dumps.
- Runtime contracts remain unchanged.
- Existing workflow execution behavior remains compatible.
- Tests pass.
---

# Codex Proposed Implementation Plan

## Summary

Update `polaris morning-report` and `polaris workflow run` so console output, progress notifications, and interactive workflow control are default behavior. `--format` becomes an optional file-output selector supporting only `html`, `json`, `markdown`, and `pdf`.

Chosen decisions:

- No `--format`: print human-readable stdout only; do not create a file.
- `--format html|json|markdown|pdf`: print appropriate stdout and write a timestamped file in the current working directory.
- Remove/reject obsolete flags: `--format console`, `--progress`, `--interactive-control`.
- Add `reportlab` for real PDF generation.
- Keep runtime/core contracts unchanged; implement this in CLI/report output layers.

## Key Interface Changes

- `polaris morning-report`
  - Default: render professional morning report to stdout, show progress, enable interactive control, write no file.
  - `--format markdown`: print markdown and write `./morning_report_<timestamp>.md`.
  - `--format html`: print readable text/markdown to stdout and write `./morning_report_<timestamp>.html`.
  - `--format json`: print JSON to stdout and write `./morning_report_<timestamp>.json`.
  - `--format pdf`: print readable text/markdown to stdout and write `./morning_report_<timestamp>.pdf`.
  - `--raw` remains supported for generic workflow output.

- `polaris workflow run <workflow_name>`
  - Same default progress/control behavior.
  - Same `--format html|json|markdown|pdf` file-output behavior.
  - Generic workflows use generic renderers; `morning_report` uses the professional report renderer.

- `--output/-o`
  - Retain as an explicit file-path override.
  - If supplied with `--format`, write that format to the provided path.
  - If supplied without `--format`, write the same default stdout text to that path while still printing stdout.

## Implementation Steps

Each step should be implemented independently, validated, summarized, and then stop for review before the next step.

- [x] 1. Append this implementation plan to `.agent/plans/plan_update_cli_output_add_new_formats.md`
  - Preserve the original plan.
  - Add a separate section titled `Codex Proposed Implementation Plan`.
  - Do not overwrite historical content.

- [x] 2. Introduce CLI output models and path helper
  - Add a small CLI output layer for rendered stdout/file artifacts.
  - Add deterministic helper for `<workflow_name>_<timestamp>.<ext>`.
  - Use a filesystem-safe UTC timestamp, e.g. `morning_report_20260527T083012Z.md`.

- [x] 3. Add renderer support for new formats
  - Extend rendering to support `html`, `json`, `markdown`, and `pdf`.
  - HTML/PDF must not print markup/binary to stdout.
  - JSON stdout and JSON file should use pretty formatted JSON.
  - Morning report formats should use `MorningReportAssembler` and professional report renderers where applicable.

- [x] 4. Add ReportLab PDF renderer
  - Add `reportlab` to `pyproject.toml` and `requirements.txt`.
  - Generate PDF from the typed morning report document for `morning_report`.
  - Provide a generic PDF fallback for non-report workflows using the generic markdown/report view.

- [x] 5. Update `polaris morning-report` CLI behavior
  - Change default output behavior from `--format console` to no format option.
  - Make progress renderer always active.
  - Make interactive control always active.
  - Reject `--format console`.
  - Remove `--progress` and `--interactive-control` options from the public command.

- [x] 6. Update `polaris workflow run` CLI behavior
  - Apply the same format/default/progress/control behavior to generic workflow runs.
  - Keep progress/control output on stderr.
  - Keep workflow result output on stdout.

- [x] 7. Implement automatic file writing
  - When `--format` is supplied, write the selected artifact to current working directory unless `--output` is supplied.
  - Always print stdout output regardless of file writing.
  - Ensure PDF writes bytes and text formats write UTF-8 text.

- [x] 8. Update tests
  - Add/update tests for default stdout-only behavior, default progress/control, obsolete flag rejection, all file formats, PDF stdout safety, HTML stdout safety, professional morning report rendering, and generic fallback rendering.
  - Use temporary working directories for file-output assertions.

- [x] 9. Update CLI help/docs
  - Help text should explain that console output, progress, and interactive control are default.
  - Help text should explain that `--format` writes an additional output file.
  - Remove public help references to `console`, `--progress`, and `--interactive-control`.

- [x] 10. Validation
  - Run focused tests: `pytest -q tests/unit/interfaces/cli tests/unit/application/reports`.
  - Run static checks on touched files with `ruff` and `mypy`.
  - Run `graphify update .` after code changes.
  - Do not commit until the user has reviewed the completed final step.

## Test Plan

- `polaris morning-report` prints the professional report and creates no file by default.
- `polaris morning-report --format markdown` prints markdown and writes `.md`.
- `polaris morning-report --format html` prints readable text and writes `.html`.
- `polaris morning-report --format json` prints JSON and writes `.json`.
- `polaris morning-report --format pdf` prints readable text and writes a valid `.pdf`.
- `polaris workflow run morning_report --format pdf` uses the professional morning report PDF path.
- `polaris workflow run <generic_workflow> --format markdown/html/pdf` uses generic workflow rendering.
- `--format console` fails with a clear error.
- `--progress` and `--interactive-control` are no longer accepted.
- Progress/control notifications go to stderr and do not corrupt stdout JSON.

## Assumptions

- Runtime/core contracts remain unchanged.
- `reportlab` is acceptable as a new dependency.
- Existing `--raw` behavior for morning report remains useful and should be preserved.
- The implementation will be completed one step at a time, with a stop-and-review checkpoint after each step.
