"""Deterministic Project Delivery reconciliation and Wayfinder guard CLI."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol

_CONTROL_LABEL = "project-delivery:management"
_WAYFINDER_LABEL = "wayfinder:map"
_STATE_BLOCK_RE = re.compile(
    r"(?ms)^## Current Delivery State\n\n"
    r"\*\*Focused Wayfinders:\*\* (?P<focused>[^\n]+)\n"
    r"\*\*Parallel authorization:\*\* (?P<authorization>[^\n]+)"
    r"(?=\n## |\n?\Z)"
)
_AUTH_RE = re.compile(
    r"(?ms)^## Project Delivery Focus Authorization\n\n"
    r"\*\*Operation:\*\* parallel-focus\n"
    r"\*\*Focused Wayfinders:\*\* (?P<focused>[^\n]+)\n"
    r"\*\*Authorization source:\*\* explicit human invocation\s*$"
)
_COMMENT_ID_RE = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/issues/\d+#issuecomment-(\d+)$"
)


class DeliveryStateError(RuntimeError):
    """Raised when durable Project Delivery state cannot be proven valid."""


class GitHubCommandError(DeliveryStateError):
    """Raised when a required GitHub read or mutation fails."""


class ProjectDeliveryClient(Protocol):
    def control_issues(self) -> list[dict[str, Any]]: ...

    def issue(self, number: int) -> dict[str, Any]: ...

    def blocked_by(self, number: int) -> list[dict[str, Any]]: ...

    def comment(self, comment_id: int) -> dict[str, Any]: ...

    def update_issue_body(self, number: int, body: str) -> None: ...


@dataclass(frozen=True, slots=True)
class ControlState:
    issue_number: int
    body: str
    focused: tuple[int, ...]
    authorization: str | None


@dataclass(frozen=True, slots=True)
class GuardResult:
    wayfinder: int
    allowed: bool
    focused: tuple[int, ...]
    reason: str | None = None

    def render(self) -> str:
        if self.allowed:
            return "\n".join(
                (
                    "PROJECT DELIVERY GUARD: ALLOWED",
                    f"Wayfinder: #{self.wayfinder}",
                    f"Focused set: {_format_focus(self.focused)}",
                )
            )
        assert self.reason is not None
        return "\n".join(
            (
                "PROJECT DELIVERY GUARD: BLOCKED",
                f"Wayfinder: #{self.wayfinder}",
                f"Reason: {self.reason}",
            )
        )


class GitHubClient:
    def __init__(self, repo: str) -> None:
        if repo.count("/") != 1 or any(not part for part in repo.split("/")):
            raise DeliveryStateError("repository must be owner/name")
        self.repo = repo

    def _request(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        fields: dict[str, str] | None = None,
    ) -> Any:
        command = ["gh", "api", "--method", method, endpoint]
        if fields:
            for key, value in fields.items():
                command.extend(("-f", f"{key}={value}"))
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            detail = (
                completed.stderr.strip() or completed.stdout.strip() or "gh api failed"
            )
            raise GitHubCommandError(detail)
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise GitHubCommandError("gh api returned invalid JSON") from exc

    def _paged(self, endpoint: str, query: dict[str, str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page = 1
        while True:
            params = {**query, "per_page": "100", "page": str(page)}
            value = self._request(endpoint, fields=params)
            if not isinstance(value, list) or not all(
                isinstance(row, dict) for row in value
            ):
                raise GitHubCommandError("GitHub paged response was not an issue list")
            rows.extend(value)
            if len(value) < 100:
                return rows
            page += 1
            if page > 1000:
                raise GitHubCommandError("GitHub pagination exceeded safety bound")

    def control_issues(self) -> list[dict[str, Any]]:
        # GitHub's label-filtered issue listing has intermittently omitted the canonical
        # control issue. Enumerate issues and enforce the label locally instead.
        rows = self._paged(
            f"repos/{self.repo}/issues",
            {"state": "all"},
        )
        return [
            row
            for row in rows
            if "pull_request" not in row and _has_label(row, _CONTROL_LABEL)
        ]

    def issue(self, number: int) -> dict[str, Any]:
        value = self._request(f"repos/{self.repo}/issues/{number}")
        if not isinstance(value, dict) or "pull_request" in value:
            raise DeliveryStateError(f"#{number} is not a GitHub issue")
        return value

    def blocked_by(self, number: int) -> list[dict[str, Any]]:
        return self._paged(
            f"repos/{self.repo}/issues/{number}/dependencies/blocked_by",
            {},
        )

    def comment(self, comment_id: int) -> dict[str, Any]:
        value = self._request(f"repos/{self.repo}/issues/comments/{comment_id}")
        if not isinstance(value, dict):
            raise GitHubCommandError("GitHub comment response was not an object")
        return value

    def update_issue_body(self, number: int, body: str) -> None:
        value = self._request(
            f"repos/{self.repo}/issues/{number}",
            method="PATCH",
            fields={"body": body},
        )
        if not isinstance(value, dict) or value.get("body") != body:
            raise GitHubCommandError("Project Delivery control issue readback mismatch")


def _labels(issue: dict[str, Any]) -> set[str]:
    labels = issue.get("labels")
    if not isinstance(labels, list):
        raise DeliveryStateError("issue labels are unreadable")
    result: set[str] = set()
    for label in labels:
        if isinstance(label, str):
            result.add(label)
        elif isinstance(label, dict) and isinstance(label.get("name"), str):
            result.add(label["name"])
        else:
            raise DeliveryStateError("issue label is malformed")
    return result


def _has_label(issue: dict[str, Any], label: str) -> bool:
    return label in _labels(issue)


def _issue_number(issue: dict[str, Any]) -> int:
    number = issue.get("number")
    if not isinstance(number, int) or number < 1:
        raise DeliveryStateError("issue number is malformed")
    return number


def _issue_state(issue: dict[str, Any]) -> str:
    state = issue.get("state")
    if not isinstance(state, str):
        raise DeliveryStateError("issue state is malformed")
    return state.lower()


def _format_focus(focused: tuple[int, ...]) -> str:
    if not focused:
        return "None"
    return ", ".join(f"#{number}" for number in focused)


def _parse_focus(value: str) -> tuple[int, ...]:
    if value == "None":
        return ()
    parts = value.split(", ")
    if any(re.fullmatch(r"#[1-9][0-9]*", part) is None for part in parts):
        raise DeliveryStateError("Focused Wayfinders is malformed")
    focused = tuple(int(part[1:]) for part in parts)
    if focused != tuple(sorted(set(focused))):
        raise DeliveryStateError("Focused Wayfinders must be unique and sorted")
    return focused


def _parse_control(issue: dict[str, Any]) -> ControlState:
    if _issue_state(issue) != "open":
        raise DeliveryStateError("canonical Project Delivery control issue is closed")
    body = issue.get("body")
    if not isinstance(body, str):
        raise DeliveryStateError("Project Delivery control body is unreadable")
    matches = list(_STATE_BLOCK_RE.finditer(body))
    if len(matches) != 1:
        raise DeliveryStateError(
            "Project Delivery control body must contain one current-state block"
        )
    match = matches[0]
    focused = _parse_focus(match.group("focused"))
    authorization_value = match.group("authorization")
    authorization = None if authorization_value == "None" else authorization_value
    if len(focused) <= 1 and authorization is not None:
        raise DeliveryStateError(
            "Parallel authorization must be None for zero or one focused Wayfinder"
        )
    if len(focused) > 1 and authorization is None:
        raise DeliveryStateError(
            "Parallel authorization is required for multiple focused Wayfinders"
        )
    return ControlState(
        issue_number=_issue_number(issue),
        body=body,
        focused=focused,
        authorization=authorization,
    )


def _load_control(client: ProjectDeliveryClient) -> ControlState:
    candidates = client.control_issues()
    if len(candidates) != 1:
        raise DeliveryStateError(
            "expected exactly one Project Delivery control issue, "
            f"found {len(candidates)}"
        )
    return _parse_control(candidates[0])


def _require_wayfinder(issue: dict[str, Any], number: int) -> None:
    if _issue_number(issue) != number or not _has_label(issue, _WAYFINDER_LABEL):
        raise DeliveryStateError(f"#{number} is not a canonical Wayfinder map")


def _has_open_map_blocker(client: ProjectDeliveryClient, number: int) -> bool:
    for blocker in client.blocked_by(number):
        if _issue_state(blocker) == "open" and _has_label(blocker, _WAYFINDER_LABEL):
            return True
    return False


def _validate_parallel_authorization(
    client: ProjectDeliveryClient, control: ControlState
) -> None:
    if len(control.focused) <= 1:
        return
    assert control.authorization is not None
    match = _COMMENT_ID_RE.fullmatch(control.authorization)
    if match is None:
        raise DeliveryStateError("Parallel authorization URL is malformed")
    body = client.comment(int(match.group(1))).get("body")
    if not isinstance(body, str):
        raise DeliveryStateError("Parallel authorization comment body is unreadable")
    auth = _AUTH_RE.fullmatch(body.strip())
    if auth is None or _parse_focus(auth.group("focused")) != control.focused:
        raise DeliveryStateError("Parallel authorization does not match focused set")


def _replace_state_block(body: str, focused: tuple[int, ...]) -> str:
    replacement = (
        "## Current Delivery State\n\n"
        f"**Focused Wayfinders:** {_format_focus(focused)}\n"
        "**Parallel authorization:** None"
    )
    matches = list(_STATE_BLOCK_RE.finditer(body))
    if len(matches) != 1:
        raise DeliveryStateError(
            "Project Delivery control body must contain one current-state block"
        )
    return body[: matches[0].start()] + replacement + body[matches[0].end() :]


def reconcile(client: ProjectDeliveryClient) -> tuple[bool, tuple[int, ...]]:
    control = _load_control(client)
    retained: list[int] = []
    for number in control.focused:
        issue = client.issue(number)
        _require_wayfinder(issue, number)
        if _issue_state(issue) != "open":
            continue
        if _has_open_map_blocker(client, number):
            continue
        retained.append(number)
    focused = tuple(retained)
    if len(focused) > 1:
        if focused != control.focused:
            raise DeliveryStateError(
                "reconciliation would leave multiple focused Wayfinders "
                "without exact authorization"
            )
        _validate_parallel_authorization(client, control)
        return False, focused
    if focused == control.focused:
        return False, focused
    body = _replace_state_block(control.body, focused)
    client.update_issue_body(control.issue_number, body)
    readback = _load_control(client)
    if readback.focused != focused or readback.authorization is not None:
        raise GitHubCommandError("Project Delivery reconciliation readback mismatch")
    return True, focused


def guard(client: ProjectDeliveryClient, wayfinder: int) -> GuardResult:
    try:
        control = _load_control(client)
        _validate_parallel_authorization(client, control)
        for number in control.focused:
            issue = client.issue(number)
            _require_wayfinder(issue, number)
            if _issue_state(issue) != "open" or _has_open_map_blocker(client, number):
                return GuardResult(
                    wayfinder, False, control.focused, "invalid control state"
                )
        target = client.issue(wayfinder)
        _require_wayfinder(target, wayfinder)
        if _issue_state(target) != "open" or _has_open_map_blocker(client, wayfinder):
            return GuardResult(
                wayfinder, False, control.focused, "not frontier-eligible"
            )
        if wayfinder not in control.focused:
            return GuardResult(wayfinder, False, control.focused, "not focused")
        return GuardResult(wayfinder, True, control.focused)
    except GitHubCommandError:
        return GuardResult(wayfinder, False, (), "unreadable blockers")
    except DeliveryStateError:
        return GuardResult(wayfinder, False, (), "invalid control state")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    reconcile_parser = sub.add_parser("reconcile")
    reconcile_parser.add_argument("--repo", required=True)
    guard_parser = sub.add_parser("guard")
    guard_parser.add_argument("--repo", required=True)
    guard_parser.add_argument("--wayfinder", type=int, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        client = GitHubClient(args.repo)
        if args.command == "reconcile":
            changed, focused = reconcile(client)
            print(f"PROJECT DELIVERY RECONCILE: {'UPDATED' if changed else 'NOOP'}")
            print(f"Focused set: {_format_focus(focused)}")
            return 0
        result = guard(client, args.wayfinder)
        print(result.render())
        return 0 if result.allowed else 1
    except DeliveryStateError as exc:
        if args.command == "guard":
            print("PROJECT DELIVERY GUARD: BLOCKED")
            print(f"Wayfinder: #{args.wayfinder}")
            print("Reason: invalid control state")
        else:
            print("PROJECT DELIVERY RECONCILE: INVALID")
            print(f"Reason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
