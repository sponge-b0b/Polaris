"""Runtime qualification for SQLAlchemy/greenlet-backed PostgreSQL."""

from __future__ import annotations

import sys
import sysconfig

_GIL_DISABLED_ERROR = (
    "PostgreSQL persistence is not qualified for GIL-disabled CPython; "
    "run the persistence-owning role under standard CPython until ADR 0005 "
    "requalification succeeds"
)
_UNQUALIFIED_RUNTIME_ERROR = (
    "PostgreSQL persistence is qualified only for standard GIL-enabled "
    "CPython 3.14+; run the persistence-owning role with a standard CPython "
    "build until ADR 0005 requalification succeeds"
)


def require_qualified_postgres_runtime() -> None:
    """Reject execution outside the ADR 0005 PostgreSQL runtime boundary."""
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if is_gil_enabled is not None and not is_gil_enabled():
        raise RuntimeError(_GIL_DISABLED_ERROR)

    if (
        sys.implementation.name != "cpython"
        or sys.version_info < (3, 14)
        or sysconfig.get_config_var("Py_GIL_DISABLED") == 1
    ):
        raise RuntimeError(_UNQUALIFIED_RUNTIME_ERROR)
