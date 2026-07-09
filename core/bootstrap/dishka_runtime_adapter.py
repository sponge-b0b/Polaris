from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any
from typing import Type

from core.runtime.contracts.runtime_node import RuntimeNode


class DishkaRuntimeAdapter:
    """
    Thin adapter around a Dishka container.

    PURPOSE
    ============================================================
    Keeps Dishka-specific dependency resolution outside runtime core.

    Runtime core depends on RuntimeNodeFactory.
    RuntimeNodeFactory may depend on this adapter.

    EXPECTED DISHKA BEHAVIOR
    ============================================================
    Dishka containers expose .get(Type) for dependency resolution.
    For shorter-lived scopes, Dishka supports entering a sub-container
    with container() as a context manager, then resolving via .get(Type).
    """

    def __init__(
        self,
        container: Any,
        use_scope: bool = False,
    ) -> None:
        self.container = container
        self.use_scope = use_scope

    def get(
        self,
        node_type: Type[RuntimeNode],
    ) -> RuntimeNode:
        """
        Resolve RuntimeNode from Dishka container.
        """

        resolved = self._resolve(
            node_type,
        )

        if not isinstance(
            resolved,
            RuntimeNode,
        ):
            raise TypeError(
                "Dishka resolved object that is not a RuntimeNode. "
                f"node_type={node_type}, resolved_type={type(resolved)}"
            )

        return resolved

    def resolve(
        self,
        node_type: Type[RuntimeNode],
    ) -> RuntimeNode:
        """
        Alias for get(), matching alternate container adapter conventions.
        """

        return self.get(
            node_type,
        )

    def _resolve(
        self,
        node_type: Type[RuntimeNode],
    ) -> Any:
        if self.use_scope:
            scoped_container = self.container()

            if not isinstance(
                scoped_container,
                AbstractContextManager,
            ):
                raise TypeError("Dishka scoped container must be a context manager.")

            with scoped_container as request_container:
                return request_container.get(
                    node_type,
                )

        return self.container.get(
            node_type,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "adapter": self.__class__.__name__,
            "container_type": self.container.__class__.__name__,
            "use_scope": self.use_scope,
        }
