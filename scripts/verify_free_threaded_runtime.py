"""Fail when Polaris is not running with supported free threading."""

from __future__ import annotations

import sys
import sysconfig

import polaris  # noqa: F401  # Import the supported package surface before the GIL check.


def main() -> None:
    """Verify the interpreter build and effective GIL state."""
    if sys.implementation.name != "cpython":
        raise SystemExit("free-threaded qualification requires CPython")
    if sysconfig.get_config_var("Py_GIL_DISABLED") != 1:
        raise SystemExit("interpreter was not built with free-threading support")

    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if is_gil_enabled is None:
        raise SystemExit("interpreter cannot report effective GIL state")
    if is_gil_enabled():
        raise SystemExit("GIL is enabled after importing the Polaris runtime surface")

    print(f"free-threaded runtime verified: {sys.version.split()[0]}")


if __name__ == "__main__":
    main()
