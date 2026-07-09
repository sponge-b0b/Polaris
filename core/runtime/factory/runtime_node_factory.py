from __future__ import annotations

from typing import Any, Type

from core.runtime.contracts.runtime_node import RuntimeNode


class RuntimeNodeFactory:
    """
    DI-friendly RuntimeNode factory.
    """

    def __init__(
        self,
        container: Any | None = None,
    ) -> None:
        self.container = container
        self._registry: dict[str, Type[RuntimeNode]] = {}

    def register(
        self,
        node_type: Type[RuntimeNode],
        name: str | None = None,
        overwrite: bool = False,
    ) -> None:
        if not issubclass(node_type, RuntimeNode):
            raise TypeError(f"{node_type} must inherit RuntimeNode.")

        key = name or node_type.node_name

        if not key.strip():
            raise ValueError("Runtime node registration name cannot be empty.")

        if key in self._registry and not overwrite:
            raise ValueError(f"Runtime node already registered: {key}")

        self._registry[key] = node_type

    def register_many(
        self,
        node_types: list[Type[RuntimeNode]],
        overwrite: bool = False,
    ) -> None:
        for node_type in node_types:
            self.register(
                node_type=node_type,
                overwrite=overwrite,
            )

    def create(
        self,
        name: str,
    ) -> RuntimeNode:
        node_type = self._registry.get(name)

        if node_type is None:
            raise KeyError(f"Runtime node not registered: {name}")

        return self.create_from_type(
            node_type,
        )

    def create_from_type(
        self,
        node_type: Type[RuntimeNode],
    ) -> RuntimeNode:
        if not issubclass(node_type, RuntimeNode):
            raise TypeError(f"{node_type} must inherit RuntimeNode.")

        if self.container is not None:
            resolved = self._resolve_from_container(
                node_type,
            )

            if resolved is not None:
                if not isinstance(resolved, RuntimeNode):
                    raise TypeError(
                        "DI container resolved object that is not "
                        f"a RuntimeNode: {type(resolved)}"
                    )

                return resolved

        return node_type()

    def exists(
        self,
        name: str,
    ) -> bool:
        return name in self._registry

    def get_node_type(
        self,
        name: str,
    ) -> Type[RuntimeNode]:
        node_type = self._registry.get(name)

        if node_type is None:
            raise KeyError(f"Runtime node not registered: {name}")

        return node_type

    def list_nodes(
        self,
    ) -> list[str]:
        return sorted(
            self._registry.keys(),
        )

    def clear(
        self,
    ) -> None:
        self._registry.clear()

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "node_count": len(self._registry),
            "nodes": {
                name: {
                    "node_class": node_type.__name__,
                    "node_module": node_type.__module__,
                    "node_type": node_type.node_type,
                    "node_version": node_type.node_version,
                }
                for name, node_type in sorted(
                    self._registry.items(),
                    key=lambda item: item[0],
                )
            },
        }

    def _resolve_from_container(
        self,
        node_type: Type[RuntimeNode],
    ) -> Any | None:

        container = self.container

        if container is None:
            return None

        if hasattr(container, "get"):
            return container.get(
                node_type,
            )

        if hasattr(container, "resolve"):
            return container.resolve(
                node_type,
            )

        return None
