from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from scripts.workflow_hashing import sha256_canonical_json

SCHEMA = "polaris.workflow-handoff/v1"
RUNTIME_CONTRACT = "polaris.workflow-handoff-runtime/v2"
DESTINATION = re.compile(r"^\$[a-z0-9][a-z0-9-]*(?: [a-z0-9][a-z0-9-]*)*$")
ARTIFACT_URL = re.compile(r"^https://github\.com/[^/\s]+/[^/\s]+/(?:issues|pull)/\d+$")
DURABLE_URL = re.compile(r"^https://github\.com/[^/\s]+/[^/\s]+/.+$")
OUTCOME_EMOJI = {"success": "✅", "warning": "⚠️"}


class HandoffError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise HandoffError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), "manifest: expected JSON object")
    return value


def render_artifact_line(destination: str, title: str, url: str) -> str:
    destination = destination.strip()
    title = title.strip()
    url = url.strip()
    _need(
        DESTINATION.fullmatch(destination) is not None, "handoff: invalid destination"
    )
    _need(
        title != "" and "\n" not in title and "\r" not in title,
        "handoff: invalid title",
    )
    _need(ARTIFACT_URL.fullmatch(url) is not None, "handoff: invalid artifact URL")
    return f"{destination} - {title} ({url})"


def render_manifest(manifest: dict[str, Any]) -> str:
    _need(manifest.get("schema") == SCHEMA, f"manifest: schema must be {SCHEMA}")
    _need(
        manifest.get("boundary") == "human-lifecycle",
        "manifest: boundary must be human-lifecycle",
    )

    if "outcome" not in manifest:
        ready_line = "WORKFLOW HANDOFF: READY"
    else:
        outcome = manifest["outcome"]
        _need(
            isinstance(outcome, str) and outcome in OUTCOME_EMOJI,
            "manifest: outcome must be success or warning",
        )
        ready_line = f"{OUTCOME_EMOJI[outcome]} WORKFLOW HANDOFF: READY"

    durability = manifest.get("durability")
    _need(isinstance(durability, dict), "manifest: missing durability receipt")
    _need(durability.get("verified") is True, "manifest: durability is not verified")
    sources = durability.get("sources")
    _need(
        isinstance(sources, list) and len(sources) > 0,
        "manifest: durability sources required",
    )
    normalized_sources: list[str] = []
    for source in sources:
        _need(
            isinstance(source, str), "manifest: durability source must be a URL string"
        )
        source = source.strip()
        _need(
            DURABLE_URL.fullmatch(source) is not None,
            "manifest: invalid durability source URL",
        )
        normalized_sources.append(source)
    _need(
        len(set(normalized_sources)) == len(normalized_sources),
        "manifest: duplicate durability source",
    )

    handoffs = manifest.get("handoffs")
    _need(
        isinstance(handoffs, list) and len(handoffs) > 0,
        "manifest: at least one handoff required",
    )

    lines: list[str] = []
    seen: set[str] = set()
    for item in handoffs:
        _need(isinstance(item, dict), "manifest: handoff must be an object")
        destination = item.get("destination")
        artifact = item.get("artifact")
        _need(isinstance(destination, str), "manifest: handoff destination missing")
        _need(isinstance(artifact, dict), "manifest: handoff artifact missing")
        title = artifact.get("title")
        url = artifact.get("url")
        _need(isinstance(title, str), "manifest: artifact title missing")
        _need(isinstance(url, str), "manifest: artifact URL missing")
        line = render_artifact_line(destination, title, url)
        _need(line not in seen, "manifest: duplicate handoff")
        seen.add(line)
        lines.append(line)

    payload_hash = sha256_canonical_json(manifest)
    return "\n".join(
        [
            ready_line,
            *lines,
            "Fresh-session durability: VERIFIED",
            f"Durability sources: {len(normalized_sources)}",
            f"Handoff manifest SHA-256: {payload_hash}",
        ]
    )


def validate_output(manifest: dict[str, Any], output: str) -> str:
    expected = render_manifest(manifest)
    actual = output.strip()
    _need(actual == expected, "output: does not match generated handoff bytes")
    return "WORKFLOW HANDOFF: VALID"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("contract")

    generate = sub.add_parser("generate")
    generate.add_argument("--manifest", type=Path, required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "contract":
            print(f"WORKFLOW HANDOFF RUNTIME: {RUNTIME_CONTRACT}")
            return 0
        manifest = _read_json(args.manifest)
        if args.command == "generate":
            print(render_manifest(manifest))
            return 0
        if args.command == "verify":
            print(validate_output(manifest, args.output.read_text(encoding="utf-8")))
            return 0
        raise HandoffError(f"unsupported command: {args.command}")
    except (HandoffError, json.JSONDecodeError, OSError) as exc:
        print(f"WORKFLOW HANDOFF: INVALID\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
