"""Tests for the MCP Streamable HTTP authentication boundary."""

from __future__ import annotations

import secrets

import httpx
import pytest
from pydantic import SecretStr
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

import mcp_server.auth as auth_module
import mcp_server.server as server_module
from mcp_server.auth import protect_streamable_http_app
from mcp_server.settings import McpServerSettings, McpTransport

_TEST_TOKEN = "unit-test-bearer"


class _DownstreamApp:
    def __init__(self) -> None:
        self.paths: list[str] = []

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        path = scope.get("path", "")
        self.paths.append(path)
        await JSONResponse(
            {
                "forwarded": True,
                "path": path,
                "dependency_details": "must-not-appear-on-health",
            }
        )(scope, receive, send)


def _settings() -> McpServerSettings:
    return McpServerSettings(
        transport=McpTransport.STREAMABLE_HTTP,
        path="/mcp",
        bearer_token=SecretStr(_TEST_TOKEN),
    )


async def _request(
    app: ASGIApp,
    *,
    path: str,
    authorization: str | None = None,
) -> httpx.Response:
    headers = {}
    if authorization is not None:
        headers["Authorization"] = authorization

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.post(path, headers=headers)


@pytest.mark.asyncio
async def test_valid_bearer_token_forwards_mcp_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downstream = _DownstreamApp()
    compare_calls: list[tuple[str, str]] = []
    original_compare = secrets.compare_digest

    def compare_digest(supplied: str, expected: str) -> bool:
        compare_calls.append((supplied, expected))
        return original_compare(supplied, expected)

    monkeypatch.setattr(auth_module.secrets, "compare_digest", compare_digest)
    app = protect_streamable_http_app(downstream, _settings())

    response = await _request(
        app,
        path="/mcp",
        authorization=f"Bearer {_TEST_TOKEN}",
    )

    assert response.status_code == 200
    assert response.json()["forwarded"] is True
    assert downstream.paths == ["/mcp"]
    assert compare_calls == [(_TEST_TOKEN, _TEST_TOKEN)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Bearer invalid-token",
        f"Basic {_TEST_TOKEN}",
        "Bearer",
    ],
)
async def test_missing_or_invalid_credentials_return_same_safe_response(
    authorization: str | None,
) -> None:
    downstream = _DownstreamApp()
    app = protect_streamable_http_app(downstream, _settings())

    response = await _request(
        app,
        path="/mcp",
        authorization=authorization,
    )

    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}
    assert response.headers["www-authenticate"] == "Bearer"
    assert downstream.paths == []


@pytest.mark.asyncio
async def test_nested_mcp_path_is_also_protected() -> None:
    downstream = _DownstreamApp()
    app = protect_streamable_http_app(downstream, _settings())

    response = await _request(app, path="/mcp/session")

    assert response.status_code == 401
    assert downstream.paths == []


@pytest.mark.asyncio
async def test_health_endpoint_is_unauthenticated_and_process_only() -> None:
    downstream = _DownstreamApp()
    app = protect_streamable_http_app(downstream, _settings())

    response = await _request(app, path="/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert downstream.paths == []
    assert "dependency_details" not in response.text


def test_stdio_entrypoint_remains_parent_process_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transports: list[str] = []

    def run(*, transport: str) -> None:
        transports.append(transport)

    monkeypatch.setattr(server_module.server, "run", run)

    server_module.main(())

    assert transports == ["stdio"]


def test_http_boundary_rejects_stdio_settings() -> None:
    with pytest.raises(
        ValueError,
        match="requires streamable-http transport",
    ):
        protect_streamable_http_app(_DownstreamApp(), McpServerSettings())
