from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

START_SCHEMA = "polaris.workflow-invocation-start/v1"
METADATA_SCHEMA = "polaris.workflow-invocation/v1"
EVENT_SCHEMA = "polaris.workflow-journal-event/v1"
ROOT_RELATIVE = Path("polaris/workflow-journal/v1")
SUPPORTED_EVENT_TYPES = frozenset(
    {
        "invocation_started",
        "authority_snapshot",
        "binding_snapshot",
        "work_completed",
        "check_result",
        "external_write",
        "frontier",
        "interruption_checkpoint",
        "resume_started",
        "resume_reconciled",
        "child_invocation_started",
        "child_result_observed",
        "invocation_completed",
        "invocation_abandoned",
    }
)
TERMINAL_EVENT_TYPES = frozenset({"invocation_completed", "invocation_abandoned"})
SKILL_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_KEY_RE = re.compile(
    r"(?:^|_)(?:password|passwd|secret|token|credential|authorization|api_key|"
    r"connection_string)(?:$|_)",
    re.IGNORECASE,
)
FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{12,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{12,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


class JournalHealth(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class LocateStatus(StrEnum):
    FOUND = "FOUND"
    NONE = "NONE"
    AMBIGUOUS = "AMBIGUOUS"
    DEGRADED = "DEGRADED"


class JournalError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoadedInvocation:
    path: Path
    metadata: dict[str, Any]
    events: tuple[dict[str, Any], ...]
    health: JournalHealth
    reason: str | None

    @property
    def terminal(self) -> bool:
        return bool(self.events and self.events[-1]["type"] in TERMINAL_EVENT_TYPES)


@dataclass(frozen=True)
class LocateResult:
    status: LocateStatus
    matches: tuple[LoadedInvocation, ...]
    reason: str | None = None


@dataclass(frozen=True)
class GcResult:
    matched: int
    removed: int
    failed: int
    failures: tuple[str, ...]


def _run_git(
    *args: str,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        text=True,
        capture_output=True,
    )
    if check and result.returncode:
        detail = result.stderr.strip()
        raise JournalError(f"git {' '.join(args)} failed: {detail}")
    return result


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def journal_root(cwd: Path | None = None) -> Path:
    git_dir = _run_git("rev-parse", "--absolute-git-dir", cwd=cwd).stdout.strip()
    if not git_dir:
        raise JournalError("git returned an empty administrative directory")
    return Path(git_dir) / ROOT_RELATIVE


def _common_git_dir(cwd: Path | None = None) -> Path:
    common = _run_git("rev-parse", "--git-common-dir", cwd=cwd).stdout.strip()
    if not common:
        raise JournalError("git returned an empty common administrative directory")
    if os.path.isabs(common):
        return Path(common).resolve()
    return ((cwd or Path.cwd()) / common).resolve()


def common_journal_roots(cwd: Path | None = None) -> tuple[Path, ...]:
    common = _common_git_dir(cwd)
    roots = {common / ROOT_RELATIVE}
    worktrees = common / "worktrees"
    if worktrees.is_dir():
        roots.update(
            child / ROOT_RELATIVE
            for child in worktrees.iterdir()
            if child.is_dir()
        )
    return tuple(sorted(roots))


def _validate_no_secrets(value: Any, path: str = "value") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise JournalError(f"{path}: object keys must be strings")
            if FORBIDDEN_KEY_RE.search(key):
                raise JournalError(
                    f"{path}.{key}: secret-bearing field names are not allowed"
                )
            _validate_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_secrets(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in FORBIDDEN_VALUE_PATTERNS):
            raise JournalError(f"{path}: value resembles credential material")


def _validate_artifact(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JournalError(f"{label}: expected object")
    kind = value.get("kind")
    url = value.get("url")
    number = value.get("number")
    if not isinstance(kind, str) or not kind.strip():
        raise JournalError(f"{label}: kind required")
    if not isinstance(url, str) or not url.strip():
        raise JournalError(f"{label}: url required")
    result: dict[str, Any] = {"kind": kind.strip(), "url": url.strip()}
    if number is not None:
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise JournalError(f"{label}: number must be a positive integer")
        result["number"] = number
    return result


def _validate_start_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != START_SCHEMA:
        raise JournalError(f"start manifest: schema must be {START_SCHEMA}")
    _validate_no_secrets(value, "start manifest")
    skill = value.get("skill")
    repository = value.get("repository")
    if not isinstance(skill, str) or SKILL_RE.fullmatch(skill) is None:
        raise JournalError("start manifest: invalid skill")
    if not isinstance(repository, dict):
        raise JournalError("start manifest: repository object required")
    identity = repository.get("identity")
    if not isinstance(identity, str) or not identity.strip():
        raise JournalError("start manifest: repository.identity required")
    scope = value.get("lifecycle_scope")
    return {
        "skill": skill,
        "repository": {"identity": identity.strip()},
        "subject": _validate_artifact(value.get("subject"), "start manifest subject"),
        "lifecycle_scope": (
            None
            if scope is None
            else _validate_artifact(scope, "start manifest lifecycle_scope")
        ),
    }


def _validate_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != METADATA_SCHEMA:
        schema = value.get("schema") if isinstance(value, dict) else None
        raise JournalError(f"metadata: unsupported schema {schema!r}")
    invocation_id = value.get("invocation_id")
    skill = value.get("skill")
    repository = value.get("repository")
    checkout = value.get("checkout")
    if not isinstance(invocation_id, str) or not invocation_id:
        raise JournalError("metadata: invocation_id required")
    if not isinstance(skill, str) or SKILL_RE.fullmatch(skill) is None:
        raise JournalError("metadata: invalid skill")
    if not isinstance(repository, dict):
        raise JournalError("metadata: repository object required")
    if not isinstance(repository.get("identity"), str):
        raise JournalError("metadata: repository.identity required")
    _validate_artifact(value.get("subject"), "metadata subject")
    scope = value.get("lifecycle_scope")
    if scope is not None:
        _validate_artifact(scope, "metadata lifecycle_scope")
    if not isinstance(checkout, dict):
        raise JournalError("metadata: checkout object required")
    if not isinstance(checkout.get("initial_head"), str):
        raise JournalError("metadata: checkout.initial_head required")
    return value


def _atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _branch(cwd: Path | None = None) -> str | None:
    result = _run_git(
        "symbolic-ref",
        "--quiet",
        "--short",
        "HEAD",
        cwd=cwd,
        check=False,
    )
    if result.returncode:
        return None
    return result.stdout.strip() or None


def _subject_token(subject: dict[str, Any]) -> str:
    number = subject.get("number")
    if isinstance(number, int):
        return str(number)
    digest = hashlib.sha256(subject["url"].encode()).hexdigest()[:8]
    return f"subject-{digest}"


def _event_hash(event_without_hash: dict[str, Any]) -> str:
    return _sha256(event_without_hash)


def _new_event(
    *,
    metadata: dict[str, Any],
    sequence: int,
    event_type: str,
    candidate_state: str | None,
    data: dict[str, Any],
    previous_hash: str,
) -> dict[str, Any]:
    event = {
        "schema": EVENT_SCHEMA,
        "sequence": sequence,
        "event_id": secrets.token_hex(16),
        "recorded_at": _utc_now(),
        "invocation_id": metadata["invocation_id"],
        "type": event_type,
        "candidate_state": candidate_state,
        "data": data,
        "previous_event_sha256": previous_hash,
    }
    event["event_sha256"] = _event_hash(event)
    return event


def _append_line(path: Path, event: dict[str, Any]) -> None:
    with path.open("ab", buffering=0) as handle:
        handle.write(_canonical(event) + b"\n")
        os.fsync(handle.fileno())


def start_invocation(
    manifest: dict[str, Any],
    cwd: Path | None = None,
) -> LoadedInvocation:
    normalized = _validate_start_manifest(manifest)
    now = _utc_now()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    invocation_id = (
        f"{normalized['skill']}-{_subject_token(normalized['subject'])}-"
        f"{stamp}-{secrets.token_hex(2)}"
    )
    directory = journal_root(cwd) / normalized["skill"] / invocation_id
    directory.mkdir(parents=True, exist_ok=False)
    metadata = {
        "schema": METADATA_SCHEMA,
        "invocation_id": invocation_id,
        "skill": normalized["skill"],
        "started_at": now,
        "repository": normalized["repository"],
        "subject": normalized["subject"],
        "lifecycle_scope": normalized["lifecycle_scope"],
        "checkout": {
            "initial_branch": _branch(cwd),
            "initial_head": _run_git("rev-parse", "HEAD", cwd=cwd).stdout.strip(),
        },
    }
    try:
        _atomic_write_json(directory / "metadata.json", metadata)
        events_path = directory / "events.jsonl"
        events_path.touch(exist_ok=False)
        _append_line(
            events_path,
            _new_event(
                metadata=metadata,
                sequence=1,
                event_type="invocation_started",
                candidate_state=None,
                data={},
                previous_hash=_sha256(metadata),
            ),
        )
        return load_invocation(directory)
    except Exception:
        try:
            shutil.rmtree(directory)
        except OSError:
            pass
        raise


def _expect(data: dict[str, Any], key: str, kind: str, label: str) -> Any:
    value = data.get(key)
    valid = {
        "str": isinstance(value, str) and bool(value.strip()),
        "bool": isinstance(value, bool),
        "int": isinstance(value, int) and not isinstance(value, bool) and value >= 0,
        "dict": isinstance(value, dict),
        "strlist": isinstance(value, list)
        and all(isinstance(item, str) for item in value),
    }.get(kind, False)
    if not valid:
        raise JournalError(f"{label}: {key} must be {kind}")
    return value


def _validate_event_data(event_type: str, data: dict[str, Any]) -> None:
    required = {
        "work_completed": (("work_id", "str"),),
        "check_result": (("check_id", "str"), ("result", "str")),
        "external_write": (
            ("system", "str"),
            ("operation", "str"),
            ("readback", "dict"),
        ),
        "frontier": (
            ("phase", "str"),
            ("completed", "strlist"),
            ("pending", "strlist"),
        ),
        "interruption_checkpoint": (
            ("reason", "str"),
            ("phase", "str"),
            ("next_expected_action", "str"),
        ),
        "resume_started": (("previous_last_sequence", "int"),),
        "resume_reconciled": (
            ("authority_compatible", "bool"),
            ("bindings_compatible", "bool"),
            ("reusable", "strlist"),
            ("redo", "strlist"),
            ("resume_point", "str"),
        ),
        "child_invocation_started": (
            ("role", "str"),
            ("skill", "str"),
            ("child_invocation_id", "str"),
        ),
        "child_result_observed": (
            ("child_invocation_id", "str"),
            ("result", "str"),
            ("result_sha256", "str"),
        ),
        "invocation_abandoned": (("reason", "str"),),
    }
    for key, kind in required.get(event_type, ()):
        _expect(data, key, kind, event_type)
    if event_type == "authority_snapshot":
        files = data.get("files")
        if not isinstance(files, list) or not files:
            raise JournalError("authority_snapshot: files must be a non-empty array")
        for item in files:
            if not isinstance(item, dict):
                raise JournalError("authority_snapshot: each file must be an object")
            _expect(item, "path", "str", "authority_snapshot file")
            digest = _expect(item, "sha256", "str", "authority_snapshot file")
            if HEX64_RE.fullmatch(digest) is None:
                raise JournalError("authority_snapshot: sha256 must be 64 hex")
    elif event_type == "binding_snapshot":
        bindings = data.get("bindings")
        if not isinstance(bindings, dict) or not bindings:
            raise JournalError("binding_snapshot: bindings must be non-empty")
    elif event_type == "check_result" and data["result"] not in {"pass", "fail"}:
        raise JournalError("check_result: result must be pass or fail")
    elif event_type == "external_write":
        if data["readback"].get("verified") is not True:
            raise JournalError("external_write: readback.verified must be true")
    elif event_type == "child_result_observed":
        if HEX64_RE.fullmatch(data["result_sha256"]) is None:
            raise JournalError("child_result_observed: result_sha256 must be 64 hex")
    elif event_type == "invocation_completed":
        if data != {"outcome": "success"}:
            raise JournalError("invocation_completed: outcome must be success")


def _validate_event_input(
    value: Any,
    *,
    stored: bool = False,
    sequence: int | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JournalError("event input: expected object")
    event_type = value.get("type")
    candidate = value.get("candidate_state")
    data = value.get("data")
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise JournalError(f"event input: unsupported type {event_type!r}")
    if candidate is not None and not isinstance(candidate, str):
        raise JournalError("event input: candidate_state must be string or null")
    if not isinstance(data, dict):
        raise JournalError("event input: data must be object")
    _validate_no_secrets(data, "event data")
    if event_type == "invocation_started":
        if not stored or sequence != 1:
            raise JournalError("invocation_started is valid only as bootstrap event 1")
        if candidate is not None or data:
            raise JournalError(
                "invocation_started requires null candidate and empty data"
            )
    else:
        _validate_event_data(event_type, data)
    return {"type": event_type, "candidate_state": candidate, "data": data}


def _parse_stored_event(
    raw: bytes,
    *,
    metadata: dict[str, Any],
    sequence: int,
    previous_hash: str,
    terminal_seen: bool,
) -> dict[str, Any]:
    if terminal_seen:
        raise JournalError("event follows terminal event")
    event = json.loads(raw)
    if not isinstance(event, dict) or event.get("schema") != EVENT_SCHEMA:
        raise JournalError("unsupported event schema")
    if event.get("invocation_id") != metadata["invocation_id"]:
        raise JournalError("invocation identity mismatch")
    if event.get("sequence") != sequence:
        raise JournalError("sequence mismatch")
    _validate_event_input(event, stored=True, sequence=sequence)
    if event.get("previous_event_sha256") != previous_hash:
        raise JournalError("previous-event hash mismatch")
    digest = event.get("event_sha256")
    if not isinstance(digest, str) or HEX64_RE.fullmatch(digest) is None:
        raise JournalError("invalid event hash")
    unhashed = dict(event)
    unhashed.pop("event_sha256", None)
    if _event_hash(unhashed) != digest:
        raise JournalError("event hash mismatch")
    return event


def _parse_events(
    directory: Path,
    metadata: dict[str, Any],
) -> tuple[tuple[dict[str, Any], ...], JournalHealth, str | None]:
    try:
        raw = (directory / "events.jsonl").read_bytes()
    except OSError as exc:
        return (), JournalHealth.DEGRADED, f"events unreadable: {exc}"
    tail_reason = None
    if raw and not raw.endswith(b"\n"):
        tail_reason = "partial final event ignored"
        cut = raw.rfind(b"\n")
        raw = raw[: cut + 1] if cut >= 0 else b""
    events: list[dict[str, Any]] = []
    previous_hash = _sha256(metadata)
    for index, line in enumerate(raw.splitlines(), start=1):
        try:
            event = _parse_stored_event(
                line,
                metadata=metadata,
                sequence=index,
                previous_hash=previous_hash,
                terminal_seen=bool(
                    events and events[-1]["type"] in TERMINAL_EVENT_TYPES
                ),
            )
        except (json.JSONDecodeError, JournalError) as exc:
            return tuple(events), JournalHealth.DEGRADED, f"event {index}: {exc}"
        events.append(event)
        previous_hash = event["event_sha256"]
    if not events:
        return (), JournalHealth.DEGRADED, "missing invocation_started event"
    if events[0]["type"] != "invocation_started":
        return (), JournalHealth.DEGRADED, "first event is not invocation_started"
    if tail_reason:
        return tuple(events), JournalHealth.DEGRADED, tail_reason
    return tuple(events), JournalHealth.HEALTHY, None


def load_invocation(path: Path | str) -> LoadedInvocation:
    directory = Path(path)
    try:
        raw = (directory / "metadata.json").read_text(encoding="utf-8")
        metadata = _validate_metadata(json.loads(raw))
    except (OSError, json.JSONDecodeError, JournalError) as exc:
        raise JournalError(f"journal metadata unavailable: {exc}") from exc
    if directory.name != metadata["invocation_id"]:
        raise JournalError("journal directory does not match invocation_id")
    if directory.parent.name != metadata["skill"]:
        raise JournalError("journal skill directory does not match metadata skill")
    events, health, reason = _parse_events(directory, metadata)
    return LoadedInvocation(directory, metadata, events, health, reason)


def _assert_local_journal_path(path: Path, cwd: Path | None) -> None:
    root = journal_root(cwd).resolve()
    try:
        path.resolve().relative_to(root)
    except ValueError as exc:
        raise JournalError(
            "journal path is outside the current checkout journal root"
        ) from exc


def append_event(
    path: Path | str,
    event: dict[str, Any],
    cwd: Path | None = None,
) -> LoadedInvocation:
    directory = Path(path)
    _assert_local_journal_path(directory, cwd)
    loaded = load_invocation(directory)
    if loaded.health is not JournalHealth.HEALTHY:
        raise JournalError(f"journal is degraded: {loaded.reason}")
    if loaded.terminal:
        raise JournalError("journal is terminal")
    normalized = _validate_event_input(event)
    stored = _new_event(
        metadata=loaded.metadata,
        sequence=len(loaded.events) + 1,
        event_type=normalized["type"],
        candidate_state=normalized["candidate_state"],
        data=normalized["data"],
        previous_hash=loaded.events[-1]["event_sha256"],
    )
    _append_line(directory / "events.jsonl", stored)
    return load_invocation(directory)


def locate_resumable(
    *,
    skill: str,
    repository: str,
    subject_url: str,
    cwd: Path | None = None,
) -> LocateResult:
    if SKILL_RE.fullmatch(skill) is None:
        return LocateResult(LocateStatus.DEGRADED, (), "invalid skill")
    try:
        base = journal_root(cwd) / skill
    except JournalError as exc:
        return LocateResult(LocateStatus.DEGRADED, (), str(exc))
    if not base.is_dir():
        return LocateResult(LocateStatus.NONE, ())
    matches: list[LoadedInvocation] = []
    degraded: list[str] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        try:
            loaded = load_invocation(child)
        except JournalError as exc:
            degraded.append(f"{child.name}: {exc}")
            continue
        target = (
            loaded.metadata["repository"]["identity"] == repository
            and loaded.metadata["subject"]["url"] == subject_url
        )
        if not target:
            continue
        if loaded.health is not JournalHealth.HEALTHY:
            degraded.append(f"{child.name}: {loaded.reason}")
        elif not loaded.terminal:
            matches.append(loaded)
    if degraded:
        reason = "; ".join(degraded)
        reason += "; automatic reuse skipped because journal identity may be ambiguous"
        return LocateResult(LocateStatus.DEGRADED, (), reason)
    if len(matches) == 1:
        return LocateResult(LocateStatus.FOUND, tuple(matches))
    if len(matches) > 1:
        return LocateResult(
            LocateStatus.AMBIGUOUS,
            tuple(matches),
            f"{len(matches)} matching nonterminal journals",
        )
    return LocateResult(LocateStatus.NONE, ())


def _iter_invocation_dirs(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return ()
    return (
        invocation
        for skill_dir in root.iterdir()
        if skill_dir.is_dir()
        for invocation in skill_dir.iterdir()
        if invocation.is_dir()
    )


def _gc_metadata(directory: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = (directory / "metadata.json").read_text(encoding="utf-8")
        return _validate_metadata(json.loads(raw)), None
    except (OSError, json.JSONDecodeError, JournalError) as exc:
        return None, f"{directory}: metadata unavailable: {exc}"


def gc_lifecycle_scope(scope_url: str, cwd: Path | None = None) -> GcResult:
    try:
        roots = common_journal_roots(cwd)
    except JournalError as exc:
        return GcResult(0, 0, 1, (str(exc),))
    matched = 0
    removed = 0
    failures: list[str] = []
    for root in roots:
        for directory in list(_iter_invocation_dirs(root)):
            metadata, error = _gc_metadata(directory)
            if error:
                failures.append(error)
                continue
            assert metadata is not None
            scope = metadata.get("lifecycle_scope")
            if not isinstance(scope, dict) or scope.get("url") != scope_url:
                continue
            matched += 1
            try:
                shutil.rmtree(directory)
                removed += 1
            except OSError as exc:
                failures.append(f"{directory}: {exc}")
    return GcResult(matched, removed, len(failures), tuple(failures))


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise JournalError("input: expected JSON object")
    return value


def _loaded_payload(loaded: LoadedInvocation, status: str) -> dict[str, Any]:
    return {
        "status": status,
        "health": loaded.health.value,
        "reason": loaded.reason,
        "journal": str(loaded.path),
        "metadata": loaded.metadata,
        "events": list(loaded.events),
        "terminal": loaded.terminal,
    }


def _emit_json(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    try:
        _atomic_write_json(path, payload)
    except OSError as exc:
        print(f"Journal JSON output unavailable: {exc}")


def _degraded(message: str, json_output: Path | None = None) -> int:
    print("WORKFLOW JOURNAL: DEGRADED")
    print(f"Reason: {message}")
    print("Fallback: workflow execution remains authoritative")
    _emit_json(
        json_output,
        {
            "status": "DEGRADED",
            "reason": message,
            "fallback": "workflow execution remains authoritative",
        },
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--manifest", type=Path, required=True)
    start.add_argument("--json-output", type=Path)
    append = sub.add_parser("append")
    append.add_argument("--journal", type=Path, required=True)
    append.add_argument("--event", type=Path, required=True)
    append.add_argument("--json-output", type=Path)
    locate = sub.add_parser("locate")
    locate.add_argument("--skill", required=True)
    locate.add_argument("--repository", required=True)
    locate.add_argument("--subject-url", required=True)
    locate.add_argument("--json-output", type=Path)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--journal", type=Path, required=True)
    inspect.add_argument("--json-output", type=Path)
    complete = sub.add_parser("complete")
    complete.add_argument("--journal", type=Path, required=True)
    complete.add_argument("--candidate-state")
    complete.add_argument("--json-output", type=Path)
    abandon = sub.add_parser("abandon")
    abandon.add_argument("--journal", type=Path, required=True)
    abandon.add_argument("--reason", required=True)
    abandon.add_argument("--json-output", type=Path)
    gc = sub.add_parser("gc")
    gc.add_argument("--lifecycle-scope-url", required=True)
    gc.add_argument("--json-output", type=Path)
    return parser


def _start_command(args: argparse.Namespace) -> None:
    loaded = start_invocation(_read_json(args.manifest))
    print("WORKFLOW JOURNAL: STARTED")
    print(f"Invocation: {loaded.metadata['invocation_id']}")
    print(f"Journal: {loaded.path}")
    _emit_json(args.json_output, _loaded_payload(loaded, "STARTED"))


def _append_command(args: argparse.Namespace) -> None:
    loaded = append_event(args.journal, _read_json(args.event))
    print("WORKFLOW JOURNAL: APPENDED")
    print(f"Invocation: {loaded.metadata['invocation_id']}")
    print(f"Sequence: {loaded.events[-1]['sequence']}")
    _emit_json(args.json_output, _loaded_payload(loaded, "APPENDED"))


def _locate_command(args: argparse.Namespace) -> None:
    result = locate_resumable(
        skill=args.skill,
        repository=args.repository,
        subject_url=args.subject_url,
    )
    print(f"WORKFLOW JOURNAL: {result.status.value}")
    if result.reason:
        print(f"Reason: {result.reason}")
    if result.status is LocateStatus.DEGRADED:
        print("Fallback: workflow execution remains authoritative")
    for match in result.matches:
        print(f"Journal: {match.path}")
        print(f"Health: {match.health.value}")
    _emit_json(
        args.json_output,
        {
            "status": result.status.value,
            "reason": result.reason,
            "matches": [_loaded_payload(item, "FOUND") for item in result.matches],
        },
    )


def _inspect_command(args: argparse.Namespace) -> None:
    loaded = load_invocation(args.journal)
    status = "VALID" if loaded.health is JournalHealth.HEALTHY else "DEGRADED"
    print(f"WORKFLOW JOURNAL: {status}")
    print(f"Invocation: {loaded.metadata['invocation_id']}")
    print(f"Events: {len(loaded.events)}")
    print(f"State: {'terminal' if loaded.terminal else 'nonterminal'}")
    print(f"Health: {loaded.health.value}")
    if loaded.reason:
        print(f"Reason: {loaded.reason}")
    if loaded.health is JournalHealth.DEGRADED:
        print("Fallback: workflow execution remains authoritative")
    _emit_json(args.json_output, _loaded_payload(loaded, status))


def _complete_command(args: argparse.Namespace) -> None:
    loaded = append_event(
        args.journal,
        {
            "type": "invocation_completed",
            "candidate_state": args.candidate_state,
            "data": {"outcome": "success"},
        },
    )
    print("WORKFLOW JOURNAL: COMPLETED")
    print(f"Invocation: {loaded.metadata['invocation_id']}")
    _emit_json(args.json_output, _loaded_payload(loaded, "COMPLETED"))


def _abandon_command(args: argparse.Namespace) -> None:
    loaded = append_event(
        args.journal,
        {
            "type": "invocation_abandoned",
            "candidate_state": None,
            "data": {"reason": args.reason},
        },
    )
    print("WORKFLOW JOURNAL: ABANDONED")
    print(f"Invocation: {loaded.metadata['invocation_id']}")
    _emit_json(args.json_output, _loaded_payload(loaded, "ABANDONED"))


def _gc_command(args: argparse.Namespace) -> None:
    result = gc_lifecycle_scope(args.lifecycle_scope_url)
    status = "COMPLETE" if result.failed == 0 else "DEGRADED"
    print(f"WORKFLOW JOURNAL GC: {status}")
    print(f"Matched: {result.matched}")
    print(f"Removed: {result.removed}")
    print(f"Failed: {result.failed}")
    for failure in result.failures:
        print(f"- {failure}")
    _emit_json(
        args.json_output,
        {
            "status": status,
            "matched": result.matched,
            "removed": result.removed,
            "failed": result.failed,
            "failures": list(result.failures),
        },
    )


COMMANDS = {
    "start": _start_command,
    "append": _append_command,
    "locate": _locate_command,
    "inspect": _inspect_command,
    "complete": _complete_command,
    "abandon": _abandon_command,
    "gc": _gc_command,
}


def main() -> int:
    args = _parser().parse_args()
    try:
        COMMANDS[args.command](args)
    except (JournalError, json.JSONDecodeError, OSError) as exc:
        return _degraded(str(exc), getattr(args, "json_output", None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
