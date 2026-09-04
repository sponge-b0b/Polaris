"""Authentication boundary for the Polaris MCP HTTP transport."""

from __future__ import annotations

import secrets

from pydantic import SecretStr
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from mcp_server.settings import McpServerSettings, McpTransport

_HEALTH_PATH = "/healthz"
_UNAUTHORIZED_RESPONSE = {"error": "unauthorized"}


class McpHttpAuthenticationBoundary:
    """Protect MCP HTTP requests while exposing process-only readiness."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        bearer_token: SecretStr,
        mcp_path: str,
    ) -> None:
        self._app = app
        self._expected_token = bearer_token.get_secret_value()
        self._mcp_path = mcp_path.rstrip("/") or "/"

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == _HEALTH_PATH:
            await JSONResponse({"status": "ready"})(scope, receive, send)
            return

        if self._is_mcp_path(path) and not self._is_authorized(scope):
            await JSONResponse(
                _UNAUTHORIZED_RESPONSE,
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
            return

        await self._app(scope, receive, send)

    def _is_mcp_path(self, path: str) -> bool:
        return path == self._mcp_path or path.startswith(f"{self._mcp_path}/")

    def _is_authorized(self, scope: Scope) -> bool:
        authorization = Headers(scope=scope).get("authorization")
        if authorization is None:
            return False

        scheme, separator, supplied_token = authorization.partition(" ")
        return (
            bool(separator)
            and scheme.lower() == "bearer"
            and bool(supplied_token)
            and secrets.compare_digest(supplied_token, self._expected_token)
        )


def protect_streamable_http_app(
    app: ASGIApp,
    settings: McpServerSettings,
) -> ASGIApp:
    """Apply the configured bearer-token boundary to an MCP HTTP app."""

    if settings.transport is not McpTransport.STREAMABLE_HTTP:
        raise ValueError("MCP HTTP authentication requires streamable-http transport.")
    if settings.bearer_token is None:  # Defensive narrowing after settings validation.
        raise ValueError("MCP HTTP authentication requires a bearer token.")

    return McpHttpAuthenticationBoundary(
        app,
        bearer_token=settings.bearer_token,
        mcp_path=settings.path,
    )


__all__ = [
    "McpHttpAuthenticationBoundary",
    "protect_streamable_http_app",
]
