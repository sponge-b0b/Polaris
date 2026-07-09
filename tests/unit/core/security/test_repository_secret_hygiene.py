from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PRODUCTION_ROOTS = (
    "application",
    "config",
    "core",
    "integration",
    "intelligence",
    "interfaces",
    "mcp_server",
    "workflows",
)
_EXCLUDED_REPOSITORY_PREFIXES = (
    ".agent/",
    ".agents/",
    ".repowise/",
    "graphify-out/",
)
_CREDENTIAL_URI_PATTERN = re.compile(
    r"(?i)\b(?:postgres(?:ql)?(?:\+asyncpg)?|neo4j|bolt|redis|rediss|"
    r"mysql(?:\+\w+)?|amqp|mongodb(?:\+srv)?)://[^\s:/]+:[^\s@]+@"
)


def test_tracked_operational_files_do_not_embed_credentials_in_urls() -> None:
    findings: list[tuple[Path, int]] = []

    for path in _repository_text_files():
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if _CREDENTIAL_URI_PATTERN.search(line):
                findings.append((path.relative_to(_PROJECT_ROOT), line_number))

    assert findings == []


def test_production_settings_do_not_define_nonempty_secret_defaults() -> None:
    findings: list[tuple[Path, int, str]] = []

    for root_name in _PRODUCTION_ROOTS:
        root = _PROJECT_ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                target_name, value = _assignment(node)
                if target_name is None or value is None:
                    continue
                normalized_name = target_name.upper()
                if (
                    "PASSWORD" not in normalized_name
                    and "SECRET" not in normalized_name
                ):
                    continue
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    if value.value:
                        findings.append(
                            (
                                path.relative_to(_PROJECT_ROOT),
                                getattr(node, "lineno", 0),
                                target_name,
                            )
                        )

    assert findings == []


def test_env_example_declares_canonical_postgres_settings() -> None:
    env_example = (_PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    declared_names = {
        line.partition("=")[0]
        for line in env_example.splitlines()
        if line and not line.startswith("#") and "=" in line
    }

    assert {
        "POLARIS_DATABASE_URL",
        "POLARIS_POSTGRES_HOST",
        "POLARIS_POSTGRES_PORT",
        "POLARIS_POSTGRES_DB",
        "POLARIS_POSTGRES_USER",
        "POLARIS_POSTGRES_PASSWORD",
        "POLARIS_POSTGRES_DRIVER",
        "POLARIS_POSTGRES_ECHO",
        "POLARIS_POSTGRES_POOL_PRE_PING",
    } <= declared_names
    assert {
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    }.isdisjoint(declared_names)


def test_docker_compose_requires_environment_supplied_service_secrets() -> None:
    compose = (_PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert (
        "POSTGRES_PASSWORD: "
        "${POLARIS_POSTGRES_PASSWORD:?Set POLARIS_POSTGRES_PASSWORD in .env}"
    ) in compose
    assert "NEO4J_AUTH=${NEO4J_AUTH:?Set NEO4J_AUTH in .env}" in compose
    assert (
        "GF_SECURITY_ADMIN_PASSWORD="
        "${GRAFANA_ADMIN_PASSWORD:?Set GRAFANA_ADMIN_PASSWORD in .env}"
    ) in compose


def _repository_text_files() -> tuple[Path, ...]:
    result = subprocess.run(
        (
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ),
        cwd=_PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    paths: list[Path] = []
    for relative_name in result.stdout.decode().split("\0"):
        if not relative_name or relative_name.startswith(_EXCLUDED_REPOSITORY_PREFIXES):
            continue
        path = _PROJECT_ROOT / relative_name
        if not path.is_file():
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        paths.append(path)
    return tuple(paths)


def _assignment(node: ast.AST) -> tuple[str | None, ast.expr | None]:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name):
            return target.id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id, node.value
    return None, None
