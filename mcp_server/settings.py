"""Typed configuration for the Polaris MCP transport boundary."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import SecretStr


class McpTransport(StrEnum):
    """Supported MCP server transports."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"


@dataclass(frozen=True, slots=True)
class McpServerSettings:
    """Validated settings owned by the Polaris MCP server boundary."""

    transport: McpTransport = McpTransport.STDIO
    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/mcp"
    bearer_token: SecretStr | None = field(default=None, repr=False)
    allow_web: bool = False
    max_query_characters: int = 8000
    max_top_k: int = 50
    max_page_size: int = 100

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("MCP host must not be blank.")
        if not 1 <= self.port <= 65535:
            raise ValueError("MCP port must be between 1 and 65535.")
        if not self.path.startswith("/"):
            raise ValueError("MCP path must start with '/'.")
        if any(
            limit <= 0
            for limit in (
                self.max_query_characters,
                self.max_top_k,
                self.max_page_size,
            )
        ):
            raise ValueError("MCP request limits must be greater than zero.")
        if self.transport is McpTransport.STREAMABLE_HTTP and not self._has_token:
            raise ValueError(
                "POLARIS_MCP_BEARER_TOKEN is required for streamable-http transport.",
            )

    @property
    def _has_token(self) -> bool:
        return self.bearer_token is not None and bool(
            self.bearer_token.get_secret_value().strip(),
        )

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
    ) -> McpServerSettings:
        """Build settings from the MCP-specific environment contract."""

        source = os.environ if env is None else env

        return cls(
            transport=_parse_transport(source.get("POLARIS_MCP_TRANSPORT")),
            host=_read_text(
                source.get("POLARIS_MCP_HOST"),
                default="127.0.0.1",
            ),
            port=_parse_int(
                source.get("POLARIS_MCP_PORT"),
                default=8000,
                name="POLARIS_MCP_PORT",
            ),
            path=_read_text(
                source.get("POLARIS_MCP_PATH"),
                default="/mcp",
            ),
            bearer_token=_parse_secret(source.get("POLARIS_MCP_BEARER_TOKEN")),
            allow_web=_parse_bool(
                source.get("POLARIS_MCP_ALLOW_WEB"),
                default=False,
                name="POLARIS_MCP_ALLOW_WEB",
            ),
            max_query_characters=_parse_int(
                source.get("POLARIS_MCP_MAX_QUERY_CHARACTERS"),
                default=8000,
                name="POLARIS_MCP_MAX_QUERY_CHARACTERS",
            ),
            max_top_k=_parse_int(
                source.get("POLARIS_MCP_MAX_TOP_K"),
                default=50,
                name="POLARIS_MCP_MAX_TOP_K",
            ),
            max_page_size=_parse_int(
                source.get("POLARIS_MCP_MAX_PAGE_SIZE"),
                default=100,
                name="POLARIS_MCP_MAX_PAGE_SIZE",
            ),
        )


def _parse_transport(value: str | None) -> McpTransport:
    normalized = _read_text(value, default=McpTransport.STDIO.value).lower()
    try:
        return McpTransport(normalized)
    except ValueError as exc:
        raise ValueError(
            "POLARIS_MCP_TRANSPORT must be 'stdio' or 'streamable-http'.",
        ) from exc


def _read_text(value: str | None, *, default: str) -> str:
    if value is None:
        return default
    return value.strip()


def _parse_secret(value: str | None) -> SecretStr | None:
    if value is None or not value.strip():
        return None
    return SecretStr(value.strip())


def _parse_bool(value: str | None, *, default: bool, name: str) -> bool:
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value.")


def _parse_int(value: str | None, *, default: int, name: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


__all__ = [
    "McpServerSettings",
    "McpTransport",
]
