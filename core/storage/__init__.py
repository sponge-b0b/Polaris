"""Core storage package.

Import contracts and implementations from their owning modules so importing a
storage subpackage does not initialize unrelated persistence infrastructure.
"""

from __future__ import annotations

__all__: list[str] = []
