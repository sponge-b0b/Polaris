from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from enum import Enum


def stable_content_digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def enum_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    return value


def datetime_value(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
