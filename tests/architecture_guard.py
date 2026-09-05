"""Static guardrails for Polaris's mechanically observable architecture rules."""

from __future__ import annotations

import ast
import importlib.util
import os
import re
from dataclasses import dataclass
from pathlib import Path

LAYERS = {"domain", "application", "infrastructure", "interfaces"}
FORBIDDEN = {
    "domain": {"application", "infrastructure", "interfaces"},
    "application": {"infrastructure", "interfaces"},
    "infrastructure": {"interfaces"},
    "interfaces": {"infrastructure"},
}
INTERFACE_MODULES = {"click", "django", "fastapi", "flask", "starlette", "typer"}
VENDORS = {
    "persistence": {"alembic", "asyncpg", "psycopg", "psycopg2", "sqlalchemy"},
    "model-provider": {
        "anthropic",
        "google.genai",
        "google.generativeai",
        "litellm",
        "ollama",
        "openai",
        "vllm",
    },
    "external-source": {
        "alpaca",
        "alpaca_trade_api",
        "finnhub",
        "fmpsdk",
        "fredapi",
        "massive",
        "newsapi",
        "polygon",
        "yfinance",
    },
    "identity": {"auth0", "keycloak", "okta"},
    "observability": {"opentelemetry", "prometheus_client", "sentry_sdk", "structlog"},
}
TECHNICAL_IDS = {
    "executionid",
    "executionidentifier",
    "jobid",
    "jobidentifier",
    "modelid",
    "modelidentifier",
    "nodeid",
    "nodeidentifier",
    "outputid",
    "outputidentifier",
    "reportid",
    "reportidentifier",
    "runid",
    "runidentifier",
    "runtimeid",
    "runtimeidentifier",
    "spanid",
    "spanidentifier",
    "traceid",
    "traceidentifier",
    "workflowid",
    "workflowidentifier",
}
LOADERS = {
    "__import__",
    "importlib.import_module",
    "importlib.machinery.SourceFileLoader",
    "importlib.util.spec_from_file_location",
    "runpy.run_module",
    "runpy.run_path",
}
IGNORED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".worktrees",
    ".tox",
    ".nox",
    "__pycache__",
    "build",
    "dist",
    "legacy",
    "venv",
}


@dataclass(frozen=True, slots=True)
class Violation:
    source: str
    line: int
    rule: str
    detail: str

    def render(self) -> str:
        return f"{self.source}:{self.line}: {self.rule}: {self.detail}"


def check_repository(repo_root: Path) -> tuple[Violation, ...]:
    root = repo_root.resolve()
    violations = [
        violation
        for path in _python_files(root)
        for violation in _check_file(root, path)
    ]
    return tuple(
        sorted(
            set(violations),
            key=lambda item: (item.source, item.line, item.rule, item.detail),
        )
    )


def _python_files(root: Path) -> tuple[Path, ...]:
    files = {
        path
        for base in (root / "src" / "polaris", root / "tests")
        if base.exists()
        for path in base.rglob("*.py")
    }
    for current, directories, names in os.walk(root):
        directories[:] = [name for name in directories if name not in IGNORED_DIRS]
        current_path = Path(current)
        if "migrations" in current_path.relative_to(root).parts:
            files.update(current_path / name for name in names if name.endswith(".py"))
    return tuple(sorted(path for path in files if path.is_file()))


def _check_file(root: Path, path: Path) -> list[Violation]:
    source = path.relative_to(root).as_posix()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=source)
    except (OSError, UnicodeError, SyntaxError) as exc:
        line = exc.lineno if isinstance(exc, SyntaxError) and exc.lineno else 1
        return [
            Violation(
                source,
                line,
                "ARCH-SCAN",
                f"cannot inspect Python file: {exc}",
            )
        ]

    guard = _Guard(root, path, tree)
    guard.visit(tree)
    return guard.violations


class _Guard(ast.NodeVisitor):
    def __init__(self, root: Path, path: Path, tree: ast.Module) -> None:
        self.source = path.relative_to(root).as_posix()
        self.layer = _layer(root, path)
        self.migration = "migrations" in path.relative_to(root).parts
        self.package = _package(root, path)
        imports = _import_aliases(tree.body, self.package)
        self.import_scopes = [imports]
        self.loader_scopes = [_loader_aliases(tree.body, imports)]
        self.technical_ids = _technical_names(tree.body)
        self.in_investment_decision = False
        self.violations: list[Violation] = []

    def fail(self, node: ast.AST, rule: str, detail: str) -> None:
        line = node.lineno if hasattr(node, "lineno") else 1
        self.violations.append(Violation(self.source, line, rule, detail))

    def visit_import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_import(node, alias.name)

    def visit_import_from(self, node: ast.ImportFrom) -> None:
        base = _from_module(self.package, node)
        for alias in node.names:
            target = base if alias.name == "*" else _join(base, alias.name)
            if target:
                self._check_import(node, target)

    def _check_import(self, node: ast.AST, target: str) -> None:
        if _prefix(target, {"legacy"}):
            self.fail(node, "ARCH-LEGACY", f"current code depends on {target!r}")
            if self.migration:
                self.fail(
                    node,
                    "ARCH-MIGRATION-LEGACY",
                    f"migration depends on {target!r}",
                )

        imported_layer = _imported_layer(target)
        outward = self.layer and imported_layer in FORBIDDEN[self.layer]
        interface_vendor = self.layer != "interfaces" and _prefix(
            target, INTERFACE_MODULES
        )
        if outward or interface_vendor:
            dependency = imported_layer or "interface implementation"
            self.fail(
                node,
                "ARCH-LAYER",
                f"{self.layer} may not depend on {dependency}: {target!r}",
            )

        family = _vendor_family(target)
        if self.layer in {"domain", "application"} and family:
            self.fail(
                node,
                "ARCH-INWARD-VENDOR",
                f"{self.layer} may not depend on {family} representation {target!r}",
            )
        elif self.layer == "interfaces" and family:
            self.fail(
                node,
                "ARCH-INTERFACE-INFRASTRUCTURE",
                (
                    "interfaces may not bypass application through "
                    f"{family} implementation {target!r}"
                ),
            )

    def visit_call(self, node: ast.Call) -> None:
        loader = _resolve(node.func, self.import_scopes[-1])
        for scope in reversed(self.loader_scopes):
            loader = scope.get(loader or "", loader)
        if loader in LOADERS:
            legacy = _legacy_literal(node)
            if legacy:
                self.fail(
                    node,
                    "ARCH-LEGACY-DYNAMIC",
                    f"runtime loader {loader!r} references {legacy!r}",
                )
                if self.migration:
                    self.fail(
                        node,
                        "ARCH-MIGRATION-LEGACY",
                        f"migration runtime-loads {legacy!r}",
                    )
        self.generic_visit(node)

    def visit_assign(self, node: ast.Assign) -> None:
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if any(_decision_name(name) for name in names):
            self._check_identity(node, "InvestmentDecisionId", node.value)
        if self.in_investment_decision and "id" in {_norm(name) for name in names}:
            self._check_identity(node, "InvestmentDecision.id", node.value)
        self.generic_visit(node)

    def visit_ann_assign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            name = node.target.id
            value = (
                node.value
                if _norm(ast.unparse(node.annotation)) == "typealias"
                else node.annotation
            )
            if _decision_name(name):
                self._check_identity(node, name, value)
            if self.in_investment_decision and _norm(name) == "id":
                self._check_identity(node, "InvestmentDecision.id", node.annotation)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        if _decision_name(node.arg) and node.annotation is not None:
            self._check_identity(node, node.arg, node.annotation)
        self.generic_visit(node)

    def visit_function_def(self, node: ast.FunctionDef) -> None:
        self._visit_scope(node, node.body)

    def visit_async_function_def(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_scope(node, node.body)

    def visit_class_def(self, node: ast.ClassDef) -> None:
        if _norm(node.name) == "investmentdecisionid":
            for base in node.bases:
                self._check_identity(node, node.name, base)

        previous_flag = self.in_investment_decision
        previous_ids = self.technical_ids
        self.in_investment_decision = _norm(node.name) == "investmentdecision"
        if self.in_investment_decision:
            self.technical_ids = _technical_names(node.body, previous_ids)
        self._visit_scope(node, node.body)
        self.in_investment_decision = previous_flag
        self.technical_ids = previous_ids

    def _visit_scope(self, node: ast.AST, body: list[ast.stmt]) -> None:
        imports = _import_aliases(body, self.package, self.import_scopes[-1])
        loaders = _loader_aliases(body, imports, self.loader_scopes[-1])
        self.import_scopes.append(imports)
        self.loader_scopes.append(loaders)
        self.generic_visit(node)
        self.loader_scopes.pop()
        self.import_scopes.pop()

    def visit_type_alias(self, node: ast.TypeAlias) -> None:
        if _decision_name(node.name.id):
            self._check_identity(node, node.name.id, node.value)
        self.generic_visit(node)

    def visit_name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self._check_migration_schema(node, node.id)

    def visit_attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load):
            self._check_migration_schema(node, _dotted(node) or node.attr)
        self.generic_visit(node)

    visit_Import = visit_import
    visit_ImportFrom = visit_import_from
    visit_Call = visit_call
    visit_Assign = visit_assign
    visit_AnnAssign = visit_ann_assign
    visit_FunctionDef = visit_function_def
    visit_AsyncFunctionDef = visit_async_function_def
    visit_ClassDef = visit_class_def
    visit_TypeAlias = visit_type_alias
    visit_Name = visit_name
    visit_Attribute = visit_attribute

    def _check_identity(self, node: ast.AST, name: str, value: ast.AST) -> None:
        if _technical(value, self.technical_ids):
            self.fail(
                node,
                "ARCH-DECISION-IDENTITY",
                f"{name} uses technical identity {ast.unparse(value)!r}",
            )

    def _check_migration_schema(self, node: ast.AST, text: str) -> None:
        if not self.migration:
            return
        parts = {_norm(part) for part in text.split(".")}
        legacy_objects = {"legacymetadata", "legacyschema", "legacytable"}
        explicit_legacy_member = "legacy" in parts and bool(
            parts & {"metadata", "schema", "table"}
        )
        if parts & legacy_objects or explicit_legacy_member:
            self.fail(
                node,
                "ARCH-MIGRATION-LEGACY-SCHEMA",
                f"migration reuses legacy schema object {text!r}",
            )


def _layer(root: Path, path: Path) -> str | None:
    try:
        first = path.relative_to(root / "src" / "polaris").parts[0]
    except ValueError:
        return None
    return first if first in LAYERS else None


def _package(root: Path, path: Path) -> str | None:
    try:
        relative = path.relative_to(root / "src" / "polaris")
    except ValueError:
        return None
    return ".".join(("polaris", *relative.parent.parts))


def _imported_layer(target: str) -> str | None:
    parts = target.split(".")
    if len(parts) > 1 and parts[0] == "polaris" and parts[1] in LAYERS:
        return parts[1]
    return None


def _vendor_family(target: str) -> str | None:
    return next(
        (family for family, modules in VENDORS.items() if _prefix(target, modules)),
        None,
    )


def _prefix(target: str, prefixes: set[str]) -> bool:
    return any(
        target == prefix or target.startswith(f"{prefix}.")
        for prefix in prefixes
    )


def _from_module(package: str | None, node: ast.ImportFrom) -> str:
    if node.level == 0 or not package:
        return node.module or ""
    try:
        return importlib.util.resolve_name(
            "." * node.level + (node.module or ""),
            package,
        )
    except (ImportError, ValueError):
        return node.module or ""


def _import_aliases(
    body: list[ast.stmt],
    package: str | None,
    inherited: dict[str, str] | None = None,
) -> dict[str, str]:
    aliases = dict(inherited or {})
    for node in body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                aliases[bound] = alias.name if alias.asname else bound
        elif isinstance(node, ast.ImportFrom):
            base = _from_module(package, node)
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = _join(base, alias.name)
    return aliases


def _loader_aliases(
    body: list[ast.stmt],
    imports: dict[str, str],
    inherited: dict[str, str] | None = None,
) -> dict[str, str]:
    bindings = [binding for node in body for binding in _loader_bindings(node)]
    aliases = dict(inherited or {})
    changed = True
    while changed:
        changed = False
        for name, value in bindings:
            resolved = _resolve(value, imports)
            resolved = aliases.get(resolved or "", resolved)
            if resolved in LOADERS and aliases.get(name) != resolved:
                aliases[name] = resolved
                changed = True
    return aliases


def _loader_bindings(node: ast.stmt) -> list[tuple[str, ast.expr]]:
    if isinstance(node, ast.Assign):
        return [
            (target.id, node.value)
            for target in node.targets
            if isinstance(target, ast.Name)
        ]
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    ):
        return [(node.target.id, node.value)]
    return []


def _technical_names(
    body: list[ast.stmt],
    inherited: set[str] | None = None,
) -> set[str]:
    names = set(inherited or TECHNICAL_IDS)
    bindings = [_type_binding(node) for node in body]
    bindings = [binding for binding in bindings if binding is not None]
    changed = True
    while changed:
        changed = False
        for name, values in bindings:
            if name not in names and any(_technical(value, names) for value in values):
                names.add(name)
                changed = True
    return names


def _type_binding(node: ast.stmt) -> tuple[str, tuple[ast.AST, ...]] | None:
    if isinstance(node, ast.Assign):
        return _assign_type_binding(node)
    if isinstance(node, ast.AnnAssign):
        return _annassign_type_binding(node)
    if isinstance(node, ast.ClassDef):
        return _norm(node.name), tuple(node.bases)
    if isinstance(node, ast.TypeAlias):
        return _norm(node.name.id), (node.value,)
    return None


def _assign_type_binding(
    node: ast.Assign,
) -> tuple[str, tuple[ast.AST, ...]] | None:
    targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
    if len(targets) != 1:
        return None
    return _norm(targets[0]), (node.value,)


def _annassign_type_binding(
    node: ast.AnnAssign,
) -> tuple[str, tuple[ast.AST, ...]] | None:
    if not isinstance(node.target, ast.Name) or node.value is None:
        return None
    return _norm(node.target.id), (node.value,)



def _technical(node: ast.AST, technical_names: set[str]) -> bool:
    tokens: set[str] = set()
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            tokens.add(_norm(item.id))
        elif isinstance(item, ast.Attribute):
            tokens.add(_norm(item.attr))
        elif isinstance(item, ast.Constant) and isinstance(item.value, str):
            tokens.update(_norm(token) for token in re.findall(r"\w+", item.value))
    return bool(tokens & technical_names)


def _resolve(node: ast.AST, aliases: dict[str, str]) -> str | None:
    dotted = _dotted(node)
    if not dotted:
        return None
    root, *tail = dotted.split(".")
    return ".".join((aliases.get(root, root), *tail))


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _legacy_literal(node: ast.Call) -> str | None:
    for value in (*node.args, *(keyword.value for keyword in node.keywords)):
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        normalized = value.value.replace("\\", "/")
        dotted = normalized.lstrip("./").replace("/", ".")
        if (
            dotted == "legacy"
            or dotted.startswith("legacy.")
            or "/legacy/" in normalized
        ):
            return value.value
    return None


def _decision_name(name: str) -> bool:
    return _norm(name) in {"decisionid", "investmentdecisionid"}


def _join(left: str, right: str) -> str:
    return ".".join(part for part in (left, right) if part)


def _norm(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).lower()
