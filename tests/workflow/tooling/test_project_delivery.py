from __future__ import annotations

import pytest

from scripts.project_delivery import DeliveryStateError, guard, reconcile

CONTROL_ISSUE = 9001
FOCUSED_WAYFINDER = 101
UNFOCUSED_WAYFINDER = 102
BLOCKING_WAYFINDER = 99


def issue(number: int, *, state: str = "open", labels: tuple[str, ...] = ()) -> dict:
    return {
        "number": number,
        "state": state,
        "labels": [{"name": label} for label in labels],
    }


class FakeClient:
    def __init__(
        self,
        *,
        control_body: str,
        controls: int = 1,
        issues: dict[int, dict] | None = None,
        blockers: dict[int, list[dict]] | None = None,
    ) -> None:
        self.control_body = control_body
        self.controls = controls
        self.issues = issues or {}
        self.blockers = blockers or {}
        self.updated: tuple[int, str] | None = None

    def control_issues(self) -> list[dict]:
        return [
            {
                "number": CONTROL_ISSUE + i,
                "state": "open",
                "labels": [{"name": "project-delivery:management"}],
                "body": self.control_body,
            }
            for i in range(self.controls)
        ]

    def issue(self, number: int) -> dict:
        return self.issues[number]

    def blocked_by(self, number: int) -> list[dict]:
        return self.blockers.get(number, [])

    def comment(self, comment_id: int) -> dict:
        raise AssertionError(f"unexpected comment read {comment_id}")

    def update_issue_body(self, number: int, body: str) -> None:
        self.updated = (number, body)
        self.control_body = body


CONTROL_FOCUSED = f"""## Current Delivery State

**Focused Wayfinders:** #{FOCUSED_WAYFINDER}
**Parallel authorization:** None"""


def test_guard_allowed_is_exact_receipt() -> None:
    client = FakeClient(
        control_body=CONTROL_FOCUSED,
        issues={
            FOCUSED_WAYFINDER: issue(
                FOCUSED_WAYFINDER,
                labels=("wayfinder:map",),
            )
        },
    )
    result = guard(client, FOCUSED_WAYFINDER)
    assert result.allowed is True
    assert result.render() == (
        "PROJECT DELIVERY GUARD: ALLOWED\n"
        f"Wayfinder: #{FOCUSED_WAYFINDER}\n"
        f"Focused set: #{FOCUSED_WAYFINDER}"
    )


def test_guard_fails_closed_on_duplicate_control_issue() -> None:
    client = FakeClient(
        control_body=CONTROL_FOCUSED,
        controls=2,
        issues={
            FOCUSED_WAYFINDER: issue(
                FOCUSED_WAYFINDER,
                labels=("wayfinder:map",),
            )
        },
    )
    result = guard(client, FOCUSED_WAYFINDER)
    assert result.allowed is False
    assert result.reason == "invalid control state"


def test_guard_rejects_unfocused_wayfinder() -> None:
    client = FakeClient(
        control_body=CONTROL_FOCUSED,
        issues={
            FOCUSED_WAYFINDER: issue(
                FOCUSED_WAYFINDER,
                labels=("wayfinder:map",),
            ),
            UNFOCUSED_WAYFINDER: issue(
                UNFOCUSED_WAYFINDER,
                labels=("wayfinder:map",),
            ),
        },
    )
    result = guard(client, UNFOCUSED_WAYFINDER)
    assert result.allowed is False
    assert result.reason == "not focused"


def test_reconcile_removes_closed_focused_wayfinder_and_reads_back() -> None:
    client = FakeClient(
        control_body=CONTROL_FOCUSED,
        issues={
            FOCUSED_WAYFINDER: issue(
                FOCUSED_WAYFINDER,
                state="closed",
                labels=("wayfinder:map",),
            )
        },
    )
    changed, focused = reconcile(client)
    assert changed is True
    assert focused == ()
    assert client.updated is not None
    assert "**Focused Wayfinders:** None" in client.updated[1]
    assert "**Parallel authorization:** None" in client.updated[1]


def test_reconcile_removes_open_map_with_open_map_blocker() -> None:
    blocker = issue(BLOCKING_WAYFINDER, labels=("wayfinder:map",))
    client = FakeClient(
        control_body=CONTROL_FOCUSED,
        issues={
            FOCUSED_WAYFINDER: issue(
                FOCUSED_WAYFINDER,
                labels=("wayfinder:map",),
            )
        },
        blockers={FOCUSED_WAYFINDER: [blocker]},
    )
    changed, focused = reconcile(client)
    assert changed is True
    assert focused == ()


def test_reconcile_rejects_non_wayfinder_focus() -> None:
    client = FakeClient(
        control_body=CONTROL_FOCUSED,
        issues={FOCUSED_WAYFINDER: issue(FOCUSED_WAYFINDER, labels=())},
    )
    with pytest.raises(DeliveryStateError, match="not a canonical Wayfinder"):
        reconcile(client)
