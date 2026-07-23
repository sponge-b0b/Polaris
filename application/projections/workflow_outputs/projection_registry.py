from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, TypeVar

if TYPE_CHECKING:
    from application.projections.workflow_outputs.projection_models import (
        WorkflowOutputProjectionOutcome,
        WorkflowOutputProjectorRequest,
    )


class WorkflowOutputProjector(Protocol):
    """Marker protocol for workflow-output projectors registered by contract."""

    @property
    def projector_name(self) -> str:
        """Stable projector identity used for jobs, logging, and attribution."""
        ...

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        """Project one eligible archived node output into curated records."""
        ...


class WorkflowOutputProjectionResolutionStatus(StrEnum):
    """Exact registry resolution status for a workflow output contract."""

    SUPPORTED = "supported"
    UNSUPPORTED_CONTRACT = "unsupported_contract"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    UNSUPPORTED_NODE_NAME = "unsupported_node_name"


ProjectorT = TypeVar("ProjectorT", bound=WorkflowOutputProjector)


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectorRegistration:
    """Exact projector registration for one output contract and schema version."""

    projector_name: str
    output_contract: str
    output_schema_version: int
    projector: WorkflowOutputProjector
    supported_node_names: tuple[str, ...] = ()
    persists_quality_status: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "projector_name",
            _require_non_empty(self.projector_name, "projector_name"),
        )
        object.__setattr__(
            self,
            "output_contract",
            _require_non_empty(self.output_contract, "output_contract"),
        )
        if self.output_schema_version <= 0:
            raise ValueError("output_schema_version must be positive.")
        object.__setattr__(
            self,
            "supported_node_names",
            _clean_optional_names(self.supported_node_names),
        )
        projector_name = _require_non_empty(
            self.projector.projector_name,
            "projector.projector_name",
        )
        if projector_name != self.projector_name:
            raise ValueError(
                "projector_name must match projector.projector_name "
                f"({self.projector_name!r} != {projector_name!r})."
            )

    @property
    def key(self) -> tuple[str, int]:
        return (self.output_contract, self.output_schema_version)

    def supports_node_name(self, node_name: str | None) -> bool:
        if not self.supported_node_names or node_name is None:
            return True
        return _require_non_empty(node_name, "node_name") in self.supported_node_names


@dataclass(frozen=True, slots=True)
class WorkflowOutputProjectionResolution:
    """Result of resolving a node output to a registered projector."""

    status: WorkflowOutputProjectionResolutionStatus
    output_contract: str | None
    output_schema_version: int | None
    node_name: str | None = None
    registration: WorkflowOutputProjectorRegistration | None = None
    message: str | None = None

    @property
    def supported(self) -> bool:
        return self.status is WorkflowOutputProjectionResolutionStatus.SUPPORTED

    @property
    def projector(self) -> WorkflowOutputProjector | None:
        if self.registration is None:
            return None
        return self.registration.projector

    @property
    def projector_name(self) -> str | None:
        if self.registration is None:
            return None
        return self.registration.projector_name


class WorkflowOutputProjectionRegistry:
    """Exact workflow-output projector registry keyed by contract and version."""

    def __init__(
        self,
        registrations: Iterable[WorkflowOutputProjectorRegistration] = (),
    ) -> None:
        self._registrations_by_key: dict[
            tuple[str, int], WorkflowOutputProjectorRegistration
        ] = {}
        self._projector_names: set[str] = set()
        for registration in registrations:
            self.register(registration)

    def register(self, registration: WorkflowOutputProjectorRegistration) -> None:
        """Register one projector, failing fast on duplicate identities."""
        if registration.key in self._registrations_by_key:
            raise ValueError(
                "Duplicate workflow output projector registration for "
                f"{registration.output_contract!r} schema "
                f"{registration.output_schema_version}."
            )
        if registration.projector_name in self._projector_names:
            raise ValueError(
                "Duplicate workflow output projector name: "
                f"{registration.projector_name!r}."
            )
        self._registrations_by_key[registration.key] = registration
        self._projector_names.add(registration.projector_name)

    def resolve(
        self,
        *,
        output_contract: str | None,
        output_schema_version: int | None,
        node_name: str | None = None,
    ) -> WorkflowOutputProjectionResolution:
        """Resolve by exact contract/version with optional node validation."""
        cleaned_contract = _clean_optional(output_contract)
        cleaned_node_name = _clean_optional(node_name)
        if cleaned_contract is None:
            return WorkflowOutputProjectionResolution(
                status=WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_CONTRACT,
                output_contract=None,
                output_schema_version=output_schema_version,
                node_name=cleaned_node_name,
                message="Workflow output has no output contract.",
            )

        supported_versions = self.supported_schema_versions(cleaned_contract)
        if not supported_versions:
            return WorkflowOutputProjectionResolution(
                status=WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_CONTRACT,
                output_contract=cleaned_contract,
                output_schema_version=output_schema_version,
                node_name=cleaned_node_name,
                message=f"Unsupported workflow output contract: {cleaned_contract}.",
            )

        if output_schema_version is None or output_schema_version <= 0:
            return WorkflowOutputProjectionResolution(
                status=WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_SCHEMA_VERSION,
                output_contract=cleaned_contract,
                output_schema_version=output_schema_version,
                node_name=cleaned_node_name,
                message=(
                    "Workflow output has an unsupported schema version for "
                    f"contract {cleaned_contract}."
                ),
            )

        registration = self._registrations_by_key.get(
            (cleaned_contract, output_schema_version)
        )
        if registration is None:
            versions = ", ".join(str(version) for version in supported_versions)
            return WorkflowOutputProjectionResolution(
                status=WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_SCHEMA_VERSION,
                output_contract=cleaned_contract,
                output_schema_version=output_schema_version,
                node_name=cleaned_node_name,
                message=(
                    f"Unsupported schema version {output_schema_version} for "
                    f"contract {cleaned_contract}; supported versions: {versions}."
                ),
            )

        if not registration.supports_node_name(cleaned_node_name):
            nodes = ", ".join(registration.supported_node_names)
            return WorkflowOutputProjectionResolution(
                status=WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_NODE_NAME,
                output_contract=cleaned_contract,
                output_schema_version=output_schema_version,
                node_name=cleaned_node_name,
                message=(
                    f"Node {cleaned_node_name!r} is not supported by projector "
                    f"{registration.projector_name}; supported nodes: {nodes}."
                ),
            )

        return WorkflowOutputProjectionResolution(
            status=WorkflowOutputProjectionResolutionStatus.SUPPORTED,
            output_contract=cleaned_contract,
            output_schema_version=output_schema_version,
            node_name=cleaned_node_name,
            registration=registration,
            message="Workflow output projector resolved.",
        )

    def supported_schema_versions(self, output_contract: str) -> tuple[int, ...]:
        cleaned_contract = _require_non_empty(output_contract, "output_contract")
        return tuple(
            sorted(
                version
                for contract, version in self._registrations_by_key
                if contract == cleaned_contract
            )
        )

    def registrations(self) -> tuple[WorkflowOutputProjectorRegistration, ...]:
        return tuple(self._registrations_by_key.values())


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned


def _clean_optional_names(names: Iterable[str]) -> tuple[str, ...]:
    cleaned = tuple(_require_non_empty(name, "supported_node_name") for name in names)
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("supported_node_names cannot contain duplicates.")
    return cleaned


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned
