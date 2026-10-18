from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _composed_skill(relative: str) -> str:
    skill = ROOT / relative / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    procedure = skill.parent / "PROCEDURE.md"
    if procedure.exists():
        text += "\n" + procedure.read_text(encoding="utf-8")
    return text


TO_TICKETS = _composed_skill(".agents/skills/to-tickets")
TO_SPECS = _composed_skill(".agents/skills/to-specs")
IMPLEMENT = _composed_skill(".agents/skills/implement-ticket")
WAYFINDER = _composed_skill(".agents/skills/wayfinder")


def test_to_tickets_preserves_prepublication_branch_guard_order() -> None:
    approval = TO_TICKETS.index("## 10. Human approval")
    branch_guard = TO_TICKETS.index("### Pre-publication Spec Branch Guard")
    publication = TO_TICKETS.index("## 11. Publication/readback")

    assert approval < branch_guard < publication
    for phrase in (
        "SPEC BRANCH GUARD: PASS",
        "## Workspace Metadata",
        "GitHub Development linkage",
        "origin/SPEC_BRANCH",
        "zero ticket-publication\nmutations",
    ):
        assert phrase in TO_TICKETS


def test_to_tickets_branch_guard_cannot_be_waived_by_approval() -> None:
    assert "Human approval authorizes the approved ticket delta" in TO_TICKETS
    assert "it does not waive branch lifecycle\nsafety" in TO_TICKETS
    assert "Publication is reachable only" in TO_TICKETS
    assert "SPEC BRANCH GUARD: PASS" in TO_TICKETS


def test_readiness_labels_remain_gate_outputs() -> None:
    assert "### Readiness label gate" in TO_SPECS
    assert "Apply it to a Spec only after" in TO_SPECS
    assert "After any label mutation, re-read the Spec" in TO_SPECS

    publication = TO_TICKETS.index("## 11. Publication/readback")
    label_rule = TO_TICKETS.index("`ready-for-agent` is readiness projection")
    assert publication < label_rule
    assert "Do not\napply it before the branch guard" in TO_TICKETS
    assert "Re-read\nlabel state after mutation" in TO_TICKETS


def test_implement_ticket_has_explicit_terminal_state_contract() -> None:
    assert "## Invocation termination" in IMPLEMENT
    for phrase in ("**Completed**", "**Human Handoff**", "**Hard Blocker**"):
        assert phrase in IMPLEMENT
    for phrase in (
        "Everything else is non-terminal",
        "`TICKET CLOSURE: FAIL`",
        "`TICKET CLOSURE: PASS` before exact persistence/closure",
        "continue the lifecycle in the same\ninvocation",
    ):
        assert phrase in IMPLEMENT


def test_implement_ticket_separates_immutable_baseline_from_execution_anchor() -> None:
    assert "## Execution-anchor invariant" in IMPLEMENT
    assert "Ticket baseline" in IMPLEMENT
    assert "Execution Anchor" in IMPLEMENT
    assert "fetch the actual remote ticket branch" in IMPLEMENT
    assert "fast-forward only" in IMPLEMENT
    assert "Do not require the current shared branch to equal that historical SHA" in IMPLEMENT


def test_wayfinder_returns_focus_choice_to_human_owner() -> None:
    assert "### Human focus handoff" in WAYFINDER
    assert "PROJECT DELIVERY: HUMAN FOCUS HANDOFF" in WAYFINDER
    assert "$project-delivery-management status" in WAYFINDER
    assert "Never switch or broaden focus automatically" in WAYFINDER
    assert "Resume Wayfinder work\nonly after" in WAYFINDER


def test_core_lifecycle_capability_matrix_remains_present() -> None:
    required = {
        "to-tickets": (
            TO_TICKETS,
            (
                "Human approval",
                "Spec Branch Guard",
                "Ticket baseline: Pending",
                "native children",
                "ready-for-agent",
                "Publication/readback",
                "Frontier handoff",
            ),
        ),
        "to-specs": (
            TO_SPECS,
            (
                "Session independence",
                "Permanent reconciliation rule",
                "Stable execution topology",
                "Cross-Spec ownership integrity",
                "Readiness label gate",
                "Human handoff",
            ),
        ),
        "implement-ticket": (
            IMPLEMENT,
            (
                "Invocation termination",
                "Guard branch and ticket baseline",
                "Durable closure checkpoint v3",
                "Independent closure dispatch",
                "Persist the exact certified candidate",
                "Frontier handoff",
            ),
        ),
        "wayfinder": (
            WAYFINDER,
            (
                "Session independence",
                "Project delivery guard",
                "Human focus handoff",
                "Human acceptance",
                "Atomic repository persistence",
                "Route clarity",
            ),
        ),
    }

    for _skill, (text, capabilities) in required.items():
        for capability in capabilities:
            assert capability in text
