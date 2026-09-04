import ast
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REPO_ROOT = Path(__file__).resolve().parents[3]
LITELLM_CONFIG_PATH = REPO_ROOT / "config" / "litellm" / "config.yaml"

# Approved by GitHub issue #15 / parent model-allocation spec #14.
APPROVED_POLARIS_LOCAL_BINDINGS = {
    "polaris-local-fast": "ollama_chat/qwen2.5:7b",
    "polaris-local-reasoning": "ollama_chat/qwen3.5:4b",
    "polaris-local-structured": "ollama_chat/qwen2.5-coder:7b",
    "polaris-local-synthesis": "ollama_chat/qwen2.5-coder:7b",
    "polaris-local-evaluation": "ollama_chat/qwen2.5-coder:7b",
    "polaris-local-optimization": "ollama_chat/qwen2.5-coder:7b",
}

CONCRETE_LOCAL_MODEL_MARKERS = (
    "ollama_chat/",
    "qwen2.5:7b",
    "qwen3.5:4b",
    "qwen3.5:9b",
    "qwen2.5-coder:7b",
    "deepseek-r1:8b",
)

PRODUCTION_SOURCE_DIRS = (
    "application",
    "config",
    "core",
    "domain",
    "integration",
    "intelligence",
    "interfaces",
    "mcp_server",
    "workflows",
)


def _load_litellm_model_bindings() -> dict[str, str]:
    raw_config = yaml.safe_load(LITELLM_CONFIG_PATH.read_text())
    model_list = raw_config["model_list"]
    return {
        entry["model_name"]: entry["litellm_params"]["model"] for entry in model_list
    }


def _string_literals(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    docstring_nodes: set[ast.Constant] = set()
    for statement in ast.walk(tree):
        if not isinstance(
            statement, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        if not statement.body or not isinstance(statement.body[0], ast.Expr):
            continue
        value = statement.body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            docstring_nodes.add(value)

    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node not in docstring_nodes
    ]


def test_litellm_config_binds_only_approved_canonical_polaris_aliases() -> None:
    bindings = _load_litellm_model_bindings()

    polaris_default_bindings = {
        alias: model
        for alias, model in bindings.items()
        if alias.startswith("polaris-local-")
    }

    assert polaris_default_bindings == APPROVED_POLARIS_LOCAL_BINDINGS


def test_deepseek_is_available_only_as_a_direct_challenger_alias() -> None:
    bindings = _load_litellm_model_bindings()

    polaris_default_bindings = {
        alias: model
        for alias, model in bindings.items()
        if alias.startswith("polaris-local-")
    }

    assert "ollama_chat/deepseek-r1:8b" not in polaris_default_bindings.values()
    assert bindings["deepseek-r1:8b"] == "ollama_chat/deepseek-r1:8b"


def test_python_architectural_defaults_do_not_hard_code_local_backends() -> None:
    violations: list[str] = []

    for source_dir in PRODUCTION_SOURCE_DIRS:
        for path in (REPO_ROOT / source_dir).rglob("*.py"):
            relative_path = path.relative_to(REPO_ROOT)
            for literal in _string_literals(path):
                for marker in CONCRETE_LOCAL_MODEL_MARKERS:
                    if marker in literal:
                        violations.append(f"{relative_path}: contains {marker}")

    assert violations == []
