"""Tests for the Polaris MCP server settings contract."""

import pytest
from pydantic import SecretStr

from mcp_server.settings import McpServerSettings, McpTransport


def test_mcp_settings_defaults_to_local_stdio() -> None:
    settings = McpServerSettings.from_env({})

    assert settings.transport is McpTransport.STDIO
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.path == "/mcp"
    assert settings.bearer_token is None
    assert settings.allow_web is False
    assert settings.max_query_characters == 8000
    assert settings.max_top_k == 50
    assert settings.max_page_size == 100


def test_mcp_settings_accept_environment_overrides() -> None:
    settings = McpServerSettings.from_env(
        {
            "POLARIS_MCP_TRANSPORT": "streamable-http",
            "POLARIS_MCP_HOST": "0.0.0.0",
            "POLARIS_MCP_PORT": "9000",
            "POLARIS_MCP_PATH": "/agent",
            "POLARIS_MCP_BEARER_TOKEN": "test-only-token",
            "POLARIS_MCP_ALLOW_WEB": "true",
            "POLARIS_MCP_MAX_QUERY_CHARACTERS": "12000",
            "POLARIS_MCP_MAX_TOP_K": "25",
            "POLARIS_MCP_MAX_PAGE_SIZE": "40",
        },
    )

    assert settings.transport is McpTransport.STREAMABLE_HTTP
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.path == "/agent"
    assert settings.bearer_token == SecretStr("test-only-token")
    assert settings.allow_web is True
    assert settings.max_query_characters == 12000
    assert settings.max_top_k == 25
    assert settings.max_page_size == 40


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("POLARIS_MCP_MAX_QUERY_CHARACTERS", "0"),
        ("POLARIS_MCP_MAX_TOP_K", "-1"),
        ("POLARIS_MCP_MAX_PAGE_SIZE", "0"),
    ],
)
def test_mcp_settings_reject_non_positive_limits(name: str, value: str) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        McpServerSettings.from_env({name: value})


def test_mcp_settings_reject_streamable_http_without_credentials() -> None:
    with pytest.raises(ValueError, match="POLARIS_MCP_BEARER_TOKEN is required"):
        McpServerSettings.from_env(
            {"POLARIS_MCP_TRANSPORT": "streamable-http"},
        )


def test_mcp_settings_do_not_render_bearer_token() -> None:
    raw_token = "test-only-token"
    settings = McpServerSettings(
        transport=McpTransport.STREAMABLE_HTTP,
        bearer_token=SecretStr(raw_token),
    )

    assert raw_token not in repr(settings)
    assert raw_token not in str(settings)


@pytest.mark.parametrize(
    "env",
    [
        {"POLARIS_MCP_TRANSPORT": "http"},
        {"POLARIS_MCP_HOST": "   "},
        {"POLARIS_MCP_PORT": "0"},
        {"POLARIS_MCP_PORT": "65536"},
        {"POLARIS_MCP_PATH": "mcp"},
    ],
)
def test_mcp_settings_reject_invalid_transport_endpoint_values(
    env: dict[str, str],
) -> None:
    with pytest.raises(ValueError):
        McpServerSettings.from_env(env)
