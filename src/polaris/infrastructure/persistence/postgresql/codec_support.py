from __future__ import annotations

import hashlib
import json
from uuid import UUID


def canonical_json_fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def uuid_value(value: object, field: str) -> UUID:
    if type(value) is UUID:
        return value
    if isinstance(value, UUID):
        return UUID(str(value))
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"{field} must be UUID-compatible")
