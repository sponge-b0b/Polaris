from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

type JsonObject = dict[str, object]


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


def json_object(value: object, field: str) -> JsonObject:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    return value


def nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def optional_nonempty_string(value: object, field: str) -> str | None:
    return None if value is None else nonempty_string(value, field)


# duplicate-code: persistence decoding owns ValueError adapter semantics;
# sharing a domain validator would couple infrastructure to domain failures.
# arid: disable
def aware_datetime(value: object, field: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware datetime")
    return value
# arid: enable


def iso_aware_datetime(value: object, field: str) -> datetime:
    return aware_datetime(
        datetime.fromisoformat(nonempty_string(value, field)),
        field,
    )
