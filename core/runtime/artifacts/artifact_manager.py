from __future__ import annotations

from typing import Any

from core.runtime.artifacts.artifact_ref import ArtifactKind
from core.runtime.artifacts.artifact_ref import ArtifactRef
from core.runtime.artifacts.artifact_serializers import (
    ArtifactSerializerRegistry,
)
from core.runtime.artifacts.artifact_store import ArtifactStore
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput


class ArtifactManager:
    """
    Canonical runtime artifact manager.

    Coordinates artifact persistence for RuntimeNodeOutput artifacts.
    """

    def __init__(
        self,
        artifact_store: ArtifactStore,
        serializer_registry: ArtifactSerializerRegistry | None = None,
    ) -> None:
        self.artifact_store = artifact_store
        self.serializer_registry = serializer_registry or ArtifactSerializerRegistry()

    # ========================================================
    # PERSIST NODE OUTPUT ARTIFACTS
    # ========================================================

    def persist_output_artifacts(
        self,
        context: RuntimeContext,
        node_name: str,
        output: RuntimeNodeOutput,
    ) -> tuple[RuntimeContext, RuntimeNodeOutput]:
        if not output.artifacts:
            return context, output

        updated_context = context
        artifact_refs: dict[str, ArtifactRef] = {}

        for artifact_name, artifact_payload in output.artifacts.items():
            artifact_ref = self.save_artifact(
                payload=artifact_payload,
                name=artifact_name,
                context=context,
                node_name=node_name,
            )

            artifact_refs[artifact_name] = artifact_ref

            updated_context = updated_context.add_artifact(
                key=self._artifact_context_key(
                    node_name=node_name,
                    artifact_name=artifact_name,
                ),
                artifact_ref=artifact_ref.to_dict(),
            )

        updated_output = RuntimeNodeOutput(
            success=output.success,
            skipped=output.skipped,
            stop_propagation=output.stop_propagation,
            outputs=dict(output.outputs),
            artifacts={name: ref.to_dict() for name, ref in artifact_refs.items()},
            emitted_events=list(output.emitted_events),
            errors=list(output.errors),
            execution_metadata=dict(output.execution_metadata),
            output_contract=output.output_contract,
            output_schema_version=output.output_schema_version,
        )

        return updated_context, updated_output

    # ========================================================
    # SAVE ARTIFACT
    # ========================================================

    def save_artifact(
        self,
        payload: Any,
        name: str,
        context: RuntimeContext,
        node_name: str | None = None,
        kind: ArtifactKind | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        serialized = self.serializer_registry.serialize(
            payload=payload,
            name=name,
        )

        artifact_kind = kind or serialized.kind

        merged_metadata = {
            **dict(serialized.metadata),
            **dict(metadata or {}),
        }

        return self.artifact_store.save_bytes(
            data=serialized.data,
            kind=artifact_kind,
            name=name,
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            runtime_id=context.runtime_id,
            node_name=node_name,
            content_type=serialized.content_type,
            metadata=merged_metadata,
        )

    # ========================================================
    # LOAD ARTIFACT
    # ========================================================

    def load_artifact_bytes(
        self,
        artifact_ref: ArtifactRef,
    ) -> bytes:
        return self.artifact_store.load_bytes(
            artifact_ref,
        )

    def load_artifact_text(
        self,
        artifact_ref: ArtifactRef,
    ) -> str:
        return self.artifact_store.load_text(
            artifact_ref,
        )

    def load_artifact_json(
        self,
        artifact_ref: ArtifactRef,
    ) -> Any:
        return self.artifact_store.load_json(
            artifact_ref,
        )

    def artifact_ref_from_dict(
        self,
        data: dict[str, Any],
    ) -> ArtifactRef:
        return ArtifactRef.from_dict(
            data,
        )

    def load_artifact_from_dict_bytes(
        self,
        data: dict[str, Any],
    ) -> bytes:
        return self.load_artifact_bytes(
            self.artifact_ref_from_dict(data),
        )

    def load_artifact_from_dict_text(
        self,
        data: dict[str, Any],
    ) -> str:
        return self.load_artifact_text(
            self.artifact_ref_from_dict(data),
        )

    def load_artifact_from_dict_json(
        self,
        data: dict[str, Any],
    ) -> Any:
        return self.load_artifact_json(
            self.artifact_ref_from_dict(data),
        )

    # ========================================================
    # INTERNALS
    # ========================================================

    def _artifact_context_key(
        self,
        node_name: str,
        artifact_name: str,
    ) -> str:
        return f"{node_name}.{artifact_name}"
