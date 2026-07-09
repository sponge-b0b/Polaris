"""Backtesting market-data providers.

Provider implementations are imported from their owning modules so package
inspection does not load PostgreSQL, Pandas, or vendor integrations.
"""

from __future__ import annotations

__all__: list[str] = []
