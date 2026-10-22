from __future__ import annotations

import pytest

from scripts.project_delivery import (
    DeliveryStateError,
    GitHubClient,
    GitHubCommandError,
    guard,
    reconcile,
)

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


def control_issue(number: int = CONTROL_ISSUE) -> dict:
    return {
        "number": number,
        "state": "open",
        "labels": [{"name": "project-delivery:management"}],
        "body": CONTROL_FOCUSED,
    }


def graphql_page(
    numbers: tuple[int, ...],
    *,
    has_next: bool = False,
    end_cursor: str | None = None,
) -> dict:
    return {
        "data": {
            "repository": {
                "issues": {
                    "nodes": [{"number": number} for number in numbers],
                    "pageInfo": {
                        "hasNextPage": has_next,
                        "endCursor": end_cursor,
                    },
                }
            }
        }
    }


def test_control_issue_discovery_uses_complete_graphql_label_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = GitHubClient("owner/repo")
    first = control_issue(CONTROL_ISSUE)
    second = control_issue(CONTROL_ISSUE + 1)
    pages = iter(
        [
            graphql_page((CONTROL_ISSUE,), has_next=True, end_cursor="cursor-1"),
            graphql_page((CONTROL_ISSUE + 1,)),
        ]
    )
    calls: list[tuple[str, str, dict[str, str]]] = []

    def fake_request(
        endpoint: str,
        *,
        method: str = "GET",
        fields: dict[str, str] | None = None,
    ) -> dict:
        assert fields is not None
        calls.append((endpoint, method, fields.copy()))
        return next(pages)

    monkeypatch.setattr(client, "_request", fake_request)
    monkeypatch.setattr(
        client,
        "issue",
        lambda number: first if number == CONTROL_ISSUE else second,
    )

    assert [row["number"] for row in client.control_issues()] == [
        CONTROL_ISSUE,
        CONTROL_ISSUE + 1,
    ]
    assert [endpoint for endpoint, _, _ in calls] == ["graphql", "graphql"]
    assert [method for _, method, _ in calls] == ["POST", "POST"]
    assert calls[0][2]["owner"] == "owner"
    assert calls[0][2]["name"] == "repo"
    assert calls[0][2]["label"] == "project-delivery:management"
    assert "after" not in calls[0][2]
    assert calls[1][2]["after"] == "cursor-1"


def test_control_issue_discovery_rechecks_current_exact_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = GitHubClient("owner/repo")
    monkeypatch.setattr(
        client,
        "_request",
        lambda endpoint, **kwargs: graphql_page((CONTROL_ISSUE,)),
    )
    monkeypatch.setattr(
        client,
        "issue",
        lambda number: issue(number, labels=()),
    )

    with pytest.raises(GitHubCommandError, match="without the exact control label"):
        client.control_issues()


def test_control_issue_discovery_fails_closed_on_incomplete_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = GitHubClient("owner/repo")
    monkeypatch.setattr(
        client,
        "_request",
        lambda endpoint, **kwargs: graphql_page(
            (CONTROL_ISSUE,), has_next=True, end_cursor=None
        ),
    )

    with pytest.raises(GitHubCommandError, match="missing end cursor"):
        client.control_issues()


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