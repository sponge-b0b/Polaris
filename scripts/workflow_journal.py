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
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

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
    r"(?:^|_)(?:password|passwd|secret|token|credential|authorization|api_key|connection_string)(?:$|_)",
    re.IGNORECASE,
)
FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{12,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{12,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


class JournalHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class LocateStatus(str, Enum):
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
    *args: str, cwd: Path | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        raise JournalError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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
    base = cwd if cwd is not None else Path.cwd()
    return (
        (base / common).resolve()
        if not os.path.isabs(common)
        else Path(common).resolve()
    )


def common_journal_roots(cwd: Path | None = None) -> tuple[Path, ...]:
    common = _common_git_dir(cwd)
    roots = {common / ROOT_RELATIVE}
    worktrees = common / "worktrees"
    if worktrees.is_dir():
        for child in worktrees.iterdir():
            if child.is_dir():
                roots.add(child / ROOT_RELATIVE)
    return tuple(sorted(roots))


def _validate_artifact(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JournalError(f"{field}: expected object")
    kind = value.get("kind")
    url = value.get("url")
    if not isinstance(kind, str) or not kind.strip():
        raise JournalError(f"{field}: kind required")
    if not isinstance(url, str) or not url.strip():
        raise JournalError(f"{field}: url required")
    result: dict[str, Any] = {"kind": kind.strip(), "url": url.strip()}
    number = value.get("number")
    if number is not None:
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise JournalError(f"{field}: number must be a positive integer")
        result["number"] = number
    return result


def _validate_start_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise JournalError("start manifest: expected object")
    if manifest.get("schema") != START_SCHEMA:
        raise JournalError(f"start manifest: schema must be {START_SCHEMA}")
    skill = manifest.get("skill")
    if not isinstance(skill, str) or SKILL_RE.fullmatch(skill) is None:
        raise JournalError("start manifest: invalid skill")
    repository = manifest.get("repository")
    if not isinstance(repository, dict):
        raise JournalError("start manifest: repository object required")
    identity = repository.get("identity")
    if not isinstance(identity, str) or not identity.strip():
        raise JournalError("start manifest: repository.identity required")
    subject = _validate_artifact(manifest.get("subject"), "start manifest subject")
    scope_value = manifest.get("lifecycle_scope")
    scope = (
        None
        if scope_value is None
        else _validate_artifact(scope_value, "start manifest lifecycle_scope")
    )
    return {
        "skill": skill,
        "repository": {"identity": identity.strip()},
        "subject": subject,
        "lifecycle_scope": scope,
    }


def _subject_token(subject: dict[str, Any]) -> str:
    number = subject.get("number")
    if isinstance(number, int):
        return str(number)
    digest = hashlib.sha256(subject["url"].encode("utf-8")).hexdigest()[:8]
    return f"subject-{digest}"


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
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
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
    value = result.stdout.strip()
    return value or None


def _validate_no_secrets(value: Any, path: str = "data") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise JournalError(f"{path}: object keys must be strings")
            if FORBIDDEN_KEY_RE.search(key):
                raise JournalError(
                    f"{path}.{key}: secret-bearing field names are not allowed"
                )
            _validate_no_secrets(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_secrets(child, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for pattern in FORBIDDEN_VALUE_PATTERNS:
            if pattern.search(value):
                raise JournalError(f"{path}: value resembles credential material")


def _metadata_hash(metadata: dict[str, Any]) -> str:
    return _sha256(metadata)


def start_invocation(
    manifest: dict[str, Any], cwd: Path | None = None
) -> LoadedInvocation:
    normalized = _validate_start_manifest(manifest)
    root = journal_root(cwd)
    now = _utc_now()
    timestamp = now.replace("-", "").replace(":", "")
    invocation_id = (
        f"{normalized['skill']}-{_subject_token(normalized['subject'])}-"
        f"{timestamp}-{secrets.token_hex(2)}"
    )
    directory = root / normalized["skill"] / invocation_id
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
    _atomic_write_json(directory / "metadata.json", metadata)
    (directory / "events.jsonl").touch(exist_ok=False)
    append_event(
        directory,
        {"type": "invocation_started", "candidate_state": None, "data": {}},
        cwd=cwd,
    )
    return load_invocation(directory)


def _validate_metadata(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise JournalError("metadata: expected object")
    if metadata.get("schema") != METADATA_SCHEMA:
        raise JournalError(f"metadata: unsupported schema {metadata.get('schema')!r}")
    invocation_id = metadata.get("invocation_id")
    skill = metadata.get("skill")
    if not isinstance(invocation_id, str) or not invocation_id:
        raise JournalError("metadata: invocation_id required")
    if not isinstance(skill, str) or SKILL_RE.fullmatch(skill) is None:
        raise JournalError("metadata: invalid skill")
    repository = metadata.get("repository")
    if not isinstance(repository, dict) or not isinstance(
        repository.get("identity"), str
    ):
        raise JournalError("metadata: repository.identity required")
    _validate_artifact(metadata.get("subject"), "metadata subject")
    scope = metadata.get("lifecycle_scope")
    if scope is not None:
        _validate_artifact(scope, "metadata lifecycle_scope")
    checkout = metadata.get("checkout")
    if not isinstance(checkout, dict) or not isinstance(
        checkout.get("initial_head"), str
    ):
        raise JournalError("metadata: checkout.initial_head required")
    return metadata


def _event_hash(event_without_hash: dict[str, Any]) -> str:
    return _sha256(event_without_hash)


def _parse_events(
    path: Path, metadata: dict[str, Any]
) -> tuple[tuple[dict[str, Any], ...], JournalHealth, str | None]:
    events_path = path / "events.jsonl"
    try:
        raw = events_path.read_bytes()
    except OSError as exc:
        return (), JournalHealth.DEGRADED, f"events unreadable: {exc}"

    health = JournalHealth.HEALTHY
    reason: str | None = None
    if raw and not raw.endswith(b"\n"):
        health = JournalHealth.DEGRADED
        reason = "partial final event ignored"
        raw = raw.rsplit(b"\n", 1)[0]
        if raw:
            raw += b"\n"

    events: list[dict[str, Any]] = []
    expected_previous = _metadata_hash(metadata)
    for index, line in enumerate(raw.splitlines(), start=1):
        if not line:
            health = JournalHealth.DEGRADED
            reason = f"event {index}: empty line"
            break
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise JournalError("expected object")
            if value.get("schema") != EVENT_SCHEMA:
                raise JournalError("unsupported event schema")
            if value.get("invocation_id") != metadata["invocation_id"]:
                raise JournalError("invocation identity mismatch")
            if value.get("sequence") != index:
                raise JournalError("sequence mismatch")
            event_type = value.get("type")
            if event_type not in SUPPORTED_EVENT_TYPES:
                raise JournalError(f"unsupported event type {event_type!r}")
            candidate = value.get("candidate_state")
            if candidate is not None and not isinstance(candidate, str):
                raise JournalError("candidate_state must be string or null")
            if not isinstance(value.get("data"), dict):
                raise JournalError("data must be object")
            if value.get("previous_event_sha256") != expected_previous:
                raise JournalError("previous-event hash mismatch")
            recorded_hash = value.get("event_sha256")
            if not isinstance(recorded_hash, str) or HEX64_RE.fullmatch(
                recorded_hash
            ) is None:
                raise JournalError("invalid event hash")
            without_hash = dict(value)
            without_hash.pop("event_sha256", None)
            if _event_hash(without_hash) != recorded_hash:
                raise JournalError("event hash mismatch")
        except (json.JSONDecodeError, JournalError) as exc:
            health = JournalHealth.DEGRADED
            reason = f"event {index}: {exc}"
            break
        events.append(value)
        expected_previous = value["event_sha256"]
    return tuple(events), health, reason


def load_invocation(path: Path | str) -> LoadedInvocation:
    directory = Path(path)
    try:
        metadata = _validate_metadata(
            json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, JournalError) as exc:
        raise JournalError(f"journal metadata unavailable: {exc}") from exc
    events, health, reason = _parse_events(directory, metadata)
    return LoadedInvocation(directory, metadata, events, health, reason)


def _validate_event_input(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise JournalError("event input: expected object")
    event_type = event.get("type")
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise JournalError(f"event input: unsupported type {event_type!r}")
    candidate = event.get("candidate_state")
    if candidate is not None and not isinstance(candidate, str):
        raise JournalError("event input: candidate_state must be string or null")
    data = event.get("data")
    if not isinstance(data, dict):
        raise JournalError("event input: data must be object")
    _validate_no_secrets(data)
    return {"type": event_type, "candidate_state": candidate, "data": data}


def _assert_local_journal_path(path: Path, cwd: Path | None) -> None:
    root = journal_root(cwd).resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
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
    sequence = len(loaded.events) + 1
    previous_hash = (
        loaded.events[-1]["event_sha256"]
        if loaded.events
        else _metadata_hash(loaded.metadata)
    )
    payload = {
        "schema": EVENT_SCHEMA,
        "sequence": sequence,
        "event_id": secrets.token_hex(16),
        "recorded_at": _utc_now(),
        "invocation_id": loaded.metadata["invocation_id"],
        "type": normalized["type"],
        "candidate_state": normalized["candidate_state"],
        "data": normalized["data"],
        "previous_event_sha256": previous_hash,
    }
    payload["event_sha256"] = _event_hash(payload)
    line = _canonical(payload) + b"\n"
    with (directory / "events.jsonl").open("ab", buffering=0) as handle:
        handle.write(line)
        os.fsync(handle.fileno())
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
    degraded_reasons: list[str] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        try:
            loaded = load_invocation(child)
        except JournalError as exc:
            degraded_reasons.append(f"{child.name}: {exc}")
            continue
        metadata = loaded.metadata
        if metadata["repository"]["identity"] != repository:
            continue
        if metadata["subject"]["url"] != subject_url:
            continue
        if loaded.terminal:
            continue
        matches.append(loaded)
    if len(matches) == 1:
        return LocateResult(LocateStatus.FOUND, tuple(matches), matches[0].reason)
    if len(matches) > 1:
        return LocateResult(
            LocateStatus.AMBIGUOUS,
            tuple(matches),
            f"{len(matches)} matching nonterminal journals",
        )
    if degraded_reasons:
        return LocateResult(
            LocateStatus.DEGRADED,
            (),
            "; ".join(degraded_reasons),
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


def gc_lifecycle_scope(scope_url: str, cwd: Path | None = None) -> GcResult:
    matched = removed = failed = 0
    failures: list[str] = []
    try:
        roots = common_journal_roots(cwd)
    except JournalError as exc:
        return GcResult(0, 0, 1, (str(exc),))
    for root in roots:
        for directory in list(_iter_invocation_dirs(root)):
            try:
                metadata = _validate_metadata(
                    json.loads(
                        (directory / "metadata.json").read_text(encoding="utf-8")
                    )
                )
            except (OSError, json.JSONDecodeError, JournalError):
                continue
            scope = metadata.get("lifecycle_scope")
            if not isinstance(scope, dict) or scope.get("url") != scope_url:
                continue
            matched += 1
            try:
                shutil.rmtree(directory)
                removed += 1
            except OSError as exc:
                failed += 1
                failures.append(f"{directory}: {exc}")
    return GcResult(matched, removed, failed, tuple(failures))


def _write_json_output(path: Path | None, payload: dict[str, Any]) -> None:
    if path is not None:
        _atomic_write_json(path, payload)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise JournalError("input: expected JSON object")
    return value


def _loaded_payload(loaded: LoadedInvocation) -> dict[str, Any]:
    return {
        "status": "FOUND",
        "health": loaded.health.value,
        "reason": loaded.reason,
        "journal": str(loaded.path),
        "metadata": loaded.metadata,
        "events": list(loaded.events),
        "terminal": loaded.terminal,
    }


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


def _degraded(message: str, json_output: Path | None = None) -> int:
    print("WORKFLOW JOURNAL: DEGRADED")
    print(f"Reason: {message}")
    print("Fallback: workflow execution remains authoritative")
    _write_json_output(
        json_output,
        {
            "status": "DEGRADED",
            "reason": message,
            "fallback": "workflow execution remains authoritative",
        },
    )
    return 0


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "start":
            loaded = start_invocation(_read_json(args.manifest))
            print("WORKFLOW JOURNAL: STARTED")
            print(f"Invocation: {loaded.metadata['invocation_id']}")
            print(f"Journal: {loaded.path}")
            _write_json_output(args.json_output, _loaded_payload(loaded))
            return 0

        if args.command == "append":
            loaded = append_event(args.journal, _read_json(args.event))
            print("WORKFLOW JOURNAL: APPENDED")
            print(f"Invocation: {loaded.metadata['invocation_id']}")
            print(f"Sequence: {loaded.events[-1]['sequence']}")
            _write_json_output(args.json_output, _loaded_payload(loaded))
            return 0

        if args.command == "locate":
            result = locate_resumable(
                skill=args.skill,
                repository=args.repository,
                subject_url=args.subject_url,
            )
            print(f"WORKFLOW JOURNAL: {result.status.value}")
            if result.reason:
                print(f"Reason: {result.reason}")
            for match in result.matches:
                print(f"Journal: {match.path}")
                print(f"Health: {match.health.value}")
            _write_json_output(
                args.json_output,
                {
                    "status": result.status.value,
                    "reason": result.reason,
                    "matches": [_loaded_payload(item) for item in result.matches],
                },
            )
            return 0

        if args.command == "inspect":
            loaded = load_invocation(args.journal)
            print(
                "WORKFLOW JOURNAL: VALID"
                if loaded.health is JournalHealth.HEALTHY
                else "WORKFLOW JOURNAL: DEGRADED"
            )
            print(f"Invocation: {loaded.metadata['invocation_id']}")
            print(f"Events: {len(loaded.events)}")
            print(f"State: {'terminal' if loaded.terminal else 'nonterminal'}")
            print(f"Health: {loaded.health.value}")
            if loaded.reason:
                print(f"Reason: {loaded.reason}")
            _write_json_output(args.json_output, _loaded_payload(loaded))
            return 0

        if args.command == "complete":
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
            _write_json_output(args.json_output, _loaded_payload(loaded))
            return 0

        if args.command == "abandon":
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
            _write_json_output(args.json_output, _loaded_payload(loaded))
            return 0

        if args.command == "gc":
            result = gc_lifecycle_scope(args.lifecycle_scope_url)
            status = "COMPLETE" if result.failed == 0 else "DEGRADED"
            print(f"WORKFLOW JOURNAL GC: {status}")
            print(f"Matched: {result.matched}")
            print(f"Removed: {result.removed}")
            print(f"Failed: {result.failed}")
            for failure in result.failures:
                print(f"- {failure}")
            _write_json_output(
                args.json_output,
                {
                    "status": status,
                    "matched": result.matched,
                    "removed": result.removed,
                    "failed": result.failed,
                    "failures": list(result.failures),
                },
            )
            return 0

        return _degraded(f"unsupported command: {args.command}")
    except (JournalError, json.JSONDecodeError, OSError) as exc:
        json_output = getattr(args, "json_output", None)
        return _degraded(str(exc), json_output)


if __name__ == "__main__":
    raise SystemExit(main())
