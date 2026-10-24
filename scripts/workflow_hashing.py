"""Canonical byte representations for durable Polaris workflow hash identities.

Durable workflow hashes are identities of bytes, not of vague "content". Callers
must choose the representation explicitly; this module is the only workflow runtime
allowed to construct SHA-256 digests directly.

Changing one of these representations changes a durable identity contract and
therefore requires an explicit versioned migration rather than an incidental refactor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(value: bytes) -> str:
    """SHA-256 of exact bytes, with no normalization or framing."""

    return hashlib.sha256(value).hexdigest()


def sha256_utf8_text(value: str) -> str:
    """SHA-256 of exact UTF-8 text, with no stripping or newline changes."""

    return sha256_bytes(value.encode("utf-8"))


def sha256_file_bytes(path: Path) -> str:
    """SHA-256 of exact serialized file bytes."""

    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical JSON used by existing Polaris workflow identities.

    This deliberately preserves the established representation: UTF-8,
    ``ensure_ascii=False``, lexicographically sorted object keys, and compact
    separators. No trailing newline is part of this representation.
    """

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_canonical_json(value: Any) -> str:
    """SHA-256 of :func:`canonical_json_bytes`."""

    return sha256_bytes(canonical_json_bytes(value))


def sha256_prefixed_canonical_json(prefix: bytes, value: Any) -> str:
    """SHA-256 of exact binary prefix followed by canonical JSON.

    The prefix is supplied as bytes because existing durable identities use
    different exact framing (for example a NUL-terminated domain or a namespace
    followed by a newline). This function does not invent or normalize framing.
    """

    return sha256_bytes(prefix + canonical_json_bytes(value))
