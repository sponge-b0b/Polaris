from __future__ import annotations

from dataclasses import dataclass

import pytest

from application.projections.workflow_outputs import (
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectionResolutionStatus,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRegistration,
    WorkflowOutputProjectorRequest,
)


@dataclass(frozen=True, slots=True)
class StubProjector:
    projector_name: str

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        return WorkflowOutputProjectionOutcome(
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            projector_name=self.projector_name,
            node_name=request.node_output.node_name,
            output_contract=request.node_output.output_contract or "unsupported",
            output_schema_version=request.node_output.output_schema_version or 1,
            source_fingerprint=request.source_fingerprint,
            records_written=1,
        )


def test_registry_resolves_projector_by_exact_contract_and_schema_version() -> None:
    projector = StubProjector(projector_name="technical_projector")
    registration = WorkflowOutputProjectorRegistration(
        projector_name="technical_projector",
        output_contract=" polaris.market.technical_analysis ",
        output_schema_version=1,
        projector=projector,
        supported_node_names=("technical_agent",),
    )
    registry = WorkflowOutputProjectionRegistry((registration,))

    resolution = registry.resolve(
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        node_name=" technical_agent ",
    )

    assert resolution.status is WorkflowOutputProjectionResolutionStatus.SUPPORTED
    assert resolution.supported is True
    assert resolution.projector is projector
    assert resolution.projector_name == "technical_projector"
    assert resolution.registration == registration


def test_registry_rejects_duplicate_contract_schema_registration() -> None:
    first = WorkflowOutputProjectorRegistration(
        projector_name="technical_projector",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        projector=StubProjector(projector_name="technical_projector"),
    )
    duplicate = WorkflowOutputProjectorRegistration(
        projector_name="other_projector",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        projector=StubProjector(projector_name="other_projector"),
    )

    with pytest.raises(ValueError, match="Duplicate workflow output projector"):
        WorkflowOutputProjectionRegistry((first, duplicate))


def test_registry_rejects_duplicate_projector_name() -> None:
    first = WorkflowOutputProjectorRegistration(
        projector_name="technical_projector",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        projector=StubProjector(projector_name="technical_projector"),
    )
    duplicate = WorkflowOutputProjectorRegistration(
        projector_name="technical_projector",
        output_contract="polaris.market.technical_regime",
        output_schema_version=1,
        projector=StubProjector(projector_name="technical_projector"),
    )

    with pytest.raises(ValueError, match="Duplicate workflow output projector name"):
        WorkflowOutputProjectionRegistry((first, duplicate))


def test_unknown_contract_returns_unsupported_resolution_not_error() -> None:
    registry = WorkflowOutputProjectionRegistry(
        (
            WorkflowOutputProjectorRegistration(
                projector_name="technical_projector",
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                projector=StubProjector(projector_name="technical_projector"),
            ),
        )
    )

    resolution = registry.resolve(
        output_contract="polaris.news.analysis",
        output_schema_version=1,
        node_name="news_agent",
    )

    assert (
        resolution.status
        is WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_CONTRACT
    )
    assert resolution.projector is None
    assert "Unsupported workflow output contract" in str(resolution.message)


def test_unsupported_schema_version_returns_visible_resolution() -> None:
    registry = WorkflowOutputProjectionRegistry(
        (
            WorkflowOutputProjectorRegistration(
                projector_name="technical_projector",
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                projector=StubProjector(projector_name="technical_projector"),
            ),
        )
    )

    resolution = registry.resolve(
        output_contract="polaris.market.technical_analysis",
        output_schema_version=2,
        node_name="technical_agent",
    )

    assert (
        resolution.status
        is WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_SCHEMA_VERSION
    )
    assert resolution.projector is None
    assert "supported versions: 1" in str(resolution.message)


def test_node_name_is_validation_constraint_not_primary_contract() -> None:
    registry = WorkflowOutputProjectionRegistry(
        (
            WorkflowOutputProjectorRegistration(
                projector_name="technical_projector",
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                projector=StubProjector(projector_name="technical_projector"),
                supported_node_names=("technical_agent",),
            ),
        )
    )

    wrong_node = registry.resolve(
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        node_name="portfolio_state_builder",
    )
    missing_contract = registry.resolve(
        output_contract=None,
        output_schema_version=1,
        node_name="technical_agent",
    )

    assert (
        wrong_node.status
        is WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_NODE_NAME
    )
    assert wrong_node.projector is None
    assert (
        missing_contract.status
        is WorkflowOutputProjectionResolutionStatus.UNSUPPORTED_CONTRACT
    )


def test_registration_validates_schema_and_projector_identity() -> None:
    with pytest.raises(ValueError, match="output_schema_version must be positive"):
        WorkflowOutputProjectorRegistration(
            projector_name="technical_projector",
            output_contract="polaris.market.technical_analysis",
            output_schema_version=0,
            projector=StubProjector(projector_name="technical_projector"),
        )

    with pytest.raises(ValueError, match="projector_name must match"):
        WorkflowOutputProjectorRegistration(
            projector_name="technical_projector",
            output_contract="polaris.market.technical_analysis",
            output_schema_version=1,
            projector=StubProjector(projector_name="other_projector"),
        )

    with pytest.raises(ValueError, match="supported_node_names cannot contain"):
        WorkflowOutputProjectorRegistration(
            projector_name="technical_projector",
            output_contract="polaris.market.technical_analysis",
            output_schema_version=1,
            projector=StubProjector(projector_name="technical_projector"),
            supported_node_names=("technical_agent", "technical_agent"),
        )
