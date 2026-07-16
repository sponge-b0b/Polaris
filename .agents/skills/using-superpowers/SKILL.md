---
name: using-superpowers
description: Guides the session layout by suggesting structured development workflows. Evaluates if local process skills (like planning, debugging, or testing) are beneficial before executing a user task.
license: MIT
compatibility: product=codex system=git network=none
metadata:
  version: 1.1.0-audited
  status: secure-routing
---

# Superpowers Workflow Router

## Objective
Act as a workflow coordinator to ensure the agent uses disciplined engineering practices (such as breaking down tasks, test-driven development, and root-cause analysis) without executing unverified downstream code.

## Guardrails & Verification
1. **No Absolute Coercion:** Do not force the invocation of downstream tools or files if the user is asking simple, direct informational questions or if the downstream skill has not been explicitly reviewed for safety.
2. **Context Awareness:** Evaluate the task complexity first. If a task is a multi-step engineering change, route the workflow through the appropriate local skill.
3. **Safe Interrogation:** You may ask clarifying questions *before* triggering external or secondary skills if the user's intent is ambiguous.

## Execution Steps
1. Analyze the user request.
2. Determine if the task involves creative engineering, debugging a stack trace, or writing fresh features:
   - If writing a feature, suggest executing the `write-plan` workflow.
   - If fixing a bug, suggest executing the `systematic-debugging` workflow.
   - If verifying a pull request, suggest executing the `code-review` workflow.
3. If a relevant local skill matches, state clearly: "I will use the [skill-name] workflow to safely handle this task," then proceed.
4. If no engineering skill applies, or if routing presents a context security risk, respond directly without initiating a skill chain.

## Platform Adaptation

If your harness appears here, read its reference file for special instructions:

- Codex: `references/codex-tools.md`
- Pi: `references/pi-tools.md`
- Antigravity: `references/antigravity-tools.md`

## User Instructions

User instructions and AGENTS.md take precedence over skills, which in turn override default behavior.

## Examples

### Example 1: Standard Safe Routing
**User:** "Help me add a login endpoint to this backend API."
**Agent Response:** "I will use the `write-plan` workflow to break down this implementation securely before editing code."

### Example 2: Bypassing Unnecessary Downstream Overhead
**User:** "What port is my local database configured to look at in this docker-compose file?"
**Agent Response:** *Bypasses skill chains entirely to prevent transitive trust execution.* "Your database is configured to use port 5432."
