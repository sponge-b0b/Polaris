from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_PRODUCTION_ROOTS = (
    "application",
    "core",
    "integration",
    "intelligence",
    "interfaces",
)
_CANONICAL_EVENT_MODULE = "core.telemetry.events.telemetry_event"
_CANONICAL_EVENT_PATH = Path("core/telemetry/events/telemetry_event.py")
_OPERATIONAL_LOG_METHODS = frozenset(
    {
        "critical",
        "error",
        "exception",
        "warning",
    }
)

# Direct operational logging is exceptional. These boundaries either cannot
# safely emit canonical telemetry or report a bounded child-source degradation
# that is not the parent provider/service lifecycle result.
_ALLOWED_DIRECT_OPERATIONAL_LOGGING: dict[Path, frozenset[str]] = {
    Path("core/telemetry/collectors/telemetry_collector.py"): frozenset({"error"}),
    Path("core/telemetry/emitters/bootstrap_configuration_telemetry.py"): frozenset(
        {"critical", "exception"}
    ),
    Path("core/workflow/execution/workflow_engine.py"): frozenset({"exception"}),
    Path("integration/clients/market_data/yfinance_data_client.py"): frozenset(
        {"warning"}
    ),
    Path("integration/clients/market_events/fed_events_client.py"): frozenset(
        {"warning"}
    ),
    Path("integration/clients/market_events/fred_events_client.py"): frozenset(
        {"warning"}
    ),
    Path("integration/clients/news/finnhub_news_client.py"): frozenset({"warning"}),
    Path("integration/providers/macro/live_macro_provider.py"): frozenset({"warning"}),
    Path("interfaces/cli/services/rag_command_service.py"): frozenset({"exception"}),
}


def test_production_uses_one_canonical_telemetry_event_contract() -> None:
    definitions: list[Path] = []
    invalid_imports: list[tuple[Path, int, str | None]] = []

    for path, tree in _production_syntax_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "TelemetryEvent":
                definitions.append(path)
            if not isinstance(node, ast.ImportFrom):
                continue
            if not any(alias.name == "TelemetryEvent" for alias in node.names):
                continue
            if node.module != _CANONICAL_EVENT_MODULE:
                invalid_imports.append((path, node.lineno, node.module))

    assert definitions == [_CANONICAL_EVENT_PATH]
    assert invalid_imports == []


def test_direct_operational_logging_is_restricted_to_documented_boundaries() -> None:
    unexpected: dict[Path, set[str]] = defaultdict(set)

    for path, tree in _production_syntax_trees():
        logger_names = _module_logger_names(tree)
        allowed_methods = _ALLOWED_DIRECT_OPERATIONAL_LOGGING.get(path, frozenset())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            if node.func.attr not in _OPERATIONAL_LOG_METHODS:
                continue
            if not isinstance(node.func.value, ast.Name):
                continue
            if node.func.value.id not in logger_names:
                continue
            if node.func.attr not in allowed_methods:
                unexpected[path].add(node.func.attr)

    assert dict(unexpected) == {}


def _production_syntax_trees() -> tuple[tuple[Path, ast.Module], ...]:
    parsed: list[tuple[Path, ast.Module]] = []
    for root_name in _PRODUCTION_ROOTS:
        root = _PROJECT_ROOT / root_name
        for absolute_path in sorted(root.rglob("*.py")):
            relative_path = absolute_path.relative_to(_PROJECT_ROOT)
            parsed.append(
                (
                    relative_path,
                    ast.parse(
                        absolute_path.read_text(encoding="utf-8"),
                        filename=str(relative_path),
                    ),
                )
            )
    return tuple(parsed)


def _module_logger_names(tree: ast.Module) -> frozenset[str]:
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Attribute):
            continue
        if value.func.attr != "getLogger":
            continue
        if not isinstance(value.func.value, ast.Name):
            continue
        if value.func.value.id != "logging":
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        names.update(target.id for target in targets if isinstance(target, ast.Name))
    return frozenset(names)
